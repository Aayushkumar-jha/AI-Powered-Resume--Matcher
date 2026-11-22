import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Briefcase, ChevronRight, PlusCircle, Trash2 } from "lucide-react";
import { JobsAPI, errorMessage } from "../api/client";
import { Alert, EmptyState, PageLoader, StatusPill } from "../components/ui";

export default function JobsPage() {
  const [jobs, setJobs] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const load = () => JobsAPI.list().then(setJobs).catch((e) => { setError(errorMessage(e)); setJobs([]); });
  useEffect(() => { load(); }, []);

  const remove = async (job) => {
    if (!window.confirm(`Delete "${job.title}" and all its resumes and results? This cannot be undone.`)) return;
    try {
      await JobsAPI.remove(job.id);
      load();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Job Openings</h1>
          <p className="mt-1 text-sm text-slate-500">Create a job, upload resumes and get an explainable candidate ranking.</p>
        </div>
        <Link to="/jobs/new" className="btn-primary"><PlusCircle className="h-4 w-4" /> New Job</Link>
      </div>
      {error && <div className="mb-4"><Alert onClose={() => setError("")}>{error}</Alert></div>}
      {jobs === null ? (
        <PageLoader />
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No jobs yet"
          description="Paste or upload a job description to get started. Sample JDs are available in sample_data/jds."
          action={<Link to="/jobs/new" className="btn-primary"><PlusCircle className="h-4 w-4" /> Create first job</Link>}
        />
      ) : (
        <div className="card overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="th">Job title</th>
                <th className="th">Resumes</th>
                <th className="th">Analysis</th>
                <th className="th hidden sm:table-cell">Created</th>
                <th className="th" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((j) => (
                <tr key={j.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/jobs/${j.id}/${j.analysis_status === "completed" ? "dashboard" : "requirements"}`)}>
                  <td className="td font-medium text-slate-900">{j.title}</td>
                  <td className="td">{j.resume_count}</td>
                  <td className="td"><StatusPill status={j.analysis_status} /></td>
                  <td className="td hidden text-slate-500 sm:table-cell">{new Date(j.created_at).toLocaleDateString()}</td>
                  <td className="td text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button className="btn-ghost p-2 text-slate-400 hover:text-rose-600" aria-label={`Delete ${j.title}`}
                        onClick={(e) => { e.stopPropagation(); remove(j); }}>
                        <Trash2 className="h-4 w-4" />
                      </button>
                      <ChevronRight className="h-4 w-4 text-slate-400" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
