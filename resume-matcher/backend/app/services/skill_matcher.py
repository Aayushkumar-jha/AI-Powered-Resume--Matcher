"""Hybrid skill matching: exact (incl. synonyms) -> taxonomy-related -> embedding-related.

Credits per JD skill:
  exact   : 1.0   candidate has the skill (or a synonym, e.g. "Postgres" == "PostgreSQL")
  related : 0.5   candidate has a transferable skill (taxonomy, e.g. PyTorch for TensorFlow)
  semantic: 0.5   embedding similarity of skill names >= threshold (for skills outside the taxonomy)
  missing : 0.0

skill_score = 100 * (mandatory_share * mandatory_coverage + (1 - mandatory_share) * preferred_coverage)
(if the JD lists only one of the two groups, that group gets 100% of the component).
"""
from app.core.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.services.skill_extractor import canonicalize, display_name, is_known, phrase_in_text, related_skills


def _match_one(skill: str, cand_keys: set[str], cand_display: list[str], resume_text: str,
               allow_semantic: bool) -> dict:
    s = get_settings()
    key = canonicalize(skill)
    # free-text phrase search only for custom skills outside the taxonomy (taxonomy skills were
    # already searched with ambiguity rules during extraction)
    if key in cand_keys or (not is_known(skill) and phrase_in_text(skill, resume_text)):
        return {"skill": display_name(skill), "match": "exact", "credit": 1.0, "via": None}
    rel = sorted(related_skills(key) & cand_keys)
    if rel:
        return {"skill": display_name(skill), "match": "related", "credit": s.related_skill_credit,
                "via": display_name(rel[0])}
    if allow_semantic and cand_display:
        svc = get_embedding_service()
        if svc.uses_transformer:
            sims = svc.similarity([display_name(skill)], cand_display)[0]
            best = int(sims.argmax())
            if sims[best] >= s.semantic_skill_threshold:
                return {"skill": display_name(skill), "match": "semantic", "credit": s.related_skill_credit,
                        "via": cand_display[best], "similarity": round(float(sims[best]), 3)}
    return {"skill": display_name(skill), "match": "missing", "credit": 0.0, "via": None}


def match_skills(required: list[str], preferred: list[str], cand_keys: list[str],
                 cand_display: list[str], resume_text: str) -> dict:
    s = get_settings()
    keys = set(cand_keys)
    req = [_match_one(sk, keys, cand_display, resume_text, True) for sk in required]
    pref = [_match_one(sk, keys, cand_display, resume_text, True) for sk in preferred]

    def coverage(items: list[dict]) -> float | None:
        return sum(i["credit"] for i in items) / len(items) if items else None

    req_cov, pref_cov = coverage(req), coverage(pref)
    if req_cov is None and pref_cov is None:
        return {"score": None, "available": False, "note": "No skills listed in the job description"}
    if req_cov is not None and pref_cov is not None:
        share = s.mandatory_skill_share
        score = share * req_cov + (1 - share) * pref_cov
        formula = f"{share:.0%} x mandatory coverage + {1 - share:.0%} x preferred coverage"
    else:
        score = req_cov if req_cov is not None else pref_cov
        formula = "100% mandatory coverage" if req_cov is not None else "100% preferred coverage"

    def names(items, kinds):
        return [i["skill"] for i in items if i["match"] in kinds]

    return {
        "score": round(score * 100, 1),
        "available": True,
        "formula": formula,
        "mandatory_coverage": round(req_cov * 100, 1) if req_cov is not None else None,
        "preferred_coverage": round(pref_cov * 100, 1) if pref_cov is not None else None,
        "mandatory": req,
        "preferred": pref,
        "matched_mandatory": names(req, {"exact"}),
        "related_mandatory": [i for i in req if i["match"] in ("related", "semantic")],
        "missing_mandatory": names(req, {"missing"}),
        "matched_preferred": names(pref, {"exact"}),
        "related_preferred": [i for i in pref if i["match"] in ("related", "semantic")],
        "missing_preferred": names(pref, {"missing"}),
    }
