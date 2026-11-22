import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useOutletContext } from "react-router-dom";
import { ArrowRight, ChevronDown, RotateCcw, Save, Scale } from "lucide-react";
import { JobsAPI, errorMessage } from "../api/client";
import TagInput from "../components/TagInput";
import { Alert, SectionTitle, Spinner } from "../components/ui";
import { COMPONENT_LABELS, EDUCATION_LABELS } from "../utils/format";

const DEFAULT_WEIGHTS = { skills: 40, semantic: 30, experience: 20, education: 10 };

function toPct(w) {
  return Object.fromEntries(Object.entries(w).map(([k, v]) => [k, Math.round(v * 100)]));
}

export default function RequirementsPage() {
  const { job, setJob } = useOutletContext();
  const location = useLocation();
  const [req, setReq] = useState(job.requirements);
  const [weights, setWeights] = useState(toPct(job.weights));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(location.state?.justCreated
    ? { type: "info", text: "Requirements were extracted automatically. Review and edit them before analysis." } : null);
  const [showRaw, setShowRaw] = useState(false);

  useEffect(() => { setReq(job.requirements); setWeights(toPct(job.weights)); }, [job.id]); // eslint-disable-line

  const set = (key) => (value) => setReq((r) => ({ ...r, [key]: value }));
  const weightTotal = useMemo(() => Object.values(weights).reduce((a, b) => a + Number(b), 0), [weights]);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      if (weightTotal <= 0) throw new Error("At least one weight must be greater than zero");
      const payload = {
        requirements: {
          ...req,
          min_experience_years: req.min_experience_years === "" ? null : req.min_experience_years,
          max_experience_years: req.max_experience_years === "" ? null : req.max_experience_years,
        },
        weights: Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, Number(v) / 100])),
      };
      const updated = await JobsAPI.update(job.id, payload);
      setJob(updated);
      setWeights(toPct(updated.weights));
      setMsg({ type: "success", text: updated.analysis_status === "outdated"
        ? "Saved. Results are now outdated - re-run the analysis on the Resumes step." : "Requirements saved." });
    } catch (e) {
      setMsg({ type: "error", text: e.response ? errorMessage(e) : e.message });
    } finally {
      setSaving(false);
    }
  };

  const numberInput = (key, placeholder) => (
    <input type="number" min="0" max="60" step="0.5" className="input" placeholder={placeholder}
      value={req[key] ?? ""} onChange={(e) => set(key)(e.target.value === "" ? "" : Number(e.target.value))} />
  );

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        {msg && <Alert type={msg.type} onClose={() => setMsg(null)}>{msg.text}</Alert>}

        <div className="card p-6">
          <SectionTitle title="Extracted requirements" description="Structured JSON extracted from the job description - edit anything that is wrong or missing." />
          <div className="space-y-5">
            <div>
              <label className="label" htmlFor="jt">Job title</label>
              <input id="jt" className="input" value={req.title} onChange={(e) => set("title")(e.target.value)} />
            </div>
            <TagInput label="Mandatory skills (must have)" variant="required" value={req.required_skills}
              onChange={set("required_skills")} placeholder="Add skill and press Enter" />
            <TagInput label="Preferred skills (nice to have)" value={req.preferred_skills}
              onChange={set("preferred_skills")} placeholder="Add skill and press Enter" />
            <div className="grid gap-4 sm:grid-cols-3">
              <div><label className="label">Min experience (yrs)</label>{numberInput("min_experience_years", "e.g. 3")}</div>
              <div><label className="label">Max experience (yrs)</label>{numberInput("max_experience_years", "optional")}</div>
              <div>
                <label className="label" htmlFor="edu">Minimum education</label>
                <select id="edu" className="input" value={req.education_level || ""} onChange={(e) => set("education_level")(e.target.value || null)}>
                  <option value="">Not specified</option>
                  {Object.entries(EDUCATION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            </div>
            <TagInput label="Accepted fields of study" value={req.education_fields} onChange={set("education_fields")}
              placeholder="e.g. computer science" />
            <div>
              <label className="label">Responsibilities (one per line)</label>
              <textarea className="input min-h-[140px] text-[13px]" value={req.responsibilities.join("\n")}
                onChange={(e) => set("responsibilities")(e.target.value.split("\n"))}
                onBlur={(e) => set("responsibilities")(e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))} />
            </div>
            <div>
              <label className="label">Qualifications (one per line)</label>
              <textarea className="input min-h-[80px] text-[13px]" value={req.qualifications.join("\n")}
                onChange={(e) => set("qualifications")(e.target.value.split("\n"))}
                onBlur={(e) => set("qualifications")(e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))} />
            </div>
          </div>
        </div>

        <div className="card">
          <button className="flex w-full items-center justify-between px-6 py-4 text-sm font-semibold text-slate-700" onClick={() => setShowRaw(!showRaw)}>
            Original job description {job.source_filename && <span className="font-normal text-slate-400">({job.source_filename})</span>}
            <ChevronDown className={`h-4 w-4 transition-transform ${showRaw ? "rotate-180" : ""}`} />
          </button>
          {showRaw && <pre className="max-h-96 overflow-auto whitespace-pre-wrap border-t border-slate-100 px-6 py-4 text-xs text-slate-600">{job.raw_text}</pre>}
        </div>
      </div>

      <div className="space-y-6">
        <div className="card p-6">
          <SectionTitle title="Scoring weights" description="Final = Σ component × weight. Weights are normalized to 100%." />
          <div className="space-y-4">
            {Object.keys(DEFAULT_WEIGHTS).map((k) => (
              <div key={k}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="font-medium text-slate-700">{COMPONENT_LABELS[k]}</span>
                  <span className="font-semibold text-blue-700">{weights[k]}%</span>
                </div>
                <input type="range" min="0" max="100" step="5" value={weights[k]} aria-label={`${COMPONENT_LABELS[k]} weight`}
                  onChange={(e) => setWeights((w) => ({ ...w, [k]: Number(e.target.value) }))} className="w-full accent-blue-600" />
              </div>
            ))}
            <div className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs ${weightTotal === 100 ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
              <span className="flex items-center gap-1.5"><Scale className="h-3.5 w-3.5" /> Total: {weightTotal}%</span>
              {weightTotal !== 100 && <span>will be normalized</span>}
            </div>
            <button className="btn-ghost w-full text-xs" onClick={() => setWeights(DEFAULT_WEIGHTS)}>
              <RotateCcw className="h-3.5 w-3.5" /> Reset to 40 / 30 / 20 / 10
            </button>
          </div>
        </div>

        <div className="card space-y-3 p-6">
          <button className="btn-primary w-full" onClick={save} disabled={saving}>
            {saving ? <Spinner className="h-4 w-4 text-white" /> : <Save className="h-4 w-4" />} Save requirements
          </button>
          <Link to={`/jobs/${job.id}/resumes`} className="btn-secondary w-full">
            Continue to resumes <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="text-xs leading-relaxed text-slate-500">
            Mandatory skills count for 75% of the skill score, preferred for 25%. Related skills (e.g. Flask for FastAPI) earn 50% credit.
          </p>
        </div>
      </div>
    </div>
  );
}
