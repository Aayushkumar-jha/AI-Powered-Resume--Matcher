import { AlertCircle, CheckCircle2, Inbox, Loader2, X } from "lucide-react";
import { TONE_CLASSES, fmtScore, scoreTone } from "../utils/format";

export function Spinner({ className = "h-5 w-5" }) {
  return <Loader2 className={`animate-spin text-blue-600 ${className}`} aria-label="Loading" />;
}

export function PageLoader({ label = "Loading…" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-slate-500">
      <Spinner className="h-8 w-8" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function Alert({ type = "error", title, children, onClose }) {
  const styles = {
    error: "bg-rose-50 border-rose-200 text-rose-800",
    success: "bg-emerald-50 border-emerald-200 text-emerald-800",
    info: "bg-blue-50 border-blue-200 text-blue-800",
    warning: "bg-amber-50 border-amber-200 text-amber-800",
  }[type];
  const Icon = type === "success" ? CheckCircle2 : AlertCircle;
  return (
    <div role="alert" className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${styles}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">
        {title && <p className="font-semibold">{title}</p>}
        <div>{children}</div>
      </div>
      {onClose && (
        <button onClick={onClose} className="opacity-60 hover:opacity-100" aria-label="Dismiss">
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-white px-6 py-14 text-center">
      <div className="mb-3 rounded-full bg-slate-100 p-3">
        <Icon className="h-6 w-6 text-slate-400" />
      </div>
      <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function StatCard({ label, value, sub, icon: Icon, tone = "blue" }) {
  const toneBg = { blue: "bg-blue-50 text-blue-600", emerald: "bg-emerald-50 text-emerald-600",
    amber: "bg-amber-50 text-amber-600", navy: "bg-navy-50 text-navy-800", rose: "bg-rose-50 text-rose-600" }[tone];
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
          {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
        </div>
        {Icon && (
          <div className={`rounded-lg p-2.5 ${toneBg}`}>
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>
    </div>
  );
}

export function ScoreBadge({ score, size = "md" }) {
  const t = TONE_CLASSES[scoreTone(score)];
  const sz = size === "lg" ? "text-base px-3 py-1" : "text-xs px-2 py-0.5";
  return (
    <span className={`inline-flex items-center rounded-md font-semibold ring-1 ring-inset ${t.bg} ${t.text} ${t.ring} ${sz}`}>
      {score === null || score === undefined ? "—" : `${fmtScore(score)}%`}
    </span>
  );
}

export function ScoreBar({ score, label, weight, note }) {
  const t = TONE_CLASSES[scoreTone(score)];
  const unavailable = score === null || score === undefined;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-sm">
        <span className="font-medium text-slate-700">
          {label}
          {weight !== undefined && <span className="ml-2 text-xs font-normal text-slate-400">weight {(weight * 100).toFixed(0)}%</span>}
        </span>
        <span className={`font-semibold ${unavailable ? "text-slate-400" : t.text}`}>
          {unavailable ? "Not applicable" : `${fmtScore(score)} / 100`}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${t.bar} transition-all`} style={{ width: `${unavailable ? 0 : score}%` }} />
      </div>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </div>
  );
}

const SKILL_STYLES = {
  matched: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  related: "bg-amber-50 text-amber-700 ring-amber-200",
  missing: "bg-rose-50 text-rose-700 ring-rose-200",
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  required: "bg-blue-50 text-blue-700 ring-blue-200",
};

export function SkillBadge({ children, variant = "neutral", onRemove, title }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${SKILL_STYLES[variant]}`}>
      {children}
      {onRemove && (
        <button type="button" onClick={onRemove} className="-mr-1 rounded-full p-0.5 hover:bg-black/10" aria-label={`Remove ${children}`}>
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}

export function ProgressBar({ value, className = "" }) {
  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-slate-100 ${className}`} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-full rounded-full bg-blue-600 transition-all duration-300" style={{ width: `${Math.min(100, value)}%` }} />
    </div>
  );
}

const STATUS_STYLES = {
  parsed: "bg-emerald-50 text-emerald-700",
  analyzed: "bg-emerald-50 text-emerald-700",
  completed: "bg-emerald-50 text-emerald-700",
  pending_analysis: "bg-blue-50 text-blue-700",
  processing: "bg-blue-50 text-blue-700",
  uploading: "bg-blue-50 text-blue-700",
  queued: "bg-slate-100 text-slate-600",
  idle: "bg-slate-100 text-slate-600",
  outdated: "bg-amber-50 text-amber-700",
  duplicate: "bg-amber-50 text-amber-700",
  failed: "bg-rose-50 text-rose-700",
  unsupported: "bg-rose-50 text-rose-700",
  rejected: "bg-rose-50 text-rose-700",
};
const STATUS_TEXT = { pending_analysis: "Pending analysis", outdated: "Needs re-run", idle: "Not analyzed" };

export function StatusPill({ status }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[status] || STATUS_STYLES.queued}`}>
      {(status === "processing" || status === "uploading") && <Loader2 className="h-3 w-3 animate-spin" />}
      {STATUS_TEXT[status] || status?.replace("_", " ")}
    </span>
  );
}

export function SectionTitle({ title, description, action }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}
