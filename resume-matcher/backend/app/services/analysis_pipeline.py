"""Background analysis job: scores every parsed candidate of a job and ranks them."""
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db.database import SessionLocal
from app.db.models import Candidate, Job, MatchResult
from app.schemas.job import JobRequirements, ScoringWeights
from app.services.matching_service import analyze_candidate
from app.services.ranking_service import assign_ranks
from app.services.skill_extractor import extract_skills

log = logging.getLogger(__name__)


def candidate_payload(c: Candidate) -> dict:
    raw = c.resume.raw_text or ""
    return {
        "name": c.name,
        "skill_keys": extract_skills(raw, skills_section=(c.sections or {}).get("skills")),
        "skills": c.skills or [],
        "sections": {k: v for k, v in (c.sections or {}).items()},
        "raw_text": raw,
        "experience_years": c.experience_years,
        "experience_method": "date_ranges" if c.employment_history else
                             ("stated" if c.experience_years is not None else "not_found"),
        "education": c.education or [],
        "warnings": c.warnings or [],
    }


def run_analysis(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        req = JobRequirements(**(job.requirements or {}))
        weights = ScoringWeights(**(job.weights or {})).model_dump()
        candidates = db.scalars(select(Candidate).where(Candidate.job_id == job_id)).all()

        db.execute(delete(MatchResult).where(MatchResult.job_id == job_id))
        job.analysis_total, job.analysis_done, job.analysis_error = len(candidates), 0, None
        db.commit()

        errors, results = [], []
        for cand in candidates:
            try:
                data = analyze_candidate(req, job.raw_text, weights, candidate_payload(cand))
                mr = MatchResult(job_id=job_id, candidate_id=cand.id, **data)
                db.add(mr)
                results.append(mr)
            except Exception as exc:  # isolate failures per candidate
                log.exception("Analysis failed for candidate %s", cand.id)
                errors.append(f"{cand.name or cand.resume.original_filename}: {exc}")
            job.analysis_done += 1
            db.commit()

        assign_ranks(results)
        job.analysis_status = "completed"
        job.analysis_error = "; ".join(errors) or None
        job.analyzed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        log.exception("Analysis failed for job %s", job_id)
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.analysis_status, job.analysis_error = "failed", str(exc)
            db.commit()
    finally:
        db.close()
