"""API + database integration tests (PostgreSQL by default)."""
import csv
import io


def _create_job(client, jd_texts, key="python_developer"):
    r = client.post("/api/jobs", json={"raw_text": jd_texts[key]})
    assert r.status_code == 201, r.text
    return r.json()


def _files(paths):
    return [("files", (p.name, p.read_bytes(), "application/octet-stream")) for p in paths]


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["database"] is True


def test_create_and_get_job(client, jd_texts):
    job = _create_job(client, jd_texts)
    assert job["title"] == "Senior Python Developer"
    assert "Python" in job["requirements"]["required_skills"]
    assert job["weights"]["skills"] == 0.4
    r = client.get(f"/api/jobs/{job['id']}")
    assert r.status_code == 200 and r.json()["resume_count"] == 0
    assert any(j["id"] == job["id"] for j in client.get("/api/jobs").json())


def test_job_validation_errors(client):
    r = client.post("/api/jobs", json={"raw_text": "too short"})
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "raw_text"
    assert client.get("/api/jobs/99999").status_code == 404


def test_upload_jd_document(client, ensure_samples):
    pdf = ensure_samples / "jds" / "data_scientist.pdf"
    r = client.post("/api/jobs/upload", files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 201, r.text
    assert r.json()["requirements"]["education_level"] == "master"
    bad = client.post("/api/jobs/upload", files={"file": ("jd.txt", b"plain text", "text/plain")})
    assert bad.status_code == 415


def test_edit_requirements_and_weights(client, jd_texts):
    job = _create_job(client, jd_texts)
    req = job["requirements"] | {"required_skills": ["Python", "Airflow"], "min_experience_years": 2}
    r = client.put(f"/api/jobs/{job['id']}", json={"requirements": req,
                                                   "weights": {"skills": 0.5, "semantic": 0.5,
                                                               "experience": 0, "education": 0}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["requirements"]["required_skills"] == ["Python", "Airflow"]
    assert body["weights"]["skills"] == 0.5
    bad = client.put(f"/api/jobs/{job['id']}", json={"requirements": req | {"education_level": "wizard"}})
    assert bad.status_code == 422


def test_full_workflow(client, jd_texts, resume_files, edge_files):
    job = _create_job(client, jd_texts)
    jid = job["id"]

    # Batch upload: 12 valid resumes + 8 problematic files in ONE request (partial batch processing)
    files = _files(resume_files) + _files(edge_files.values())
    r = client.post(f"/api/jobs/{jid}/resumes", files=files)
    assert r.status_code == 207, r.text
    batch = r.json()
    assert batch["total"] == 20 and batch["parsed"] == 12 and batch["failed"] == 8
    by_name = {x["filename"]: x for x in batch["results"]}
    assert by_name["duplicate_of_priya.docx"]["status"] == "duplicate"
    assert by_name["unsupported_resume.txt"]["status"] == "unsupported"
    assert "scanned" in by_name["scanned_resume.pdf"]["error"]
    assert by_name["01_aarav_mehta_senior_python.pdf"]["candidate_name"] == "Aarav Mehta"

    resumes = client.get(f"/api/jobs/{jid}/resumes").json()
    assert len(resumes) == 20

    # Analysis
    r = client.post(f"/api/jobs/{jid}/analyze")
    assert r.status_code == 202
    status = client.get(f"/api/jobs/{jid}/status").json()
    assert status["status"] == "completed" and status["done"] == 12 and status["progress"] == 100

    # Ranking
    ranked = client.get(f"/api/jobs/{jid}/candidates").json()
    assert len(ranked) == 20
    assert ranked[0]["name"] == "Aarav Mehta" and ranked[0]["rank"] == 1
    scores = [c["final_score"] for c in ranked if c["final_score"] is not None]
    assert scores == sorted(scores, reverse=True)
    assert all(c["final_score"] is None for c in ranked[12:])  # failed files last

    # Search / filter / sort
    found = client.get(f"/api/jobs/{jid}/candidates?search=priya").json()
    assert [(c["name"], c["status"]) for c in found] == [("Priya Nair", "analyzed"), (None, "duplicate")]
    strong = client.get(f"/api/jobs/{jid}/candidates?min_score=75").json()
    assert strong and all(c["final_score"] >= 75 for c in strong)
    assert all(c["status"] == "failed" for c in client.get(f"/api/jobs/{jid}/candidates?status=failed").json())
    by_name_sorted = client.get(f"/api/jobs/{jid}/candidates?sort_by=name&status=analyzed").json()
    assert [c["name"] for c in by_name_sorted] == sorted(c["name"] for c in by_name_sorted)
    fastapi = client.get(f"/api/jobs/{jid}/candidates?skill=FastAPI").json()
    assert {"Aarav Mehta", "Fatima Sheikh"} <= {c["name"] for c in fastapi}

    # Candidate detail
    top_id = ranked[0]["candidate_id"]
    d = client.get(f"/api/jobs/{jid}/candidates/{top_id}").json()
    assert d["candidate"]["email"] == "aarav.mehta@example.com"
    assert d["scores"]["final_score"] == ranked[0]["final_score"]
    assert d["explanation"]["summary"] and d["explanation"]["breakdown"]
    assert d["experience_details"]["required_min"] == 4

    # Compare
    ids = ",".join(str(c["candidate_id"]) for c in ranked[:3])
    assert len(client.get(f"/api/jobs/{jid}/compare?ids={ids}").json()) == 3
    assert client.get(f"/api/jobs/{jid}/compare?ids={top_id}").status_code == 400

    # Dashboard
    dash = client.get(f"/api/jobs/{jid}/dashboard").json()
    assert dash["total_candidates"] == 20 and dash["processed"] == 12 and dash["analyzed"] == 12
    assert dash["highest_score"] == ranked[0]["final_score"]
    assert sum(b["count"] for b in dash["score_distribution"]) == 12

    # CSV export
    r = client.get(f"/api/jobs/{jid}/export")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0][0] == "Rank" and rows[1][1] == "Aarav Mehta" and len(rows) == 21

    # Re-analysis after editing weights marks results outdated, then recomputes
    client.put(f"/api/jobs/{jid}", json={"weights": {"skills": 1, "semantic": 0, "experience": 0, "education": 0}})
    assert client.get(f"/api/jobs/{jid}").json()["analysis_status"] == "outdated"
    client.post(f"/api/jobs/{jid}/analyze")
    top = client.get(f"/api/jobs/{jid}/candidates").json()[0]
    assert top["final_score"] == top["skill_score"]


def test_document_access_is_scoped_to_job(client, jd_texts, resume_files):
    a = _create_job(client, jd_texts)
    b = _create_job(client, jd_texts, "data_scientist")
    up = client.post(f"/api/jobs/{a['id']}/resumes", files=_files(resume_files[:1])).json()
    rid = up["results"][0]["resume_id"]
    assert client.get(f"/api/jobs/{a['id']}/resumes/{rid}/file").status_code == 200
    assert client.get(f"/api/jobs/{b['id']}/resumes/{rid}/file").status_code == 404
    assert client.get(f"/api/jobs/{b['id']}/resumes/{rid}").status_code == 404
    cid = up["results"][0]["candidate_id"]
    assert client.get(f"/api/jobs/{b['id']}/candidates/{cid}").status_code == 404


def test_analyze_without_resumes_is_rejected(client, jd_texts):
    job = _create_job(client, jd_texts)
    assert client.post(f"/api/jobs/{job['id']}/analyze").status_code == 422


def test_batch_limit_and_size_limit(client, jd_texts, monkeypatch):
    from app.core.config import get_settings

    job = _create_job(client, jd_texts)
    monkeypatch.setattr(get_settings(), "max_files_per_batch", 2)
    files = [("files", (f"r{i}.pdf", b"%PDF-1.4", "application/pdf")) for i in range(3)]
    assert client.post(f"/api/jobs/{job['id']}/resumes", files=files).status_code == 400
    monkeypatch.setattr(get_settings(), "max_files_per_batch", 50)
    monkeypatch.setattr(get_settings(), "max_file_size_mb", 0.001)
    big = [("files", ("big.pdf", b"%PDF-1.4" + b"0" * 5000, "application/pdf"))]
    res = client.post(f"/api/jobs/{job['id']}/resumes", files=big).json()
    assert res["results"][0]["status"] == "failed" and "size limit" in res["results"][0]["error"]


def test_delete_resume_and_job(client, jd_texts, resume_files):
    job = _create_job(client, jd_texts)
    up = client.post(f"/api/jobs/{job['id']}/resumes", files=_files(resume_files[:2])).json()
    rid = up["results"][0]["resume_id"]
    assert client.delete(f"/api/jobs/{job['id']}/resumes/{rid}").status_code == 204
    assert len(client.get(f"/api/jobs/{job['id']}/resumes").json()) == 1
    assert client.delete(f"/api/jobs/{job['id']}").status_code == 204
    assert client.get(f"/api/jobs/{job['id']}").status_code == 404


def test_stateless_parse_endpoint(client, resume_files):
    f = resume_files[0]
    r = client.post("/api/resumes/parse", files={"file": (f.name, f.read_bytes(), "application/pdf")})
    assert r.status_code == 200 and r.json()["name"] == "Aarav Mehta"


def test_api_key_protection(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "api_key", "secret-key")
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/jobs", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/jobs", headers={"X-API-Key": "secret-key"}).status_code == 200
