"use client";

import {
  CartesianGrid, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { useLang } from "@/lib/i18n";

interface Point {
  date: string;
  activity_id: number;
  activity_name: string;
  decoupling_pct: number;
  duration_min: number;
  sport: string;
}

interface Props {
  points: Point[];
  interpretation: string;
}

function CustomTooltip({ active, payload, locale, t }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as Point;
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg p-3 text-xs space-y-1">
      <p className="font-semibold text-gray-700 max-w-[180px] truncate">{d.activity_name}</p>
      <p className="text-gray-500">{new Date(d.date).toLocaleDateString(locale, { day: "2-digit", month: "short", year: "numeric" })}</p>
      <p><span className="font-medium tabular-nums">{d.decoupling_pct.toFixed(1)}%</span> {t("Entkopplung", "Decoupling")}</p>
      <p className="text-gray-400">{d.duration_min.toFixed(0)} min</p>
    </div>
  );
}

function trendLine(points: Point[]): { x: number; y: number }[] {
  if (points.length < 2) return [];
  const first = new Date(points[0].date).getTime();
  const x = points.map((p) => (new Date(p.date).getTime() - first) / 86400000);
  const y = points.map((p) => p.decoupling_pct);
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

export function DecouplingChart({ points, interpretation }: Props) {
  const { t, locale } = useLang();
  if (!points.length) return (
    <div className="h-40 flex items-center justify-center text-sm text-gray-400">
      {t("Keine Z2–Z3-Aktivitäten ≥45 min in den letzten 6 Monaten.", "No Z2–Z3 activities ≥45 min in the last 6 months.")}
    </div>
  );

  const first = new Date(points[0].date).getTime();
  const scatterData = points.map((p) => ({
    ...p,
    x: (new Date(p.date).getTime() - first) / 86400000,
    y: p.decoupling_pct,
  }));

  const trend = trendLine(points);
  const xMax = scatterData[scatterData.length - 1].x;

  // Use date strings for X axis labels
  const tickDates = [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]].map((p) => ({
    x: (new Date(p.date).getTime() - first) / 86400000,
    label: new Date(p.date).toLocaleDateString(locale, { month: "short", day: "numeric" }),
  }));

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" />
          <XAxis
            dataKey="x"
            type="number"
            domain={[0, xMax * 1.05]}
            ticks={tickDates.map((t) => t.x)}
            tickFormatter={(v) => tickDates.find((t) => Math.abs(t.x - v) < 2)?.label ?? ""}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            dataKey="y"
            domain={[0, "auto"]}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
            width={36}
            unit="%"
          />
          <Tooltip content={<CustomTooltip locale={locale} t={t} />} />
          {/* Reference lines */}
          <ReferenceLine y={5} stroke="#1D9E75" strokeDasharray="4 3" strokeWidth={1} label={{ value: t("5% gut", "5% good"), position: "right", fill: "#1D9E75", fontSize: 9 }} />
          <ReferenceLine y={7} stroke="#D97706" strokeDasharray="4 3" strokeWidth={1} label={{ value: t("7% Grenze", "7% limit"), position: "right", fill: "#D97706", fontSize: 9 }} />
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
          <Scatter
            data={scatterData}
            fill="#D85A30"
            fillOpacity={0.75}
            r={4}
          />
        </ScatterChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-500 bg-surface rounded-lg px-3 py-2">{interpretation}</p>
    </div>
  );
}
