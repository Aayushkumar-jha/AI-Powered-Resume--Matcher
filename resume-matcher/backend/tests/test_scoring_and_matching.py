import pytest

from app.schemas.job import JobRequirements, ScoringWeights
from app.services.document_parser import extract_text
from app.services.jd_extractor import extract_job_requirements
from app.services.matching_service import analyze_candidate
from app.services.ranking_service import assign_ranks
from app.services.resume_parser import parse_resume
from app.services.scoring_engine import combine_scores, fit_label, score_experience
from app.services.skill_matcher import match_skills

DEFAULT_W = {"skills": 0.4, "semantic": 0.3, "experience": 0.2, "education": 0.1}


# ---------------- Formula ----------------
def test_weighted_formula_exact():
    r = combine_scores({"skills": 80, "semantic": 60, "experience": 100, "education": 50}, DEFAULT_W)
    assert r.final_score == pytest.approx(80 * .4 + 60 * .3 + 100 * .2 + 50 * .1)  # 75.0
    assert r.fit_label == "Strong match"


def test_unavailable_component_is_renormalized():
    r = combine_scores({"skills": 80, "semantic": 60, "experience": 100, "education": None}, DEFAULT_W)
    assert "education" in r.excluded
    assert r.weights_used["education"] == 0
    assert sum(r.weights_used.values()) == pytest.approx(1.0, abs=1e-3)
    assert r.final_score == pytest.approx((80 * .4 + 60 * .3 + 100 * .2) / 0.9, abs=0.1)


def test_scores_bounded():
    assert combine_scores({"skills": 100, "semantic": 100, "experience": 100, "education": 100}, DEFAULT_W).final_score == 100
    assert combine_scores({"skills": 0, "semantic": 0, "experience": 0, "education": 0}, DEFAULT_W).final_score == 0


def test_weights_are_normalized_and_validated():
    w = ScoringWeights(skills=2, semantic=1, experience=1, education=0)
    assert w.skills == pytest.approx(0.5)
    with pytest.raises(ValueError):
        ScoringWeights(skills=0, semantic=0, experience=0, education=0)


def test_requirements_validation():
    with pytest.raises(ValueError):
        JobRequirements(min_experience_years=5, max_experience_years=2)
    r = JobRequirements(required_skills=["Python", "python", " SQL "], preferred_skills=["SQL", "AWS"])
    assert r.required_skills == ["Python", "SQL"] and r.preferred_skills == ["AWS"]


@pytest.mark.parametrize("required,years,expected", [
    (4, 6, 100.0), (4, 2, 50.0), (4, 0, 0.0), (None, 3, None),
])
def test_experience_score(required, years, expected):
    assert score_experience(required, None, years)["score"] == expected


def test_experience_unknown_is_flagged_not_assumed():
    r = score_experience(3, None, None)
    assert r["score"] == 0.0 and "verify manually" in r["note"]


def test_fit_labels():
    assert fit_label(80) == "Strong match" and fit_label(60) == "Moderate match"
    assert fit_label(40) == "Weak match" and fit_label(10) == "Low match"


# ---------------- Skill matching ----------------
def test_mandatory_vs_preferred_and_related_credit():
    r = match_skills(["Python", "TensorFlow", "Kubernetes"], ["AWS"],
                     cand_keys=["python", "pytorch", "aws"], cand_display=["Python", "PyTorch", "AWS"],
                     resume_text="Python PyTorch AWS")
    m = {i["skill"]: i for i in r["mandatory"]}
    assert m["Python"]["match"] == "exact"
    assert m["TensorFlow"]["match"] == "related" and m["TensorFlow"]["via"] == "PyTorch"
    assert m["Kubernetes"]["match"] == "missing"
    assert r["missing_mandatory"] == ["Kubernetes"]
    assert r["matched_preferred"] == ["AWS"]
    # 0.75 * (1 + .5 + 0)/3 + 0.25 * 1
    assert r["score"] == pytest.approx(100 * (0.75 * 0.5 + 0.25), abs=0.1)


def test_custom_skill_outside_taxonomy_matched_by_phrase():
    r = match_skills(["Airtable"], [], [], [], "Automated workflows in Airtable for the ops team")
    assert r["mandatory"][0]["match"] == "exact"


def test_no_skills_in_jd_is_unavailable():
    assert match_skills([], [], ["python"], ["Python"], "")["available"] is False


# ---------------- End-to-end matching accuracy ----------------
@pytest.fixture(scope="module")
def parsed_resumes(resume_files):
    out = {}
    for f in resume_files:
        _, text = extract_text(f.name, f.read_bytes())
        d = parse_resume(text).to_dict()
        d["raw_text"] = text
        out[f.name[:2]] = d
    return out


def _rank(jd_text, parsed):
    req = extract_job_requirements(jd_text)
    scored = {k: analyze_candidate(req, jd_text, DEFAULT_W, v) for k, v in parsed.items()}
    return scored, sorted(scored, key=lambda k: scored[k]["final_score"], reverse=True)


def test_python_developer_ranking(jd_texts, parsed_resumes):
    scored, order = _rank(jd_texts["python_developer"], parsed_resumes)
    assert order[0] == "01"                                       # strong match on top
    assert order.index("10") < order.index("06")                  # python backend > frontend
    assert scored["02"]["final_score"] > scored["06"]["final_score"]  # Flask/MySQL related credit
    related = {i["skill"] for i in scored["02"]["skill_details"]["related_mandatory"]}
    assert {"FastAPI", "PostgreSQL"} <= related
    assert scored["03"]["experience_score"] < 50                  # junior penalized on experience


def test_data_scientist_ranking(jd_texts, parsed_resumes):
    scored, order = _rank(jd_texts["data_scientist"], parsed_resumes)
    assert order[0] == "04"
    assert scored["04"]["fit_label"] == "Strong match"
    assert scored["06"]["final_score"] < 40


def test_ai_ml_ranking_and_semantic_synonyms(jd_texts, parsed_resumes):
    scored, order = _rank(jd_texts["ai_ml_engineer"], parsed_resumes)
    assert order[0] == "05"
    # Neha uses synonyms (Hugging Face, Keras, Natural Language Processing) - must still rank 2nd
    assert order[1] == "12"
    assert scored["12"]["semantic_score"] > scored["06"]["semantic_score"] + 20


def test_explanation_is_grounded(jd_texts, parsed_resumes):
    scored, _ = _rank(jd_texts["python_developer"], parsed_resumes)
    ex = scored["02"]["explanation"]
    assert "Priya Nair" in ex["summary"]
    assert any("Flask" in s for s in ex["strengths"])           # related-skill evidence
    assert ex["formula"].endswith(f"= {scored['02']['final_score']:.1f}")
    assert "not hiring probabilities" in ex["disclaimer"]
    total = sum(b["contribution"] for b in ex["breakdown"])
    assert total == pytest.approx(scored["02"]["final_score"], abs=0.2)


def test_semantic_scores_normalized(jd_texts, parsed_resumes):
    scored, _ = _rank(jd_texts["ai_ml_engineer"], parsed_resumes)
    for s in scored.values():
        for key in ("skill_score", "semantic_score", "experience_score", "education_score", "final_score"):
            assert s[key] is None or 0 <= s[key] <= 100


def test_ranking_ties_share_rank():
    class R:
        def __init__(self, f, s):
            self.final_score, self.skill_score, self.semantic_score, self.rank = f, s, 0, None
    rows = assign_ranks([R(80, 50), R(90, 50), R(80, 50), R(70, 10)])
    assert [r.rank for r in rows] == [1, 2, 2, 4]
