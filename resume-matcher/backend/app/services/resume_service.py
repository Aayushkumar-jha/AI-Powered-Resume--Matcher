"""Batch resume ingestion: validation -> duplicate detection -> secure storage -> parsing.

Each file is processed independently (partial batch processing): one corrupted file never
stops the rest of the batch, and every file gets its own status + error message.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import safe_filename, sha256, store_file
from app.db.models import Candidate, Job, Resume
from app.schemas.candidate import ResumeUploadResult
from app.services.document_parser import DocumentParseError, extract_text
from app.services.resume_parser import parse_resume

log = logging.getLogger(__name__)


def process_resume_file(db: Session, job: Job, filename: str, content: bytes) -> ResumeUploadResult:
    settings = get_settings()
    display = safe_filename(filename)
    ext = display.rsplit(".", 1)[-1].lower() if "." in display else ""
    resume = Resume(job_id=job.id, original_filename=display, file_type=ext[:10] or "unknown",
                    file_size=len(content))

    def fail(status: str, message: str) -> ResumeUploadResult:
        resume.status, resume.error_message = status, message
        db.add(resume)
        db.commit()
        return ResumeUploadResult(filename=display, resume_id=resume.id, status=status, error=message)

    if len(content) > settings.max_file_size_bytes:
        return fail("failed", f"File exceeds the {settings.max_file_size_mb:g} MB size limit")

    try:
        ftype, text = extract_text(display, content)
    except DocumentParseError as exc:
        return fail(exc.status, str(exc))

    digest = sha256(content)
    resume.file_hash = digest
    dup = db.scalar(select(Resume).where(Resume.job_id == job.id, Resume.file_hash == digest,
                                         Resume.status == "parsed"))
    if dup:
        return fail("duplicate", f"Duplicate file: identical to '{dup.original_filename}' already uploaded")

    try:
        resume.stored_filename = store_file(job.id, ftype, content)
        parsed = parse_resume(text)
    except Exception as exc:  # unexpected parser bug -> isolate to this file
        log.exception("Failed to parse %s", display)
        return fail("failed", f"Unexpected error while parsing: {exc}")

    warnings = list(parsed.warnings)
    if parsed.email:
        same = db.scalar(select(Candidate).where(Candidate.job_id == job.id, Candidate.email == parsed.email))
        if same:
            warnings.append(f"Possible duplicate candidate: same email as resume #{same.resume_id}")

    resume.file_type, resume.raw_text, resume.status = ftype, text, "parsed"
    db.add(resume)
    db.flush()
    candidate = Candidate(
        job_id=job.id, resume_id=resume.id, name=parsed.name, email=parsed.email, phone=parsed.phone,
        summary=parsed.summary, skills=parsed.skills, education=parsed.education,
        highest_education=parsed.highest_education, experience_years=parsed.experience_years,
        employment_history=parsed.employment_history, projects=parsed.projects,
        certifications=parsed.certifications, sections=parsed.sections, warnings=warnings,
    )
    db.add(candidate)
    db.commit()
    return ResumeUploadResult(filename=display, resume_id=resume.id, candidate_id=candidate.id,
                              status="parsed", candidate_name=parsed.name, warnings=warnings)
