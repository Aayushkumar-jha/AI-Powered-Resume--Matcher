"""Database models: Job -> Resume -> Candidate -> MatchResult.

    jobs (1) ──< resumes (1) ── (1) candidates (1) ── (1) match_results
      └──────────────────────────────< candidates
      └──────────────────────────────────────────────< match_results
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# JSONB on PostgreSQL, plain JSON elsewhere (e.g. SQLite in quick tests)
JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="Untitled Position")
    raw_text: Mapped[str] = mapped_column(Text)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Structured, recruiter-editable requirements (see schemas.job.JobRequirements)
    requirements: Mapped[dict] = mapped_column(JSONType, default=dict)
    weights: Mapped[dict] = mapped_column(JSONType, default=dict)

    # idle | processing | completed | outdated | failed
    analysis_status: Mapped[str] = mapped_column(String(20), default="idle")
    analysis_total: Mapped[int] = mapped_column(Integer, default=0)
    analysis_done: Mapped[int] = mapped_column(Integer, default=0)
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class Resume(Base):
    """An uploaded resume file and its parsing status."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(10))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # parsed | failed | duplicate | unsupported
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="resumes")
    candidate: Mapped["Candidate | None"] = relationship(
        back_populates="resume", cascade="all, delete-orphan", uselist=False
    )


class Candidate(Base):
    """Structured information extracted from a resume."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list] = mapped_column(JSONType, default=list)
    education: Mapped[list] = mapped_column(JSONType, default=list)
    highest_education: Mapped[str | None] = mapped_column(String(50), nullable=True)
    experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    employment_history: Mapped[list] = mapped_column(JSONType, default=list)
    projects: Mapped[list] = mapped_column(JSONType, default=list)
    certifications: Mapped[list] = mapped_column(JSONType, default=list)
    sections: Mapped[dict] = mapped_column(JSONType, default=dict)
    warnings: Mapped[list] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="candidates")
    resume: Mapped[Resume] = relationship(back_populates="candidate")
    match_result: Mapped["MatchResult | None"] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", uselist=False
    )


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_match_job_candidate"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))

    final_score: Mapped[float] = mapped_column(Float, index=True)
    skill_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fit_label: Mapped[str] = mapped_column(String(30), default="")

    weights_used: Mapped[dict] = mapped_column(JSONType, default=dict)
    skill_details: Mapped[dict] = mapped_column(JSONType, default=dict)
    semantic_details: Mapped[dict] = mapped_column(JSONType, default=dict)
    experience_details: Mapped[dict] = mapped_column(JSONType, default=dict)
    education_details: Mapped[dict] = mapped_column(JSONType, default=dict)
    explanation: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="match_results")
    candidate: Mapped[Candidate] = relationship(back_populates="match_result")
