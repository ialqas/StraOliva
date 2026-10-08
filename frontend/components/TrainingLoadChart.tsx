"use client";

import {
  Bar, ComposedChart, Legend, Line,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { TrainingLoadDay } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  data: TrainingLoadDay[];
}

const COLORS = {
  ctl: "#D85A30",
  atl: "#E24B4A",
  tsb: "#1D9E75",
  tss: "#E5E7EB",
};

function formatXDate(dateStr: string, locale: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString(locale, { month: "short", day: "numeric" });
}

function CustomTooltip({ active, payload, label, locale }: any) {
  if (!active || !payload?.length) return null;
  const d = new Date(label);
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg p-3 text-xs space-y-1">
      <p className="font-semibold text-gray-700">
        {d.toLocaleDateString(locale, { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}
      </p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: p.color }} />
          <span className="text-gray-500 w-8">{p.dataKey === "total_tss" ? "TSS" : p.dataKey.toUpperCase()}</span>
          <span className="font-medium tabular-nums">{Number(p.value).toFixed(1)}</span>
        </div>
      ))}
    </div>
  );
}

export function TrainingLoadChart({ data }: Props) {
  const { t, locale } = useLang();
  if (!data.length) return (
    <div className="h-64 flex items-center justify-center text-sm text-gray-400">
      {t("Keine Daten.", "No data. Run")} <code className="mx-1 bg-gray-100 px-1 rounded">strava-dash recompute</code>{t(" ausführen.", ".")}
    </div>
  );

  // Dynamic Y-axis domain for lines (CTL/ATL/TSB), separate axis for TSS bars
  const lineVals = data.flatMap((d) => [d.ctl, d.atl, d.tsb]);
  const lineMin = Math.min(...lineVals);
  const lineMax = Math.max(...lineVals);
  const pad = (lineMax - lineMin) * 0.12;
  const lineDomain: [number, number] = [
    Math.floor(lineMin - pad),
    Math.ceil(lineMax + pad),
  ];

  const tssMax = Math.max(...data.map((d) => d.total_tss)) * 1.1;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
        <XAxis
          dataKey="date"
          tickFormatter={(v) => formatXDate(v, locale)}
          tick={{ fontSize: 11, fill: "#9CA3AF" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          minTickGap={60}
        />
        {/* Left axis: CTL / ATL / TSB — tight dynamic domain */}
        <YAxis
          yAxisId="lines"
          domain={lineDomain}
          tick={{ fontSize: 11, fill: "#9CA3AF" }}
          tickLine={false}
          axisLine={false}
          width={40}
        />
        {/* Right axis: TSS bars — hidden ticks, separate scale */}
        <YAxis
          yAxisId="tss"
          orientation="right"
          domain={[0, tssMax]}
          hide
        />
        <Tooltip content={<CustomTooltip locale={locale} />} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
        />
        <Bar
          yAxisId="tss"
          dataKey="total_tss"
          fill={COLORS.tss}
          name="TSS"
          radius={[1, 1, 0, 0]}
          maxBarSize={6}
        />
        <Line
          yAxisId="lines"
          dataKey="ctl"
          stroke={COLORS.ctl}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name="CTL"
        />
        <Line
          yAxisId="lines"
          dataKey="atl"
          stroke={COLORS.atl}
          strokeWidth={1.5}
          dot={false}
          strokeDasharray="4 2"
          name="ATL"
        />
        <Line
          yAxisId="lines"
          dataKey="tsb"
          stroke={COLORS.tsb}
          strokeWidth={1.5}
          dot={false}
          name="TSB"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
