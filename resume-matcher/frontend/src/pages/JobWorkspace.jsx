import { useCallback, useEffect, useState } from "react";
import { Link, Outlet, useParams } from "react-router-dom";
import { JobsAPI, errorMessage } from "../api/client";
import JobHeader from "../components/JobHeader";
import { Alert, PageLoader } from "../components/ui";

/** Loads the job once and shares it (plus a refresh function) with nested pages via Outlet context. */
export default function JobWorkspace() {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  const refresh = useCallback(
    () => JobsAPI.get(jobId).then((j) => { setJob(j); return j; }).catch((e) => setError(errorMessage(e))),
    [jobId]
  );
  useEffect(() => { setJob(null); setError(""); refresh(); }, [refresh]);

  if (error) return <Alert title="Could not load job">{error} <Link className="underline" to="/">Back to jobs</Link></Alert>;
  if (!job) return <PageLoader label="Loading job…" />;
  return (
    <div>
      <JobHeader job={job} />
      <Outlet context={{ job, setJob, refresh }} />
    </div>
  );
}
