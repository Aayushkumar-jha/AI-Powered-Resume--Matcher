"""Test configuration.

Integration tests run against a real PostgreSQL test database (TEST_DATABASE_URL, default
postgresql://postgres:postgres@localhost:5432/resume_matcher_test). Set TEST_DATABASE_URL to
"sqlite:///./test.db" to run without PostgreSQL.
"""
import os
import tempfile
from pathlib import Path

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/resume_matcher_test"
)
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="rm_uploads_")
os.environ["API_KEY"] = ""

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "sample_data"


@pytest.fixture(scope="session", autouse=True)
def ensure_samples():
    if not (SAMPLES / "resumes").exists() or len(list((SAMPLES / "resumes").iterdir())) < 10:
        from scripts.generate_samples import main

        main()
    return SAMPLES


@pytest.fixture(scope="session")
def db_engine():
    from app.db.database import Base, engine, init_db

    Base.metadata.drop_all(bind=engine)
    init_db()
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_engine):
    from fastapi.testclient import TestClient

    from app.db.database import Base
    from app.main import app

    with db_engine.begin() as conn:  # clean tables between tests
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def jd_texts(ensure_samples):
    return {p.stem: p.read_text() for p in (SAMPLES / "jds").glob("*.txt")}


@pytest.fixture(scope="session")
def resume_files(ensure_samples):
    return sorted((SAMPLES / "resumes").iterdir())


@pytest.fixture(scope="session")
def edge_files(ensure_samples):
    return {p.name: p for p in (SAMPLES / "edge_cases").iterdir()}
