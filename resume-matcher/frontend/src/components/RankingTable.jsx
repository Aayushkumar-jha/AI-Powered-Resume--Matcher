import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { ScoreBadge, SkillBadge, StatusPill } from "./ui";
import { fmtYears } from "../utils/format";

const COLUMNS = [
  { key: "rank", label: "Rank" },
  { key: "name", label: "Candidate" },
  { key: "experience_years", label: "Experience" },
  { key: "final_score", label: "Match" },
  { key: null, label: "Matched skills" },
  { key: null, label: "Missing skills" },
  { key: null, label: "Status" },
];

function SortIcon({ active, order }) {
  if (!active) return <ArrowUpDown className="h-3 w-3 opacity-40" />;
  return order === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />;
}

function SkillList({ items, variant, max = 4 }) {
  if (!items.length) return <span className="text-xs text-slate-400">—</span>;
  return (
    <div className="flex max-w-xs flex-wrap gap-1">
      {items.slice(0, max).map((s) => <SkillBadge key={s} variant={variant}>{s}</SkillBadge>)}
      {items.length > max && <span className="text-xs text-slate-500" title={items.slice(max).join(", ")}>+{items.length - max}</span>}
    </div>
  );
}

export default function RankingTable({ rows, sort, onSort, selected, onToggle, onOpen }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th className="th w-10"><span className="sr-only">Select</span></th>
            {COLUMNS.map((c) => (
              <th key={c.label} className="th">
                {c.key ? (
                  <button className="inline-flex items-center gap-1 uppercase hover:text-slate-800" onClick={() => onSort(c.key)}>
                    {c.label} <SortIcon active={sort.by === c.key} order={sort.order} />
                  </button>
                ) : c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {rows.map((r) => {
            const clickable = !!r.candidate_id && r.final_score !== null;
            return (
              <tr key={r.resume_id} className={clickable ? "cursor-pointer hover:bg-blue-50/40" : "bg-slate-50/50"} onClick={() => clickable && onOpen(r)}>
                <td className="td" onClick={(e) => e.stopPropagation()}>
                  {clickable && (
                    <input type="checkbox" className="h-4 w-4 rounded border-slate-300 accent-blue-600" aria-label={`Select ${r.name} for comparison`}
                      checked={selected.includes(r.candidate_id)} onChange={() => onToggle(r.candidate_id)} />
                  )}
                </td>
                <td className="td">
                  {r.rank ? (
                    <span className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${r.rank <= 3 ? "bg-navy-900 text-white" : "bg-slate-100 text-slate-600"}`}>{r.rank}</span>
                  ) : <span className="text-slate-300">—</span>}
                </td>
                <td className="td">
                  <p className="font-medium text-slate-900">{r.name || <span className="italic text-slate-400">Unknown</span>}</p>
                  <p className="text-xs text-slate-500">{r.email || r.filename}</p>
                </td>
                <td className="td whitespace-nowrap text-slate-600">{r.candidate_id ? fmtYears(r.experience_years) : "—"}</td>
                <td className="td">
                  <ScoreBadge score={r.final_score} />
                  {r.fit_label && <p className="mt-1 whitespace-nowrap text-[11px] text-slate-500">{r.fit_label}</p>}
                </td>
                <td className="td"><SkillList items={r.matched_skills} variant="matched" /></td>
                <td className="td"><SkillList items={r.missing_skills} variant="missing" /></td>
                <td className="td">
                  <StatusPill status={r.status} />
                  {r.error && <p className="mt-1 max-w-[200px] text-[11px] leading-snug text-rose-600">{r.error}</p>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
