"""Resume information extraction (spaCy + regular expressions + section heuristics)."""
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from functools import lru_cache

from app.core.config import get_settings
from app.services import education as edu
from app.services.experience_calculator import calculate_experience
from app.services.skill_extractor import display_name, extract_skills, extract_unknown_list_skills
from app.services.text_preprocessing import SECTION_HEADINGS, clean_text, remove_sensitive_lines, split_sections

log = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d{1,3}[\s.-]?)?(\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}(?!\d)")
URL_RE = re.compile(r"(https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+)", re.IGNORECASE)
_ALL_HEADINGS = {kw for kws in SECTION_HEADINGS.values() for kw in kws}
_NAME_STOPWORDS = {"resume", "curriculum", "vitae", "cv", "profile", "engineer", "developer", "scientist",
                   "manager", "analyst", "contact", "email", "phone", "address", "linkedin", "github"}


@lru_cache
def get_nlp():
    """Lazily load spaCy (NER is only needed as a fallback for candidate names)."""
    import spacy

    try:
        return spacy.load(get_settings().spacy_model, disable=["lemmatizer"])
    except OSError:
        log.warning("spaCy model '%s' not installed; using blank English pipeline", get_settings().spacy_model)
        return spacy.blank("en")


@dataclass
class ParsedResume:
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    skills: list[str] = field(default_factory=list)          # display names
    skill_keys: list[str] = field(default_factory=list)      # canonical keys
    education: list[dict] = field(default_factory=list)
    highest_education: str | None = None
    experience_years: float | None = None
    experience_method: str = "not_found"
    experience_note: str = ""
    employment_history: list[dict] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _extract_name(header: str, full_text: str) -> str | None:
    lines = [ln.strip() for ln in header.split("\n") if ln.strip()][:6]
    for line in lines:
        cleaned = re.sub(r"\s+", " ", URL_RE.sub("", EMAIL_RE.sub("", line))).strip(" |,-")
        if "|" in cleaned:
            cleaned = cleaned.split("|")[0].strip()
        words = cleaned.split()
        if not (2 <= len(words) <= 4) or any(ch.isdigit() for ch in cleaned):
            continue
        if cleaned.lower() in _ALL_HEADINGS or any(w.lower().strip(".,") in _NAME_STOPWORDS for w in words):
            continue
        if all(re.fullmatch(r"[A-Z][a-zA-Z.'-]*|[A-Z]{2,}", w) for w in words):
            return " ".join(w.capitalize() if w.isupper() else w for w in words)
    # Fallback: spaCy named-entity recognition on the top of the document
    doc = get_nlp()(full_text[:600])
    for ent in getattr(doc, "ents", []):
        if ent.label_ == "PERSON" and 2 <= len(ent.text.split()) <= 4 and "\n" not in ent.text:
            return ent.text.strip()
    return None


def _extract_phone(text: str) -> str | None:
    for m in PHONE_RE.finditer(text[:1500]):
        candidate = m.group(0).strip()
        digits = re.sub(r"\D", "", candidate)
        # avoid date ranges like 2019-2022 and years
        if 10 <= len(digits) <= 15 and not re.fullmatch(r"(19|20)\d{2}\s*-\s*(19|20)\d{2}", candidate):
            return candidate
    return None


def _list_items(section: str, limit: int = 12, max_len: int = 220) -> list[str]:
    items = []
    for line in section.split("\n"):
        line = line.strip(" •-*\t")
        if len(line) >= 4:
            items.append(line[:max_len])
        if len(items) >= limit:
            break
    return items


def _project_titles(section: str, limit: int = 10) -> list[str]:
    """Projects: keep the title lines (non-bullet lines) or the first bullets when no titles exist."""
    raw_lines = [ln for ln in section.split("\n") if ln.strip()]
    titles = [ln.strip() for ln in raw_lines if not ln.lstrip().startswith(("•", "-", "*"))]
    return _list_items("\n".join(titles or raw_lines), limit=limit)


def parse_resume(raw_text: str, today: date | None = None) -> ParsedResume:
    text = clean_text(raw_text)
    text, removed = remove_sensitive_lines(text)
    sections = split_sections(text)
    result = ParsedResume(sections=sections)
    if removed:
        result.warnings.append(f"{removed} personal-attribute line(s) (e.g. age/gender) ignored for fairness")

    header = sections.get("header", text[:400])
    result.name = _extract_name(header, text)
    emails = EMAIL_RE.findall(text)
    result.email = emails[0].lower() if emails else None
    result.phone = _extract_phone(text)

    summary = sections.get("summary")
    result.summary = summary[:1000] if summary else None

    # Skills: taxonomy matches anywhere + unknown items in the skills list
    keys = extract_skills(text, skills_section=sections.get("skills"))
    result.skill_keys = keys
    extra = extract_unknown_list_skills(sections["skills"]) if sections.get("skills") else []
    result.skills = [display_name(k) for k in keys] + [e for e in extra if e.lower() not in {k for k in keys}]

    # Education
    result.education = edu.extract_education(sections.get("education", ""))
    result.highest_education = edu.highest_level(result.education)

    # Experience: only from the experience section (avoid counting education dates)
    exp_text = sections.get("experience")
    if exp_text:
        exp = calculate_experience(exp_text, today=today, fallback_text=text)
    else:
        no_edu = "\n".join(v for k, v in sections.items() if k not in ("education", "projects", "certifications"))
        exp = calculate_experience(no_edu, today=today, fallback_text=text)
    result.experience_years = exp.total_years
    result.experience_method = exp.method
    result.experience_note = exp.note
    result.employment_history = [p.to_dict() for p in exp.periods]

    result.projects = _project_titles(sections.get("projects", ""))
    result.certifications = _list_items(sections.get("certifications", ""), limit=10)

    # Transparency warnings
    if not result.name:
        result.warnings.append("Candidate name could not be identified")
    if not result.email:
        result.warnings.append("No email address found")
    if not result.phone:
        result.warnings.append("No phone number found")
    if not keys:
        result.warnings.append("No recognizable skills found")
    if not result.education:
        result.warnings.append("No education details found")
    if exp.method == "not_found":
        result.warnings.append("Work experience duration could not be determined")
    elif exp.method == "stated":
        result.warnings.append("Experience taken from a stated summary (no dated employment history)")
    if len(sections) <= 1:
        result.warnings.append("No standard resume sections detected; extraction may be less accurate")
    return result
