"""Education extraction (degree level + field) and education matching."""
import re

from app.data.skills_taxonomy import EDUCATION_FIELD_GROUPS, STEM_FIELDS

LEVEL_RANK = {"high_school": 1, "diploma": 2, "associate": 2, "bachelor": 3, "master": 4, "phd": 5}
LEVEL_LABEL = {"high_school": "High School", "diploma": "Diploma", "associate": "Associate Degree",
               "bachelor": "Bachelor's", "master": "Master's", "phd": "PhD / Doctorate"}

# Order matters: check higher levels first
DEGREE_PATTERNS: list[tuple[str, str]] = [
    ("phd", r"(\bph\.?\s?d\b|\bdoctor of philosophy\b|\bdoctorate\b|\bd\.phil\b)"),
    ("master", r"(\bmaster'?s?\b|\bm\.?\s?sc\b|\bm\.s\.?|\bms\b|\bm\.?\s?tech\b|\bm\.e\.|\bmba\b|"
               r"\bm\.a\.|\bmca\b|\bpost\s?graduate\b|\bpg diploma\b)"),
    ("bachelor", r"(\bbachelor'?s?\b|\bb\.?\s?sc\b|\bb\.s\.?|\bbs\b|\bb\.?\s?tech\b|\bb\.e\.|\bba\b|"
                 r"\bb\.a\.|\bbca\b|\bundergraduate degree\b|\bb\.?\s?eng\b|\bbba\b|\bb\.?\s?com\b)"),
    ("associate", r"\b(associate'?s? degree|associate of)\b"),
    ("diploma", r"\b(diploma)\b"),
    ("high_school", r"\b(high school|secondary school|higher secondary|12th|hsc|ssc|a-levels?)\b"),
]

FIELD_KEYWORDS = sorted(
    {f for group in EDUCATION_FIELD_GROUPS for f in group} | STEM_FIELDS, key=len, reverse=True
)
_FIELD_ALIASES = {"cs": "computer science", "cse": "computer science", "it": "information technology",
                  "ece": "electronics and communication", "ai": "artificial intelligence",
                  "ml": "machine learning", "ee": "electrical engineering", "maths": "mathematics",
                  "math": "mathematics", "stats": "statistics"}


def detect_level(text: str) -> str | None:
    t = text.lower()
    for level, pat in DEGREE_PATTERNS:
        if re.search(pat, t):
            return level
    return None


def detect_fields(text: str) -> list[str]:
    t = " " + re.sub(r"[^a-z&\s]", " ", text.lower()) + " "
    found = []
    for f in FIELD_KEYWORDS:
        if f" {f} " in t and not any(f in g for g in found):
            found.append(f)
    for alias, f in _FIELD_ALIASES.items():
        if re.search(rf"\b{alias}\b", text.lower()) and f not in found and len(text) < 160:
            found.append(f)
    return found


def extract_education(section_text: str) -> list[dict]:
    """Parse an education section into entries [{degree, level, field, institution, year}]."""
    entries: list[dict] = []
    if not section_text:
        return entries
    lines = [ln.strip(" •-\t") for ln in section_text.split("\n") if ln.strip(" •-\t")]
    for i, line in enumerate(lines):
        level = detect_level(line)
        if not level:
            continue
        context = " ".join(lines[i:i + 2])
        fields = detect_fields(line) or detect_fields(context)
        year = re.findall(r"(?:19|20)\d{2}", context)
        institution = None
        for cand in [line, *(lines[i + 1:i + 2])]:
            m = re.search(r"([A-Z][\w.&'-]*(?:\s+[A-Z][\w.&'-]*)*\s+(?:University|Institute|College|School)"
                          r"(?:\s+of\s+[A-Z][\w&'-]*(?:\s+[A-Z][\w&'-]*)*)?|"
                          r"(?:University|Institute|College)\s+of\s+[A-Z][\w&'-]*(?:\s+[A-Z][\w&'-]*)*)", cand)
            if m:
                institution = m.group(1).strip()
                break
        entries.append({
            "degree": line[:150],
            "level": level,
            "level_label": LEVEL_LABEL[level],
            "field": fields[0] if fields else None,
            "institution": institution,
            "year": int(year[-1]) if year else None,
        })
    return entries


def highest_level(entries: list[dict]) -> str | None:
    levels = [e["level"] for e in entries if e.get("level")]
    return max(levels, key=lambda lv: LEVEL_RANK[lv]) if levels else None


def _field_relation(required_fields: list[str], candidate_fields: list[str]) -> tuple[float, str]:
    if not required_fields:
        return 1.0, "No specific field of study required"
    if not candidate_fields:
        return 0.0, "Field of study not found in resume"
    req = [f.lower() for f in required_fields]
    cand = [f.lower() for f in candidate_fields]
    for c in cand:
        if c in req:
            return 1.0, f"Field '{c}' matches a required field"
    for c in cand:
        for group in EDUCATION_FIELD_GROUPS:
            if c in group and any(r in group for r in req):
                return 0.75, f"Field '{c}' is closely related to required field(s): {', '.join(required_fields)}"
    for c in cand:
        if c in STEM_FIELDS and any(r in STEM_FIELDS for r in req):
            return 0.5, f"Field '{c}' is a related STEM field"
    return 0.2, f"Field '{cand[0]}' differs from required field(s): {', '.join(required_fields)}"


def score_education(required_level: str | None, required_fields: list[str], entries: list[dict]) -> dict:
    """Return {score (0-100) | None, available, details...}.

    score = 70% degree level + 30% field relevance (field part only if JD specifies fields).
    Returns available=False when the JD states no education requirement at all.
    """
    if not required_level and not required_fields:
        return {"score": None, "available": False,
                "note": "Job description specifies no education requirement; component excluded"}

    cand_level = highest_level(entries)
    cand_fields = [e["field"] for e in entries if e.get("field")]
    if not entries:
        return {"score": 0.0, "available": True, "candidate_level": None, "required_level": required_level,
                "required_fields": required_fields, "candidate_fields": [],
                "note": "No education information found in resume - verify manually"}

    if required_level:
        diff = LEVEL_RANK.get(cand_level, 0) - LEVEL_RANK[required_level]
        if cand_level is None:
            level_score, level_note = 0.0, "Degree level could not be determined"
        elif diff >= 0:
            level_score = 1.0
            level_note = (f"{LEVEL_LABEL[cand_level]} meets the required {LEVEL_LABEL[required_level]}"
                          + (" (exceeds requirement)" if diff > 0 else ""))
        elif diff == -1:
            level_score, level_note = 0.6, f"{LEVEL_LABEL[cand_level]} is one level below required {LEVEL_LABEL[required_level]}"
        else:
            level_score, level_note = 0.3, f"{LEVEL_LABEL[cand_level]} is well below required {LEVEL_LABEL[required_level]}"
    else:
        level_score, level_note = 1.0, "No minimum degree level specified"

    field_score, field_note = _field_relation(required_fields, cand_fields)
    score = (0.7 * level_score + 0.3 * field_score) if required_fields else level_score
    return {
        "score": round(score * 100, 1), "available": True,
        "candidate_level": cand_level, "candidate_level_label": LEVEL_LABEL.get(cand_level) if cand_level else None,
        "required_level": required_level,
        "required_level_label": LEVEL_LABEL.get(required_level) if required_level else None,
        "required_fields": required_fields, "candidate_fields": cand_fields,
        "level_score": round(level_score * 100, 1), "field_score": round(field_score * 100, 1),
        "level_note": level_note, "field_note": field_note, "note": f"{level_note}. {field_note}.",
    }
