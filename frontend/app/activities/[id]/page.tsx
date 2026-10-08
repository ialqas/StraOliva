"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Area, ComposedChart, Line, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import dynamic from "next/dynamic";
import {
  api, formatDate, formatDistance, formatDuration,
  formatPace, formatSpeed, sportLabel, type SplitAnomaly,
} from "@/lib/api";
import { ActivityZoneBar } from "@/components/ActivityZoneBar";
import { useLang } from "@/lib/i18n";

const ActivityMapInner = dynamic(
  () => import("@/components/ActivityMapInner").then((m) => ({ default: m.ActivityMapInner })),
  {
    ssr: false,
    loading: () => <div className="w-full bg-gray-100 rounded-lg animate-pulse" style={{ height: 300 }} />,
  }
);

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatStreamTime(s: number) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

function formatPaceTick(secPerKm: number) {
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

// ── Speed smoothing ────────────────────────────────────────────────────────────

/** Below this speed a sample counts as standing / paused / GPS dropout (≈ 16:40 /km).
 *  As pace (1000 / speed) such samples explode towards infinity and flatten the chart. */
const PAUSE_SPEED_MS = 1.0;
/** Pace is averaged over this window — raw per-second GPS speed is too jumpy to read. */
const SMOOTH_WINDOW_S = 30;

/** Centered time-window moving average of speed over moving samples only.
 *  Paused samples come back as null, so the chart shows a gap instead of a spike. */
function smoothSpeed(time: (number | null)[], vel: (number | null)[]): (number | null)[] {
  const n = time.length;
  const half = SMOOTH_WINDOW_S / 2;
  const isMoving = (i: number) => time[i] != null && vel[i] != null && vel[i]! >= PAUSE_SPEED_MS;
  const out: (number | null)[] = new Array(n).fill(null);
  let lo = 0, hi = 0, sum = 0, count = 0;
  for (let i = 0; i < n; i++) {
    const t = time[i];
    if (t == null) continue;
    while (hi < n && (time[hi] ?? t) <= t + half) {
      if (isMoving(hi)) { sum += vel[hi]!; count++; }
      hi++;
    }
    while (lo < hi && (time[lo] ?? t) < t - half) {
      if (isMoving(lo)) { sum -= vel[lo]!; count--; }
      lo++;
    }
    out[i] = isMoving(i) && count > 0 ? sum / count : null;
  }
  return out;
}

/** Axis domain covering the typical range — robust against remaining GPS outliers. */
function percentileDomain(values: number[], lowP = 0.02, highP = 0.98): [number, number] | undefined {
  if (values.length < 2) return undefined;
  const sorted = [...values].sort((a, b) => a - b);
  const lo = sorted[Math.floor(lowP * (sorted.length - 1))];
  const hi = sorted[Math.ceil(highP * (sorted.length - 1))];
  const pad = Math.max((hi - lo) * 0.08, 1);
  return [Math.floor(lo - pad), Math.ceil(hi + pad)];
}

// ── Metric Card ────────────────────────────────────────────────────────────────

function MetricCard({
  label, value, sub, accent,
}: {
  label: string; value: string; sub?: string; accent?: string;
}) {
  return (
    <div className="bg-white border border-border rounded-xl p-4">
      <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-medium mt-1 tabular-nums" style={accent ? { color: accent } : undefined}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Split table ────────────────────────────────────────────────────────────────

interface SplitRow {
  key: string;
  label: string;
  distance_m: number | null;
  time_s: number | null;
  avg_hr: number | null;
  avg_watts?: number | null;
  elevation_diff_m?: number | null;
  anomaly?: SplitAnomaly | null;  // only for watch laps
}

function SplitTable({ title, rows, isRide }: { title: string; rows: SplitRow[]; isRide: boolean }) {
  const { t } = useLang();
  const showDeviation = rows.some((r) => r.anomaly !== undefined);
  const showElevation = !showDeviation && rows.some((r) => r.elevation_diff_m != null);
  const hasAnomalies = rows.some((r) => r.anomaly?.anomaly);

  return (
    <div className="bg-white border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-border">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-surface text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-2 text-left font-medium">#</th>
              <th className="px-4 py-2 text-right font-medium">{t("Distanz", "Distance")}</th>
              <th className="px-4 py-2 text-right font-medium">{t("Zeit", "Time")}</th>
              <th className="px-4 py-2 text-right font-medium">{isRide ? "Watt" : "Pace"}</th>
              <th className="px-4 py-2 text-right font-medium">{t("Ø HF", "Avg HR")}</th>
              {showDeviation && (
                <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">{t("Abw.", "Dev.")}</th>
              )}
              {showElevation && (
                <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">{t("Höhe", "Elev.")}</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((row) => {
              const anom = row.anomaly;
              const rowBg =
                anom?.anomaly === "slow" ? "bg-amber-50"
                : anom?.anomaly === "fast" ? "bg-emerald-50"
                : "";
              return (
                <tr key={row.key} className={`${rowBg} hover:brightness-95 transition-colors`} title={anom?.tooltip ?? undefined}>
                  <td className="px-4 py-2.5 text-gray-400">{row.label}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{formatDistance(row.distance_m)}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{formatDuration(row.time_s)}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums font-medium">
                    {isRide
                      ? row.avg_watts ? `${Math.round(row.avg_watts)} W` : "—"
                      : formatPace(row.distance_m, row.time_s)}
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-gray-500">
                    {row.avg_hr ? `${Math.round(row.avg_hr)} bpm` : "—"}
                  </td>
                  {showDeviation && (
                    <td className="px-4 py-2.5 text-right hidden sm:table-cell">
                      {anom?.anomaly ? (
                        <span
                          className={`text-[11px] font-medium px-1.5 py-0.5 rounded-full ${
                            anom.anomaly === "slow"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {anom.pct_from_median != null
                            ? `${anom.pct_from_median > 0 ? "+" : ""}${anom.pct_from_median.toFixed(0)}%`
                            : anom.anomaly === "slow" ? t("langsam", "slow") : t("schnell", "fast")}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                  )}
                  {showElevation && (
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-500 hidden sm:table-cell">
                      {row.elevation_diff_m != null
                        ? `${row.elevation_diff_m > 0 ? "+" : ""}${Math.round(row.elevation_diff_m)} m`
                        : "—"}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {hasAnomalies && (
        <div className="px-5 py-2 border-t border-border text-xs text-gray-400 flex flex-wrap gap-x-4 gap-y-1">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-amber-100 inline-block" /> {t("Langsamer als Median", "Slower than median")}</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-emerald-100 inline-block" /> {t("Schneller als Median", "Faster than median")}</span>
        </div>
      )}
    </div>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const actId = Number(id);
  const { lang, t } = useLang();

  const { data: act } = useQuery({ queryKey: ["activity", actId], queryFn: () => api.activity(actId) });
  const { data: streams } = useQuery({
    queryKey: ["streams", actId],
    queryFn: () => api.streams(actId),
    enabled: !!act?.has_streams,
  });
  const { data: splits } = useQuery({ queryKey: ["splits", actId], queryFn: () => api.splits(actId) });
  const laps = splits?.laps;
  const { data: analytics } = useQuery({
    queryKey: ["activity-analytics", actId, lang],
    queryFn: () => api.activityAnalytics(actId, lang),
    enabled: !!act,
  });

  const sport = act ? sportLabel(act.type) : null;
  const isRide = sport?.label === "Ride";
  const isRun = sport?.label === "Run";

  // ── Chart data ──────────────────────────────────────────────────────────────
  const chartData = (() => {
    if (!streams?.time_s?.length) return [];
    // Smooth at full resolution first, then downsample for rendering
    const speed = smoothSpeed(streams.time_s, streams.velocity_smooth);
    const step = Math.max(1, Math.floor(streams.time_s.length / 600));
    return streams.time_s
      .filter((_, i) => i % step === 0)
      .map((t, i) => {
        const idx = i * step;
        const vel = speed[idx];
        return {
          t,
          hr: streams.hr[idx] ?? null,
          watts: streams.watts[idx] ?? null,
          velocity: vel != null
            ? isRide
              ? Math.round(vel * 3.6 * 10) / 10
              : Math.round(1000 / vel)
            : null,
          altitude: streams.altitude_m[idx] ?? null,
        };
      });
  })();

  const hasHr = chartData.some((d) => d.hr != null);
  const hasPower = chartData.some((d) => d.watts != null && d.watts > 0);
  const hasVelocity = chartData.some((d) => d.velocity != null);
  const showVelocity = !hasPower && hasVelocity;
  const velocityDomain = percentileDomain(
    chartData.map((d) => d.velocity).filter((v): v is number => v != null),
  );

  // ── Lap markers (cumulative start seconds) ──────────────────────────────────
  const lapMarkers: number[] = (() => {
    if (!laps || laps.length < 2) return [];
    const starts: number[] = [0];
    for (let i = 0; i < laps.length - 1; i++) {
      starts.push(starts[i] + (laps[i].time_s ?? 0));
    }
    return starts.slice(1); // skip first (t=0)
  })();

  // ── Anomaly lookup map ──────────────────────────────────────────────────────
  const anomalyMap = new Map(
    (analytics?.split_anomalies ?? []).map((a) => [a.lap_index, a])
  );

  // ── Split tables ────────────────────────────────────────────────────────────
  // Times are moving time (pauses excluded) — what the watch and Strava's lap view show.
  const lapRows: SplitRow[] = (laps ?? []).map((lap) => ({
    key: `lap-${lap.lap_index}`,
    label: String(lap.lap_index + 1),
    distance_m: lap.distance_m,
    time_s: lap.moving_time_s,
    avg_hr: lap.avg_hr,
    avg_watts: lap.avg_watts,
    anomaly: anomalyMap.get(lap.lap_index) ?? null,
  }));
  const kmSplitRows: SplitRow[] = (splits?.km_splits ?? []).map((s) => ({
    key: `km-${s.split_index}`,
    label: String(s.split_index),
    distance_m: s.distance_m,
    time_s: s.moving_time_s,
    avg_hr: s.avg_hr,
    elevation_diff_m: s.elevation_diff_m,
  }));
  const multipleLaps = lapRows.length > 1;
  // Rides: watch laps only. Others: manual laps, then km splits — falling back to the
  // watch's own 1 km auto-laps for runs synced before km splits were stored.
  const manualRows = isRide ? (multipleLaps ? lapRows : []) : splits?.laps_are_manual ? lapRows : [];
  const kmRows = isRide
    ? []
    : kmSplitRows.length > 0
      ? kmSplitRows
      : !splits?.laps_are_manual && multipleLaps ? lapRows : [];

  // ── Key metrics ────────────────────────────────────────────────────────────
  const metrics = act ? [
    {
      label: isRide ? t("Norm. Leistung", "Norm. Power") : t("Ø Pace", "Avg Pace"),
      value: isRide
        ? analytics?.np_w ? `${Math.round(analytics.np_w)} W` : "—"
        : formatPace(act.distance_m, act.moving_time_s),
      sub: isRide ? "NP" : "min/km",
    },
    {
      label: t("Intensitätsfaktor", "Intensity Factor"),
      value: analytics?.intensity_factor != null
        ? analytics.intensity_factor.toFixed(2)
        : "—",
      sub: analytics?.ftp_w ? `FTP ${analytics.ftp_w} W` : "IF",
      accent: analytics?.intensity_factor != null
        ? analytics.intensity_factor > 1.05 ? "#EF4444"
          : analytics.intensity_factor > 0.85 ? "#D85A30"
          : "#22C55E"
        : undefined,
    },
    {
      label: "TSS",
      value: act.tss != null ? String(Math.round(act.tss)) : "—",
      sub: "Training Stress Score",
    },
    {
      label: "Decoupling",
      value: analytics?.decoupling_pct != null
        ? `${analytics.decoupling_pct > 0 ? "+" : ""}${analytics.decoupling_pct.toFixed(1)}%`
        : "—",
      sub: analytics?.decoupling_pct != null
        ? analytics.decoupling_pct < 5 ? t("Gut (<5%)", "Good (<5%)") : analytics.decoupling_pct < 7 ? "OK (5–7%)" : t("Hoch (>7%)", "High (>7%)")
        : t("Aerobe Effizienz", "Aerobic efficiency"),
      accent: analytics?.decoupling_pct != null
        ? analytics.decoupling_pct < 5 ? "#16A34A" : analytics.decoupling_pct < 7 ? "#D97706" : "#EF4444"
        : undefined,
    },
    {
      label: t("HF-Drift", "HR Drift"),
      value: analytics?.hr_drift_pct != null
        ? `${analytics.hr_drift_pct > 0 ? "+" : ""}${analytics.hr_drift_pct.toFixed(1)}%`
        : "—",
      sub: t("Herzfrequenz-Drift (2. Hälfte)", "Heart rate drift (2nd half)"),
      accent: analytics?.hr_drift_pct != null
        ? analytics.hr_drift_pct < 3 ? "#16A34A" : analytics.hr_drift_pct < 7 ? "#D97706" : "#EF4444"
        : undefined,
    },
    {
      label: t("Ø HF", "Avg HR"),
      value: act.avg_hr ? `${Math.round(act.avg_hr)} bpm` : "—",
      sub: analytics?.avg_hr_zone
        ? `${analytics.avg_hr_zone} — ${
            analytics.avg_hr_zone === "Z1" ? t("Regeneration", "Recovery")
            : analytics.avg_hr_zone === "Z2" ? t("Aerob", "Aerobic")
            : analytics.avg_hr_zone === "Z3" ? "Tempo"
            : analytics.avg_hr_zone === "Z4" ? t("Schwelle", "Threshold")
            : t("Anaerob", "Anaerobic")
          }`
        : t("Herzfrequenz", "Heart rate"),
    },
  ] : [];

  return (
    <div className="space-y-5">
      {/* Back */}
      <Link href="/activities" className="text-sm text-gray-400 hover:text-strava flex items-center gap-1">
        ← {t("Aktivitäten", "Activities")}
      </Link>

      {/* Header */}
      {act && (
        <div className="flex items-start gap-3 sm:gap-4">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-xl shrink-0 mt-0.5"
            style={{ background: sport!.color + "18" }}
          >
            {sport!.emoji}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold truncate">{act.name}</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              {formatDate(act.start_time, lang)} · {formatDistance(act.distance_m)} · {formatDuration(act.moving_time_s)}
            </p>
          </div>
        </div>
      )}

      {/* Key Metrics Grid — 3 × 2 */}
      {act && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {metrics.map((m) => (
            <MetricCard key={m.label} label={m.label} value={m.value} sub={m.sub} accent={m.accent} />
          ))}
        </div>
      )}

      {/* Route map */}
      {streams && streams.lat?.some((v) => v != null) && (
        <div className="bg-white border border-border rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-4">{t("Strecke", "Route")}</p>
          <ActivityMapInner lat={streams.lat} lng={streams.lng} height={300} />
        </div>
      )}

      {/* Streams chart with lap markers */}
      {streams && chartData.length > 0 && (
        <div className="bg-white border border-border rounded-xl p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-4">{t("Verlauf", "Activity Streams")}</p>
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
              <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="t"
                tickFormatter={formatStreamTime}
                tick={{ fontSize: 10, fill: "#9CA3AF" }}
                tickLine={false}
                axisLine={false}
                minTickGap={60}
              />
              {/* HR / power axis — hidden when pace/speed owns the left axis (values stay in the tooltip) */}
              <YAxis
                yAxisId="main"
                hide={showVelocity}
                tick={{ fontSize: 10, fill: "#9CA3AF" }}
                tickLine={false}
                axisLine={false}
                width={40}
              />
              {showVelocity && (
                <YAxis
                  yAxisId="vel"
                  domain={velocityDomain ?? ["auto", "auto"]}
                  allowDataOverflow
                  reversed={!isRide} // pace: faster = higher, like Strava
                  tickFormatter={!isRide ? formatPaceTick : undefined}
                  tick={{ fontSize: 10, fill: "#9CA3AF" }}
                  tickLine={false}
                  axisLine={false}
                  width={40}
                />
              )}
              <YAxis yAxisId="alt" orientation="right" tick={{ fontSize: 10, fill: "#9CA3AF" }} tickLine={false} axisLine={false} width={34} />
              <Tooltip
                labelFormatter={(v) => formatStreamTime(Number(v))}
                formatter={(value, name, item) =>
                  item.dataKey === "velocity" && !isRide
                    ? [`${formatPaceTick(Number(value))} /km`, name]
                    : item.dataKey === "velocity"
                    ? [`${value} km/h`, name]
                    : [value, name]
                }
                contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #E5E7EB" }}
              />
              {/* Lap markers */}
              {lapMarkers.map((t) => (
                <ReferenceLine
                  key={t}
                  x={t}
                  yAxisId="main"
                  stroke="#D1D5DB"
                  strokeWidth={1}
                  strokeDasharray="3 2"
                />
              ))}
              {/* Altitude */}
              {chartData.some((d) => d.altitude != null) && (
                <Area yAxisId="alt" dataKey="altitude" fill="#F3F4F6" stroke="#E5E7EB" strokeWidth={1} dot={false} name={t("Höhe (m)", "Altitude (m)")} />
              )}
              {hasHr && <Line yAxisId="main" dataKey="hr" stroke="#EF4444" strokeWidth={1.5} dot={false} name={t("HF (bpm)", "HR (bpm)")} />}
              {hasPower && <Line yAxisId="main" dataKey="watts" stroke="#FC4C02" strokeWidth={1.5} dot={false} name={t("Leistung (W)", "Power (W)")} />}
              {showVelocity && (
                <Line yAxisId="vel" dataKey="velocity" connectNulls={false} stroke="#3B82F6" strokeWidth={1.5} dot={false} name={isRide ? t("Tempo (km/h)", "Speed (km/h)") : "Pace (min/km)"} />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Time-in-Zone */}
      {analytics && (analytics.zones_hr || analytics.zones_power) && (
        <div className="bg-white border border-border rounded-xl p-5 space-y-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t("Zeit in Zonen", "Time in Zone")}</p>
          {analytics.zones_hr && (
            <ActivityZoneBar zones={analytics.zones_hr} label={t("HF-Zonen", "HR Zones")} />
          )}
          {analytics.zones_power && (
            <ActivityZoneBar zones={analytics.zones_power} label={t("Leistungszonen (Coggan)", "Power Zones (Coggan)")} />
          )}
        </div>
      )}

      {/* Manual watch laps first, then the automatic kilometres */}
      {manualRows.length > 0 && (
        <SplitTable
          title={isRide ? t("Runden", "Laps") : t("Runden (manuell)", "Laps (manual)")}
          rows={manualRows}
          isRide={isRide}
        />
      )}
      {kmRows.length > 0 && (
        <SplitTable title={t("Kilometer", "Kilometres")} rows={kmRows} isRide={false} />
      )}
    </div>
  );
}
