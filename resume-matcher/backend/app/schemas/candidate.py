from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ResumeUploadResult(BaseModel):
    filename: str
    resume_id: int | None = None
    candidate_id: int | None = None
    status: str  # parsed | failed | duplicate | unsupported
    error: str | None = None
    candidate_name: str | None = None
    warnings: list[str] = []


class BatchUploadResponse(BaseModel):
    job_id: int
    total: int
    parsed: int
    failed: int
    results: list[ResumeUploadResult]


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    file_size: int
    status: str
    error_message: str | None
    uploaded_at: datetime
    candidate_id: int | None = None
    candidate_name: str | None = None


class CandidateInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    email: str | None
    phone: str | None
    summary: str | None
    skills: list[str]
    education: list[dict[str, Any]]
    highest_education: str | None
    experience_years: float | None
    employment_history: list[dict[str, Any]]
    projects: list[str]
    certifications: list[str]
    warnings: list[str]


class ScoreBreakdown(BaseModel):
    final_score: float
    skill_score: float | None
    semantic_score: float | None
    experience_score: float | None
    education_score: float | None
    weights_used: dict[str, float]
    fit_label: str
    rank: int | None


class RankedCandidate(BaseModel):
    rank: int | None
    candidate_id: int | None
    resume_id: int
    filename: str
    name: str | None
    email: str | None
    experience_years: float | None
    highest_education: str | None
    final_score: float | None
    skill_score: float | None
    semantic_score: float | None
    experience_score: float | None
    education_score: float | None
    fit_label: str | None
    matched_skills: list[str]
    missing_skills: list[str]
    status: str  # resume status, or "analyzed" / "pending_analysis"
    error: str | None = None


class CandidateAnalysis(BaseModel):
    job_id: int
    job_title: str
    candidate: CandidateInfo
    filename: str
    scores: ScoreBreakdown | None
    skill_details: dict[str, Any] = {}
    semantic_details: dict[str, Any] = {}
    experience_details: dict[str, Any] = {}
    education_details: dict[str, Any] = {}
    explanation: dict[str, Any] = {}


class AnalysisStatus(BaseModel):
    job_id: int
    status: str
    total: int
    done: int
    progress: float
    error: str | None
    analyzed_at: datetime | None


class DashboardStats(BaseModel):
    job_id: int
    job_title: str
    total_candidates: int
    processed: int
    failed: int
    analyzed: int
    average_score: float | None
    highest_score: float | None
    lowest_score: float | None
    fit_distribution: dict[str, int]
    score_distribution: list[dict[str, Any]]
    top_missing_skills: list[dict[str, Any]]
    component_averages: dict[str, float | None]
    analysis_status: str
