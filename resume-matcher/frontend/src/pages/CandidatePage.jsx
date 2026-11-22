import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import {
  AlertTriangle, ArrowLeft, Briefcase, CheckCircle2, Download, GraduationCap, Info, Mail, MinusCircle, Phone, Sparkles, XCircle,
} from "lucide-react";
import { AnalysisAPI, ResumesAPI, errorMessage, saveBlob } from "../api/client";
import { Alert, PageLoader, ScoreBadge, ScoreBar, SectionTitle, SkillBadge } from "../components/ui";
import { EDUCATION_LABELS, TONE_CLASSES, fmtScore, fmtYears, scoreTone } from "../utils/format";

const MATCH_META = {
  exact: { icon: CheckCircle2, cls: "text-emerald-600", label: "Matched" },
  related: { icon: MinusCircle, cls: "text-amber-500", label: "Related" },
  semantic: { icon: MinusCircle, cls: "text-amber-500", label: "Semantically similar" },
  missing: { icon: XCircle, cls: "text-rose-500", label: "Missing" },
};

function SkillRows({ items }) {
  if (!items?.length) return <p className="text-sm text-slate-400">None specified in the JD</p>;
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((s) => {
        const m = MATCH_META[s.match];
        const Icon = m.icon;
        return (
          <li key={s.skill} className="flex items-center gap-3 py-2 text-sm">
            <Icon className={`h-4 w-4 shrink-0 ${m.cls}`} />
            <span className="flex-1 font-medium text-slate-800">{s.skill}</span>
            <span className="text-xs text-slate-500">
              {m.label}{s.via ? ` via ${s.via}` : ""}{s.similarity ? ` (${s.similarity})` : ""}
            </span>
            <span className="w-12 text-right text-xs font-semibold text-slate-600">{Math.round(s.credit * 100)}%</span>
          </li>
        );
      })}
    </ul>
  );
}

function Bullets({ items, icon: Icon, cls }) {
  if (!items?.length) return <p className="text-sm text-slate-400">None</p>;
  return (
    <ul className="space-y-2">
      {items.map((t, i) => (
        <li key={i} className="flex gap-2 text-sm text-slate-700"><Icon className={`mt-0.5 h-4 w-4 shrink-0 ${cls}`} /><span>{t}</span></li>
      ))}
    </ul>
  );
}

export default function CandidatePage() {
  const { job } = useOutletContext();
  const { candidateId } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    AnalysisAPI.candidate(job.id, candidateId).then(setData).catch((e) => setError(errorMessage(e)));
  }, [job.id, candidateId]);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <PageLoader label="Loading candidate analysis…" />;

  const { candidate: c, scores, skill_details: sk, semantic_details: sem, experience_details: exp,
    education_details: edu, explanation: ex } = data;
  const tone = TONE_CLASSES[scoreTone(scores?.final_score)];

  const download = async () => {
    try {
      const resumes = await ResumesAPI.list(job.id);
      const r = resumes.find((x) => x.candidate_id === c.id);
      saveBlob(await ResumesAPI.download(job.id, r.id), r.original_filename);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to={`/jobs/${job.id}/dashboard`} className="btn-ghost -ml-3"><ArrowLeft className="h-4 w-4" /> Back to ranking</Link>
        <button className="btn-secondary" onClick={download}><Download className="h-4 w-4" /> Original resume</button>
      </div>

      {/* Header */}
      <div className="card flex flex-col gap-6 p-6 md:flex-row md:items-center">
        <div className={`flex h-28 w-28 shrink-0 flex-col items-center justify-center rounded-2xl ring-1 ring-inset ${tone.bg} ${tone.ring}`}>
          <span className={`text-3xl font-bold ${tone.text}`}>{scores ? fmtScore(scores.final_score, 0) : "—"}</span>
          <span className="text-xs text-slate-500">/ 100</span>
        </div>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900">{c.name || "Unknown candidate"}</h2>
            {scores?.rank && <span className="rounded-full bg-navy-900 px-2.5 py-0.5 text-xs font-semibold text-white">Rank #{scores.rank}</span>}
            {scores && <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${tone.bg} ${tone.text}`}>{scores.fit_label}</span>}
          </div>
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-600">
            {c.email && <span className="flex items-center gap-1.5"><Mail className="h-4 w-4 text-slate-400" />{c.email}</span>}
            {c.phone && <span className="flex items-center gap-1.5"><Phone className="h-4 w-4 text-slate-400" />{c.phone}</span>}
            <span className="flex items-center gap-1.5"><Briefcase className="h-4 w-4 text-slate-400" />{fmtYears(c.experience_years)}</span>
            <span className="flex items-center gap-1.5"><GraduationCap className="h-4 w-4 text-slate-400" />{EDUCATION_LABELS[c.highest_education] || "Unknown"}</span>
          </div>
          {ex?.summary && <p className="mt-3 text-sm leading-relaxed text-slate-700">{ex.summary}</p>}
        </div>
      </div>

      {!scores && <Alert type="info">This candidate has not been analyzed yet. Run the analysis from the Resumes step.</Alert>}

      {scores && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="card p-6 lg:col-span-1">
            <SectionTitle title="Score breakdown" />
            <div className="space-y-4">
              <ScoreBar label="Skill match" score={scores.skill_score} weight={scores.weights_used.skills} note={sk.formula} />
              <ScoreBar label="Semantic similarity" score={scores.semantic_score} weight={scores.weights_used.semantic} />
              <ScoreBar label="Experience" score={scores.experience_score} weight={scores.weights_used.experience} />
              <ScoreBar label="Education" score={scores.education_score} weight={scores.weights_used.education} />
            </div>
            <div className="mt-5 rounded-lg bg-slate-50 p-3">
              <p className="label mb-1">Calculation</p>
              <p className="font-mono text-xs leading-relaxed text-slate-700">{ex.formula}</p>
            </div>
          </div>

          <div className="card p-6 lg:col-span-2">
            <SectionTitle title="Why this score?" description="Generated only from extracted resume data and calculated results" />
            <div className="grid gap-6 md:grid-cols-2">
              <div><p className="label">Strengths</p><Bullets items={ex.strengths} icon={CheckCircle2} cls="text-emerald-500" /></div>
              <div><p className="label">Gaps</p><Bullets items={ex.gaps} icon={AlertTriangle} cls="text-amber-500" /></div>
            </div>
            {ex.notes?.length > 0 && (
              <div className="mt-5 border-t border-slate-100 pt-4"><p className="label">Notes for the recruiter</p><Bullets items={ex.notes} icon={Info} cls="text-blue-500" /></div>
            )}
          </div>

          <div className="card p-6">
            <SectionTitle title="Mandatory skills" description={sk.mandatory_coverage !== null && sk.mandatory_coverage !== undefined ? `Coverage ${fmtScore(sk.mandatory_coverage)}%` : ""} />
            <SkillRows items={sk.mandatory} />
          </div>
          <div className="card p-6">
            <SectionTitle title="Preferred skills" description={sk.preferred_coverage !== null && sk.preferred_coverage !== undefined ? `Coverage ${fmtScore(sk.preferred_coverage)}%` : ""} />
            <SkillRows items={sk.preferred} />
          </div>

          <div className="card space-y-5 p-6">
            <div>
              <SectionTitle title="Experience" />
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Required</p>
                  <p className="text-lg font-bold text-slate-900">{exp.required_min !== undefined && exp.required_min !== null ? `${exp.required_min}${exp.required_max ? `–${exp.required_max}` : "+"} yrs` : "—"}</p></div>
                <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Candidate</p>
                  <p className="text-lg font-bold text-slate-900">{fmtYears(exp.candidate_years ?? c.experience_years)}</p></div>
              </div>
              <p className="mt-2 text-xs text-slate-500">{exp.note}</p>
            </div>
            <div>
              <SectionTitle title="Education" />
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Required</p>
                  <p className="text-sm font-bold text-slate-900">{edu.required_level_label || "Not specified"}</p></div>
                <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Candidate</p>
                  <p className="text-sm font-bold text-slate-900">{edu.candidate_level_label || EDUCATION_LABELS[c.highest_education] || "Unknown"}</p></div>
              </div>
              <p className="mt-2 text-xs text-slate-500">{edu.note}</p>
            </div>
          </div>

          {sem?.available && (
            <div className="card p-6 lg:col-span-3">
              <SectionTitle title="Semantic evidence" description={`Cosine similarity of ${sem.method} embeddings · ${sem.jd_chunks_compared} JD statements × ${sem.resume_chunks_compared} resume sentences`} />
              <div className="grid gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <p className="label">Best-matching JD requirements</p>
                  <ul className="space-y-3">
                    {sem.top_evidence.map((e, i) => (
                      <li key={i} className="rounded-lg border border-slate-100 p-3 text-sm">
                        <div className="flex items-start justify-between gap-3">
                          <p className="font-medium text-slate-800">{e.requirement}</p>
                          <span className="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-xs font-semibold text-blue-700">{e.similarity.toFixed(2)}</span>
                        </div>
                        <p className="mt-1 text-slate-500">↳ “{e.resume_evidence}”</p>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="space-y-5">
                  <div>
                    <p className="label">Section similarity to JD</p>
                    <ul className="space-y-1.5 text-sm">
                      {Object.entries(sem.section_similarities).map(([k, v]) => (
                        <li key={k} className="flex justify-between"><span className="capitalize text-slate-600">{k.replace("_", " ")}</span><span className="font-semibold">{v.toFixed(2)}</span></li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="label">Least-covered requirements</p>
                    <ul className="space-y-1.5 text-xs text-slate-600">
                      {sem.weakest_requirements.map((w, i) => <li key={i}>• {w.requirement} <span className="text-slate-400">({w.best_similarity.toFixed(2)})</span></li>)}
                    </ul>
                  </div>
                  <p className="text-[11px] text-slate-400">Raw similarity {sem.raw_similarity} → calibrated {fmtScore(sem.score)}/100</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Extracted information */}
      <div className="card p-6">
        <SectionTitle title="Extracted candidate information" description={`Parsed from ${data.filename}`} />
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-5">
            <div>
              <p className="label">Skills ({c.skills.length})</p>
              <div className="flex flex-wrap gap-1.5">{c.skills.map((s) => <SkillBadge key={s}>{s}</SkillBadge>)}</div>
            </div>
            <div>
              <p className="label">Education</p>
              {c.education.length ? c.education.map((e, i) => (
                <div key={i} className="mb-2 text-sm"><p className="font-medium text-slate-800">{e.degree}</p>
                  <p className="text-xs text-slate-500">{[e.institution, e.year, e.field].filter(Boolean).join(" · ")}</p></div>
              )) : <p className="text-sm text-slate-400">Not found</p>}
            </div>
            <div><p className="label">Certifications</p>{c.certifications.length ? <ul className="list-inside list-disc text-sm text-slate-700">{c.certifications.map((x) => <li key={x}>{x}</li>)}</ul> : <p className="text-sm text-slate-400">None listed</p>}</div>
            <div><p className="label">Projects</p>{c.projects.length ? <ul className="list-inside list-disc text-sm text-slate-700">{c.projects.map((x) => <li key={x}>{x}</li>)}</ul> : <p className="text-sm text-slate-400">None listed</p>}</div>
          </div>
          <div className="space-y-5">
            <div>
              <p className="label">Employment history (overlaps counted once)</p>
              {c.employment_history.length ? (
                <ol className="relative space-y-4 border-l border-slate-200 pl-5">
                  {c.employment_history.map((h, i) => (
                    <li key={i} className="text-sm">
                      <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-blue-500" />
                      <p className="font-medium text-slate-800">{h.title || "Role"}{h.company && <span className="font-normal text-slate-500"> · {h.company}</span>}</p>
                      <p className="text-xs text-slate-500">{h.start} → {h.end} · {(h.duration_months / 12).toFixed(1)} yrs</p>
                    </li>
                  ))}
                </ol>
              ) : <p className="text-sm text-slate-400">No dated employment found</p>}
            </div>
            {c.summary && <div><p className="label">Summary</p><p className="text-sm text-slate-700">{c.summary}</p></div>}
            {c.warnings.length > 0 && (
              <div><p className="label">Extraction warnings</p><Bullets items={c.warnings} icon={AlertTriangle} cls="text-amber-500" /></div>
            )}
          </div>
        </div>
      </div>

      {ex?.disclaimer && (
        <p className="flex items-start gap-2 rounded-lg bg-navy-50 p-4 text-xs leading-relaxed text-navy-800">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0" /> {ex.disclaimer}
        </p>
      )}
    </div>
  );
}
