# Technical Interview Preparation: TalentMatch AI

This guide is meant to help you explain **every part of the project in your own words**. Read it alongside the
code: each section points to the file to open.

---

## Part 1: The 60-second pitch

> "I built an AI-based resume matching and ranking system. A recruiter pastes or uploads a job description, and the
> backend extracts structured requirements (mandatory and preferred skills, experience, education) that the
> recruiter can edit. They then upload a batch of PDF/DOCX resumes. Each file is validated and parsed
> independently with PyMuPDF, python-docx, regex and spaCy, and experience is calculated by merging overlapping
> employment periods. The matching engine is hybrid: taxonomy-based skill matching with synonyms and related-skill
> partial credit (40%), semantic similarity using all-MiniLM-L6-v2 sentence embeddings (30%), experience (20%) and
> education (10%). Every score is explained from the actual extracted data, and results are shown on a React
> dashboard with charts, filtering, comparison and CSV export. It's FastAPI + PostgreSQL + React, with 70 pytest
> tests, and it's designed as decision support: no auto-rejection, and sensitive attributes are stripped before
> matching."

---

## Part 2: Walk through the request lifecycle (know this cold)

1. `POST /api/jobs` → `api/routes/jobs.py::create_job` → `services/jd_extractor.py::extract_job_requirements`
   → stored in `jobs.requirements` (JSONB) with default weights from `.env`.
2. `PUT /api/jobs/{id}` → Pydantic `JobRequirements` validates (dedupes skills, removes skills that are both
   mandatory and preferred, checks max ≥ min) and `ScoringWeights` normalizes the weights to sum to 1.
3. `POST /api/jobs/{id}/resumes` → for each file, `services/resume_service.py::process_resume_file`:
   size check → `document_parser.extract_text` (magic bytes, PDF/DOCX, scanned detection) → SHA-256 duplicate
   check → `security.store_file` (UUID name) → `resume_parser.parse_resume` → rows in `resumes` + `candidates`.
   Returns **207 Multi-Status** with one result per file.
4. `POST /api/jobs/{id}/analyze` → sets status `processing` and schedules `analysis_pipeline.run_analysis` as a
   FastAPI BackgroundTask (returns **202 Accepted** immediately).
5. `run_analysis` → for each candidate, `matching_service.analyze_candidate` → `skill_matcher`,
   `semantic_matcher`, `scoring_engine.score_experience`, `education.score_education` → `combine_scores` →
   `explanation_service.build_explanation` → `MatchResult`. Progress is committed after each candidate, then
   `ranking_service.assign_ranks`.
6. The frontend polls `GET /status` every 800 ms and then navigates to the dashboard.

---

## Part 3: Module deep dives

### Document parsing (`document_parser.py`)
- **Why check magic bytes?** An attacker or a confused user can rename `photo.png` to `cv.pdf`. A real PDF starts
  with `%PDF`, and DOCX is a ZIP archive starting with `PK`.
- **Scanned detection:** if PyMuPDF extracts fewer than 50 characters but the pages contain images, the PDF is
  image-only. We report it instead of producing an empty profile.
- **Why `get_text("blocks", sort=True)`?** It returns text blocks sorted top-to-bottom, left-to-right, which keeps
  two-column resumes readable.

### Section segmentation (`text_preprocessing.py`)
- A dictionary maps heading variants ("Work History", "Professional Experience"…) to canonical sections. A short
  line that matches a heading starts a new section. `Skills: Python, SQL` is handled as an inline heading.
- **Why segment at all?** So we only compute experience from the Experience section (education dates like
  "2014–2018" must not count as work), and so semantic matching compares the relevant parts.

### Skill extraction & synonym mapping (`skill_extractor.py`, `data/skills_taxonomy.py`)
- Taxonomy: canonical skill → aliases (synonyms), category and related skills. ~150 skills.
- Regex with **custom boundaries** `(?<![a-z0-9+#])alias(?![a-z0-9+#]|\.[a-z0-9])`, because `\b` fails on `C++`,
  `C#` and `.NET`.
- Longest aliases are matched first. **Ambiguous** aliases (R, Go, ML, Spark, Node) and **soft skills** are only
  accepted as whole items in a skills list. That stops "R&D" → R and "dashboards for leadership" → Leadership.
- **Related graph** is made bidirectional automatically (if TensorFlow lists PyTorch, PyTorch also gets TensorFlow).

### Experience calculator (`experience_calculator.py`)
- A regex finds ranges in many formats (`Jan 2019 - Mar 2022`, `06/2017 – Present`, `2018 to 2020`).
- Each range becomes a half-open month interval `[start, end)`.
- **Merge overlapping intervals** (the classic sort-and-sweep algorithm, O(n log n)): sort by start, and if the
  next start ≤ the current end, extend; otherwise start a new block. Total = sum of merged block lengths.
- It also reports gross and overlap years, so the recruiter sees, for example, "2.1 overlapping years counted once".
- Fallbacks: a stated "5+ years of experience" (flagged), otherwise unknown (flagged, scored 0, "verify manually").

### Education (`education.py`)
- Degree-level regex ordered from high to low. Short abbreviations require dots or exact tokens (`B.E.`, `MS`) so
  "to be" isn't read as B.E.
- Field groups (CS ≈ IT ≈ Software Eng; Statistics ≈ Maths ≈ Data Science…) give partial credit.

### Semantic matcher (`semantic_matcher.py`, `embedding_service.py`)
- all-MiniLM-L6-v2: a 6-layer distilled transformer, 384-dimensional embeddings, mean pooling, trained
  contrastively on 1B+ sentence pairs. It's fast on CPU (~thousands of sentences/sec) and its quality is good
  for semantic similarity.
- Embeddings are **L2-normalized**, so cosine similarity = dot product.
- **Requirement coverage** (max over resume sentences, mean over JD requirements) plus **best section
  similarity**, weighted 0.6/0.4, then calibrated to 0–100.
- Embeddings are cached by text, so the JD is encoded once per analysis.

### Scoring, ranking, explanation
- `scoring_engine.combine_scores` drops unavailable components and re-normalizes the weights.
- `ranking_service.assign_ranks` uses competition ranking with deterministic tie-breakers.
- `explanation_service` builds strengths, gaps, notes, a breakdown and a human-readable formula string, all from
  computed dictionaries. There is no free-text generation, so nothing can be hallucinated.

---

## Part 4: Likely interview questions & model answers

### Architecture & design
**Q1. Why FastAPI instead of Flask or Django?**
FastAPI gives Pydantic validation and automatic OpenAPI docs out of the box, along with async support,
dependency injection (used for the DB session and API-key check) and BackgroundTasks. Django would bring an ORM
and admin we don't need. Flask would need extra libraries for validation and docs.

**Q2. Why PostgreSQL? Why JSONB columns?**
It gives relational integrity for the core entities (jobs → resumes → candidates → results with foreign keys and
cascades), while the nested, variable-shape data (skill details, explanations, employment history) fits naturally
in JSONB without dozens of child tables. JSONB can also be indexed and queried later.

**Q3. Why separate `resumes` and `candidates` tables?**
A resume is the *file and its processing status*, and it exists even when parsing fails. A candidate is the
*structured information* extracted from a successful parse. Failed, duplicate and unsupported uploads have a
`resumes` row but no `candidates` row, which is how the dashboard shows total vs processed.

**Q4. How does the analysis avoid blocking the HTTP request?**
`POST /analyze` returns 202 and schedules `run_analysis` as a BackgroundTask with its own DB session. Progress
(`analysis_done/total`) is committed after every candidate, and the UI polls `/status`. In production I'd move
this to Celery/RQ so it survives restarts and scales across workers.

**Q5. What happens if two analyses are triggered at once?**
The endpoint returns 409 if the status is already `processing`. Uploads and requirement edits are also blocked
with 409 during processing, so the results stay consistent.

**Q6. How do you keep results consistent with edits?**
Any change to requirements, weights or resumes sets `analysis_status = "outdated"`. The dashboard shows a warning
and offers to re-run, and each result stores `weights_used` for auditability.

### NLP & matching
**Q7. Why not just use keyword matching?**
Keywords miss synonyms ("Postgres" vs "PostgreSQL"), transferable skills (Flask vs FastAPI) and paraphrased
experience ("built RESTful services" vs "develop APIs"). Keyword-only systems also reward keyword stuffing. We use
taxonomy matching for precision and explainability, and embeddings for meaning.

**Q8. Why not use only embeddings?**
A single similarity number is hard to explain and can be high for a resume in the right domain that lacks a
critical mandatory skill. Mandatory skills need explicit, auditable checks. That's why the score is hybrid.

**Q9. Explain cosine similarity.**
cos(θ) = A·B / (‖A‖‖B‖). It measures the angle between vectors and ignores their length. With L2-normalized
embeddings it's just the dot product. 1 means the same direction, 0 means unrelated.

**Q10. Why all-MiniLM-L6-v2?**
It's open source, small (~90 MB), fast on CPU, has a strong semantic-textual-similarity benchmark, and needs no
paid API. Larger models (mpnet, e5, bge) are more accurate but slower. It's configurable via `EMBEDDING_MODEL`.

**Q11. Why chunk the resume into sentences?**
MiniLM truncates input at 256 word-pieces, so a whole resume would be cut off. Sentence-level comparison also
lets us point at the exact resume sentence that supports each JD requirement, which is explainability.

**Q12. How did you normalize the semantic score to 0–100?**
Raw cosine values for related professional text cluster between about 0.15 and 0.75, so a raw score would look
deceptively low. We linearly map [0.15, 0.75] → [0, 100] and clip. It's an empirical calibration, documented as a
limitation. A data-driven alternative is isotonic calibration against recruiter labels.

**Q13. What is the TF-IDF fallback for?**
If the transformer can't load (offline first run, low memory), the system still works by using TF-IDF vectors
with its own calibration, and it reports `method: tfidf` in the UI. Graceful degradation instead of failure.

**Q14. How do you distinguish mandatory from preferred skills?**
The JD extractor uses section headings and cue phrases ("nice to have", "a plus"). The skill score is 75%
mandatory coverage and 25% preferred coverage, and missing mandatory skills are listed separately as key gaps.

**Q15. How does related-skill matching work, and why 50%?**
The taxonomy lists transferable skills. If the exact skill is missing but a related one is present, the candidate
gets 0.5 credit and the explanation says "no direct FastAPI, but has related skill Flask". 50% is a configurable
middle ground (`RELATED_SKILL_CREDIT`): it acknowledges a shorter learning curve without treating it as
equivalent.

**Q16. How do you avoid false positives like "R" or "Go"?**
Those aliases are "list-only": they only count as complete items in a skills list, never in free text.

**Q17. How is experience calculated with overlapping jobs?**
Interval merging (explained above). Example: Fatima has a 2020–2023 job plus a 2021–2023 freelance gig. Gross
time is ~8.9 years, but merged time is 6.8 years.

**Q18. What if a resume has no dates?**
We look for a stated "N+ years of experience" and flag it. If nothing is found, experience is unknown: it scores
0 and is flagged "verify manually". We never assume.

### Scoring
**Q19. Walk me through the formula with a real example.**
Priya Nair: skills 50.8, semantic 63.3, experience 100, education 100 →
50.8×0.4 + 63.3×0.3 + 100×0.2 + 100×0.1 = 20.32 + 18.99 + 20 + 10 = 69.3.

**Q20. What if the JD has no education requirement?**
The education component is excluded for **every** candidate and the other weights are re-normalized
(0.4/0.9, 0.3/0.9, 0.2/0.9). Giving everyone 100 would compress the scores, and giving everyone 0 would penalize
them unfairly. Excluding it is the honest option.

**Q21. Why are weights configurable, and how are they validated?**
Different roles value different things (a research role might weigh education more). Pydantic accepts any
non-negative values, rejects an all-zero set and normalizes them to sum to 1.

**Q22. Is 85% a hiring probability?**
No. It's a similarity score between a resume's text and a JD's text. The UI labels it accordingly and every
candidate stays visible. Final decisions belong to the recruiter.

**Q23. How are ties handled?**
Sort by final score, then skill score, then semantic score. Exact ties share a rank (1, 2, 2, 4).

### Data quality, errors & security
**Q24. How does partial batch processing work?**
Each file is processed in its own try/except with its own commit. A corrupted file produces a `failed` row with a
message while the others continue. The endpoint returns 207 with per-file statuses.

**Q25. How do you detect duplicates?**
A SHA-256 hash of the file bytes is compared within the same job (exact duplicates). Same-email candidates also
get a "possible duplicate" warning, which catches the same person with a different file.

**Q26. How do you secure uploaded files?**
Extension and magic-byte validation, a size limit, and a batch limit. Files are stored under random UUID names
(never user input) with 0600 permissions, outside the web root, with a path-traversal check. Downloads are scoped
to the job. There's an optional API key with constant-time comparison. Secrets live in `.env`, and the export is
protected against CSV formula injection.

**Q27. What is "protection against unauthorized document access" in your app?**
All routes require the API key when it's configured. Resources are looked up by both `job_id` *and* the resource
id, so guessing a resume id from another job returns 404 (an IDOR protection). Raw files are never served
statically.

**Q28. How do you handle database failures?**
`OperationalError` maps to 503 with a clear message, other SQLAlchemy errors map to 500 without leaking SQL, and
upload loops roll back the session for the failed file only.

### Fairness & ethics
**Q29. How do you prevent bias?**
Lines with age, DOB, gender, marital status, religion, caste and nationality are removed before parsing results
are used for matching. Names and contact details are never used in scoring. Results are explained and
human-reviewed, never auto-rejected. Remaining risks: proxies (university names, career gaps) and taxonomy bias
toward certain terminology. Mitigations would be bias audits across groups and blind-review modes.

**Q30. Could embeddings carry bias?**
Yes. Pretrained models reflect their training data. That's one reason embeddings are only 30% of the score, they
compare *job-relevant sections*, and explanations make the influence visible.

### Testing
**Q31. How did you test matching accuracy?**
There are 12 synthetic resumes with an intended profile per JD. Tests assert the expected ordering: Aarav first
for Python Developer, Sneha first for Data Scientist, Karan first for AI/ML, and Neha (written with synonyms only)
second for AI/ML, plus property checks (all scores in 0–100, breakdown contributions sum to the final score).

**Q32. How are API and DB integration tested?**
`TestClient` against a real PostgreSQL test database. One test uploads 20 files (12 valid plus 8 edge cases) in a
single batch, runs the analysis, and checks ranking, filters, detail, compare, dashboard, CSV and re-analysis
after a weight change. The test DB is reset between tests.

**Q33. What would you add with more time?**
OCR, a job queue, Alembic migrations, auth/RBAC, pgvector, cross-encoder re-ranking, recruiter feedback loops
with bias monitoring, and multilingual support.

### Frontend
**Q34. How is the frontend structured?**
Pages per workflow step (`RequirementsPage`, `ResumesPage`, `DashboardPage`, `CandidatePage`, `ComparePage`)
inside a `JobWorkspace` that loads the job once and shares it through React Router's `Outlet` context. There are
reusable UI primitives (`ScoreBadge`, `SkillBadge`, `StatCard`, `StatusPill`, `ProgressBar`, `Alert`,
`EmptyState`), `RankingTable`, and Recharts wrappers. A single Axios client handles the base URL, API key and
error-message normalization.

**Q35. How is the upload progress shown?**
Axios `onUploadProgress` drives a progress bar. Each queued file goes queued → uploading → processing →
parsed/failed/duplicate, with the server's message. Client-side validation rejects bad types and sizes before
upload.

**Q36. How do search and filters work?**
Server-side query parameters (`search`, `fit`, `status`, `min_score`, `sort_by`, `order`), with the search box
debounced by 300 ms. Unscored or failed rows always sort last.

### Scalability
**Q37. How would this scale to 10,000 resumes?**
Parse on worker processes through a queue, batch-encode embeddings (or use a GPU), store resume embeddings in
pgvector to pre-filter candidates by ANN search before full scoring, paginate the candidates endpoint, and move
files to object storage (S3).

**Q38. What's the complexity of semantic matching?**
O(J × R) dot products per candidate (J JD statements ≤ 40, R resume sentences ≤ 80), so about 3,200
multiply-adds of 384 dimensions. That's trivial compared with encoding, which is cached per sentence.

---

## Part 5: Things to demo live (and what to say)
1. Paste the Python JD and point out **mandatory vs preferred** and the "4+ years / Bachelor's in CS" extraction.
   Edit one skill.
2. Upload the resumes **together with the edge cases** and narrate each error (scanned, corrupted, duplicate,
   .txt): "partial batch processing".
3. Run the analysis and show the progress bar, charts and "most missing skills" (good for spotting unrealistic JDs).
4. Open **Priya**: related-skill credit, the calculation string and the semantic evidence pairs.
5. Open **Fatima**: the employment timeline and overlap note.
6. Compare the top 3 with the radar chart, then export CSV.
7. Change weights to 100% skills, show the "outdated" banner, re-run, and watch the ranking change.

## Part 6: Numbers to remember
- Default weights: 40 / 30 / 20 / 10. Mandatory/preferred split: 75 / 25. Related credit: 50%. Semantic skill
  threshold: 0.70.
- Fit bands: ≥75 strong, ≥55 moderate, ≥35 weak.
- Semantic: 0.6 coverage + 0.4 best section, calibrated on [0.15, 0.75].
- Limits: 5 MB per file, 50 files per batch. MiniLM: 384 dimensions, 256-token limit.
- Tests: 70 backend + 6 frontend.
