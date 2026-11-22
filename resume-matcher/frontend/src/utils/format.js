export const EDUCATION_LABELS = {
  high_school: "High School",
  diploma: "Diploma",
  associate: "Associate",
  bachelor: "Bachelor's",
  master: "Master's",
  phd: "PhD",
};

export const COMPONENT_LABELS = {
  skills: "Skills",
  semantic: "Semantic",
  experience: "Experience",
  education: "Education",
};

export function fmtScore(v, digits = 1) {
  return v === null || v === undefined ? "—" : Number(v).toFixed(digits);
}

export function fmtYears(v) {
  if (v === null || v === undefined) return "Unknown";
  return `${Number(v).toFixed(1)} yrs`;
}

export function scoreTone(score) {
  if (score === null || score === undefined) return "slate";
  if (score >= 75) return "emerald";
  if (score >= 55) return "blue";
  if (score >= 35) return "amber";
  return "rose";
}

export const TONE_CLASSES = {
  emerald: { text: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200", bar: "bg-emerald-500" },
  blue: { text: "text-blue-700", bg: "bg-blue-50", ring: "ring-blue-200", bar: "bg-blue-500" },
  amber: { text: "text-amber-700", bg: "bg-amber-50", ring: "ring-amber-200", bar: "bg-amber-500" },
  rose: { text: "text-rose-700", bg: "bg-rose-50", ring: "ring-rose-200", bar: "bg-rose-500" },
  slate: { text: "text-slate-500", bg: "bg-slate-50", ring: "ring-slate-200", bar: "bg-slate-300" },
};

export const ALLOWED_EXT = ["pdf", "docx"];

export function validateFile(file, maxMb = 5) {
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (!ALLOWED_EXT.includes(ext)) return `Unsupported type .${ext || "?"} (PDF/DOCX only)`;
  if (file.size === 0) return "File is empty";
  if (file.size > maxMb * 1024 * 1024) return `Exceeds ${maxMb} MB limit`;
  return null;
}

export function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
