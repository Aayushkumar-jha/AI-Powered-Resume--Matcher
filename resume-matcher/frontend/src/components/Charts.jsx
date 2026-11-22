import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis,
  Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const BLUE = "#2563eb";
const FIT_COLORS = { "Strong match": "#10b981", "Moderate match": "#3b82f6", "Weak match": "#f59e0b", "Low match": "#f43f5e" };
const tooltipStyle = { borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 };

export function ScoreDistributionChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="range" tick={{ fontSize: 11, fill: "#64748b" }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => [v, "Candidates"]} labelFormatter={(l) => `Score ${l}`} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((d) => <Cell key={d.range} fill={d.min >= 75 ? "#10b981" : d.min >= 50 ? BLUE : d.min >= 30 ? "#f59e0b" : "#f43f5e"} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function FitDistributionChart({ data }) {
  const rows = Object.entries(data).map(([name, value]) => ({ name, value })).filter((r) => r.value > 0);
  if (!rows.length) return <p className="py-16 text-center text-sm text-slate-400">No results yet</p>;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={rows} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
          {rows.map((r) => <Cell key={r.name} fill={FIT_COLORS[r.name]} />)}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function HorizontalBarChart({ data, dataKey, nameKey, color = BLUE, height = 240, max }) {
  if (!data.length) return <p className="py-16 text-center text-sm text-slate-400">Nothing to show</p>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
        <XAxis type="number" allowDecimals={false} domain={max ? [0, max] : undefined} tick={{ fontSize: 11, fill: "#64748b" }} />
        <YAxis type="category" dataKey={nameKey} width={110} tick={{ fontSize: 11, fill: "#334155" }} />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey={dataKey} fill={color} radius={[0, 4, 4, 0]} barSize={16} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const RADAR_COLORS = ["#2563eb", "#10b981", "#f59e0b", "#e11d48"];

export function ComponentRadar({ series }) {
  // series: [{name, skills, semantic, experience, education}]
  const axes = ["skills", "semantic", "experience", "education"];
  const data = axes.map((a) => ({ axis: a[0].toUpperCase() + a.slice(1), ...Object.fromEntries(series.map((s) => [s.name, s[a] ?? 0])) }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} outerRadius="70%">
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12, fill: "#334155" }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94a3b8" }} />
        {series.map((s, i) => (
          <Radar key={s.name} name={s.name} dataKey={s.name} stroke={RADAR_COLORS[i]} fill={RADAR_COLORS[i]} fillOpacity={0.15} />
        ))}
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Tooltip contentStyle={tooltipStyle} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
