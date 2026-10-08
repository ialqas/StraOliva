"use client";

import {
  CartesianGrid, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { useLang } from "@/lib/i18n";

interface PacePoint {
  date: string;
  activity_id: number;
  activity_name: string;
  pace_sec_per_km: number;
  avg_hr: number;
  distance_km: number;
  distance_category: "5-10km" | "10-15km" | "15km+";
}

interface Props {
  points: PacePoint[];
  trend_slope_sec_per_km_per_month: number | null;
  interpretation: string;
}

const CAT_COLORS: Record<string, string> = {
  "5-10km":  "#60A5FA",
  "10-15km": "#D85A30",
  "15km+":   "#1D9E75",
};

function formatPace(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, "0")} /km`;
}

function CustomTooltip({ active, payload, locale, t }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as PacePoint & { x: number };
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg p-3 text-xs space-y-1">
      <p className="font-semibold text-gray-700 max-w-[180px] truncate">{d.activity_name}</p>
      <p className="text-gray-500">{new Date(d.date).toLocaleDateString(locale, { day: "2-digit", month: "short", year: "numeric" })}</p>
      <p><span className="font-medium">{formatPace(d.pace_sec_per_km)}</span></p>
      <p className="text-gray-400">{t("Ø HF", "Avg HR")} {Math.round(d.avg_hr)} bpm · {d.distance_km.toFixed(1)} km</p>
    </div>
  );
}

function trendLine(points: (PacePoint & { x: number })[]): { x: number; y: number }[] {
  if (points.length < 2) return [];
  const x = points.map((p) => p.x);
  const y = points.map((p) => p.pace_sec_per_km);
  const n = x.length;
  const xm = x.reduce((a, b) => a + b) / n;
  const ym = y.reduce((a, b) => a + b) / n;
  const ssxy = x.reduce((s, xi, i) => s + (xi - xm) * (y[i] - ym), 0);
  const ssxx = x.reduce((s, xi) => s + (xi - xm) ** 2, 0);
  const slope = ssxx > 0 ? ssxy / ssxx : 0;
  return [
    { x: x[0],     y: ym + slope * (x[0] - xm) },
    { x: x[n - 1], y: ym + slope * (x[n - 1] - xm) },
  ];
}

export function EffectivePaceChart({ points, trend_slope_sec_per_km_per_month, interpretation }: Props) {
  const { t, locale } = useLang();
  if (!points.length) return (
    <div className="h-40 flex items-center justify-center text-sm text-gray-400">
      {t("Keine Z2–Z3-Läufe ≥4 km in den letzten 6 Monaten gefunden.", "No Z2–Z3 runs ≥4 km found in the last 6 months.")}
    </div>
  );

  const first = new Date(points[0].date).getTime();
  const scatterData = points.map((p) => ({
    ...p,
    x: (new Date(p.date).getTime() - first) / 86400000,
  }));

  const trend = trendLine(scatterData);
  const xMax = scatterData[scatterData.length - 1].x;
  const allPace = scatterData.map((p) => p.pace_sec_per_km);
  const yMin = Math.min(...allPace);
  const yMax = Math.max(...allPace);
  const yPad = (yMax - yMin) * 0.15;

  const tickDates = [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]].map((p) => ({
    x: (new Date(p.date).getTime() - first) / 86400000,
    label: new Date(p.date).toLocaleDateString(locale, { month: "short", day: "numeric" }),
  }));

  return (
    <div className="space-y-3">
      {/* Category legend */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
        {Object.entries(CAT_COLORS).map(([cat, color]) => (
          <span key={cat} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: color }} />
            {cat}
          </span>
        ))}
        {trend_slope_sec_per_km_per_month !== null && (
          <span className="ml-auto font-medium" style={{ color: trend_slope_sec_per_km_per_month < 0 ? "#1D9E75" : "#E24B4A" }}>
            {trend_slope_sec_per_km_per_month < 0 ? "↓" : "↑"} {Math.abs(trend_slope_sec_per_km_per_month).toFixed(1)} s/km·{t("Monat", "month")}
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" />
          <XAxis
            dataKey="x"
            type="number"
            domain={[0, xMax * 1.05]}
            ticks={tickDates.map((t) => t.x)}
            tickFormatter={(v) => tickDates.find((t) => Math.abs(t.x - v) < 3)?.label ?? ""}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            dataKey="pace_sec_per_km"
            type="number"
            domain={[yMin - yPad, yMax + yPad]}
            tickFormatter={(v) => `${Math.floor(v / 60)}:${String(Math.round(v % 60)).padStart(2, "0")}`}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
            width={44}
            reversed
          />
          <Tooltip content={<CustomTooltip locale={locale} t={t} />} />
          {/* Trend line */}
          {trend.length === 2 && (
            <Line
              data={trend}
              dataKey="y"
              type="linear"
              stroke="#6B7280"
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={false}
              isAnimationActive={false}
            />
          )}
          {/* Scatter by category */}
          {(["5-10km", "10-15km", "15km+"] as const).map((cat) => (
            <Scatter
              key={cat}
              name={cat}
              data={scatterData.filter((p) => p.distance_category === cat)}
              fill={CAT_COLORS[cat]}
              fillOpacity={0.8}
              r={4}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>

      <p className="text-xs text-gray-500 bg-surface rounded-lg px-3 py-2">{interpretation}</p>
    </div>
  );
}
