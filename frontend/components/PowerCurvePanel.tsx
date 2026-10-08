"use client";

import {
  Area, CartesianGrid, ComposedChart, Line,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { CPModel, PDCPoint, PowerCurve } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  pdc: PowerCurve;
  ftp?: number | null;
}

const DUR_LABELS: Record<number, string> = {
  1: "1s", 5: "5s", 15: "15s", 30: "30s",
  60: "1m", 120: "2m", 300: "5m", 600: "10m",
  1200: "20m", 1800: "30m", 3600: "60m",
};

const ANNOTATIONS: { dur: number; de: string; en: string }[] = [
  { dur: 5,    de: "Neuromusk.",  en: "Neuromusc." },
  { dur: 60,   de: "Anaerob",     en: "Anaerobic" },
  { dur: 300,  de: "VO₂max",      en: "VO₂max" },
  { dur: 1200, de: "FTP-Bereich", en: "FTP range" },
  { dur: 3600, de: "Ausdauer",    en: "Endurance" },
];

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const dur = DUR_LABELS[label] ?? `${label}s`;
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg p-3 text-xs space-y-1">
      <p className="font-semibold text-gray-700">{dur}</p>
      {payload
        .filter((p: any) => p.value != null && p.dataKey !== "_base" && p.dataKey !== "_band")
        .map((p: any) => (
          <div key={p.dataKey} className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: p.color ?? "#ccc" }} />
            <span className="text-gray-500">{p.name}</span>
            <span className="font-medium tabular-nums">{Math.round(p.value)} W</span>
          </div>
        ))}
    </div>
  );
}

function buildChartData(allTime: PDCPoint[], recent: PDCPoint[], model: CPModel | null) {
  const map = new Map<number, Record<string, number | undefined>>();
  const allDurations = new Set<number>();

  // Minimum duration for which the CP/W' model is valid (shortest fit anchor = 3 min)
  const MODEL_MIN_S = 180;

  for (const p of allTime)  { allDurations.add(p.duration_s); map.set(p.duration_s, { duration_s: p.duration_s, all_time: p.power_w }); }
  for (const p of recent)   { allDurations.add(p.duration_s); const e = map.get(p.duration_s) ?? { duration_s: p.duration_s }; map.set(p.duration_s, { ...e, recent_6w: p.power_w }); }
  for (const p of model?.curve ?? []) {
    // Only show model within the valid fit range — below 3min the hyperbolic model
    // P(t)=CP+W'/t diverges to physically impossible values as t→0
    if (p.duration_s < MODEL_MIN_S) continue;
    allDurations.add(p.duration_s);
    const e = map.get(p.duration_s) ?? { duration_s: p.duration_s };
    map.set(p.duration_s, { ...e, _base: p.ci_lower, _band: p.ci_upper - p.ci_lower, model: p.power_w });
  }

  return Array.from(map.values()).sort((a, b) => (a.duration_s as number) - (b.duration_s as number));
}

export function PowerCurvePanel({ pdc, ftp }: Props) {
  const { t } = useLang();
  const chartData = buildChartData(pdc.all_time, pdc.recent_6w, pdc.cp_model);
  const hasData = chartData.some((d) => d.all_time || d.recent_6w);

  if (!hasData) return (
    <div className="h-64 flex flex-col items-center justify-center gap-2 text-sm text-gray-400">
      <p>{t("Keine Leistungsdaten.", "No power data.")}</p>
      <p>
        {t("", "Run ")}
        <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">strava-dash recompute</code>
        {t(" ausführen.", ".")}
      </p>
      {pdc.note && <p className="text-xs text-amber-500">{pdc.note}</p>}
    </div>
  );

  // Y-axis domain from empirical data only — model values can be huge outside the fit range
  const empiricalVals = chartData
    .flatMap((d) => [d.all_time, d.recent_6w])
    .filter((v): v is number => v != null && v > 0);
  const yMin = Math.floor(Math.min(...empiricalVals) * 0.92);
  const yMax = Math.ceil(Math.max(...empiricalVals) * 1.1);

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1.5"><span className="w-5 h-0.5 bg-strava inline-block rounded" />{t("Gesamt", "All-time")}</span>
        <span className="flex items-center gap-1.5"><span className="w-5 h-0.5 border-t-2 border-dashed border-gray-400 inline-block" />{t("Letzte 6 Wochen", "Last 6 weeks")}</span>
        {pdc.cp_model && (
          <span
            className="flex items-center gap-1.5"
            title={t(
              "Nur ab 3min gültig — das Modell P(t)=CP+W'/t divergiert bei sehr kurzen Dauern",
              "Only valid from 3min — the model P(t)=CP+W'/t diverges for very short durations",
            )}
          >
            <span className="w-5 h-0.5 border-t-2 border-dotted border-violet-500 inline-block" />
            {t("CP/W'-Modell (3–60min)", "CP/W' model (3–60min)")}
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 16, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="duration_s"
            scale="log"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(v) => DUR_LABELS[v] ?? `${v}s`}
            ticks={[1, 5, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600]}
            tick={{ fontSize: 11, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 11, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
            width={44}
            unit=" W"
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Annotation reference lines */}
          {ANNOTATIONS.map(({ dur, de, en }) => (
            <ReferenceLine
              key={dur}
              x={dur}
              stroke="#E5E7EB"
              strokeWidth={1}
              label={{ value: t(de, en), position: "top", fill: "#D1D5DB", fontSize: 9 }}
            />
          ))}

          {/* FTP reference */}
          {ftp && (
            <ReferenceLine
              y={ftp}
              stroke="#3B82F6"
              strokeDasharray="4 3"
              strokeWidth={1}
              label={{ value: `FTP ${ftp}W`, position: "right", fill: "#3B82F6", fontSize: 10 }}
            />
          )}

          {/* CP/W' confidence band */}
          {pdc.cp_model && (
            <>
              <Area dataKey="_base" stackId="ci" stroke="none" fill="transparent" legendType="none" isAnimationActive={false} />
              <Area dataKey="_band" name={t("KI", "CI")} stackId="ci" stroke="none" fill="#7C3AED" fillOpacity={0.1} legendType="none" isAnimationActive={false} />
            </>
          )}

          {/* CP/W' model line */}
          {pdc.cp_model && (
            <Line dataKey="model" name={t("Modell", "Model")} stroke="#7C3AED" strokeWidth={1.5} strokeDasharray="3 2" dot={false} connectNulls isAnimationActive={false} />
          )}

          {/* Recent 6w */}
          <Line dataKey="recent_6w" name={t("Letzte 6 Wo.", "Last 6 wk")} stroke="#9CA3AF" strokeWidth={1.5} strokeDasharray="5 3" dot={{ r: 2.5, fill: "#9CA3AF", strokeWidth: 0 }} activeDot={{ r: 4 }} connectNulls isAnimationActive={false} />

          {/* All-time */}
          <Line dataKey="all_time" name={t("Gesamt", "All-time")} stroke="#FC4C02" strokeWidth={2.5} dot={{ r: 3, fill: "#FC4C02", strokeWidth: 0 }} activeDot={{ r: 5 }} connectNulls isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>

      {/* CP / W' stat cards */}
      {pdc.cp_model && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-surface border border-border rounded-xl p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">CP (Critical Power)</p>
            <p className="text-2xl font-bold tabular-nums mt-1">{pdc.cp_model.cp_w} <span className="text-sm font-normal text-gray-400">W</span></p>
            <p className="text-xs text-gray-400 mt-0.5">{t("Schwellen-Näherung · entspricht etwa der FTP", "Threshold proxy · approximates FTP")}</p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{t("W' (Anaerobe Kapazität)", "W' (Anaerobic capacity)")}</p>
            <p className="text-2xl font-bold tabular-nums mt-1">{pdc.cp_model.w_prime_kj} <span className="text-sm font-normal text-gray-400">kJ</span></p>
            <p className="text-xs text-gray-400 mt-0.5">{t("Energie über CP bis zur Erschöpfung", "Energy above CP until exhaustion")}</p>
          </div>
        </div>
      )}
    </div>
  );
}
