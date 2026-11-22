  # TalentMatch AI: Resume Matching & Candidate Ranking System

An AI-powered recruitment platform. A recruiter uploads a **job description** and a batch of **resumes**
(PDF/DOCX). The system parses both, compares them with a **hybrid NLP engine** (taxonomy-based skill matching
plus sentence-embedding semantic similarity plus experience and education rules), computes an **explainable
weighted score** and ranks the candidates on a recruiter dashboard.

> **Human-in-the-loop by design.** Scores measure how closely a resume's text matches a job description.
> They are **not hiring probabilities**, they never auto-reject anyone, and personal attributes (age, gender,
> religion, caste and so on) are stripped before matching and never used in scoring.

---

## Table of contents
1. [Features](#features)
2. [Technology stack](#technology-stack)
3. [Architecture & workflow](#architecture--workflow)
4. [NLP & resume-parsing methodology](#nlp--resume-parsing-methodology)
5. [Semantic matching approach](#semantic-matching-approach)
6. [Scoring formula](#scoring-formula)
7. [Database schema](#database-schema)
8. [API documentation](#api-documentation)
9. [Installation & execution (no Docker)](#installation--execution-no-docker)
10. [Testing](#testing)
11. [Sample data](#sample-data)
12. [Security & fairness](#security--fairness)
13. [Deployment (optional cloud)](#deployment-optional-cloud)
14. [Limitations & future improvements](#limitations--future-improvements)

---

## Features

| Module | What it does |
|---|---|
| **1. JD input** | Paste text or upload PDF/DOCX. Extracts title, mandatory/preferred skills, min/max experience, education level and fields, qualifications and responsibilities into structured JSON. The recruiter **reviews and edits** everything (tag editor, sliders) before analysis. |
| **2. Batch resume upload** | Drag & drop or multi-select (≥10 at once, up to 50 per batch). Extracts name, email, phone, skills, education, experience, projects, certifications and employment history. Computes experience **without double-counting overlapping jobs**. Corrupted, empty, scanned, duplicate and unsupported files are each reported with a clear status and message, and one bad file never stops the batch. |
| **3. Matching engine** | Text normalization → skill extraction & synonym mapping → exact/related/semantic skill matching → all-MiniLM-L6-v2 embeddings → cosine similarity between JD statements and resume sections → experience and education comparison → explainable weighted score. Weights are configurable, and mandatory and preferred skills are scored separately. |
| **4. Ranking dashboard** | KPI cards (total, processed, average, highest), score-distribution, fit-category, component-average and missing-skill charts, and a ranked table with search, filters, column sorting, 2–4 candidate comparison (radar plus side-by-side table) and CSV export. |
| **5. Candidate analysis** | Extracted profile, overall and component scores, the exact calculation, matched/related/missing mandatory and preferred skills, required vs actual experience, education comparison, semantic evidence (which resume sentence supports which JD requirement) and a grounded strengths/gaps explanation. |

---

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 6, Tailwind CSS 3, React Router, Axios, Recharts, lucide-react |
| Backend | Python 3.12, FastAPI, Pydantic v2, Uvicorn |
| AI / NLP | Sentence-Transformers (**all-MiniLM-L6-v2**), spaCy (`en_core_web_sm`), scikit-learn (TF-IDF fallback, cosine similarity), regular expressions |
| Parsing | PyMuPDF (PDF), python-docx (DOCX) |
| Database | PostgreSQL 16 + SQLAlchemy 2 (JSONB columns) |
| Testing | Pytest (70 backend tests), Vitest + Testing Library (frontend) |

Everything is open source and runs offline after the first model download. No paid API is required.

---

## Architecture & workflow

```
┌──────────────────────── React (Vite + Tailwind) ────────────────────────┐
│ JobsPage · NewJobPage · RequirementsPage · ResumesPage · DashboardPage   │
│ CandidatePage · ComparePage · components (RankingTable, Charts, ui…)     │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ Axios (REST/JSON, optional X-API-Key)
┌──────────────────────────────▼───────────────────────────────────────────┐
│ FastAPI  app/api/routes: jobs.py · resumes.py · analysis.py              │
├──────────────────────────────────────────────────────────────────────────┤
│ services/                                                                │
│  document_parser ─► text_preprocessing ─► jd_extractor / resume_parser   │
│                                     │            ├─ skill_extractor      │
│                                     │            ├─ experience_calculator│
│                                     │            └─ education            │
│  analysis_pipeline (background) ─► matching_service                      │
│        ├─ skill_matcher ─────────┐                                       │
│        ├─ semantic_matcher ◄─ embedding_service (MiniLM / TF-IDF)        │
│        ├─ scoring_engine ◄───────┘                                       │
│        ├─ explanation_service                                            │
│        └─ ranking_service                                                │
├──────────────────────────────────────────────────────────────────────────┤
│ SQLAlchemy models ─► PostgreSQL: jobs · resumes · candidates · match_results│
│ Secure file storage: storage/uploads/job_<id>/<uuid>.pdf                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**Workflow**

1. **Create job.** `POST /api/jobs` (text) or `/api/jobs/upload` (file). The JD extractor returns structured requirements.
2. **Review.** The recruiter edits skills, experience, education and weights (`PUT /api/jobs/{id}`).
3. **Upload resumes.** `POST /api/jobs/{id}/resumes` validates, de-duplicates, stores and parses each file independently.
4. **Analyze.** `POST /api/jobs/{id}/analyze` starts a background task; the UI polls `/status` for progress.
5. **Rank & explain.** The dashboard reads `/candidates`, `/dashboard`, `/candidates/{cid}`, `/compare` and `/export`.
6. Changing requirements, weights or resumes marks the results **outdated** so they can be re-run.

### Project structure
```
resume-matcher/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, error handlers, routers
│   │   ├── core/config.py          # env-driven settings (pydantic-settings)
│   │   ├── core/security.py        # API key, safe filenames, secure storage
│   │   ├── db/database.py, models.py
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── data/skills_taxonomy.py # ~150 skills, aliases, related skills
│   │   ├── services/               # all NLP + scoring logic (see diagram)
│   │   └── api/routes/             # jobs, resumes, analysis
│   ├── scripts/generate_samples.py # builds the synthetic dataset
│   ├── tests/                      # pytest suite
│   ├── requirements.txt, .env.example, pytest.ini
├── frontend/
│   ├── src/{api,components,pages,utils,__tests__}
│   ├── package.json, vite.config.js, tailwind.config.js, .env.example
├── sample_data/{jds,resumes,edge_cases}
├── scripts/{setup.sh,start.sh,local_postgres.sh}
└── docs/{INTERVIEW_PREP.md,DEMO_SCRIPT.md}
```

---

## NLP & resume-parsing methodology

**1. Text extraction (`document_parser.py`)**
- File type is checked by **extension and magic bytes** (`%PDF`, `PK` zip header), so a renamed file is rejected.
- PDF: PyMuPDF `get_text("blocks", sort=True)` keeps a sensible reading order for multi-column layouts.
  If there is almost no text but the pages contain images, the file is classified as a **scanned PDF**.
- DOCX: paragraphs plus table cells (de-duplicating merged cells).
- Corrupted, password-protected, empty and blank files raise `DocumentParseError` with a readable message.

**2. Preprocessing (`text_preprocessing.py`)**: Unicode NFKC normalization, dash/quote/bullet unification,
whitespace cleanup, **section segmentation** using a heading dictionary (Summary, Experience, Education, Skills,
Projects, Certifications…, including inline headings such as `Skills: Python, SQL`), and **removal of
personal-attribute lines** (DOB, age, gender, religion, caste, marital status…).

**3. Field extraction (`resume_parser.py`)**
- **Name**: first header line with 2–4 capitalized words (no digits or heading words); falls back to **spaCy NER** (`PERSON`).
- **Email / phone**: regular expressions (the phone must have 10–15 digits and not be a date range).
- **Skills** (`skill_extractor.py`): every alias in the taxonomy is matched with custom word boundaries that handle
  `C++`, `C#`, `Node.js`, `CI/CD`. Ambiguous tokens (`R`, `Go`, `ML`, `Spark`…) and soft skills are only accepted
  as items of a skills **list**, which avoids false positives like "R&D" or "leadership team". Each alias maps to a
  **canonical skill** (synonym mapping: `Postgres → PostgreSQL`, `sklearn → scikit-learn`, `k8s → Kubernetes`).
  Unknown items in the skills list are kept as free-form skills.
- **Education** (`education.py`): degree-level regexes (PhD › Master › Bachelor › Associate/Diploma › High school),
  field of study, institution and year.
- **Experience** (`experience_calculator.py`): date ranges such as `Jan 2019 – Mar 2022`, `06/2017 – Present`,
  `2015 to 2018` are found only in the **Experience section**, so education dates are never counted. They are
  turned into month intervals and **merged when they overlap**:

  ```
  Django Dev   Jan 2020 ───────────── Dec 2023
  Freelance         Jun 2021 ── Jun 2023          (fully inside → counted once)
  Python Dev                                Feb 2024 ── Present
  total = merged intervals, gross and overlap are also reported
  ```
  If no dates exist, a stated "5+ years of experience" is used and flagged. If neither exists, the result is
  "unknown" and flagged for manual review.
- **Projects / certifications**: items of the respective sections.

**4. JD extraction (`jd_extractor.py`)**: JD-specific headings (Requirements, Must have, Nice to have,
Responsibilities…). Lines containing cues such as "preferred", "nice to have" or "a plus" become **preferred**.
Skills that appear only in responsibilities are added as mandatory unless marked preferred. Experience ranges
(`3-6 years`, `4+ years`) are parsed. For education, the **lowest** acceptable degree in the requirement line is
used ("Bachelor's or Master's" → Bachelor's).

---

## Semantic matching approach

`embedding_service.py` loads **all-MiniLM-L6-v2** (384-dimensional, L2-normalized embeddings, CPU friendly) once
per process and caches vectors. Cosine similarity of normalized vectors is a dot product.

`semantic_matcher.py` computes two complementary signals:

1. **Requirement coverage.** Each JD responsibility/qualification sentence is compared with every resume sentence
   from Experience, Projects, Summary, Skills and Certifications. For every requirement the **best** match is kept,
   and these are averaged. This answers: *how much of the JD is evidenced somewhere in the resume?* Chunking also
   avoids MiniLM's 256-token truncation.
2. **Section similarity.** The JD overview is compared with each resume section as a whole, and the best section
   is kept. This captures overall role and domain alignment.

```
raw      = 0.6 × coverage + 0.4 × best_section_similarity
semantic = clip((raw − 0.15) / (0.75 − 0.15), 0, 1) × 100
```
Raw MiniLM cosine values for related professional text usually fall between about 0.15 and 0.75, so they are
linearly calibrated to 0–100. The top evidence pairs and the least-covered requirements are stored for
explainability. If the model cannot be loaded (for example, offline on the first run), the service **falls back
to TF-IDF** with its own calibration and the UI reports that.

**Skill matching (`skill_matcher.py`)** is a hybrid:

| Match | Credit | Example |
|---|---|---|
| exact / synonym | 1.0 | `Postgres` satisfies `PostgreSQL` |
| related (taxonomy) | 0.5 | `PyTorch` for `TensorFlow`, `Flask` for `FastAPI`, `MySQL` for `PostgreSQL` |
| semantic (embeddings) | 0.5 | skill-name cosine ≥ 0.70 (for skills outside the taxonomy) |
| missing | 0 | |

Custom skills that a recruiter adds and that are not in the taxonomy are found by boundary-aware phrase search.

---

## Scoring formula

```
Final Score = Skill × 0.40 + Semantic × 0.30 + Experience × 0.20 + Education × 0.10
```

| Component (0–100) | Definition |
|---|---|
| **Skill** | `100 × (0.75 × mandatory_coverage + 0.25 × preferred_coverage)`; coverage = Σ credit / #skills. If the JD lists only one group, it gets 100%. |
| **Semantic** | Calibrated embedding similarity (above). |
| **Experience** | `100` if years ≥ required min, else `100 × years / required` (proportional). `85` if far above a stated max (possible over-qualification). |
| **Education** | `70% degree level` (meets = 100, one level below = 60, lower = 30) + `30% field` (same = 100, related group = 75, other STEM = 50, unrelated = 20). |

**Missing information is handled transparently:**
- If the **JD** gives no requirement for a component (for example, no education requirement), the component is
  **excluded and the remaining weights are re-normalized**, identically for every candidate, so ranking stays fair.
  `weights_used` is stored with each result and shown in the UI.
- If the **resume** lacks the information (for example, no dates), the component scores **0 and is flagged
  "verify manually"**. The system never assumes a requirement is met.

**Weights are configurable** per job in the UI or API (any non-negative values, normalized to sum to 1). The
defaults come from `.env`. **Fit bands** (labels only, never decisions): Strong ≥ 75, Moderate ≥ 55, Weak ≥ 35,
Low < 35. **Ranking** is by final score descending, with ties broken by skill score and then semantic score.
Equal scores share a rank (1, 2, 2, 4).

Worked example (Priya Nair vs Senior Python Developer):
`50.8 × 0.40 + 63.3 × 0.30 + 100 × 0.20 + 100 × 0.10 = 69.3` → *Moderate match*. She gets partial credit for
FastAPI/Django through Flask and for PostgreSQL through MySQL.

---

## Database schema

```
jobs ─────────────┐ 1
  id PK            │
  title, raw_text, source_filename
  requirements JSONB   (editable structured requirements)
  weights JSONB
  analysis_status, analysis_total, analysis_done, analysis_error, analyzed_at
  created_at, updated_at
        │1                      │1                       │1
        ▼*                      ▼*                       ▼*
resumes                    candidates                match_results
  id PK                      id PK                     id PK
  job_id FK→jobs             job_id FK→jobs            job_id FK→jobs
  original_filename          resume_id FK→resumes (UQ) candidate_id FK→candidates
  stored_filename (uuid)     name, email, phone        final_score, skill_score, semantic_score,
  file_type, file_size       summary, skills JSONB     experience_score, education_score
  file_hash (sha256, idx)    education JSONB           rank, fit_label, weights_used JSONB
  raw_text                   highest_education         skill/semantic/experience/education
  status, error_message      experience_years            _details JSONB, explanation JSONB
  uploaded_at                employment_history JSONB  UQ(job_id, candidate_id)
                             projects, certifications
                             sections, warnings JSONB
```
All foreign keys use `ON DELETE CASCADE`. Deleting a job removes its resumes, candidates, results and stored
files. Tables are created automatically at startup (`Base.metadata.create_all`).

---

## API documentation

Interactive docs: **http://localhost:8000/docs** (Swagger) and **/redoc**.

| Method | Endpoint | Description | Codes |
|---|---|---|---|
| GET | `/api/health` | API, DB and embedding status | 200 |
| GET | `/api/config/defaults` | Default weights and limits | 200 |
| POST | `/api/jobs` | Create a job from JD text (auto-extract) | 201, 422 |
| POST | `/api/jobs/upload` | Create a job from a PDF/DOCX JD | 201, 413, 415, 422 |
| POST | `/api/jobs/extract` | Preview extraction without saving | 200 |
| GET | `/api/jobs` | List jobs | 200 |
| GET | `/api/jobs/{id}` | Job with requirements and weights | 200, 404 |
| PUT | `/api/jobs/{id}` | Edit requirements and/or weights | 200, 409, 422 |
| DELETE | `/api/jobs/{id}` | Delete a job and all its data | 204 |
| POST | `/api/jobs/{id}/resumes` | **Batch upload** (multipart `files`) with per-file results | 207, 400, 409 |
| GET | `/api/jobs/{id}/resumes` | Upload/processing status of every file | 200 |
| GET | `/api/jobs/{id}/resumes/{rid}` | Extracted candidate information | 200, 404, 422 |
| GET | `/api/jobs/{id}/resumes/{rid}/file` | Download the original (job-scoped) | 200, 404 |
| DELETE | `/api/jobs/{id}/resumes/{rid}` | Delete a resume | 204 |
| POST | `/api/resumes/parse` | Stateless single-resume extraction preview | 200, 415, 422 |
| POST | `/api/jobs/{id}/analyze` | Start matching analysis (background) | 202, 409, 422 |
| GET | `/api/jobs/{id}/status` | Analysis progress | 200 |
| GET | `/api/jobs/{id}/candidates` | Ranked list. Query: `search, min_score, max_score, fit, status, skill, min_experience, sort_by, order` | 200 |
| GET | `/api/jobs/{id}/candidates/{cid}` | Detailed explainable analysis | 200, 404 |
| GET | `/api/jobs/{id}/compare?ids=1,2,3` | Compare 2–4 candidates | 200, 400 |
| GET | `/api/jobs/{id}/dashboard` | Dashboard statistics and chart data | 200 |
| GET | `/api/jobs/{id}/export` | CSV export of the ranking | 200 |

Validation errors return `422 {"detail": "Validation failed", "errors": [{"field", "message"}]}`.
A database outage returns `503`.

Example:
```bash
curl -X POST localhost:8000/api/jobs -H 'Content-Type: application/json' \
     -d "{\"raw_text\": $(python3 -c 'import json;print(json.dumps(open("sample_data/jds/python_developer.txt").read()))')}"
curl -X POST localhost:8000/api/jobs/1/resumes -F files=@sample_data/resumes/01_aarav_mehta_senior_python.pdf \
     -F files=@sample_data/resumes/02_priya_nair_python_flask.docx
curl -X POST localhost:8000/api/jobs/1/analyze
curl "localhost:8000/api/jobs/1/candidates?min_score=50&sort_by=final_score"
```

---

## Installation & execution (no Docker)

**Prerequisites:** Python 3.10–3.12, Node 18+, PostgreSQL 14+.

### 1. PostgreSQL
Use any local PostgreSQL (Postgres.app, Homebrew `postgresql@16`, the official installer) and create the databases:
```sql
CREATE DATABASE resume_matcher;
CREATE DATABASE resume_matcher_test;   -- for the test suite
```
If you don't have PostgreSQL, you can run one inside the project folder without Docker or admin rights:
```bash
conda create -y -n resume-pg -c conda-forge postgresql=16
```
```bash
scripts/local_postgres.sh init     # first time: initdb + start + create both databases
```
```bash
scripts/local_postgres.sh start    # later sessions
```

### 2. Backend
```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env               # adjust DATABASE_URL if needed
python -m scripts.generate_samples # (re)build the synthetic dataset
uvicorn app.main:app --reload --port 8000
```
The first analysis downloads all-MiniLM-L6-v2 (~90 MB) from Hugging Face. After that, everything works offline.

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev                        # http://localhost:5173 (proxies /api to :8000)
```

Shortcut: `scripts/setup.sh` once, then `scripts/start.sh` starts both servers.

### Demo walkthrough
1. **New Job.** Paste `sample_data/jds/python_developer.txt` and click *Extract requirements*.
2. Review the extracted skills, experience and education, adjust weights and click *Save*.
3. **Resumes.** Drag every file from `sample_data/resumes/` **and** `sample_data/edge_cases/` and click *Upload*.
   You get 12 parsed plus 8 individually explained errors.
4. *Start analysis* shows a progress bar, then the **Results** dashboard.
5. Explore charts, search for "FastAPI", filter "Strong match", tick 3 candidates and *Compare*, then *Export CSV*.
6. Open **Priya Nair** to see related-skill credit (Flask → FastAPI) and the full calculation.

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for a timed demo-video script.

---

## Testing

```bash
cd backend && source .venv/bin/activate
pytest                              # 70 tests: parsing, NLP, scoring, accuracy, API + PostgreSQL, security
TEST_DATABASE_URL=sqlite:///./test.db pytest   # without PostgreSQL
```
```bash
cd frontend && npm test             # Vitest + Testing Library
```

| Test file | Covers |
|---|---|
| `test_document_parsing.py` | PDF/DOCX extraction, 7 edge-case files, field extraction on all 12 resumes, sensitive-line removal |
| `test_nlp_components.py` | synonyms, special-character skills, ambiguous tokens, overlapping experience, date formats, education, JD extraction |
| `test_scoring_and_matching.py` | exact formula, re-normalization, bounds, weight validation, related-skill credit, **ranking accuracy on all three JDs**, grounded explanations, tie ranking |
| `test_api.py` | full workflow against PostgreSQL: 20-file batch with partial failures, analysis, ranking, search/filter/sort, detail, compare, dashboard, CSV, re-analysis, job-scoped document access, limits, API key |
| `test_security.py` | path-traversal-safe filenames, random storage names, CSV formula injection |

Ranking produced by the engine for **Senior Python Developer** (default weights):

| # | Candidate | Score | Why |
|---|---|---|---|
| 1 | Aarav Mehta | 96.7 | all mandatory skills, 8 yrs, B.Tech CS |
| 2 | Fatima Sheikh | 82.2 | strong Django/FastAPI; overlapping freelance counted once |
| 3 | Priya Nair | 69.3 | related skills (Flask, MySQL) earn partial credit |
| 4 | Vikram Singh | 68.1 | transferable backend skills, but Java instead of Python |
| … | Ananya Gupta (frontend) | 40.0 | few backend skills |

---

## Sample data

`sample_data/` is **100% synthetic** (fictional people, `@example.com` emails). See `sample_data/README.md`.
- **3 JDs**: Python Developer, Data Scientist, AI/ML Engineer (TXT, PDF, DOCX).
- **12 resumes** (6 PDF, 6 DOCX): strong, moderate and weak matches, missing skills, junior to 9+ years, diploma
  to PhD, overlapping employment, career changer, and a resume written entirely with **synonyms** (Hugging Face,
  Keras, "Natural Language Processing") to test semantic matching.
- **8 edge cases**: empty, corrupted PDF, corrupted DOCX, renamed image, blank PDF, scanned image-only PDF,
  unsupported `.txt`, exact duplicate.

---

## Security & fairness

- **File validation**: extension whitelist + magic bytes, 5 MB size limit, 50 files per batch (configurable).
- **Safe filenames**: user filenames are sanitized for display only. Files are stored as random UUIDs under
  `storage/uploads/job_<id>/` with `0600` permissions, outside any web root, with path-traversal checks.
- **Access control**: optional `API_KEY` (constant-time comparison) protects every `/api` route. Documents and
  candidates are only reachable through their **own job** (`/jobs/{job}/resumes/{id}` returns 404 for another job).
- **Secrets** live in `.env` (git-ignored). `.env.example` files document every variable.
- **Error handling**: per-file isolation (partial batch processing), per-candidate isolation during analysis,
  DB errors mapped to 503/500 without leaking internals, structured 422 validation errors.
- **CSV injection** prevention on export.
- **Fairness**: lines with age, DOB, gender, marital status, religion, caste, nationality and similar attributes are
  removed before any matching, and names and contact details are never used in scoring. Results are labeled as
  decision support with a disclaimer, and **nothing is auto-rejected**: every candidate stays visible and sortable.

---

## Deployment (optional cloud)

Everything is a plain process, so no containers are needed:
- **Database**: managed PostgreSQL (Neon, Supabase, Render, RDS). Set `DATABASE_URL`.
- **Backend**: Render/Railway/Fly "Python web service". Build: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`.
  Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `CORS_ORIGINS` to the frontend URL and
  `API_KEY`. Use at least 1 GB RAM for the embedding model and persistent disk (or object storage) for `UPLOAD_DIR`.
- **Frontend**: Vercel/Netlify static build (`npm run build` → `dist/`). Set `VITE_API_URL=https://<backend>/api`
  and `VITE_API_KEY`. Add an SPA rewrite to `index.html`.

---

## Limitations & future improvements

**Limitations**
- Rule- and taxonomy-based extraction can miss unusual layouts, tables-as-images or uncommon section names.
  Recruiters can edit JD requirements, but candidate extraction is read-only.
- No OCR: scanned resumes are detected and reported, not read.
- English only. Dates must contain a year, and ambiguous formats default to month/year.
- The semantic calibration (0.15–0.75) is empirical for MiniLM on professional text. Scores are relative
  indicators, not probabilities.
- The skill taxonomy (~150 skills) is tech-focused. Other domains need taxonomy entries.
- Background analysis runs in-process (FastAPI `BackgroundTasks`). A server restart mid-analysis requires a re-run.
- Single-tenant: an API key instead of user accounts and roles.

**Future improvements**
- OCR (Tesseract) for scanned PDFs and a fine-tuned NER model for resume entities.
- Learn the skill taxonomy from ESCO/O*NET and add multilingual embeddings.
- Cross-encoder re-ranking and recruiter feedback to tune weights (with bias audits).
- A job queue (Celery/RQ + Redis), Alembic migrations, pgvector for embedding storage and search.
- Authentication (OAuth/JWT), RBAC, audit logs, data-retention policies and PII redaction in the UI.
- Editable candidate profiles, interview-stage pipeline and ATS integrations.
