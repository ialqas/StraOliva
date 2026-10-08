"use client";

import { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { useLang } from "@/lib/i18n";

interface MonthEntry {
  month: string;
  distance_km: number;
  elevation_m: number;
  tss: number;
  hours: number;
  count: number;
  run_km: number;
  ride_km: number;
  run_hours: number;
  ride_hours: number;
  run_elevation: number;
  ride_elevation: number;
  run_count: number;
  ride_count: number;
}

interface Props {
  data: MonthEntry[];
  sport?: "all" | "run" | "bike";
}

type Metric = "distance_km" | "tss" | "hours" | "elevation_m";

const METRIC_OPTS: { key: Metric; de: string; en: string; unit: string; color: string }[] = [
  { key: "distance_km", de: "Distanz",    en: "Distance",  unit: "km", color: "#FC4C02" },
  { key: "tss",         de: "TSS",        en: "TSS",       unit: "",   color: "#8B5CF6" },
  { key: "hours",       de: "Stunden",    en: "Hours",     unit: "h",  color: "#3B82F6" },
  { key: "elevation_m", de: "Höhenmeter", en: "Elevation", unit: "m",  color: "#10B981" },
];

function shortMonth(iso: string, locale: string) {
  const [y, m] = iso.split("-");
  const d = new Date(Number(y), Number(m) - 1, 1);
  return d.toLocaleDateString(locale, { month: "short" });
}

export function MonthlyChart({ data, sport = "all" }: Props) {
  const { t, locale } = useLang();
  const [metric, setMetric] = useState<Metric>("distance_km");
  const opt = METRIC_OPTS.find((o) => o.key === metric)!;
  const optLabel = t(opt.de, opt.en);

  if (!data.length) return (
    <div className="h-48 flex items-center justify-center text-sm text-gray-400">{t("Keine Daten", "No data")}</div>
  );

  const currentMonth = new Date().toISOString().slice(0, 7);

  // Resolve effective metric value based on sport filter
  function getValue(entry: MonthEntry): number {
    if (sport === "run") {
      if (metric === "distance_km") return entry.run_km;
      if (metric === "hours")       return entry.run_hours;
      if (metric === "elevation_m") return entry.run_elevation;
    }
    if (sport === "bike") {
      if (metric === "distance_km") return entry.ride_km;
      if (metric === "hours")       return entry.ride_hours;
      if (metric === "elevation_m") return entry.ride_elevation;
    }
    return entry[metric];
  }

  const chartData = data.map((e) => ({ ...e, _value: getValue(e) }));

  // Average reference line (last 12 months)
  const last12 = chartData.slice(-12);
  const avg = last12.reduce((s, e) => s + e._value, 0) / (last12.length || 1);

  return (
    <div>
      {/* Metric tabs */}
      <div className="flex flex-wrap gap-1 mb-3">
        {METRIC_OPTS.map((o) => (
          <button
            key={o.key}
            onClick={() => setMetric(o.key)}
            className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
              metric === o.key ? "text-white" : "text-gray-500 hover:bg-gray-50"
            }`}
            style={metric === o.key ? { background: o.color } : undefined}
          >
            {t(o.de, o.en)}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 8 }} barCategoryGap="25%">
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="month"
            tickFormatter={(v) => shortMonth(v, locale)}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
            width={40}
            unit={opt.unit ? ` ${opt.unit}` : ""}
          />
          <Tooltip
            contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #E5E7EB" }}
            labelFormatter={(v) => {
              const [y, m] = String(v).split("-");
              return new Date(Number(y), Number(m) - 1).toLocaleDateString(locale, { month: "long", year: "numeric" });
            }}
            formatter={(v: number) => [`${Math.round(v * 10) / 10}${opt.unit ? ` ${opt.unit}` : ""}`, optLabel]}
            cursor={{ fill: "#F9FAFB" }}
          />
          {/* Average reference line */}
          <ReferenceLine
            y={avg}
            stroke={opt.color}
            strokeDasharray="4 3"
            strokeWidth={1}
            strokeOpacity={0.5}
          />
          <Bar dataKey="_value" name={optLabel} radius={[3, 3, 0, 0]} maxBarSize={28}>
            {chartData.map((entry) => (
              <Cell
                key={entry.month}
                fill={entry.month === currentMonth ? opt.color : opt.color + "99"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
