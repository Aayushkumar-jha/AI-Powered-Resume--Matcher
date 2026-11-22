"""Text preprocessing, normalization and section segmentation."""
import re
import unicodedata

# Heading keyword -> canonical section name
SECTION_HEADINGS: dict[str, list[str]] = {
    "summary": ["summary", "professional summary", "profile", "professional profile", "objective",
                "career objective", "about me", "about", "overview", "career summary"],
    "experience": ["experience", "work experience", "professional experience", "employment",
                   "employment history", "work history", "career history", "relevant experience",
                   "internships", "internship", "internship experience"],
    "education": ["education", "academic background", "academics", "educational qualifications",
                  "academic qualifications", "qualifications and education", "education and training"],
    "skills": ["skills", "technical skills", "core skills", "key skills", "skill set", "skillset",
               "core competencies", "competencies", "technologies", "tech stack", "tools and technologies",
               "technical proficiencies", "areas of expertise"],
    "projects": ["projects", "academic projects", "personal projects", "key projects",
                 "selected projects", "project experience", "side projects"],
    "certifications": ["certifications", "certificates", "certification", "licenses and certifications",
                       "courses", "training", "certifications and training"],
    "achievements": ["achievements", "awards", "honors", "accomplishments", "awards and honors"],
    "publications": ["publications", "research", "papers"],
    "languages": ["languages", "spoken languages"],
    "interests": ["interests", "hobbies", "hobbies and interests"],
}

_HEADING_LOOKUP = {kw: sec for sec, kws in SECTION_HEADINGS.items() for kw in kws}


def normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "–": "-", "—": "-", "‒": "-", "−": "-",
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "•": "\n• ", "●": "\n• ", "▪": "\n• ", "": "\n• ", " ": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def clean_text(text: str) -> str:
    """Unicode normalization + whitespace cleanup, keeping line structure."""
    text = normalize_unicode(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    out, blank = [], 0
    for ln in lines:
        if not ln:
            blank += 1
            if blank <= 1:
                out.append("")
            continue
        blank = 0
        out.append(ln)
    return "\n".join(out).strip()


def normalize_for_matching(text: str) -> str:
    """Lower-case, collapse whitespace; keep characters meaningful for skills (+ # . /)."""
    text = normalize_unicode(text).lower()
    text = re.sub(r"[^a-z0-9+#./\-\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _heading_of(line: str) -> str | None:
    """Return the canonical section name if `line` looks like a section heading."""
    raw = line.strip().strip("•-*#|").strip()
    if not raw or len(raw) > 45:
        return None
    candidate = re.sub(r"[:\-–|]+$", "", raw).strip().lower()
    candidate = re.sub(r"\s+", " ", candidate).replace("&", "and")
    if candidate in _HEADING_LOOKUP:
        return _HEADING_LOOKUP[candidate]
    # "SKILLS:" with trailing content on the same line, e.g. "Skills: Python, SQL"
    return None


def split_sections(text: str) -> dict[str, str]:
    """Segment a resume/JD into sections based on heading lines.

    Text before the first heading is stored under "header". Lines like
    "Skills: Python, SQL" are treated as a heading followed by content.
    """
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.split("\n"):
        heading = _heading_of(line)
        if heading is None and ":" in line:
            head, _, rest = line.partition(":")
            inline = _heading_of(head)
            if inline and rest.strip():
                current = inline
                sections.setdefault(current, []).append(rest.strip())
                continue
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


SENSITIVE_LINE_RE = re.compile(
    r"^\s*(date of birth|d\.?o\.?b\.?|birth ?date|age|gender|sex|marital status|religion|caste|"
    r"nationality|ethnicity|race|blood group|father'?s name|mother'?s name)\s*[:\-]",
    re.IGNORECASE,
)


def remove_sensitive_lines(text: str) -> tuple[str, int]:
    """Drop personal-attribute lines (age, gender, religion, caste ...) so they can never
    influence matching. Returns (clean_text, removed_count)."""
    kept, removed = [], 0
    for line in text.split("\n"):
        if SENSITIVE_LINE_RE.match(line):
            removed += 1
            continue
        kept.append(line)
    return "\n".join(kept), removed


def split_sentences(text: str, min_len: int = 15) -> list[str]:
    """Lightweight sentence/bullet splitter used to build embedding chunks."""
    parts = re.split(r"(?<=[.!?])\s+|\n+|•", text)
    return [p.strip(" -•\t") for p in parts if len(p.strip(" -•\t")) >= min_len]
