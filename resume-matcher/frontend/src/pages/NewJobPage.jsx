import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Sparkles, Upload } from "lucide-react";
import { JobsAPI, errorMessage } from "../api/client";
import { Alert, Spinner } from "../components/ui";
import { formatBytes, validateFile } from "../utils/format";

export default function NewJobPage() {
  const [mode, setMode] = useState("paste");
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (mode === "paste" && text.trim().length < 30) return setError("Please paste a job description (at least 30 characters).");
    if (mode === "upload") {
      if (!file) return setError("Please choose a PDF or DOCX file.");
      const v = validateFile(file);
      if (v) return setError(v);
    }
    setBusy(true);
    try {
      const job = mode === "paste" ? await JobsAPI.create(text, title) : await JobsAPI.upload(file, title);
      navigate(`/jobs/${job.id}/requirements`, { state: { justCreated: true } });
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-900">New Job Description</h1>
      <p className="mt-1 text-sm text-slate-500">
        The AI extracts title, skills, experience and education into structured requirements you can review and edit.
      </p>

      <form onSubmit={submit} className="card mt-6 space-y-5 p-6">
        <div className="inline-flex rounded-lg bg-slate-100 p-1">
          {[["paste", "Paste text", FileText], ["upload", "Upload file", Upload]].map(([m, label, Icon]) => (
            <button key={m} type="button" onClick={() => setMode(m)}
              className={`flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium ${mode === m ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"}`}>
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </div>

        <div>
          <label className="label" htmlFor="title">Job title (optional – auto-detected)</label>
          <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Senior Python Developer" maxLength={255} />
        </div>

        {mode === "paste" ? (
          <div>
            <label className="label" htmlFor="jd">Job description</label>
            <textarea id="jd" className="input min-h-[320px] font-mono text-[13px] leading-relaxed" value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={"Job Title: ...\n\nResponsibilities\n- ...\n\nRequired Skills\n- Python, SQL ...\n\nPreferred Skills\n- ...\n\nExperience\n- 3+ years ...\n\nEducation\n- Bachelor's degree in ..."} />
            <p className="mt-1 text-xs text-slate-400">{text.length.toLocaleString()} characters</p>
          </div>
        ) : (
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); setFile(e.dataTransfer.files[0]); }}
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center hover:border-blue-400 hover:bg-blue-50/40"
          >
            <Upload className="mb-2 h-8 w-8 text-blue-500" />
            {file ? (
              <p className="text-sm font-medium text-slate-800">{file.name} <span className="text-slate-400">({formatBytes(file.size)})</span></p>
            ) : (
              <>
                <p className="text-sm font-medium text-slate-700">Drop a JD here or click to browse</p>
                <p className="mt-1 text-xs text-slate-500">PDF or DOCX, max 5 MB</p>
              </>
            )}
            <input ref={inputRef} type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => setFile(e.target.files[0])} />
          </div>
        )}

        {error && <Alert>{error}</Alert>}

        <div className="flex justify-end">
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? <Spinner className="h-4 w-4 text-white" /> : <Sparkles className="h-4 w-4" />}
            {busy ? "Extracting requirements…" : "Extract requirements"}
          </button>
        </div>
      </form>
    </div>
  );
}
