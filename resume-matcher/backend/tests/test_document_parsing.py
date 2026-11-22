import pytest

from app.services.document_parser import DocumentParseError, detect_file_type, extract_text
from app.services.resume_parser import parse_resume


@pytest.mark.parametrize("ext", ["pdf", "docx"])
def test_extracts_text_from_both_formats(resume_files, ext):
    files = [f for f in resume_files if f.suffix == f".{ext}"]
    assert len(files) >= 5
    for f in files:
        ftype, text = extract_text(f.name, f.read_bytes())
        assert ftype == ext
        assert len(text) > 200


@pytest.mark.parametrize("name,status,fragment", [
    ("empty_file.pdf", "failed", "empty"),
    ("corrupted_resume.docx", "failed", "Corrupted"),
    ("corrupted_resume.pdf", "failed", "Corrupted"),
    ("renamed_image.pdf", "failed", "not a valid PDF"),
    ("blank_page.pdf", "failed", "no extractable text"),
    ("scanned_resume.pdf", "failed", "scanned"),
    ("unsupported_resume.txt", "unsupported", "Unsupported"),
])
def test_edge_cases_raise_clear_errors(edge_files, name, status, fragment):
    f = edge_files[name]
    with pytest.raises(DocumentParseError) as exc:
        extract_text(f.name, f.read_bytes())
    assert exc.value.status == status
    assert fragment.lower() in str(exc.value).lower()


def test_extension_and_magic_bytes_must_agree():
    with pytest.raises(DocumentParseError):
        detect_file_type("resume.docx", b"%PDF-1.4 ...")
    with pytest.raises(DocumentParseError):
        detect_file_type("resume.exe", b"MZ")


def test_parse_resume_fields(resume_files):
    f = next(x for x in resume_files if x.name.startswith("01_"))
    _, text = extract_text(f.name, f.read_bytes())
    p = parse_resume(text)
    assert p.name == "Aarav Mehta"
    assert p.email == "aarav.mehta@example.com"
    assert p.phone and "98765" in p.phone
    assert {"Python", "FastAPI", "PostgreSQL", "Docker"} <= set(p.skills)
    assert p.highest_education == "bachelor"
    assert p.education[0]["field"] == "computer science"
    assert len(p.employment_history) == 3
    assert p.employment_history[0]["company"] == "CloudNova Technologies"
    assert p.certifications and "AWS" in p.certifications[0]
    assert p.projects


def test_all_samples_extract_name_email_and_skills(resume_files):
    for f in resume_files:
        _, text = extract_text(f.name, f.read_bytes())
        p = parse_resume(text)
        assert p.name, f.name
        assert p.email and p.email.endswith("@example.com"), f.name
        assert len(p.skills) >= 4, f.name
        assert p.experience_years is not None, f.name


def test_sensitive_attributes_are_removed(resume_files):
    f = next(x for x in resume_files if x.name.startswith("10_"))
    _, text = extract_text(f.name, f.read_bytes())
    assert "Gender" in text
    p = parse_resume(text)
    joined = " ".join(p.sections.values())
    assert "Gender" not in joined and "Date of Birth" not in joined
    assert any("personal-attribute" in w for w in p.warnings)


def test_minimal_resume_reports_warnings():
    p = parse_resume("Some text without structure that talks about cooking and gardening hobbies at length.")
    assert "No email address found" in p.warnings
    assert p.experience_years is None
