from datetime import date

from app.services.education import extract_education, score_education
from app.services.experience_calculator import calculate_experience, merge_intervals
from app.services.jd_extractor import extract_job_requirements
from app.services.skill_extractor import canonicalize, display_name, extract_skills, related_skills
from app.services.text_preprocessing import clean_text, split_sections

TODAY = date(2026, 1, 15)


# ---------------- Skills ----------------
def test_synonyms_map_to_canonical_skill():
    assert canonicalize("Postgres") == "postgresql"
    assert canonicalize("sklearn") == "scikit-learn"
    assert canonicalize("k8s") == "kubernetes"
    assert canonicalize("ReactJS") == "react"
    assert display_name("postgres") == "PostgreSQL"


def test_extract_skills_handles_special_characters():
    skills = extract_skills("Worked with C++, C#, Node.js and CI/CD pipelines using GitHub Actions.")
    assert {"c++", "c#", "node.js", "ci/cd"} <= set(skills)


def test_ambiguous_short_skills_only_in_lists():
    assert "r" not in extract_skills("I led R&D projects and wrote a go-to-market plan.")
    assert {"r", "go"} <= set(extract_skills("x", skills_section="Languages: Python, R, Go"))


def test_soft_skills_not_matched_from_prose():
    assert "leadership" not in extract_skills("Built dashboards for the leadership team")


def test_related_skills_are_bidirectional():
    assert "pytorch" in related_skills("tensorflow")
    assert "tensorflow" in related_skills("pytorch")
    assert "mysql" in related_skills("PostgreSQL")


# ---------------- Experience ----------------
def test_overlapping_periods_counted_once():
    text = """Django Developer | AppNest | Jan 2020 - Dec 2023
Freelance Developer | Self | Jun 2021 - Jun 2023
Python Developer | CodeCraft | Jan 2024 - Dec 2025"""
    r = calculate_experience(text, today=TODAY)
    assert r.total_years == 6.0          # 48 + 24 months, freelance fully overlapped
    assert r.gross_years == round((48 + 25 + 24) / 12, 1)
    assert r.overlap_years > 0
    assert len(r.periods) == 3


def test_present_and_numeric_formats():
    r = calculate_experience("Engineer, Acme, 06/2023 - Present", today=TODAY)
    assert r.periods[0].is_current
    assert r.total_years == round(32 / 12, 1)  # Jun 2023 .. Jan 2026 inclusive


def test_year_only_ranges():
    r = calculate_experience("Analyst at Foo 2018 - 2020", today=TODAY)
    assert r.total_years == 2.0


def test_stated_experience_fallback_and_not_found():
    r = calculate_experience("No dates here", today=TODAY, fallback_text="I have 5+ years of experience in Python")
    assert r.method == "stated" and r.total_years == 5.0
    r = calculate_experience("Nothing useful", today=TODAY)
    assert r.method == "not_found" and r.total_years is None


def test_merge_intervals():
    assert merge_intervals([(0, 10), (5, 15), (20, 25)]) == [(0, 15), (20, 25)]


# ---------------- Education ----------------
def test_education_extraction_and_scoring():
    entries = extract_education("M.Sc in Statistics\nIndian Statistical Institute | 2018 - 2020\nB.Sc in Mathematics")
    assert entries[0]["level"] == "master" and entries[0]["field"] == "statistics"
    s = score_education("master", ["statistics", "computer science"], entries)
    assert s["score"] == 100.0
    s = score_education("phd", ["computer science"], entries)
    assert 0 < s["score"] < 100
    assert score_education(None, [], entries)["available"] is False
    assert score_education("bachelor", [], [])["score"] == 0.0


def test_degree_regex_does_not_match_common_words():
    assert extract_education("I want to be a great engineer and a team player") == []
    assert extract_education("Bachelor of Technology in Computer Science")[0]["level"] == "bachelor"
    assert extract_education("Ph.D. in Physics")[0]["level"] == "phd"


# ---------------- Preprocessing / JD ----------------
def test_section_split():
    s = split_sections(clean_text("John Doe\nSKILLS\nPython, SQL\nEducation:\nB.Tech CS"))
    assert s["skills"] == "Python, SQL" and "B.Tech" in s["education"]


def test_jd_extraction_python(jd_texts):
    req = extract_job_requirements(jd_texts["python_developer"])
    assert req.title == "Senior Python Developer"
    assert {"Python", "FastAPI", "PostgreSQL", "Docker", "pytest"} <= set(req.required_skills)
    assert {"AWS", "Redis", "Kubernetes"} <= set(req.preferred_skills)
    assert not set(req.required_skills) & set(req.preferred_skills)
    assert req.min_experience_years == 4
    assert req.education_level == "bachelor"
    assert "computer science" in req.education_fields
    assert len(req.responsibilities) >= 5


def test_jd_extraction_ranges_and_levels(jd_texts):
    ds = extract_job_requirements(jd_texts["data_scientist"])
    assert (ds.min_experience_years, ds.max_experience_years) == (3, 6)
    assert ds.education_level == "master"
    ml = extract_job_requirements(jd_texts["ai_ml_engineer"])
    assert ml.education_level == "bachelor"  # "Bachelor's or Master's" -> minimum is bachelor
    assert {"PyTorch", "TensorFlow", "NLP"} <= set(ml.required_skills)


def test_unstructured_jd_still_extracts_skills():
    req = extract_job_requirements("We need someone who knows Python, Django and Postgres with 2 years of experience.")
    assert {"Python", "Django", "PostgreSQL"} <= set(req.required_skills)
    assert req.min_experience_years == 2
