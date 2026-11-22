"""Generate the synthetic dataset: 3 JDs (TXT/PDF/DOCX), 12 resumes (PDF/DOCX) and edge-case files.

Usage (from backend/):  python -m scripts.generate_samples
"""
import html
import shutil
from pathlib import Path

import docx
import fitz
from docx.shared import Pt, RGBColor

from scripts.sample_content import JOB_DESCRIPTIONS, RESUMES

ROOT = Path(__file__).resolve().parents[2] / "sample_data"
CSS = """
* { font-family: sans-serif; }
h1 { font-size: 20px; color: #0b1f44; margin-bottom: 2px; }
h2 { font-size: 13px; color: #1d4ed8; border-bottom: 1px solid #cbd5e1; margin-top: 12px; margin-bottom: 4px; }
p, li { font-size: 10.5px; line-height: 1.35; margin: 1px 0; }
.contact { color: #475569; font-size: 10px; }
.role { font-weight: bold; }
"""


def resume_html(r: dict) -> str:
    e = html.escape
    parts = [f"<h1>{e(r['name'])}</h1>",
             f"<p class='contact'>{e(r['email'])} | {e(r['phone'])} | linkedin.com/in/{r['name'].lower().replace(' ', '-')}</p>"]
    for line in r.get("personal", []):
        parts.append(f"<p class='contact'>{e(line)}</p>")
    parts += ["<h2>Professional Summary</h2>", f"<p>{e(r['summary'])}</p>", "<h2>Work Experience</h2>"]
    for title, company, dates, bullets in r["experience"]:
        parts.append(f"<p class='role'>{e(title)} | {e(company)} | {e(dates)}</p><ul>")
        parts += [f"<li>{e(b)}</li>" for b in bullets]
        parts.append("</ul>")
    parts += ["<h2>Technical Skills</h2>", f"<p>{e(r['skills'])}</p>", "<h2>Education</h2>"]
    for degree, inst, dates in r["education"]:
        parts.append(f"<p><b>{e(degree)}</b></p><p>{e(inst)} | {e(dates)}</p>")
    if r.get("projects"):
        parts.append("<h2>Projects</h2><ul>" + "".join(f"<li>{e(p)}</li>" for p in r["projects"]) + "</ul>")
    if r.get("certifications"):
        parts.append("<h2>Certifications</h2><ul>" + "".join(f"<li>{e(c)}</li>" for c in r["certifications"]) + "</ul>")
    return "".join(parts)


def write_pdf(path: Path, body_html: str) -> None:
    story = fitz.Story(html=body_html, user_css=CSS)
    writer = fitz.DocumentWriter(str(path))
    mediabox = fitz.paper_rect("a4")
    where = mediabox + (48, 48, -48, -48)
    more = True
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()


def _heading(d: docx.Document, text: str) -> None:
    p = d.add_paragraph()
    run = p.add_run(text.upper())
    run.bold, run.font.size = True, Pt(12)
    run.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)


def write_resume_docx(path: Path, r: dict) -> None:
    d = docx.Document()
    title = d.add_paragraph()
    run = title.add_run(r["name"])
    run.bold, run.font.size = True, Pt(20)
    d.add_paragraph(f"{r['email']} | {r['phone']}")
    for line in r.get("personal", []):
        d.add_paragraph(line)
    _heading(d, "Summary")
    d.add_paragraph(r["summary"])
    _heading(d, "Professional Experience")
    for t, c, dates, bullets in r["experience"]:
        p = d.add_paragraph()
        p.add_run(f"{t} | {c} | {dates}").bold = True
        for b in bullets:
            d.add_paragraph(b, style="List Bullet")
    _heading(d, "Skills")
    d.add_paragraph(r["skills"])
    _heading(d, "Education")
    for degree, inst, dates in r["education"]:
        d.add_paragraph(degree)
        d.add_paragraph(f"{inst} | {dates}")
    if r.get("projects"):
        _heading(d, "Projects")
        for p in r["projects"]:
            d.add_paragraph(p, style="List Bullet")
    if r.get("certifications"):
        _heading(d, "Certifications")
        for c in r["certifications"]:
            d.add_paragraph(c, style="List Bullet")
    d.save(str(path))


def write_jd_docx(path: Path, text: str) -> None:
    d = docx.Document()
    for line in text.strip().split("\n"):
        d.add_paragraph(line.lstrip("- ").strip(), style="List Bullet" if line.startswith("- ") else None)
    d.save(str(path))


def jd_html(text: str) -> str:
    out = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        if line.startswith("- "):
            out.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.startswith("Job Title"):
            out.append(f"<h1>{html.escape(line)}</h1>")
        elif len(line) < 40 and not line.endswith("."):
            out.append(f"<h2>{html.escape(line)}</h2>")
        else:
            out.append(f"<p>{html.escape(line)}</p>")
    return "".join(out)


def make_edge_cases(folder: Path, resumes_dir: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "empty_file.pdf").write_bytes(b"")
    (folder / "corrupted_resume.docx").write_bytes(b"PK\x03\x04 this is not really a docx archive \x00\xff")
    (folder / "corrupted_resume.pdf").write_bytes(b"%PDF-1.4\n%garbage that is not a real pdf body\n")
    (folder / "unsupported_resume.txt").write_text("John Doe - Python developer. This format is not supported.")
    (folder / "renamed_image.pdf").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    # Blank PDF (valid, but no text at all)
    doc = fitz.open()
    doc.new_page()
    doc.save(str(folder / "blank_page.pdf"))
    doc.close()
    # Scanned PDF: render a real resume page to an image and embed only the image
    src = fitz.open(str(resumes_dir / "01_aarav_mehta_senior_python.pdf"))
    pix = src[0].get_pixmap(dpi=110)
    scanned = fitz.open()
    page = scanned.new_page(width=src[0].rect.width, height=src[0].rect.height)
    page.insert_image(page.rect, pixmap=pix)
    scanned.save(str(folder / "scanned_resume.pdf"))
    scanned.close()
    src.close()
    # Exact duplicate of an existing resume
    shutil.copy(resumes_dir / "02_priya_nair_python_flask.docx", folder / "duplicate_of_priya.docx")


def main() -> None:
    jd_dir, res_dir, edge_dir = ROOT / "jds", ROOT / "resumes", ROOT / "edge_cases"
    for d in (jd_dir, res_dir):
        d.mkdir(parents=True, exist_ok=True)

    for key, text in JOB_DESCRIPTIONS.items():
        (jd_dir / f"{key}.txt").write_text(text.strip() + "\n")
        write_pdf(jd_dir / f"{key}.pdf", jd_html(text))
        write_jd_docx(jd_dir / f"{key}.docx", text)

    for r in RESUMES:
        path = res_dir / r["_file"]
        if path.suffix == ".pdf":
            write_pdf(path, resume_html(r))
        else:
            write_resume_docx(path, r)

    make_edge_cases(edge_dir, res_dir)
    with open(ROOT / "README.md", "w") as f:
        f.write("# Synthetic sample data\n\nAll people, contact details and companies are fictional and were "
                "generated by `backend/scripts/generate_samples.py`.\n\n## Resumes\n\n| File | Intended profile |\n|---|---|\n")
        for r in RESUMES:
            f.write(f"| `{r['_file']}` | {r['_profile']} |\n")
        f.write("\n## Edge cases (`edge_cases/`)\n\nEmpty, corrupted PDF/DOCX, renamed image, blank PDF, "
                "scanned (image-only) PDF, unsupported `.txt` and an exact duplicate file. Upload them together "
                "with the resumes to see per-file error handling.\n\n## Job descriptions (`jds/`)\n\n"
                "Python Developer, Data Scientist and AI/ML Engineer in TXT, PDF and DOCX formats.\n")
    print(f"Generated sample data in {ROOT}")


if __name__ == "__main__":
    main()
