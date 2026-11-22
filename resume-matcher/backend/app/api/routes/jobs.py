"""Job description endpoints: create (text / file), list, get, edit requirements & weights, delete."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import safe_filename
from app.db.database import get_db
from app.db.models import Job, Resume
from app.schemas.job import JobCreate, JobOut, JobRequirements, JobSummary, JobUpdate, ScoringWeights
from app.services.document_parser import DocumentParseError, extract_text
from app.services.jd_extractor import extract_job_requirements

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Job {job_id} not found")
    return job


def to_out(db: Session, job: Job) -> JobOut:
    count = db.scalar(select(func.count(Resume.id)).where(Resume.job_id == job.id)) or 0
    return JobOut(
        id=job.id, title=job.title, raw_text=job.raw_text, source_filename=job.source_filename,
        requirements=JobRequirements(**(job.requirements or {})),
        weights=ScoringWeights(**(job.weights or {})),
        analysis_status=job.analysis_status, analysis_total=job.analysis_total,
        analysis_done=job.analysis_done, analysis_error=job.analysis_error, analyzed_at=job.analyzed_at,
        created_at=job.created_at, updated_at=job.updated_at, resume_count=count,
    )


def _create(db: Session, raw_text: str, title: str | None, source: str | None) -> Job:
    req = extract_job_requirements(raw_text)
    if title:
        req.title = title
    job = Job(title=req.title, raw_text=raw_text, source_filename=source,
              requirements=req.model_dump(), weights=get_settings().default_weights)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED,
             summary="Create a job from pasted JD text (requirements are auto-extracted)")
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    return to_out(db, _create(db, payload.raw_text, payload.title, None))


@router.post("/upload", response_model=JobOut, status_code=status.HTTP_201_CREATED,
             summary="Create a job from an uploaded JD document (PDF/DOCX)")
async def upload_job(file: UploadFile = File(...), title: str | None = Form(None),
                     db: Session = Depends(get_db)):
    settings = get_settings()
    content = await file.read(settings.max_file_size_bytes + 1)
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File exceeds {settings.max_file_size_mb:g} MB")
    name = safe_filename(file.filename or "jd")
    try:
        _, text = extract_text(name, content)
    except DocumentParseError as exc:
        code = (status.HTTP_415_UNSUPPORTED_MEDIA_TYPE if exc.status == "unsupported"
                else status.HTTP_422_UNPROCESSABLE_ENTITY)
        raise HTTPException(code, str(exc)) from exc
    return to_out(db, _create(db, text, title, name))


@router.post("/extract", response_model=JobRequirements,
             summary="Preview structured extraction for JD text without saving")
def extract_preview(payload: JobCreate):
    return extract_job_requirements(payload.raw_text)


@router.get("", response_model=list[JobSummary], summary="List jobs")
def list_jobs(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Job, func.count(Resume.id)).outerjoin(Resume).group_by(Job.id).order_by(Job.created_at.desc())
    ).all()
    return [JobSummary(id=j.id, title=j.title, analysis_status=j.analysis_status, resume_count=c,
                       created_at=j.created_at) for j, c in rows]


@router.get("/{job_id}", response_model=JobOut, summary="Get a job with its structured requirements")
def get_job(job_id: int, db: Session = Depends(get_db)):
    return to_out(db, get_job_or_404(db, job_id))


@router.put("/{job_id}", response_model=JobOut,
            summary="Edit extracted requirements and/or scoring weights (re-run analysis afterwards)")
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)):
    job = get_job_or_404(db, job_id)
    if job.analysis_status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Analysis is running; wait until it finishes")
    changed = False
    if payload.requirements is not None:
        job.requirements = payload.requirements.model_dump()
        job.title = payload.requirements.title
        changed = True
    if payload.title:
        job.title = payload.title
        job.requirements = {**job.requirements, "title": payload.title}
    if payload.weights is not None:
        job.weights = payload.weights.model_dump()
        changed = True
    if changed and job.analysis_status == "completed":
        job.analysis_status = "outdated"  # results no longer reflect current settings
    db.commit()
    db.refresh(job)
    return to_out(db, job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a job and its data")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    from app.core.security import resolve_stored

    job = get_job_or_404(db, job_id)
    for r in job.resumes:
        if r.stored_filename:
            try:
                resolve_stored(r.stored_filename).unlink(missing_ok=True)
            except (ValueError, OSError):
                pass
    db.delete(job)
    db.commit()
