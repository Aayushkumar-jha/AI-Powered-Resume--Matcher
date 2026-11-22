"""Weighted scoring engine.

Final Score = Skill x 0.40 + Semantic x 0.30 + Experience x 0.20 + Education x 0.10 (default weights)

* Every component is normalized to 0-100.
* Weights are configurable per job (normalized to sum to 1).
* If a component is UNAVAILABLE for the job (e.g. the JD states no education requirement), it is
  excluded and the remaining weights are re-normalized - identically for every candidate, so the
  ranking stays fair. The weights actually used are stored with each result.
* If information is missing in a RESUME, that component scores 0 and is flagged for manual review
  (the system never silently assumes a candidate meets a requirement).
"""
from dataclasses import dataclass

COMPONENTS = ("skills", "semantic", "experience", "education")

FIT_BANDS = [(75, "Strong match"), (55, "Moderate match"), (35, "Weak match"), (0, "Low match")]


def score_experience(required_min: float | None, required_max: float | None, candidate_years: float | None,
                     method: str = "date_ranges") -> dict:
    if required_min is None or required_min <= 0:
        if required_max is None:
            return {"score": None, "available": False,
                    "note": "Job description specifies no experience requirement; component excluded",
                    "candidate_years": candidate_years}
        required_min = 0.0
    if candidate_years is None:
        return {"score": 0.0, "available": True, "required_min": required_min, "required_max": required_max,
                "candidate_years": None, "gap_years": required_min,
                "note": "Experience could not be determined from the resume - verify manually"}

    if candidate_years >= required_min:
        score = 100.0
        note = f"{candidate_years} years meets the {required_min:g}+ years requirement"
        if required_max is not None and candidate_years > required_max + 3:
            score = 85.0
            note = (f"{candidate_years} years exceeds the {required_min:g}-{required_max:g} year range; "
                    "may be over-qualified for the level (minor adjustment)")
    else:
        # proportional credit: 3 of 5 required years -> 60
        score = round(100.0 * candidate_years / required_min, 1)
        note = f"{candidate_years} years vs {required_min:g} required ({required_min - candidate_years:.1f} years short)"
    if method == "stated":
        note += " (based on stated years in summary)"
    return {"score": score, "available": True, "required_min": required_min, "required_max": required_max,
            "candidate_years": candidate_years, "gap_years": round(max(0.0, required_min - candidate_years), 1),
            "note": note}


@dataclass
class FinalScore:
    final_score: float
    weights_used: dict[str, float]
    excluded: list[str]
    contributions: dict[str, float]
    fit_label: str


def fit_label(score: float) -> str:
    for threshold, label in FIT_BANDS:
        if score >= threshold:
            return label
    return FIT_BANDS[-1][1]


def combine_scores(components: dict[str, float | None], weights: dict[str, float]) -> FinalScore:
    """components: {"skills": 0-100 | None, ...}. None = unavailable -> excluded and re-weighted."""
    available = {c: v for c, v in components.items() if c in COMPONENTS and v is not None}
    excluded = [c for c in COMPONENTS if components.get(c) is None]
    total_w = sum(weights.get(c, 0.0) for c in available)
    if not available or total_w <= 0:
        return FinalScore(0.0, {c: 0.0 for c in COMPONENTS}, excluded, {}, fit_label(0.0))
    used = {c: (weights.get(c, 0.0) / total_w if c in available else 0.0) for c in COMPONENTS}
    contributions = {c: round(available[c] * used[c], 2) for c in available}
    final = round(sum(available[c] * used[c] for c in available), 1)
    final = max(0.0, min(100.0, final))
    return FinalScore(final, {c: round(w, 4) for c, w in used.items()}, excluded, contributions, fit_label(final))
