"use client";

import {
  Area, ComposedChart, CartesianGrid, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis, Scatter,
} from "recharts";
import type { RacePrediction } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  predictions: RacePrediction[];
}

const DIST_LABELS: Record<number, string> = {
  5000: "5k", 10000: "10k", 21097: "HM", 42195: "Marathon",
};

function formatTime(secs: number): string {
  const s = Math.round(secs);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
               : `${m}:${String(sec).padStart(2, "0")}`;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const distLabel = DIST_LABELS[label] ?? `${(label / 1000).toFixed(0)} km`;
  const predicted = payload.find((p: any) => p.dataKey === "predicted_s");
  const ciLower = payload.find((p: any) => p.dataKey === "_base");
  const band = payload.find((p: any) => p.dataKey === "_band");
  const lower = ciLower ? ciLower.value : null;
  const upper = lower !== null && band ? lower + band.value : null;
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg p-3 text-xs space-y-1">
      <p className="font-semibold text-gray-700">{distLabel}</p>
      {predicted && (
        <p className="text-strava font-medium">{formatTime(predicted.value)}</p>
      )}
      {lower !== null && upper !== null && (
        <p className="text-gray-400">{formatTime(lower)} – {formatTime(upper)}</p>
      )}
    </div>
  );
}

const CONF_COLOR: Record<string, string> = {
  high:    "#1D9E75",
  medium:  "#D97706",
  low:     "#9CA3AF",
  no_data: "#E5E7EB",
};

export function RacePredictionChart({ predictions }: Props) {
  const { t } = useLang();
  const withData = predictions.filter((p) => p.predicted_s !== null);
  if (withData.length < 2) return null;

  const chartData = withData.map((p) => ({
    distance_m: p.distance_m,
    predicted_s: p.predicted_s!,
    _base: p.ci_lower_s!,
    _band: p.ci_upper_s! - p.ci_lower_s!,
    confidence: p.confidence,
    label: DIST_LABELS[p.distance_m] ?? `${(p.distance_m / 1000).toFixed(0)} km`,
  }));

  // Y-axis domain
  const allVals = chartData.flatMap((d) => [d._base, d._base + d._band, d.predicted_s]);
  const yMin = Math.min(...allVals);
  const yMax = Math.max(...allVals);
  const yPad = (yMax - yMin) * 0.12;

  return (
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-3">
        {t("Prognostizierte Zeit — Konfidenzband", "Predicted Time — Confidence Band")}
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="distance_m"
            type="number"
            scale="log"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(v) => DIST_LABELS[v] ?? `${(v / 1000).toFixed(0)}k`}
            ticks={withData.map((p) => p.distance_m)}
            tick={{ fontSize: 11, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tickFormatter={formatTime}
            tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickLine={false}
            axisLine={false}
            width={44}
            domain={[Math.floor(yMin - yPad), Math.ceil(yMax + yPad)]}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* CI band: transparent base + colored band on top */}
          <Area
            dataKey="_base"
            stackId="ci"
            stroke="none"
            fill="transparent"
            legendType="none"
            isAnimationActive={false}
          />
          <Area
            dataKey="_band"
            stackId="ci"
            stroke="none"
            fill="#D85A30"
            fillOpacity={0.12}
            legendType="none"
            isAnimationActive={false}
          />
          <Line
            dataKey="predicted_s"
            stroke="#D85A30"
            strokeWidth={2}
            dot={(props: any) => {
              const { cx, cy, payload } = props;
              return (
                <circle
                  key={payload.distance_m}
                  cx={cx} cy={cy} r={5}
                  fill={CONF_COLOR[payload.confidence] ?? "#D85A30"}
                  stroke="white"
                  strokeWidth={1.5}
                />
              );
            }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-2 text-[10px] text-gray-400">
        {(["high", "medium", "low"] as const).map((c) => (
          <span key={c} className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: CONF_COLOR[c] }} />
            {c === "high"
              ? t("Hohe Konfidenz", "High confidence")
              : c === "medium"
                ? t("Mittlere Konfidenz", "Medium confidence")
                : t("Niedrige Konfidenz", "Low confidence")}
          </span>
        ))}
      </div>
    </div>
  );
}
