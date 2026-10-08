"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { useLang } from "@/lib/i18n";

const DURATION_LABELS: Record<number, string> = {
  1: "1s", 5: "5s", 15: "15s", 30: "30s", 60: "1m",
  120: "2m", 300: "5m", 600: "10m", 1200: "20m",
  1800: "30m", 3600: "60m",
};

function formatDuration(s: number) {
  return DURATION_LABELS[s] ?? `${s}s`;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg p-3 text-xs space-y-1.5">
      <p className="font-semibold text-gray-700">{formatDuration(Number(label))}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-gray-500">{p.name}</span>
          <span className="font-medium tabular-nums">{Math.round(p.value)} W</span>
        </div>
      ))}
    </div>
  );
}

export default function PowerCurvePage() {
  const { lang, t } = useLang();
  const { data: stats } = useQuery({ queryKey: ["stats", lang], queryFn: () => api.stats(lang) });
  const { data: pdc, isLoading } = useQuery({ queryKey: ["power-curve", lang], queryFn: () => api.powerCurve(lang) });

  // Merge all-time and recent into one dataset keyed by duration_s
  const chartData = (() => {
    const map = new Map<number, { duration_s: number; all_time?: number; recent_6w?: number }>();
    for (const p of pdc?.all_time ?? []) {
      map.set(p.duration_s, { duration_s: p.duration_s, all_time: p.power_w });
    }
    for (const p of pdc?.recent_6w ?? []) {
      const existing = map.get(p.duration_s) ?? { duration_s: p.duration_s };
      map.set(p.duration_s, { ...existing, recent_6w: p.power_w });
    }
    return Array.from(map.values()).sort((a, b) => a.duration_s - b.duration_s);
  })();

  const ftp = stats?.ftp_w;
  const hasData = chartData.length > 0;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">{t("Leistungskurve", "Power-Duration Curve")}</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          {t("Beste mittlere Maximalleistung über alle Radaktivitäten", "Best mean maximal power across all bike activities")}
        </p>
      </div>

      {/* FTP reference */}
      {ftp && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="bg-strava/8 border border-strava/20 rounded-lg px-4 py-2.5 flex items-center gap-3">
            <div className="w-1 h-8 bg-strava rounded-full" />
            <div>
              <p className="text-xs text-gray-500">{t("FTP (automatisch erkannt)", "FTP (auto-detected)")}</p>
              <p className="text-xl font-bold text-strava tabular-nums">{ftp} W</p>
            </div>
          </div>
          {pdc?.all_time?.find((p) => p.duration_s === 1200) && (
            <div className="bg-surface border border-border rounded-lg px-4 py-2.5">
              <p className="text-xs text-gray-500">{t("Beste 20 min", "Best 20 min")}</p>
              <p className="text-xl font-bold tabular-nums">
                {Math.round(pdc.all_time.find((p) => p.duration_s === 1200)!.power_w)} W
              </p>
            </div>
          )}
          {pdc?.all_time?.find((p) => p.duration_s === 5) && (
            <div className="bg-surface border border-border rounded-lg px-4 py-2.5">
              <p className="text-xs text-gray-500">{t("Beste 5 s", "Best 5 sec")}</p>
              <p className="text-xl font-bold tabular-nums">
                {Math.round(pdc.all_time.find((p) => p.duration_s === 5)!.power_w)} W
              </p>
            </div>
          )}
        </div>
      )}

      {/* Chart */}
      <div className="bg-white border border-border rounded-xl p-5">
        {isLoading && (
          <div className="h-72 flex items-center justify-center text-sm text-gray-400">
            {t("Leistungskurve wird geladen…", "Loading power curve…")}
          </div>
        )}
        {!isLoading && !hasData && (
          <div className="h-72 flex flex-col items-center justify-center gap-2 text-sm text-gray-400">
            <p>{t("Noch keine Leistungsdaten.", "No power curve data yet.")}</p>
            <p>
              {t("", "Run ")}
              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">
                strava-dash recompute
              </code>{" "}
              {t("ausführen, um sie zu erzeugen.", "to generate it.")}
            </p>
            {pdc?.note && <p className="text-xs text-amber-500">{pdc.note}</p>}
          </div>
        )}
        {!isLoading && hasData && (
          <>
            <div className="flex items-center gap-4 mb-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-5 h-0.5 bg-strava inline-block rounded" />
                <span className="text-gray-500">{t("Bestwert (gesamt)", "All-time best")}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-5 h-0.5 border-t-2 border-dashed border-gray-400 inline-block" />
                <span className="text-gray-500">{t("Letzte 6 Wochen", "Last 6 weeks")}</span>
              </div>
              {ftp && (
                <div className="flex items-center gap-1.5">
                  <span className="w-5 h-0.5 border-t border-dashed border-blue-400 inline-block" />
                  <span className="text-gray-500">FTP</span>
                </div>
              )}
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
                <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="duration_s"
                  scale="log"
                  domain={["dataMin", "dataMax"]}
                  type="number"
                  tickFormatter={formatDuration}
                  tick={{ fontSize: 11, fill: "#9CA3AF" }}
                  tickLine={false}
                  axisLine={false}
                  ticks={[1, 5, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600]}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "#9CA3AF" }}
                  tickLine={false}
                  axisLine={false}
                  width={40}
                  unit=" W"
                />
                <Tooltip content={<CustomTooltip />} />
                {ftp && (
                  <ReferenceLine
                    y={ftp}
                    stroke="#3B82F6"
                    strokeDasharray="4 3"
                    strokeWidth={1}
                    label={{ value: `FTP ${ftp}W`, position: "right", fill: "#3B82F6", fontSize: 10 }}
                  />
                )}
                <Line
                  dataKey="all_time"
                  stroke="#FC4C02"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: "#FC4C02", strokeWidth: 0 }}
                  activeDot={{ r: 5 }}
                  name={t("Gesamt", "All-time")}
                  connectNulls
                />
                <Line
                  dataKey="recent_6w"
                  stroke="#9CA3AF"
                  strokeWidth={1.5}
                  strokeDasharray="5 3"
                  dot={{ r: 2.5, fill: "#9CA3AF", strokeWidth: 0 }}
                  activeDot={{ r: 4 }}
                  name={t("Letzte 6 Wochen", "Last 6 weeks")}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </>
        )}
      </div>
    </div>
  );
}
