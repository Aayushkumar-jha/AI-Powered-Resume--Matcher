"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "AI Resume Matcher"
    environment: str = "development"

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/resume_matcher"

    # Storage & upload limits
    upload_dir: Path = BACKEND_DIR / "storage" / "uploads"
    max_file_size_mb: float = 5.0
    max_files_per_batch: int = 50

    # Security
    # When set, every /api request must send header `X-API-Key: <value>`.
    api_key: str | None = None
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # NLP
    spacy_model: str = "en_core_web_sm"
    embedding_model: str = "all-MiniLM-L6-v2"
    # "sentence-transformers" (default) or "tfidf" (offline/lightweight fallback)
    embedding_backend: str = "sentence-transformers"

    # Default scoring weights (must sum to 1.0)
    weight_skills: float = 0.40
    weight_semantic: float = 0.30
    weight_experience: float = 0.20
    weight_education: float = 0.10

    # Inside the skill component: share of mandatory vs preferred skills
    mandatory_skill_share: float = Field(0.75, ge=0, le=1)
    related_skill_credit: float = Field(0.5, ge=0, le=1)
    semantic_skill_threshold: float = Field(0.70, ge=0, le=1)

    @field_validator("upload_dir")
    @classmethod
    def _absolute_upload_dir(cls, v: Path) -> Path:
        return v if v.is_absolute() else (BACKEND_DIR / v).resolve()

    @field_validator("api_key")
    @classmethod
    def _empty_key_is_none(cls, v: str | None) -> str | None:
        return v or None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return int(self.max_file_size_mb * 1024 * 1024)

    @property
    def default_weights(self) -> dict[str, float]:
        return {
            "skills": self.weight_skills,
            "semantic": self.weight_semantic,
            "experience": self.weight_experience,
            "education": self.weight_education,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
