"""Resume endpoints: batch upload, list, extracted info, download (authorized), delete, stateless parse."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.jobs import get_job_or_404
from app.core.config import get_settings
from app.core.security import resolve_stored, safe_filename
from app.db.database import get_db
from app.db.models import Resume
from app.schemas.candidate import BatchUploadResponse, CandidateInfo, ResumeOut, ResumeUploadResult
from app.services.document_parser import DocumentParseError, extract_text
from app.services.resume_parser import parse_resume
from app.services.resume_service import process_resume_file

router = APIRouter(tags=["Resumes"])


def _resume_or_404(db: Session, job_id: int, resume_id: int) -> Resume:
    # Scoped lookup: a resume is only reachable through the job it belongs to
    r = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.job_id == job_id))
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found for this job")
    return r


@router.post("/jobs/{job_id}/resumes", response_model=BatchUploadResponse,
             status_code=status.HTTP_207_MULTI_STATUS,
             summary="Upload multiple resumes (PDF/DOCX). Each file is processed independently.")
async def upload_resumes(job_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    settings = get_settings()
    job = get_job_or_404(db, job_id)
    if job.analysis_status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Analysis is running; upload after it finishes")
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No files provided")
    if len(files) > settings.max_files_per_batch:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"Too many files: maximum {settings.max_files_per_batch} per batch")

    results: list[ResumeUploadResult] = []
    for f in files:
        try:
            content = await f.read(settings.max_file_size_bytes + 1)
            results.append(process_resume_file(db, job, f.filename or "resume", content))
        except Exception as exc:  # database or I/O issue for this file only
            db.rollback()
            results.append(ResumeUploadResult(filename=safe_filename(f.filename or "resume"),
                                              status="failed", error=f"Server error: {exc}"))
        finally:
            await f.close()

    if job.analysis_status == "completed":
        job.analysis_status = "outdated"
        db.commit()
    parsed = sum(r.status == "parsed" for r in results)
    return BatchUploadResponse(job_id=job_id, total=len(results), parsed=parsed,
                               failed=len(results) - parsed, results=results)


@router.get("/jobs/{job_id}/resumes", response_model=list[ResumeOut], summary="List resumes and processing status")
def list_resumes(job_id: int, db: Session = Depends(get_db)):
    get_job_or_404(db, job_id)
    rows = db.scalars(select(Resume).where(Resume.job_id == job_id).order_by(Resume.uploaded_at)).all()
    return [ResumeOut.model_validate(r).model_copy(update={
        "candidate_id": r.candidate.id if r.candidate else None,
        "candidate_name": r.candidate.name if r.candidate else None}) for r in rows]


@router.get("/jobs/{job_id}/resumes/{resume_id}", response_model=CandidateInfo,
            summary="Extracted candidate information for a resume")
def get_resume_extraction(job_id: int, resume_id: int, db: Session = Depends(get_db)):
    r = _resume_or_404(db, job_id, resume_id)
    if not r.candidate:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Resume was not parsed ({r.status}): {r.error_message}")
    return CandidateInfo.model_validate(r.candidate)


@router.get("/jobs/{job_id}/resumes/{resume_id}/file", summary="Download the original resume file")
def download_resume(job_id: int, resume_id: int, db: Session = Depends(get_db)):
    r = _resume_or_404(db, job_id, resume_id)
    if not r.stored_filename:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No stored file for this resume")
    try:
        path = resolve_stored(r.stored_filename)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid file path") from exc
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File missing from storage")
    media = "application/pdf" if r.file_type == "pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media, filename=r.original_filename)


@router.delete("/jobs/{job_id}/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a resume and its candidate/match data")
def delete_resume(job_id: int, resume_id: int, db: Session = Depends(get_db)):
    r = _resume_or_404(db, job_id, resume_id)
    if r.stored_filename:
        try:
            resolve_stored(r.stored_filename).unlink(missing_ok=True)
        except (ValueError, OSError):
            pass
    db.delete(r)
    db.commit()


@router.post("/resumes/parse", response_model=dict,
             summary="Stateless extraction preview for a single resume (nothing is stored)")
async def parse_single(file: UploadFile = File(...)):
    settings = get_settings()
    content = await file.read(settings.max_file_size_bytes + 1)
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    try:
        ftype, text = extract_text(safe_filename(file.filename or "resume"), content)
    except DocumentParseError as exc:
        code = 415 if exc.status == "unsupported" else 422
        raise HTTPException(code, str(exc)) from exc
    data = parse_resume(text).to_dict()
    data.pop("sections", None)
    return {"file_type": ftype, **data}
