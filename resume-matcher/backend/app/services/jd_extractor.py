"""Job-description extraction: raw JD text -> structured, editable JSON requirements."""
import re

from app.schemas.job import JobRequirements
from app.services import education as edu
from app.services.skill_extractor import display_name, extract_skills, extract_unknown_list_skills
from app.services.text_preprocessing import clean_text

JD_HEADINGS: dict[str, list[str]] = {
    "required": ["required skills", "requirements", "must have", "must-have", "must have skills",
                 "mandatory skills", "required qualifications", "technical requirements", "key skills",
                 "skills required", "what we're looking for", "what we are looking for",
                 "what you bring", "who you are", "minimum qualifications", "basic qualifications",
                 "skills", "technical skills", "required technical skills"],
    "preferred": ["preferred skills", "preferred qualifications", "nice to have", "nice-to-have",
                  "good to have", "bonus points", "bonus", "desired skills", "plus", "pluses",
                  "additional skills", "preferred"],
    "responsibilities": ["responsibilities", "key responsibilities", "job responsibilities", "duties",
                         "what you'll do", "what you will do", "role and responsibilities",
                         "the role", "your role", "day to day", "job duties"],
    "qualifications": ["qualifications", "eligibility", "education and experience",
                       "experience and qualifications"],
    "education": ["education", "educational requirements", "education requirements", "academic requirements"],
    "experience": ["experience", "experience required", "work experience"],
    "about": ["about the role", "about us", "job summary", "overview", "role overview", "job description",
              "summary", "about the company", "position summary", "benefits", "what we offer", "perks"],
}
_LOOKUP = {kw: sec for sec, kws in JD_HEADINGS.items() for kw in kws}
PREFERRED_CUES = re.compile(r"\b(preferred|nice to have|nice-to-have|good to have|is a plus|a plus|bonus|"
                            r"desirable|advantageous|optional|familiarity with)\b", re.IGNORECASE)
EXPERIENCE_RE = re.compile(
    r"(\d{1,2}(?:\.\d)?)\s*(?:\+|plus)?\s*(?:(?:-|–|to)\s*(\d{1,2}(?:\.\d)?))?\s*\+?\s*(?:years|yrs)",
    re.IGNORECASE,
)
TITLE_RE = re.compile(r"^(?:job\s*title|position|role|title)\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _heading(line: str) -> str | None:
    raw = line.strip().strip("•-*#|:").strip().lower()
    raw = re.sub(r"[:\-–]+$", "", raw).strip().replace("&", "and")
    if len(raw) > 50:
        return None
    return _LOOKUP.get(raw)


def split_jd_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.split("\n"):
        if not line.strip():
            continue
        h = _heading(line)
        if h is None and ":" in line:
            head, _, rest = line.partition(":")
            if _heading(head) and rest.strip():
                current = _heading(head)
                sections.setdefault(current, []).append(rest.strip())
                continue
        if h:
            current = h
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line.strip(" •-*\t"))
    return sections


def _extract_title(text: str, sections: dict[str, list[str]]) -> str:
    m = TITLE_RE.search(text)
    if m:
        return m.group(1).strip()[:120]
    for line in sections.get("header", [])[:3]:
        if 3 <= len(line) <= 80 and not line.endswith("."):
            return line.strip()
    return "Untitled Position"


def _extract_experience(lines: list[str]) -> tuple[float | None, float | None]:
    # Prefer lines that talk about experience
    ordered = [ln for ln in lines if "experience" in ln.lower()] + lines
    for line in ordered:
        m = EXPERIENCE_RE.search(line)
        if m:
            lo = float(m.group(1))
            hi = float(m.group(2)) if m.group(2) else None
            if lo <= 40 and (hi is None or hi >= lo):
                return lo, hi
    return None, None


def extract_job_requirements(raw_text: str) -> JobRequirements:
    text = clean_text(raw_text)
    sections = split_jd_sections(text)
    all_lines = [ln for lines in sections.values() for ln in lines]

    title = _extract_title(text, sections)

    # Preferred: explicit section + any line carrying a "nice to have" cue
    preferred_lines = list(sections.get("preferred", []))
    required_lines = sections.get("required", []) + sections.get("qualifications", []) + sections.get("experience", [])
    cue_lines = [ln for ln in all_lines if PREFERRED_CUES.search(ln) and ln not in preferred_lines]
    preferred_lines += cue_lines
    required_lines = [ln for ln in required_lines if ln not in cue_lines]

    if not required_lines:  # unstructured JD: use everything that isn't preferred
        required_lines = [ln for ln in all_lines if ln not in preferred_lines]

    req_text, pref_text = "\n".join(required_lines), "\n".join(preferred_lines)
    preferred_keys = extract_skills(pref_text, skills_section=pref_text)
    required_keys = [k for k in extract_skills(req_text, skills_section=req_text) if k not in preferred_keys]
    # Skills mentioned only in responsibilities still matter -> required unless marked preferred
    resp_text = "\n".join(sections.get("responsibilities", []))
    for k in extract_skills(resp_text):
        if k not in required_keys and k not in preferred_keys:
            required_keys.append(k)
    # Soft skills are noisy as hard requirements -> keep them preferred
    soft = {"communication", "leadership", "problem solving", "project management", "agile"}
    preferred_keys += [k for k in required_keys if k in soft and k not in preferred_keys]
    required_keys = [k for k in required_keys if k not in soft]

    required = [display_name(k) for k in required_keys]
    required += [s for s in extract_unknown_list_skills("\n".join(sections.get("required", [])), limit=5)
                 if len(s.split()) <= 3 and s.lower() not in {r.lower() for r in required}]
    preferred = [display_name(k) for k in preferred_keys]

    min_exp, max_exp = _extract_experience(sections.get("experience", []) + required_lines + all_lines)

    edu_lines = [ln for ln in sections.get("education", []) + sections.get("qualifications", []) + all_lines
                 if edu.detect_level(ln)]
    level = None
    fields: list[str] = []
    if edu_lines:
        # The minimum acceptable level is the lowest degree mentioned in the requirement line
        levels = [lv for lv, pat in edu.DEGREE_PATTERNS if re.search(pat, edu_lines[0].lower())]
        level = min(levels, key=lambda lv: edu.LEVEL_RANK[lv]) if levels else None
        for ln in edu_lines[:2]:
            fields += [f for f in edu.detect_fields(ln) if f not in fields]

    return JobRequirements(
        title=title,
        required_skills=required,
        preferred_skills=preferred,
        min_experience_years=min_exp,
        max_experience_years=max_exp,
        education_level=level,
        education_fields=fields[:5],
        qualifications=sections.get("qualifications", [])[:15] or sections.get("education", [])[:10],
        responsibilities=sections.get("responsibilities", [])[:20],
    )
