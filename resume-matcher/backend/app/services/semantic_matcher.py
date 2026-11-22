"""Semantic similarity between a JD and the relevant sections of a resume.

Two complementary signals (both cosine similarity of sentence embeddings):

1. Requirement coverage - every JD requirement/responsibility sentence is compared with every
   resume sentence (experience, projects, summary, skills); for each requirement we keep the best
   match and average them. This answers "how much of the JD is evidenced somewhere in the resume?"
2. Section similarity - the JD overview vs each resume section as a whole; we keep the best
   section. This captures overall domain/role alignment.

raw = 0.6 * coverage + 0.4 * best_section, then linearly calibrated to 0-100 because raw
MiniLM cosine values for related professional text typically fall between ~0.15 and ~0.75.
The result is a similarity indicator, NOT a probability of being a good hire.
"""
from app.schemas.job import JobRequirements
from app.services.embedding_service import get_embedding_service
from app.services.text_preprocessing import clean_text, split_sentences

RESUME_SECTIONS = ("summary", "experience", "projects", "skills")
CALIBRATION = {"transformer": (0.15, 0.75), "tfidf": (0.0, 0.45)}
MAX_CHUNKS = 80


def _calibrate(raw: float, transformer: bool) -> float:
    lo, hi = CALIBRATION["transformer" if transformer else "tfidf"]
    return round(max(0.0, min(1.0, (raw - lo) / (hi - lo))) * 100, 1)


def build_jd_chunks(req: JobRequirements, raw_text: str) -> tuple[list[str], str]:
    chunks = [r for r in req.responsibilities + req.qualifications if len(r) >= 15]
    if req.required_skills:
        chunks.append(f"{req.title} with skills in " + ", ".join(req.required_skills))
    if len(chunks) < 3:
        chunks += split_sentences(clean_text(raw_text))
    chunks = list(dict.fromkeys(chunks))[:40]
    overview = f"{req.title}. " + " ".join(req.responsibilities[:8]) + " Skills: " + \
        ", ".join(req.required_skills + req.preferred_skills)
    if len(overview) < 120:
        overview = clean_text(raw_text)[:1500]
    return chunks, overview


def semantic_match(req: JobRequirements, raw_jd: str, sections: dict[str, str], full_text: str) -> dict:
    svc = get_embedding_service()
    jd_chunks, jd_overview = build_jd_chunks(req, raw_jd)

    resume_chunks: list[str] = []
    for sec in ("experience", "projects", "summary", "skills", "certifications"):
        resume_chunks += split_sentences(sections.get(sec, ""), min_len=12)
    if len(resume_chunks) < 3:
        resume_chunks += split_sentences(full_text, min_len=12)
    resume_chunks = list(dict.fromkeys(resume_chunks))[:MAX_CHUNKS]

    if not jd_chunks or not resume_chunks:
        return {"score": None, "available": False, "method": svc.backend_name,
                "note": "Not enough text in the JD or resume for semantic comparison"}

    transformer = svc.uses_transformer
    sim = svc.similarity(jd_chunks, resume_chunks)
    best_idx = sim.argmax(axis=1)
    best_val = sim.max(axis=1)
    coverage = float(best_val.mean())

    section_sims: dict[str, float] = {}
    sec_texts = {s: sections[s][:1500] for s in RESUME_SECTIONS if sections.get(s)}
    if sec_texts:
        ssim = svc.similarity([jd_overview], list(sec_texts.values()))[0]
        section_sims = {name: round(float(v), 3) for name, v in zip(sec_texts, ssim)}
    else:
        section_sims = {"full_resume": round(float(svc.similarity([jd_overview], [full_text[:2000]])[0][0]), 3)}
    best_section = max(section_sims.values())

    raw = 0.6 * coverage + 0.4 * best_section
    order = best_val.argsort()[::-1]
    evidence = [
        {"requirement": jd_chunks[i], "resume_evidence": resume_chunks[best_idx[i]],
         "similarity": round(float(best_val[i]), 3)}
        for i in order[:5]
    ]
    weakest = [
        {"requirement": jd_chunks[i], "best_similarity": round(float(best_val[i]), 3)}
        for i in order[::-1][:3]
    ]
    return {
        "score": _calibrate(raw, transformer),
        "available": True,
        "method": svc.backend_name,
        "raw_similarity": round(raw, 4),
        "requirement_coverage": round(coverage, 4),
        "best_section": max(section_sims, key=section_sims.get),
        "section_similarities": section_sims,
        "top_evidence": evidence,
        "weakest_requirements": weakest,
        "jd_chunks_compared": len(jd_chunks),
        "resume_chunks_compared": len(resume_chunks),
    }
