"""Hybrid matching for one candidate: skills + semantics + experience + education -> explained score."""
from app.schemas.job import JobRequirements
from app.services.education import score_education
from app.services.explanation_service import build_explanation
from app.services.scoring_engine import combine_scores, score_experience
from app.services.semantic_matcher import semantic_match
from app.services.skill_matcher import match_skills


def analyze_candidate(req: JobRequirements, raw_jd: str, weights: dict[str, float], cand: dict) -> dict:
    """`cand` keys: name, skill_keys, skills, sections, raw_text, experience_years,
    experience_method, education, warnings."""
    skill = match_skills(req.required_skills, req.preferred_skills, cand.get("skill_keys", []),
                         cand.get("skills", []), cand.get("raw_text", ""))
    semantic = semantic_match(req, raw_jd, cand.get("sections", {}), cand.get("raw_text", ""))
    experience = score_experience(req.min_experience_years, req.max_experience_years,
                                  cand.get("experience_years"), cand.get("experience_method", "date_ranges"))
    education = score_education(req.education_level, req.education_fields, cand.get("education", []))

    final = combine_scores(
        {"skills": skill.get("score"), "semantic": semantic.get("score"),
         "experience": experience.get("score"), "education": education.get("score")},
        weights,
    )
    explanation = build_explanation(cand.get("name"), final, skill, semantic, experience, education,
                                    final.weights_used, cand.get("warnings", []))
    return {
        "final_score": final.final_score,
        "fit_label": final.fit_label,
        "skill_score": skill.get("score"),
        "semantic_score": semantic.get("score"),
        "experience_score": experience.get("score"),
        "education_score": education.get("score"),
        "weights_used": final.weights_used,
        "skill_details": skill,
        "semantic_details": semantic,
        "experience_details": experience,
        "education_details": education,
        "explanation": explanation,
    }
