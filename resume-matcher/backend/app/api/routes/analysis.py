"""Analysis, ranking, candidate-level analysis, comparison, dashboard and CSV export endpoints."""
import csv
import io
from collections import Counter
from statistics import mean
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.jobs import get_job_or_404
from app.core.security import safe_filename
from app.db.database import get_db
from app.db.models import Candidate, MatchResult, Resume
from app.schemas.candidate import (
    AnalysisStatus,
    CandidateAnalysis,
    CandidateInfo,
    DashboardStats,
    RankedCandidate,
    ScoreBreakdown,
)
from app.schemas.job import JobRequirements
from app.services.analysis_pipeline import run_analysis

router = APIRouter(prefix="/jobs/{job_id}", tags=["Analysis & Ranking"])

SortField = Literal["rank", "final_score", "skill_score", "semantic_score", "experience_score",
                    "education_score", "experience_years", "name"]


@router.post("/analyze", response_model=AnalysisStatus, status_code=status.HTTP_202_ACCEPTED,
             summary="Start (or re-run) matching analysis in the background")
def start_analysis(job_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    if job.analysis_status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Analysis already in progress")
    req = JobRequirements(**(job.requirements or {}))
    if not (req.required_skills or req.preferred_skills or req.responsibilities):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Job has no skills or responsibilities to match against; edit requirements first")
    n = db.scalar(select(func.count(Candidate.id)).where(Candidate.job_id == job_id)) or 0
    if n == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No successfully parsed resumes to analyze")
    job.analysis_status, job.analysis_total, job.analysis_done, job.analysis_error = "processing", n, 0, None
    db.commit()
    background.add_task(run_analysis, job_id)
    return _status(job)


def _status(job) -> AnalysisStatus:
    progress = (job.analysis_done / job.analysis_total * 100) if job.analysis_total else 0.0
    return AnalysisStatus(job_id=job.id, status=job.analysis_status, total=job.analysis_total,
                          done=job.analysis_done, progress=round(progress, 1), error=job.analysis_error,
                          analyzed_at=job.analyzed_at)


@router.get("/status", response_model=AnalysisStatus, summary="Check analysis progress")
def analysis_status(job_id: int, db: Session = Depends(get_db)):
    return _status(get_job_or_404(db, job_id))


def _ranked_rows(db: Session, job_id: int) -> list[RankedCandidate]:
    rows = db.execute(
        select(Resume, Candidate, MatchResult)
        .outerjoin(Candidate, Candidate.resume_id == Resume.id)
        .outerjoin(MatchResult, MatchResult.candidate_id == Candidate.id)
        .where(Resume.job_id == job_id)
    ).all()
    out = []
    for r, c, m in rows:
        sd = (m.skill_details if m else {}) or {}
        matched = sd.get("matched_mandatory", []) + sd.get("matched_preferred", [])
        related = [f"{i['skill']} (~{i['via']})" for i in sd.get("related_mandatory", [])]
        out.append(RankedCandidate(
            rank=m.rank if m else None, candidate_id=c.id if c else None, resume_id=r.id,
            filename=r.original_filename, name=c.name if c else None, email=c.email if c else None,
            experience_years=c.experience_years if c else None,
            highest_education=c.highest_education if c else None,
            final_score=m.final_score if m else None, skill_score=m.skill_score if m else None,
            semantic_score=m.semantic_score if m else None, experience_score=m.experience_score if m else None,
            education_score=m.education_score if m else None, fit_label=m.fit_label if m else None,
            matched_skills=matched + related,
            missing_skills=sd.get("missing_mandatory", []) + sd.get("missing_preferred", []),
            status=("analyzed" if m else "pending_analysis") if r.status == "parsed" else r.status,
            error=r.error_message,
        ))
    return out


@router.get("/candidates", response_model=list[RankedCandidate],
            summary="Ranked candidates with search, filtering and sorting")
def ranked_candidates(
    job_id: int,
    db: Session = Depends(get_db),
    search: str | None = Query(None, max_length=100, description="Name, email, filename or skill"),
    min_score: float | None = Query(None, ge=0, le=100),
    max_score: float | None = Query(None, ge=0, le=100),
    fit: str | None = Query(None, description="e.g. 'Strong match'"),
    status_filter: str | None = Query(None, alias="status"),
    skill: str | None = Query(None, max_length=60, description="Only candidates who matched this skill"),
    min_experience: float | None = Query(None, ge=0),
    sort_by: SortField = "rank",
    order: Literal["asc", "desc"] | None = None,
):
    get_job_or_404(db, job_id)
    rows = _ranked_rows(db, job_id)
    if search:
        s = search.lower()
        rows = [r for r in rows if s in (r.name or "").lower() or s in (r.email or "").lower()
                or s in r.filename.lower() or any(s in m.lower() for m in r.matched_skills)]
    if min_score is not None:
        rows = [r for r in rows if r.final_score is not None and r.final_score >= min_score]
    if max_score is not None:
        rows = [r for r in rows if r.final_score is not None and r.final_score <= max_score]
    if fit:
        rows = [r for r in rows if (r.fit_label or "").lower() == fit.lower()]
    if status_filter:
        rows = [r for r in rows if r.status == status_filter]
    if skill:
        sk = skill.lower()
        rows = [r for r in rows if any(m.lower().startswith(sk) for m in r.matched_skills)]
    if min_experience is not None:
        rows = [r for r in rows if (r.experience_years or 0) >= min_experience]

    if sort_by == "rank":
        default_order = "asc"
    elif sort_by == "name":
        default_order = "asc"
    else:
        default_order = "desc"
    reverse = (order or default_order) == "desc"
    present = [r for r in rows if getattr(r, sort_by) is not None]
    missing = [r for r in rows if getattr(r, sort_by) is None]
    key = (lambda r: (r.name or "").lower()) if sort_by == "name" else (lambda r: getattr(r, sort_by))
    return sorted(present, key=key, reverse=reverse) + missing  # unscored/failed always last


@router.get("/candidates/{candidate_id}", response_model=CandidateAnalysis,
            summary="Detailed, explainable analysis for one candidate")
def candidate_analysis(job_id: int, candidate_id: int, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    c = db.scalar(select(Candidate).where(Candidate.id == candidate_id, Candidate.job_id == job_id))
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found for this job")
    m = c.match_result
    scores = None
    if m:
        scores = ScoreBreakdown(final_score=m.final_score, skill_score=m.skill_score,
                                semantic_score=m.semantic_score, experience_score=m.experience_score,
                                education_score=m.education_score, weights_used=m.weights_used,
                                fit_label=m.fit_label, rank=m.rank)
    return CandidateAnalysis(
        job_id=job.id, job_title=job.title, candidate=CandidateInfo.model_validate(c),
        filename=c.resume.original_filename, scores=scores,
        skill_details=m.skill_details if m else {}, semantic_details=m.semantic_details if m else {},
        experience_details=m.experience_details if m else {},
        education_details=m.education_details if m else {}, explanation=m.explanation if m else {},
    )


@router.get("/compare", response_model=list[CandidateAnalysis], summary="Compare 2-4 candidates side by side")
def compare(job_id: int, ids: str = Query(..., description="Comma-separated candidate ids, e.g. 3,5,9"),
            db: Session = Depends(get_db)):
    try:
        id_list = list(dict.fromkeys(int(x) for x in ids.split(",") if x.strip()))
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ids must be comma-separated integers") from exc
    if not 2 <= len(id_list) <= 4:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Select between 2 and 4 candidates to compare")
    return [candidate_analysis(job_id, cid, db) for cid in id_list]


@router.get("/dashboard", response_model=DashboardStats, summary="Dashboard statistics")
def dashboard(job_id: int, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    resumes = db.scalars(select(Resume).where(Resume.job_id == job_id)).all()
    results = db.scalars(select(MatchResult).where(MatchResult.job_id == job_id)).all()
    scores = [m.final_score for m in results]

    buckets = [{"range": f"{lo}-{lo + 9 if lo < 90 else 100}", "min": lo, "count": 0} for lo in range(0, 100, 10)]
    for s in scores:
        buckets[min(int(s // 10), 9)]["count"] += 1
    fit = Counter(m.fit_label for m in results)
    missing = Counter(sk for m in results for sk in (m.skill_details or {}).get("missing_mandatory", []))

    def avg(attr: str) -> float | None:
        vals = [getattr(m, attr) for m in results if getattr(m, attr) is not None]
        return round(mean(vals), 1) if vals else None

    return DashboardStats(
        job_id=job.id, job_title=job.title, total_candidates=len(resumes),
        processed=sum(r.status == "parsed" for r in resumes),
        failed=sum(r.status != "parsed" for r in resumes), analyzed=len(results),
        average_score=round(mean(scores), 1) if scores else None,
        highest_score=max(scores) if scores else None, lowest_score=min(scores) if scores else None,
        fit_distribution={label: fit.get(label, 0) for label in
                          ("Strong match", "Moderate match", "Weak match", "Low match")},
        score_distribution=buckets,
        top_missing_skills=[{"skill": k, "count": v} for k, v in missing.most_common(8)],
        component_averages={"skills": avg("skill_score"), "semantic": avg("semantic_score"),
                            "experience": avg("experience_score"), "education": avg("education_score")},
        analysis_status=job.analysis_status,
    )


def _csv_safe(value) -> str:
    """Prevent CSV/formula injection when opened in Excel."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


@router.get("/export", summary="Export ranked results as CSV")
def export_csv(job_id: int, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    rows = ranked_candidates(job_id, db, None, None, None, None, None, None, None, "rank", None)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Rank", "Name", "Email", "File", "Experience (yrs)", "Highest Education", "Final Score",
                "Skill Score", "Semantic Score", "Experience Score", "Education Score", "Fit",
                "Matched Skills", "Missing Skills", "Status", "Error"])
    for r in rows:
        w.writerow([_csv_safe(x) for x in [
            r.rank, r.name, r.email, r.filename, r.experience_years, r.highest_education, r.final_score,
            r.skill_score, r.semantic_score, r.experience_score, r.education_score, r.fit_label,
            "; ".join(r.matched_skills), "; ".join(r.missing_skills), r.status, r.error]])
    filename = safe_filename(f"{job.title}_ranking.csv").replace(" ", "_")
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
