import { useState } from "react";
import { SkillBadge } from "./ui";

/** Editable list of tags (skills / fields). Enter or comma adds; × removes. */
export default function TagInput({ value, onChange, placeholder, variant = "neutral", label }) {
  const [draft, setDraft] = useState("");

  const add = (raw) => {
    const items = raw.split(",").map((s) => s.trim()).filter(Boolean);
    const existing = new Set(value.map((v) => v.toLowerCase()));
    const next = [...value];
    items.forEach((i) => {
      if (!existing.has(i.toLowerCase())) {
        next.push(i);
        existing.add(i.toLowerCase());
      }
    });
    onChange(next);
    setDraft("");
  };

  return (
    <div>
      {label && <label className="label">{label}</label>}
      <div className="flex min-h-[44px] flex-wrap items-center gap-1.5 rounded-lg border border-slate-300 bg-white p-2 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20">
        {value.map((v) => (
          <SkillBadge key={v} variant={variant} onRemove={() => onChange(value.filter((x) => x !== v))}>
            {v}
          </SkillBadge>
        ))}
        <input
          className="min-w-[140px] flex-1 border-0 p-1 text-sm outline-none placeholder:text-slate-400"
          value={draft}
          placeholder={placeholder}
          aria-label={label || placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === ",") && draft.trim()) {
              e.preventDefault();
              add(draft);
            } else if (e.key === "Backspace" && !draft && value.length) {
              onChange(value.slice(0, -1));
            }
          }}
          onBlur={() => draft.trim() && add(draft)}
        />
      </div>
    </div>
  );
}
