import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { Award, Download, FileCheck2, GitCompare, Search, TrendingUp, Upload, Users } from "lucide-react";
import { AnalysisAPI, errorMessage, saveBlob } from "../api/client";
import { FitDistributionChart, HorizontalBarChart, ScoreDistributionChart } from "../components/Charts";
import RankingTable from "../components/RankingTable";
import { Alert, EmptyState, PageLoader, SectionTitle, Spinner, StatCard } from "../components/ui";
import { COMPONENT_LABELS, fmtScore } from "../utils/format";

const DEFAULT_ORDER = { rank: "asc", name: "asc" };

export default function DashboardPage() {
  const { job } = useOutletContext();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [fit, setFit] = useState("");
  const [status, setStatus] = useState("");
  const [minScore, setMinScore] = useState("");
  const [sort, setSort] = useState({ by: "rank", order: "asc" });
  const [selected, setSelected] = useState([]);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    AnalysisAPI.dashboard(job.id).then(setStats).catch((e) => setError(errorMessage(e)));
  }, [job.id, job.analysis_status]);

  useEffect(() => {
    const params = { sort_by: sort.by, order: sort.order };
    if (debounced) params.search = debounced;
    if (fit) params.fit = fit;
    if (status) params.status = status;
    if (minScore !== "") params.min_score = minScore;
    AnalysisAPI.candidates(job.id, params).then(setRows).catch((e) => setError(errorMessage(e)));
  }, [job.id, job.analysis_status, debounced, fit, status, minScore, sort]);

  const onSort = (by) =>
    setSort((s) => (s.by === by ? { by, order: s.order === "asc" ? "desc" : "asc" } : { by, order: DEFAULT_ORDER[by] || "desc" }));
  const toggle = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 4 ? s : [...s, id]));

  const exportCsv = async () => {
    setExporting(true);
    try {
      const res = await AnalysisAPI.exportCsv(job.id);
      saveBlob(res.data, `${job.title.replace(/\W+/g, "_")}_ranking.csv`);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setExporting(false);
    }
  };

  const componentData = useMemo(
    () => stats ? Object.entries(stats.component_averages).filter(([, v]) => v !== null).map(([k, v]) => ({ name: COMPONENT_LABELS[k], value: v })) : [],
    [stats]
  );

  if (!stats && !error) return <PageLoader label="Loading dashboard…" />;
  if (stats && stats.total_candidates === 0) {
    return (
      <EmptyState icon={Upload} title="No resumes yet" description="Upload resumes and run the analysis to see the candidate ranking."
        action={<Link className="btn-primary" to={`/jobs/${job.id}/resumes`}><Upload className="h-4 w-4" /> Upload resumes</Link>} />
    );
  }

  return (
    <div className="space-y-6">
      {error && <Alert onClose={() => setError("")}>{error}</Alert>}
      {stats && stats.analyzed === 0 && (
        <Alert type="info" title="Analysis not run yet">
          Resumes are uploaded but not scored. <Link className="font-semibold underline" to={`/jobs/${job.id}/resumes`}>Start the analysis</Link>.
        </Alert>
      )}
      {job.analysis_status === "outdated" && (
        <Alert type="warning">These results are outdated because the requirements, weights or resumes changed. <Link className="font-semibold underline" to={`/jobs/${job.id}/resumes`}>Re-run analysis</Link>.</Alert>
      )}

      {stats && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total candidates" value={stats.total_candidates} sub={`${stats.failed} file(s) not processed`} icon={Users} tone="navy" />
          <StatCard label="Successfully processed" value={stats.processed} sub={`${stats.analyzed} analyzed`} icon={FileCheck2} tone="emerald" />
          <StatCard label="Average match" value={stats.average_score !== null ? `${fmtScore(stats.average_score)}%` : "—"} sub={stats.lowest_score !== null ? `Lowest ${fmtScore(stats.lowest_score)}%` : ""} icon={TrendingUp} tone="blue" />
          <StatCard label="Highest match" value={stats.highest_score !== null ? `${fmtScore(stats.highest_score)}%` : "—"} sub={rows?.[0]?.rank === 1 ? rows[0].name : ""} icon={Award} tone="amber" />
        </div>
      )}

      {stats && stats.analyzed > 0 && (
        <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-4">
          <div className="card p-5 xl:col-span-2">
            <SectionTitle title="Score distribution" description="Number of candidates per score range" />
            <ScoreDistributionChart data={stats.score_distribution} />
          </div>
          <div className="card p-5">
            <SectionTitle title="Fit categories" />
            <FitDistributionChart data={stats.fit_distribution} />
          </div>
          <div className="card p-5">
            <SectionTitle title="Avg. component scores" />
            <HorizontalBarChart data={componentData} dataKey="value" nameKey="name" max={100} color="#1d4ed8" />
          </div>
          {stats.top_missing_skills.length > 0 && (
            <div className="card p-5 lg:col-span-2 xl:col-span-4">
              <SectionTitle title="Most frequently missing mandatory skills" description="Useful to judge whether requirements are realistic for this talent pool" />
              <HorizontalBarChart data={stats.top_missing_skills} dataKey="count" nameKey="skill" color="#f43f5e" height={Math.max(160, stats.top_missing_skills.length * 30)} />
            </div>
          )}
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="space-y-4 p-5">
          <SectionTitle
            title="Candidate ranking"
            description="Ranked by final weighted score. Click a candidate for the full explanation."
            action={
              <div className="flex flex-wrap gap-2">
                <button className="btn-secondary" disabled={selected.length < 2} onClick={() => navigate(`/jobs/${job.id}/compare?ids=${selected.join(",")}`)}>
                  <GitCompare className="h-4 w-4" /> Compare ({selected.length})
                </button>
                <button className="btn-primary" onClick={exportCsv} disabled={exporting || !rows?.length}>
                  {exporting ? <Spinner className="h-4 w-4 text-white" /> : <Download className="h-4 w-4" />} Export CSV
                </button>
              </div>
            }
          />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative sm:col-span-2 lg:col-span-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input className="input pl-9" placeholder="Search name, email, skill…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search candidates" />
            </div>
            <select className="input" value={fit} onChange={(e) => setFit(e.target.value)} aria-label="Filter by fit">
              <option value="">All fit categories</option>
              {["Strong match", "Moderate match", "Weak match", "Low match"].map((f) => <option key={f}>{f}</option>)}
            </select>
            <select className="input" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
              <option value="">All statuses</option>
              <option value="analyzed">Analyzed</option>
              <option value="pending_analysis">Pending analysis</option>
              <option value="failed">Failed</option>
              <option value="duplicate">Duplicate</option>
              <option value="unsupported">Unsupported</option>
            </select>
            <select className="input" value={minScore} onChange={(e) => setMinScore(e.target.value)} aria-label="Minimum score">
              <option value="">Any score</option>
              {[75, 55, 35].map((s) => <option key={s} value={s}>Score ≥ {s}</option>)}
            </select>
          </div>
          {selected.length > 0 && <p className="text-xs text-slate-500">{selected.length} selected for comparison (2–4 candidates).</p>}
        </div>
        {rows === null ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : rows.length === 0 ? (
          <div className="px-5 pb-5"><EmptyState icon={Search} title="No candidates match these filters" /></div>
        ) : (
          <RankingTable rows={rows} sort={sort} onSort={onSort} selected={selected} onToggle={toggle}
            onOpen={(r) => navigate(`/jobs/${job.id}/candidates/${r.candidate_id}`)} />
        )}
      </div>
    </div>
  );
}
