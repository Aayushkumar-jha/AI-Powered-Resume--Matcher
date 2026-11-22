"""Explainable results: turns the calculated numbers into recruiter-readable statements.

Every sentence is generated from the actual extracted data and computed scores - nothing is
invented. The output is decision support for a human recruiter, not an automatic decision.
"""
from app.services.scoring_engine import COMPONENTS

LABELS = {"skills": "Skill match", "semantic": "Semantic similarity",
          "experience": "Experience", "education": "Education"}
DISCLAIMER = ("Scores indicate how closely the resume matches the job description text. They are not "
              "hiring probabilities and must not be used to automatically reject candidates. Personal "
              "attributes (age, gender, religion, caste, etc.) are never used in scoring.")


def _join(items: list[str], limit: int = 8) -> str:
    items = list(items)
    if len(items) > limit:
        return ", ".join(items[:limit]) + f" and {len(items) - limit} more"
    return ", ".join(items)


def build_explanation(name: str | None, final, skill: dict, semantic: dict, experience: dict,
                      education: dict, weights_used: dict, warnings: list[str]) -> dict:
    who = name or "The candidate"
    strengths, gaps, notes = [], [], []

    # --- Skills ---
    if skill.get("available"):
        n_req = len(skill.get("mandatory", []))
        if n_req:
            exact = skill["matched_mandatory"]
            if exact:
                strengths.append(f"Has {len(exact)} of {n_req} mandatory skills: {_join(exact)}")
            for r in skill.get("related_mandatory", []):
                how = "semantically similar skill" if r["match"] == "semantic" else "related skill"
                strengths.append(f"No direct '{r['skill']}' experience, but has {how} '{r['via']}' (partial credit)")
            if skill["missing_mandatory"]:
                gaps.append(f"Missing mandatory skill(s): {_join(skill['missing_mandatory'])}")
        if skill.get("matched_preferred"):
            strengths.append(f"Also has preferred skill(s): {_join(skill['matched_preferred'])}")
        if skill.get("missing_preferred"):
            gaps.append(f"Missing preferred skill(s): {_join(skill['missing_preferred'])}")
    else:
        notes.append(skill.get("note", "Skill component excluded"))

    # --- Experience ---
    if experience.get("available"):
        (strengths if (experience.get("score") or 0) >= 100 else gaps).append(experience["note"])
    else:
        notes.append(experience.get("note", "Experience component excluded"))

    # --- Education ---
    if education.get("available"):
        (strengths if (education.get("score") or 0) >= 80 else gaps).append(education["note"])
    else:
        notes.append(education.get("note", "Education component excluded"))

    # --- Semantic ---
    if semantic.get("available"):
        sc = semantic["score"]
        level = "high" if sc >= 70 else "moderate" if sc >= 45 else "low"
        best = semantic.get("best_section", "")
        statement = (f"Resume content shows {level} semantic similarity to the job description "
                     f"({sc:.0f}/100; strongest alignment in the '{best}' section)")
        (strengths if sc >= 55 else gaps).append(statement)
        ev = (semantic.get("top_evidence") or [None])[0]
        if ev and ev["similarity"] >= 0.45:
            strengths.append(f"Evidence: JD requirement \"{ev['requirement'][:90]}\" is reflected by "
                             f"\"{ev['resume_evidence'][:110]}\" (similarity {ev['similarity']:.2f})")
        if "tfidf" in semantic.get("method", ""):
            notes.append("Semantic score computed with TF-IDF fallback (embedding model unavailable)")
    else:
        notes.append(semantic.get("note", "Semantic component excluded"))

    if final.excluded:
        notes.append("Excluded component(s) " + ", ".join(LABELS[c] for c in final.excluded)
                     + " - remaining weights were re-normalized for all candidates")
    notes += [w for w in warnings if "personal-attribute" not in w][:4]

    breakdown = [
        {"component": LABELS[c], "key": c,
         "score": {"skills": skill, "semantic": semantic, "experience": experience,
                   "education": education}[c].get("score"),
         "weight": weights_used.get(c, 0.0),
         "contribution": final.contributions.get(c, 0.0)}
        for c in COMPONENTS
    ]
    formula = " + ".join(
        f"{b['score']:.1f} x {b['weight']:.2f}" for b in breakdown if b["score"] is not None and b["weight"] > 0
    ) + f" = {final.final_score:.1f}"

    summary = (f"{who} is a {final.fit_label.lower()} with an overall score of {final.final_score:.1f}/100. ")
    top = max((b for b in breakdown if b["score"] is not None), key=lambda b: b["contribution"], default=None)
    if top:
        summary += f"The largest contribution comes from {top['component'].lower()} ({top['score']:.0f}/100). "
    if skill.get("missing_mandatory"):
        summary += f"Key gaps: {_join(skill['missing_mandatory'], 4)}."
    elif skill.get("available"):
        summary += "All mandatory skills are present or covered by related skills."

    return {"summary": summary.strip(), "strengths": [s for s in strengths if s], "gaps": gaps,
            "notes": notes, "breakdown": breakdown, "formula": formula, "disclaimer": DISCLAIMER}
