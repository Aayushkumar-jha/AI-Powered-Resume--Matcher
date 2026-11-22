"""Skill extraction and synonym mapping based on the skill taxonomy.

Pipeline:
1. Normalize text (lower-case, keep + # . / characters).
2. Regex-match every alias with custom word boundaries (handles c++, c#, node.js, ci/cd).
3. Ambiguous short aliases (R, Go, ML ...) are only accepted as full items in
   comma/pipe-separated lists inside a "Skills" section.
4. Each alias maps to one canonical skill (synonym mapping).
"""
import re
from functools import lru_cache

from app.data.skills_taxonomy import LIST_ONLY_SKILLS, SKILLS
from app.services.text_preprocessing import normalize_for_matching

DISPLAY_NAMES = {
    "aws": "AWS", "gcp": "GCP", "sql": "SQL", "nlp": "NLP", "llms": "LLMs", "ci/cd": "CI/CD",
    "oop": "OOP", "etl": "ETL", "mlops": "MLOps", "html": "HTML", "css": "CSS", "rest api": "REST API",
    "graphql": "GraphQL", "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "fastapi": "FastAPI", "javascript": "JavaScript", "typescript": "TypeScript", "node.js": "Node.js",
    "express.js": "Express.js", "vue.js": "Vue.js", "scikit-learn": "scikit-learn", "xgboost": "XGBoost",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch", "numpy": "NumPy", "scipy": "SciPy",
    "dynamodb": "DynamoDB", "sqlalchemy": "SQLAlchemy", "spacy": "spaCy", "nltk": "NLTK", "onnx": "ONNX",
    "cuda": "CUDA", "c#": "C#", "c++": "C++", "r": "R", "c": "C", "go": "Go", "sql server": "SQL Server",
    "power bi": "Power BI", "rabbitmq": "RabbitMQ", "django orm": "Django ORM", "sqlite": "SQLite",
    "pytest": "pytest", "pandas": "pandas", "jupyter": "Jupyter", "kafka": "Kafka", ".net": ".NET",
    "tailwind css": "Tailwind CSS", "llm": "LLMs", "ui/ux": "UI/UX", "data structures": "Data Structures & Algorithms",
}

_BOUNDARY_L = r"(?<![a-z0-9+#])"
_BOUNDARY_R = r"(?![a-z0-9+#]|\.[a-z0-9])"


@lru_cache
def _alias_map() -> dict[str, str]:
    """alias (normalized) -> canonical skill."""
    mapping: dict[str, str] = {}
    for canonical, meta in SKILLS.items():
        mapping[canonical] = canonical
        for alias in meta.get("aliases", []):
            mapping[normalize_for_matching(alias)] = canonical
    return mapping


@lru_cache
def _free_text_patterns() -> list[tuple[re.Pattern, str]]:
    patterns = []
    # longest aliases first so multi-word phrases win
    for alias, canonical in sorted(_alias_map().items(), key=lambda kv: -len(kv[0])):
        # ambiguous aliases and soft skills ("leadership", "communication") are too noisy in prose
        if alias in LIST_ONLY_SKILLS or len(alias) <= 1 or SKILLS[canonical].get("category") == "soft":
            continue
        patterns.append((re.compile(_BOUNDARY_L + re.escape(alias) + _BOUNDARY_R), canonical))
    return patterns


@lru_cache
def _related_map() -> dict[str, set[str]]:
    """Bidirectional related-skill graph."""
    rel: dict[str, set[str]] = {k: set() for k in SKILLS}
    for canonical, meta in SKILLS.items():
        for r in meta.get("related", []):
            if r in SKILLS:
                rel[canonical].add(r)
                rel[r].add(canonical)
    return rel


def canonicalize(skill: str) -> str:
    """Map any skill spelling to its canonical form (or a normalized form if unknown)."""
    norm = normalize_for_matching(skill)
    return _alias_map().get(norm, norm)


def is_known(skill: str) -> bool:
    return canonicalize(skill) in SKILLS


def display_name(skill: str) -> str:
    key = canonicalize(skill)
    if key in DISPLAY_NAMES:
        return DISPLAY_NAMES[key]
    if key in SKILLS:
        return " ".join(w if w.isupper() else w.capitalize() for w in key.split())
    return skill.strip()


def related_skills(skill: str) -> set[str]:
    return _related_map().get(canonicalize(skill), set())


def category_of(skill: str) -> str:
    return SKILLS.get(canonicalize(skill), {}).get("category", "other")


GENERIC_TOKENS = {"api", "apis", "ci", "cd", "etc", "tools", "others", "other", "frameworks", "languages",
                  "databases", "cloud", "basic", "advanced", "intermediate", "familiar", "skills"}


def _list_items(skills_section: str, split_slash: bool = True) -> list[str]:
    items = []
    sep = r"[,|;•/\t]|\s{2,}|\band\b" if split_slash else r"[,|;•\t]|\s{2,}|\band\b"
    for line in skills_section.split("\n"):
        # drop "Languages:" / "Frameworks -" style prefixes
        if ":" in line:
            line = line.split(":", 1)[1]
        for token in re.split(sep, line):
            token = token.strip(" .-*()[]")
            if token:
                items.append(token)
    return items


def extract_skills(text: str, skills_section: str | None = None) -> list[str]:
    """Return canonical skills found, in order of first appearance."""
    norm = normalize_for_matching(text)
    found: dict[str, int] = {}
    for pattern, canonical in _free_text_patterns():
        m = pattern.search(norm)
        if m and (canonical not in found or m.start() < found[canonical]):
            found[canonical] = m.start()

    if skills_section:
        amap = _alias_map()
        items = dict.fromkeys(_list_items(skills_section, split_slash=False) + _list_items(skills_section))
        pos = len(norm)
        for item in items:
            key = normalize_for_matching(item)
            if key in amap and amap[key] not in found:
                found[amap[key]] = pos  # list-only skills sort last, in list order
                pos += 1
    return sorted(found, key=found.get)


def extract_unknown_list_skills(skills_section: str, limit: int = 15) -> list[str]:
    """Items in a skills list that are not in the taxonomy (kept as free-form skills)."""
    amap = _alias_map()
    out, seen = [], set()
    for item in _list_items(skills_section, split_slash=False):
        key = normalize_for_matching(item)
        if key in GENERIC_TOKENS or ("/" in key and all(p.strip() in amap for p in key.split("/"))):
            continue
        words = key.split()
        if (key and key not in amap and 1 <= len(words) <= 4 and len(key) <= 30
                and not any(ch.isdigit() for ch in key[:1]) and key not in seen):
            # avoid matching sentences: require list-item shape
            if not re.search(r"\b(years?|experience|with|using|in|of|the)\b", key):
                seen.add(key)
                out.append(item.strip())
        if len(out) >= limit:
            break
    return out


def phrase_in_text(phrase: str, text: str) -> bool:
    """Boundary-aware phrase search for skills not present in the taxonomy."""
    p = normalize_for_matching(phrase)
    if not p:
        return False
    return re.search(_BOUNDARY_L + re.escape(p) + _BOUNDARY_R, normalize_for_matching(text)) is not None
