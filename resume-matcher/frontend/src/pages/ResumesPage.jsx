import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { CheckCircle2, CloudUpload, FileText, Play, Trash2, X, XCircle } from "lucide-react";
import { AnalysisAPI, ResumesAPI, errorMessage } from "../api/client";
import { Alert, EmptyState, ProgressBar, SectionTitle, Spinner, StatusPill } from "../components/ui";
import { formatBytes, validateFile } from "../utils/format";

let uid = 0;

export default function ResumesPage() {
  const { job, refresh } = useOutletContext();
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [queue, setQueue] = useState([]); // {id, file, status, error}
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [resumes, setResumes] = useState(null);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  const loadResumes = useCallback(() => ResumesAPI.list(job.id).then(setResumes).catch((e) => setError(errorMessage(e))), [job.id]);
  useEffect(() => { loadResumes(); }, [loadResumes]);

  // Resume polling if the page is opened while an analysis is running
  useEffect(() => { if (job.analysis_status === "processing") poll(); }, []); // eslint-disable-line

  const addFiles = (fileList) => {
    const items = Array.from(fileList).map((file) => {
      const err = validateFile(file);
      return { id: ++uid, file, status: err ? "rejected" : "queued", error: err };
    });
    setQueue((q) => [...q, ...items]);
    setSummary(null);
  };

  const upload = async () => {
    const valid = queue.filter((q) => q.status === "queued");
    if (!valid.length) return;
    setUploading(true);
    setError("");
    setProgress(0);
    setQueue((q) => q.map((i) => (i.status === "queued" ? { ...i, status: "uploading" } : i)));
    try {
      const res = await ResumesAPI.upload(job.id, valid.map((v) => v.file), (p) => {
        setProgress(p);
        if (p >= 100) setQueue((q) => q.map((i) => (i.status === "uploading" ? { ...i, status: "processing" } : i)));
      });
      // results come back in the same order as the files we sent
      const byId = new Map(valid.map((v, idx) => [v.id, res.results[idx]]));
      setQueue((q) => q.map((i) => {
        const r = byId.get(i.id);
        return r ? { ...i, status: r.status, error: r.error, name: r.candidate_name, warnings: r.warnings } : i;
      }));
      setSummary(res);
      await Promise.all([loadResumes(), refresh()]);
    } catch (e) {
      setError(errorMessage(e));
      setQueue((q) => q.map((i) => (["uploading", "processing"].includes(i.status) ? { ...i, status: "queued" } : i)));
    } finally {
      setUploading(false);
    }
  };

  const poll = async () => {
    try {
      const s = await AnalysisAPI.status(job.id);
      setAnalysis(s);
      if (s.status === "processing") return setTimeout(poll, 800);
      await refresh();
      if (s.status === "completed") navigate(`/jobs/${job.id}/dashboard`);
      if (s.status === "failed") setError(`Analysis failed: ${s.error}`);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const startAnalysis = async () => {
    setError("");
    try {
      setAnalysis(await AnalysisAPI.start(job.id));
      poll();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const removeResume = async (r) => {
    if (!window.confirm(`Remove ${r.original_filename}?`)) return;
    try {
      await ResumesAPI.remove(job.id, r.id);
      await Promise.all([loadResumes(), refresh()]);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const queuedCount = queue.filter((q) => q.status === "queued").length;
  const parsedCount = resumes?.filter((r) => r.status === "parsed").length || 0;
  const running = analysis?.status === "processing";

  return (
    <div className="space-y-6">
      {error && <Alert onClose={() => setError("")}>{error}</Alert>}

      <div className="card p-6">
        <SectionTitle title="Upload resumes" description="Drag & drop or select multiple PDF/DOCX files (max 5 MB each, up to 50 per batch)." />
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-blue-50/40"}`}
        >
          <CloudUpload className="mb-2 h-10 w-10 text-blue-500" />
          <p className="text-sm font-medium text-slate-700">Drop resumes here or <span className="text-blue-600">browse</span></p>
          <p className="mt-1 text-xs text-slate-500">Corrupted, scanned, duplicate and unsupported files are reported individually</p>
          <input ref={inputRef} type="file" multiple accept=".pdf,.docx" className="hidden" data-testid="file-input"
            onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
        </div>

        {queue.length > 0 && (
          <div className="mt-5">
            {uploading && (
              <div className="mb-3">
                <div className="mb-1 flex justify-between text-xs text-slate-500">
                  <span>{progress < 100 ? "Uploading…" : "Parsing resumes on the server…"}</span><span>{progress}%</span>
                </div>
                <ProgressBar value={progress} />
              </div>
            )}
            <ul className="max-h-80 divide-y divide-slate-100 overflow-auto rounded-lg border border-slate-200">
              {queue.map((q) => (
                <li key={q.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                  <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-slate-800">{q.file.name}
                      {q.name && <span className="ml-2 font-normal text-slate-500">→ {q.name}</span>}
                    </p>
                    {q.error && <p className="text-xs text-rose-600">{q.error}</p>}
                    {q.warnings?.length > 0 && <p className="truncate text-xs text-amber-600" title={q.warnings.join("; ")}>{q.warnings.join("; ")}</p>}
                  </div>
                  <span className="hidden text-xs text-slate-400 sm:inline">{formatBytes(q.file.size)}</span>
                  <StatusPill status={q.status} />
                  {["queued", "rejected"].includes(q.status) && !uploading && (
                    <button onClick={() => setQueue((all) => all.filter((x) => x.id !== q.id))} className="text-slate-400 hover:text-slate-700" aria-label="Remove from queue">
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              {summary ? (
                <p className="flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1 text-emerald-700"><CheckCircle2 className="h-4 w-4" /> {summary.parsed} parsed</span>
                  {summary.failed > 0 && <span className="flex items-center gap-1 text-rose-700"><XCircle className="h-4 w-4" /> {summary.failed} not processed</span>}
                </p>
              ) : <span className="text-sm text-slate-500">{queuedCount} file(s) ready</span>}
              <div className="flex gap-2">
                <button className="btn-ghost" onClick={() => { setQueue([]); setSummary(null); }} disabled={uploading}>Clear list</button>
                <button className="btn-primary" onClick={upload} disabled={uploading || !queuedCount}>
                  {uploading ? <Spinner className="h-4 w-4 text-white" /> : <CloudUpload className="h-4 w-4" />}
                  Upload {queuedCount || ""} file(s)
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card p-6">
        <SectionTitle
          title="Run AI matching"
          description={`${parsedCount} successfully parsed resume(s) will be scored against "${job.title}".`}
          action={
            <button className="btn-primary" onClick={startAnalysis} disabled={running || !parsedCount}>
              {running ? <Spinner className="h-4 w-4 text-white" /> : <Play className="h-4 w-4" />}
              {job.analysis_status === "completed" || job.analysis_status === "outdated" ? "Re-run analysis" : "Start analysis"}
            </button>
          }
        />
        {running && (
          <div>
            <div className="mb-1 flex justify-between text-xs text-slate-500">
              <span>Embedding resumes and computing scores… ({analysis.done}/{analysis.total})</span>
              <span>{analysis.progress}%</span>
            </div>
            <ProgressBar value={analysis.progress} />
            <p className="mt-2 text-xs text-slate-400">The first run downloads/loads the all-MiniLM-L6-v2 model and may take a little longer.</p>
          </div>
        )}
        {job.analysis_status === "outdated" && !running && (
          <Alert type="warning">Requirements, weights or resumes changed since the last analysis. Re-run to update the ranking.</Alert>
        )}
      </div>

      <div className="card overflow-hidden">
        <div className="px-6 pt-6"><SectionTitle title="Processing status" description="Every uploaded file with its individual parsing result." /></div>
        {resumes === null ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : resumes.length === 0 ? (
          <div className="px-6 pb-6"><EmptyState title="No resumes uploaded" description="Sample resumes are in sample_data/resumes and edge cases in sample_data/edge_cases." /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50"><tr>
                <th className="th">File</th><th className="th">Candidate</th><th className="th">Status</th><th className="th">Details</th><th className="th" />
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {resumes.map((r) => (
                  <tr key={r.id}>
                    <td className="td font-medium text-slate-800">{r.original_filename}<div className="text-xs font-normal uppercase text-slate-400">{r.file_type} · {formatBytes(r.file_size)}</div></td>
                    <td className="td">{r.candidate_name || <span className="text-slate-400">—</span>}</td>
                    <td className="td"><StatusPill status={r.status} /></td>
                    <td className="td max-w-md text-xs text-slate-500">{r.error_message || "Parsed successfully"}</td>
                    <td className="td text-right">
                      <button className="text-slate-400 hover:text-rose-600" onClick={() => removeResume(r)} aria-label={`Delete ${r.original_filename}`}>
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
