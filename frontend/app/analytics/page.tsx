"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { WeeklyVolumeChart } from "@/components/WeeklyVolumeChart";
import { RacePredictor } from "@/components/RacePredictor";
import { RacePredictionChart } from "@/components/RacePredictionChart";
import { MonthlyChart } from "@/components/MonthlyChart";
import { TrainingLoadChart } from "@/components/TrainingLoadChart";
import { PowerCurvePanel } from "@/components/PowerCurvePanel";
import { DecouplingChart } from "@/components/DecouplingChart";
import { TimeInZoneChart } from "@/components/TimeInZoneChart";
import { EffectivePaceChart } from "@/components/EffectivePaceChart";
import { ZoneReference } from "@/components/ZoneReference";
import { useLang } from "@/lib/i18n";

type Sport = "all" | "run" | "bike";
type VolumeMetric = "km" | "tss" | "hours";

const SPORT_PILLS: { key: Sport; de: string; en: string }[] = [
  { key: "all",  de: "Alle",  en: "All"  },
  { key: "run",  de: "Laufen", en: "Run"  },
  { key: "bike", de: "Rad",   en: "Bike" },
];

function SectionTitle({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <h2 className={`text-xs font-medium text-gray-500 uppercase tracking-wide ${className}`}>{children}</h2>;
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white dark:bg-gray-800 border border-border dark:border-gray-700 rounded-xl p-4 sm:p-5 ${className}`}>
      {children}
    </div>
  );
}

function AnalyticsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { lang, t } = useLang();
  const sport = (searchParams.get("sport") as Sport) || "all";

  const [volMetric, setVolMetric] = useState<VolumeMetric>("km");
  const [lookback, setLookback] = useState(8);

  const { data: weekly } = useQuery({ queryKey: ["weekly-volume"], queryFn: () => api.weeklyVolume(20) });
  const { data: monthly } = useQuery({ queryKey: ["monthly-stats"], queryFn: () => api.monthlyStats(18) });
  const { data: load } = useQuery({ queryKey: ["training-load", 180], queryFn: () => api.trainingLoad(180) });
  const { data: stats } = useQuery({ queryKey: ["stats", lang], queryFn: () => api.stats(lang) });
  const { data: pdc } = useQuery({ queryKey: ["power-curve", lang], queryFn: () => api.powerCurve(lang), enabled: sport === "bike" || sport === "all" });
  const { data: predictions, isLoading: predLoading } = useQuery({
    queryKey: ["race-predictions", lookback, lang],
    queryFn: () => api.racePredictions(lookback, lang),
    enabled: sport !== "bike",
  });
  const { data: decoupling } = useQuery({
    queryKey: ["decoupling-timeline", lang],
    queryFn: () => api.decouplingTimeline(lang),
  });
  const { data: zones } = useQuery({
    queryKey: ["time-in-zone", sport, stats?.ftp_w, lang],
    queryFn: () => api.timeInZone(sport === "bike" ? "bike" : sport === "run" ? "run" : "all", 12, stats?.ftp_w ?? undefined, lang),
  });
  const { data: effectivePace } = useQuery({
    queryKey: ["effective-pace", lang],
    queryFn: () => api.effectivePace(lang),
    enabled: sport !== "bike",
  });

  function setSport(s: Sport) {
    const params = new URLSearchParams(searchParams.toString());
    if (s === "all") params.delete("sport");
    else params.set("sport", s);
    router.replace(`/analytics?${params.toString()}`, { scroll: false });
  }

  // YTD stats filtered by sport
  const ytdKey = new Date().getFullYear() + "-";
  const ytd = monthly?.filter((m) => m.month.startsWith(ytdKey)) ?? [];
  const ytdDistance =
    sport === "run"  ? ytd.reduce((s, m) => s + m.run_km, 0)
    : sport === "bike" ? ytd.reduce((s, m) => s + m.ride_km, 0)
    : ytd.reduce((s, m) => s + m.distance_km, 0);
  const ytdElevation =
    sport === "run"  ? ytd.reduce((s, m) => s + m.run_elevation, 0)
    : sport === "bike" ? ytd.reduce((s, m) => s + m.ride_elevation, 0)
    : ytd.reduce((s, m) => s + m.elevation_m, 0);
  const ytdHours =
    sport === "run"  ? ytd.reduce((s, m) => s + m.run_hours, 0)
    : sport === "bike" ? ytd.reduce((s, m) => s + m.ride_hours, 0)
    : ytd.reduce((s, m) => s + m.hours, 0);
  const ytdActivities =
    sport === "run"  ? ytd.reduce((s, m) => s + m.run_count, 0)
    : sport === "bike" ? ytd.reduce((s, m) => s + m.ride_count, 0)
    : ytd.reduce((s, m) => s + m.count, 0);

  return (
    <div className="space-y-6">
      {/* Header + Sport filter */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("Analyse", "Analytics")}</h1>
          <p className="text-sm text-gray-400 mt-0.5">{t("Volumen-Trends, Wettkampfprognosen und Trainingsmuster", "Volume trends, race predictions and training patterns")}</p>
        </div>
        <div className="flex rounded-lg border border-border overflow-hidden text-sm font-medium">
          {SPORT_PILLS.map((p) => (
            <button
              key={p.key}
              onClick={() => setSport(p.key)}
              className={`px-4 py-1.5 transition-colors ${
                sport === p.key ? "bg-strava text-white" : "bg-white text-gray-500 hover:bg-surface"
              }`}
            >
              {t(p.de, p.en)}
            </button>
          ))}
        </div>
      </div>

      {/* YTD summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: t("Distanz (lfd. Jahr)", "YTD Distance"), value: `${Math.round(ytdDistance)} km` },
          { label: t("Höhenmeter (lfd. Jahr)", "YTD Elevation"), value: `${(ytdElevation / 1000).toFixed(1)} km` },
          { label: t("Stunden (lfd. Jahr)", "YTD Hours"), value: `${Math.round(ytdHours)} h` },
          { label: t("Aktivitäten (lfd. Jahr)", "YTD Activities"), value: ytdActivities },
        ].map(({ label, value }) => (
          <Card key={label}>
            <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
            <p className="text-2xl sm:text-[28px] font-medium mt-1 tabular-nums dark:text-white">{value}</p>
          </Card>
        ))}
      </div>

      {/* Training Load — 6 months */}
      <Card>
        <div className="flex items-center justify-between flex-wrap gap-x-3 gap-y-1 mb-4">
          <SectionTitle>{t("Trainingsbelastung — 6 Monate", "Training Load — 6 months")}</SectionTitle>
          <span className="text-xs text-gray-400">CTL · ATL · TSB</span>
        </div>
        <TrainingLoadChart data={load ?? []} />
      </Card>

      {/* Monthly overview + Race predictor / Power Curve */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <SectionTitle className="mb-4">{t("Monatsübersicht — 18 Monate", "Monthly Overview — 18 months")}</SectionTitle>
          <MonthlyChart data={monthly ?? []} sport={sport} />
        </Card>

        {sport !== "bike" ? (
          <Card>
            <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
              <SectionTitle>{t("Wettkampfprognose", "Race Predictions")}</SectionTitle>
              <select
                value={lookback}
                onChange={(e) => setLookback(Number(e.target.value))}
                className="text-xs border border-border rounded-md px-2 py-1 text-gray-600"
              >
                <option value={4}>{t("Letzte 4 Wochen", "Last 4 weeks")}</option>
                <option value={8}>{t("Letzte 8 Wochen", "Last 8 weeks")}</option>
                <option value={12}>{t("Letzte 12 Wochen", "Last 12 weeks")}</option>
                <option value={24}>{t("Letzte 6 Monate", "Last 6 months")}</option>
              </select>
            </div>
            {predLoading ? (
              <div className="py-8 text-center text-sm text-gray-400">{t("Berechne…", "Calculating…")}</div>
            ) : (
              <>
                <RacePredictor predictions={predictions ?? []} lookbackWeeks={lookback} />
                <div className="mt-4 pt-4 border-t border-border">
                  <RacePredictionChart predictions={predictions ?? []} />
                </div>
              </>
            )}
          </Card>
        ) : (
          <Card>
            <SectionTitle className="mb-4">{t("Leistungskurve", "Power-Duration Curve")}</SectionTitle>
            {pdc ? (
              <PowerCurvePanel pdc={pdc} ftp={stats?.ftp_w} />
            ) : (
              <div className="h-48 flex items-center justify-center text-sm text-gray-400">{t("Laden…", "Loading…")}</div>
            )}
          </Card>
        )}
      </div>

      {/* Weekly Volume */}
      <Card>
        <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
          <SectionTitle>{t("Wochenumfang — 20 Wochen", "Weekly Volume — 20 weeks")}</SectionTitle>
          <div className="flex gap-1">
            {(["km", "tss", "hours"] as VolumeMetric[]).map((m) => (
              <button
                key={m}
                onClick={() => setVolMetric(m)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                  volMetric === m ? "bg-strava text-white" : "text-gray-500 hover:bg-gray-50 border border-border"
                }`}
              >
                {m === "km" ? t("Distanz", "Distance") : m === "tss" ? "TSS" : t("Stunden", "Hours")}
              </button>
            ))}
          </div>
        </div>
        <WeeklyVolumeChart data={weekly ?? []} metric={volMetric} sport={sport} />
      </Card>

      {/* My zones — HR + pace ranges to aim for */}
      {stats && (
        <Card>
          <SectionTitle className="mb-4">{t("Meine Zonen", "My Zones")}</SectionTitle>
          <ZoneReference max_hr={stats.max_hr} threshold_pace_ms={stats.threshold_pace_ms} />
        </Card>
      )}

      {/* Time in Zone */}
      <Card>
        <SectionTitle className="mb-4">{t("Zeit in Zonen — letzte 12 Wochen", "Time in Zone — last 12 weeks")}</SectionTitle>
        <TimeInZoneChart
          weeks={zones?.weeks ?? []}
          summary={zones?.summary ?? ""}
          zoneType={sport === "bike" && stats?.ftp_w ? "power" : "hr"}
        />
      </Card>

      {/* Aerobic Decoupling + Effective Pace — side by side or stacked */}
      <div className={`grid gap-4 ${sport !== "bike" ? "lg:grid-cols-2" : ""}`}>
        <Card>
          <SectionTitle className="mb-4">{t("Aerobe Entkopplung — Z2–Z3-Aktivitäten", "Aerobic Decoupling — Z2–Z3 activities")}</SectionTitle>
          <DecouplingChart
            points={decoupling?.points ?? []}
            interpretation={decoupling?.interpretation ?? ""}
          />
        </Card>

        {sport !== "bike" && (
          <Card>
            <SectionTitle className="mb-4">{t("Effektive Pace — Z2–Z3-Läufe", "Effective Pace — Z2–Z3 runs")}</SectionTitle>
            <EffectivePaceChart
              points={effectivePace?.points ?? []}
              trend_slope_sec_per_km_per_month={effectivePace?.trend_slope_sec_per_km_per_month ?? null}
              interpretation={effectivePace?.interpretation ?? ""}
            />
          </Card>
        )}
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <Suspense>
      <AnalyticsContent />
    </Suspense>
  );
}
