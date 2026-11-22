import { NavLink, useLocation } from "react-router-dom";
import { BarChart3, ClipboardList, Upload } from "lucide-react";
import { StatusPill } from "./ui";

const steps = [
  { to: "requirements", label: "1. Requirements", icon: ClipboardList },
  { to: "resumes", label: "2. Resumes", icon: Upload },
  { to: "dashboard", label: "3. Results", icon: BarChart3 },
];

export default function JobHeader({ job }) {
  const { pathname } = useLocation();
  const resultsActive = /\/(candidates|compare)/.test(pathname);
  return (
    <div className="mb-6">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-900">{job.title}</h1>
        <StatusPill status={job.analysis_status} />
        <span className="text-sm text-slate-500">{job.resume_count} resume(s)</span>
      </div>
      <nav className="flex gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1">
        {steps.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={`/jobs/${job.id}/${to}`}
            className={({ isActive }) =>
              `${(isActive || (to === "dashboard" && resultsActive)) ? "bg-navy-900 text-white" : "text-slate-600 hover:bg-slate-100"} flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition-colors`
            }
          >
            <Icon className="h-4 w-4" /> {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
