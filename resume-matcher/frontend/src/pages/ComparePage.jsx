import { useEffect, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { AnalysisAPI, errorMessage } from "../api/client";
import { ComponentRadar } from "../components/Charts";
import { Alert, PageLoader, ScoreBadge, SectionTitle, SkillBadge } from "../components/ui";
import { EDUCATION_LABELS, fmtYears } from "../utils/format";

export default function ComparePage() {
  const { job } = useOutletContext();
  const [params] = useSearchParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const ids = (params.get("ids") || "").split(",").filter(Boolean);
    AnalysisAPI.compare(job.id, ids).then(setData).catch((e) => setError(errorMessage(e)));
  }, [job.id, params]);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <PageLoader label="Loading comparison…" />;

  const series = data.map((d) => ({
    name: d.candidate.name || `#${d.candidate.id}`,
    skills: d.scores?.skill_score, semantic: d.scores?.semantic_score,
    experience: d.scores?.experience_score, education: d.scores?.education_score,
  }));

  const rows = [
    ["Rank", (d) => d.scores?.rank ?? "—"],
    ["Overall match", (d) => <ScoreBadge score={d.scores?.final_score} size="lg" />],
    ["Fit", (d) => d.scores?.fit_label],
    ["Skill score", (d) => <ScoreBadge score={d.scores?.skill_score} />],
    ["Semantic score", (d) => <ScoreBadge score={d.scores?.semantic_score} />],
    ["Experience score", (d) => <ScoreBadge score={d.scores?.experience_score} />],
    ["Education score", (d) => <ScoreBadge score={d.scores?.education_score} />],
    ["Experience", (d) => fmtYears(d.candidate.experience_years)],
    ["Highest education", (d) => EDUCATION_LABELS[d.candidate.highest_education] || "Unknown"],
    ["Matched mandatory", (d) => <div className="flex flex-wrap gap-1">{(d.skill_details.matched_mandatory || []).map((s) => <SkillBadge key={s} variant="matched">{s}</SkillBadge>)}</div>],
    ["Related (partial)", (d) => <div className="flex flex-wrap gap-1">{(d.skill_details.related_mandatory || []).map((s) => <SkillBadge key={s.skill} variant="related">{s.skill} ~ {s.via}</SkillBadge>)}</div>],
    ["Missing mandatory", (d) => <div className="flex flex-wrap gap-1">{(d.skill_details.missing_mandatory || []).map((s) => <SkillBadge key={s} variant="missing">{s}</SkillBadge>)}</div>],
    ["Missing preferred", (d) => <div className="flex flex-wrap gap-1">{(d.skill_details.missing_preferred || []).map((s) => <SkillBadge key={s} variant="missing">{s}</SkillBadge>)}</div>],
  ];

  return (
    <div className="space-y-6">
      <Link to={`/jobs/${job.id}/dashboard`} className="btn-ghost -ml-3"><ArrowLeft className="h-4 w-4" /> Back to ranking</Link>
      <div className="card p-6">
        <SectionTitle title="Component comparison" description="Each axis is a 0–100 component score" />
        <ComponentRadar series={series} />
      </div>
      <div className="card overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="th w-44" />
              {data.map((d) => (
                <th key={d.candidate.id} className="th normal-case">
                  <Link className="text-sm font-semibold text-blue-700 hover:underline" to={`/jobs/${job.id}/candidates/${d.candidate.id}`}>{d.candidate.name || "Unknown"}</Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map(([label, render]) => (
              <tr key={label}>
                <td className="td text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</td>
                {data.map((d) => <td key={d.candidate.id} className="td">{render(d)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
