"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.api.routes import analysis, jobs, resumes
from app.core.config import get_settings
from app.core.security import require_api_key
from app.db.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    try:
        init_db()
        log.info("Database ready")
    except OperationalError as exc:
        log.error("Database unavailable at startup: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-based resume matching & candidate ranking (hybrid NLP + explainable weighted scoring). "
                "Scores support - never replace - human recruitment decisions.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(OperationalError)
async def db_unavailable(_: Request, exc: OperationalError):
    log.error("Database error: %s", exc)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={"detail": "Database is unavailable. Check DATABASE_URL and that PostgreSQL is running."})


@app.exception_handler(SQLAlchemyError)
async def db_error(_: Request, exc: SQLAlchemyError):
    log.exception("Database error")
    return JSONResponse(status_code=500, content={"detail": "A database error occurred."})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"detail": "Validation failed", "errors": errors})


protected = [Depends(require_api_key)]
app.include_router(jobs.router, prefix="/api", dependencies=protected)
app.include_router(resumes.router, prefix="/api", dependencies=protected)
app.include_router(analysis.router, prefix="/api", dependencies=protected)


@app.get("/api/health", tags=["Health"])
def health():
    from sqlalchemy import text

    from app.db.database import engine
    from app.services.embedding_service import get_embedding_service

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok,
            "embedding_backend": get_embedding_service().backend_name,
            "auth_required": bool(settings.api_key)}


@app.get("/api/config/defaults", tags=["Health"], dependencies=protected)
def default_config():
    return {"weights": settings.default_weights, "max_file_size_mb": settings.max_file_size_mb,
            "max_files_per_batch": settings.max_files_per_batch, "allowed_types": ["pdf", "docx"],
            "mandatory_skill_share": settings.mandatory_skill_share,
            "related_skill_credit": settings.related_skill_credit}
