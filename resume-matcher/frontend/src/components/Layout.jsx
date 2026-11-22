import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { BarChart3, Briefcase, Menu, PlusCircle, ShieldCheck, X } from "lucide-react";
import { SystemAPI } from "../api/client";

function NavItem({ to, icon: Icon, children, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isActive ? "bg-white/10 text-white" : "text-navy-100/70 hover:bg-white/5 hover:text-white"
        }`
      }
    >
      <Icon className="h-4 w-4" />
      {children}
    </NavLink>
  );
}

export default function Layout() {
  const [health, setHealth] = useState(null);
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    SystemAPI.health().then(setHealth).catch(() => setHealth({ status: "down" }));
  }, []);
  useEffect(() => setOpen(false), [location.pathname]);

  const sidebar = (
    <div className="flex h-full flex-col bg-navy-900 px-4 py-6">
      <div className="mb-8 flex items-center gap-2.5 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
          <BarChart3 className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-white">TalentMatch AI</p>
          <p className="text-[11px] text-navy-100/60">Resume Matching & Ranking</p>
        </div>
      </div>
      <nav className="space-y-1">
        <NavItem to="/" icon={Briefcase} end>Jobs</NavItem>
        <NavItem to="/jobs/new" icon={PlusCircle}>New Job</NavItem>
      </nav>
      <div className="mt-auto space-y-3 px-2">
        <div className="rounded-lg bg-white/5 p-3 text-[11px] leading-relaxed text-navy-100/70">
          <div className="mb-1 flex items-center gap-1.5 font-semibold text-white">
            <ShieldCheck className="h-3.5 w-3.5 text-blue-400" /> Human-in-the-loop
          </div>
          Scores support recruiter decisions. They are not hiring probabilities and never auto-reject candidates.
        </div>
        <div className="flex items-center gap-2 text-[11px] text-navy-100/60">
          <span className={`h-2 w-2 rounded-full ${health?.status === "ok" ? "bg-emerald-400" : health ? "bg-rose-400" : "bg-slate-500"}`} />
          {health?.status === "ok" ? "API & database online" : health ? "API/database unavailable" : "Checking API…"}
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">{sidebar}</aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64">{sidebar}</aside>
        </div>
      )}
      <div className="min-w-0 flex-1 lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <button className="btn-ghost p-2" onClick={() => setOpen(!open)} aria-label="Toggle menu">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <span className="text-sm font-semibold">TalentMatch AI</span>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
