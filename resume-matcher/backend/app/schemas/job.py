from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EDUCATION_LEVELS = ["high_school", "diploma", "associate", "bachelor", "master", "phd"]


class ScoringWeights(BaseModel):
    """Weights of the four score components. Any positive values are accepted and
    normalized so they sum to 1.0."""

    skills: float = Field(0.40, ge=0, le=100)
    semantic: float = Field(0.30, ge=0, le=100)
    experience: float = Field(0.20, ge=0, le=100)
    education: float = Field(0.10, ge=0, le=100)

    @model_validator(mode="after")
    def _normalize(self) -> "ScoringWeights":
        total = self.skills + self.semantic + self.experience + self.education
        if total <= 0:
            raise ValueError("At least one weight must be greater than zero")
        if abs(total - 1.0) > 1e-6:
            self.skills, self.semantic = self.skills / total, self.semantic / total
            self.experience, self.education = self.experience / total, self.education / total
        return self


def _clean_list(values: list[str]) -> list[str]:
    seen, out = set(), []
    for v in values:
        v = (v or "").strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


class JobRequirements(BaseModel):
    title: str = "Untitled Position"
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: float | None = Field(None, ge=0, le=60)
    max_experience_years: float | None = Field(None, ge=0, le=60)
    education_level: str | None = None
    education_fields: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)

    @field_validator("required_skills", "preferred_skills", "education_fields",
                     "qualifications", "responsibilities")
    @classmethod
    def _dedupe(cls, v: list[str]) -> list[str]:
        return _clean_list(v)

    @field_validator("education_level")
    @classmethod
    def _valid_level(cls, v: str | None) -> str | None:
        if v in (None, "", "none"):
            return None
        if v not in EDUCATION_LEVELS:
            raise ValueError(f"education_level must be one of {EDUCATION_LEVELS}")
        return v

    @model_validator(mode="after")
    def _check_range(self) -> "JobRequirements":
        lo, hi = self.min_experience_years, self.max_experience_years
        if lo is not None and hi is not None and hi < lo:
            raise ValueError("max_experience_years must be >= min_experience_years")
        # A skill cannot be both mandatory and preferred
        req = {s.lower() for s in self.required_skills}
        self.preferred_skills = [s for s in self.preferred_skills if s.lower() not in req]
        return self


class JobCreate(BaseModel):
    raw_text: str = Field(..., min_length=30, max_length=50_000)
    title: str | None = Field(None, max_length=255)


class JobUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    requirements: JobRequirements | None = None
    weights: ScoringWeights | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    raw_text: str
    source_filename: str | None
    requirements: JobRequirements
    weights: ScoringWeights
    analysis_status: str
    analysis_total: int
    analysis_done: int
    analysis_error: str | None
    analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    resume_count: int = 0


class JobSummary(BaseModel):
    id: int
    title: str
    analysis_status: str
    resume_count: int
    created_at: datetime
