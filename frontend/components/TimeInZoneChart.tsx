"use client";

import {
  Bar, BarChart, CartesianGrid, Legend,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { useLang } from "@/lib/i18n";

interface WeekZone {
  week: string;
  zones: Record<string, number>;
}

interface Props {
  weeks: WeekZone[];
  summary: string;
  zoneType?: "hr" | "power";  // determines which interval descriptions to show
}

export const ZONE_COLORS: Record<string, string> = {
  Z1: "#9CA3AF",
  Z2: "#60A5FA",
  Z3: "#34D399",
  Z4: "#FBBF24",
  Z5: "#F87171",
  Z6: "#A78BFA",
  Z7: "#F43F5E",
};

// HR zones (% of HRmax)
const HR_ZONE_LABELS: Record<string, { range: string; de: string; en: string }> = {
  Z1: { range: "50–60% HRmax",  de: "Sehr leicht", en: "Very light" },
  Z2: { range: "60–70% HRmax",  de: "Grundlage",   en: "Endurance" },
  Z3: { range: "70–80% HRmax",  de: "Aerob",       en: "Aerobic" },
  Z4: { range: "80–90% HRmax",  de: "Schwelle",    en: "Threshold" },
  Z5: { range: "90–100% HRmax", de: "VO₂max",      en: "VO₂max" },
};

// Power zones (Coggan, % of FTP)
const POWER_ZONE_LABELS: Record<string, { range: string; de: string; en: string }> = {
  Z1: { range: "< 55% FTP",    de: "Aktive Erholung", en: "Active recovery" },
  Z2: { range: "55–75% FTP",   de: "Ausdauer",        en: "Endurance" },
  Z3: { range: "76–90% FTP",   de: "Tempo",           en: "Tempo" },
  Z4: { range: "91–105% FTP",  de: "Schwelle",        en: "Threshold" },
  Z5: { range: "106–120% FTP", de: "VO₂max",          en: "VO₂max" },
  Z6: { range: "121–150% FTP", de: "Anaerob",         en: "Anaerobic" },
  Z7: { range: "> 150% FTP",   de: "Neuromuskulär",   en: "Neuromuscular" },
};

function shortWeek(iso: string, locale: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString(locale, { month: "short", day: "numeric" });
}

export function TimeInZoneChart({ weeks, summary, zoneType = "hr" }: Props) {
  const { t, locale } = useLang();
  if (!weeks.length) return (
    <div className="h-40 flex items-center justify-center text-sm text-gray-400">
      {t("Keine Aktivitäten mit Streams in den letzten 12 Wochen.", "No activities with streams in the last 12 weeks.")}
    </div>
  );

  const zones = Object.keys(weeks[0]?.zones ?? {});
  const hasData = weeks.some((w) => Object.values(w.zones).some((v) => v > 0));

  if (!hasData) return (
    <div className="h-40 flex items-center justify-center text-sm text-gray-400">
      {t("Keine HF-/Leistungsdaten in den Streams gefunden.", "No HR/power data found in the streams.")}
    </div>
  );

  // Infer zone type from zone count if not explicitly passed
  const effectiveType = zones.some((z) => z === "Z6" || z === "Z7") ? "power" : zoneType;
  const zoneLabels = effectiveType === "power" ? POWER_ZONE_LABELS : HR_ZONE_LABELS;

  const chartData = weeks.map((w) => ({ week: w.week, ...w.zones }));

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 8 }} barCategoryGap="20%">
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="week"
            tickFormatter={(v) => shortWeek(v, locale)}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
            interval={Math.floor(weeks.length / 5)}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
            width={36}
            unit=" h"
          />
          <Tooltip
            contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #E5E7EB" }}
            labelFormatter={(v) => shortWeek(v, locale)}
            formatter={(v: number, name: string) => {
              const info = zoneLabels[name];
              return [`${v.toFixed(1)} h`, info ? `${name} · ${t(info.de, info.en)}` : name];
            }}
          />
          {zones.map((z) => (
            <Bar key={z} dataKey={z} stackId="zones" fill={ZONE_COLORS[z] ?? "#ccc"} maxBarSize={28} />
          ))}
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
        </BarChart>
      </ResponsiveContainer>

      {/* Zone descriptions */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
        {zones.map((z) => {
          const info = zoneLabels[z];
          if (!info) return null;
          return (
            <div key={z} className="flex items-start gap-2 text-[11px]">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 mt-0.5"
                style={{ background: ZONE_COLORS[z] ?? "#ccc" }}
              />
              <span>
                <span className="font-medium text-gray-700 dark:text-gray-200">{z} · {t(info.de, info.en)}</span>
                <br />
                <span className="text-gray-400">{info.range}</span>
              </span>
            </div>
          );
        })}
      </div>

      {summary && (
        <p className="text-xs text-gray-500 bg-surface rounded-lg px-3 py-2">{summary}</p>
      )}
    </div>
  );
}
