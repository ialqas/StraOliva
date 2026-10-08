"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { api, formatDate, formatDistance, formatDuration, formatPace, formatSpeed, sportLabel } from "@/lib/api";
import { CalendarHeatmap } from "@/components/CalendarHeatmap";
import { FormGaugeCard } from "@/components/FormGaugeCard";
import { FitnessCard } from "@/components/FitnessCard";
import { QuickStatsRow } from "@/components/QuickStatsRow";
import { FtpCard } from "@/components/FtpCard";
import { GreetingsCard } from "@/components/GreetingsCard";
import { useLang } from "@/lib/i18n";

export default function DashboardPage() {
  const qc = useQueryClient();
  const { lang, t } = useLang();
  const { data: stats } = useQuery({ queryKey: ["stats", lang], queryFn: () => api.stats(lang) });
  const { data: load } = useQuery({ queryKey: ["training-load", 180], queryFn: () => api.trainingLoad(180) });
  const { data: recent } = useQuery({ queryKey: ["activities", { limit: 7 }], queryFn: () => api.activities({ limit: 7 }) });
  const { data: greetings } = useQuery({ queryKey: ["greetings"], queryFn: () => api.greetings() });

  const sync = useMutation({
    mutationFn: api.recompute,
    onSuccess: () => qc.invalidateQueries(),
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">{t("Deine aktuelle Trainingsform auf einen Blick", "Your current training form at a glance")}</p>
        </div>
        <div className="flex flex-col items-start sm:items-end gap-1 max-w-full">
          <button
            onClick={() => sync.mutate()}
            disabled={sync.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-strava px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-strava/90 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <svg
              className={`h-4 w-4 ${sync.isPending ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {sync.isPending ? (
                <>
                  <path className="opacity-25" strokeWidth={4} d="M12 3a9 9 0 100 18 9 9 0 000-18" />
                  <path strokeLinecap="round" strokeWidth={4} d="M12 3a9 9 0 019 9" />
                </>
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              )}
            </svg>
            {sync.isPending ? t("Synchronisiere…", "Syncing…") : "Sync"}
          </button>
          {sync.isPending && (
            <span className="text-xs text-gray-400">{t("Strava-Sync + Neuberechnung – kann etwas dauern.", "Strava sync + recompute – this may take a while.")}</span>
          )}
          {sync.isError && (
            <span className="text-xs text-red-500">{t("Sync fehlgeschlagen. Backend & Strava-Login prüfen.", "Sync failed. Check the backend & Strava login.")}</span>
          )}
          {sync.isSuccess && !sync.isPending && (
            <span className="text-xs text-green-600 dark:text-green-500">
              ✓ {sync.data.sync.new} {t("neu", "new")} · {sync.data.tss_computed} {t("TSS neu berechnet", "TSS recomputed")}
              {sync.data.sync_error ? t(" (Sync übersprungen)", " (sync skipped)") : ""}
              {sync.data.timings?.total != null && ` · ${sync.data.timings.total.toFixed(1)} s`}
            </span>
          )}
        </div>
      </div>

      {/* Activity Calendar — full width */}
      <div className="bg-white dark:bg-gray-800 border border-border dark:border-gray-700 rounded-xl p-4 sm:p-5">
        <div className="mb-3">
          <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t("Aktivitäts-Kalender", "Activity Calendar")}</h2>
          <p className="text-xs text-gray-400 mt-0.5">{t("Letzte 52 Wochen · eingefärbt nach TSS", "Last 52 weeks · colored by TSS")}</p>
        </div>
        <CalendarHeatmap data={load ?? []} />
      </div>

      {/* Form Gauge + Fitness Trajectory — 2 col */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {stats ? (
          <FormGaugeCard
            tsb={stats.tsb}
            ctl={stats.ctl}
            atl={stats.atl}
            interpretation={stats.form_interpretation}
          />
        ) : (
          <div className="bg-white dark:bg-gray-800 border border-border dark:border-gray-700 rounded-xl p-5 animate-pulse h-48" />
        )}
        {stats && load ? (
          <FitnessCard
            ctl={stats.ctl}
            ramp_rate={stats.ramp_rate}
            trajectory={stats.fitness_trajectory}
            loadHistory={load}
          />
        ) : (
          <div className="bg-white border border-border rounded-xl p-5 animate-pulse h-48" />
        )}
      </div>

      {/* Quick Stats this Week — full width, slim */}
      {stats && (
        <QuickStatsRow
          tss={stats.tss_this_week}
          tss4wAvg={stats.tss_4week_avg}
          hours={stats.hours_this_week}
          activities={stats.activities_this_week}
          avgHr={stats.avg_hr_this_week}
        />
      )}

      {/* Recent Activities + FTP Card — 2 col, FTP narrower */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
        {/* Recent Activities */}
        <div className="bg-white dark:bg-gray-800 border border-border dark:border-gray-700 rounded-xl">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border dark:border-gray-700">
            <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              {t("Letzte Aktivitäten", "Recent Activities")}
            </h2>
            <Link href="/activities" className="text-xs text-strava font-medium hover:underline">
              {t("Alle →", "All →")}
            </Link>
          </div>
          <div className="divide-y divide-border dark:divide-gray-700">
            {!recent && (
              <div className="px-5 py-8 text-center text-sm text-gray-400">{t("Laden…", "Loading…")}</div>
            )}
            {recent?.items.map((act) => {
              const sport = sportLabel(act.type);
              const isRun = sport.label === "Run";
              return (
                <Link
                  key={act.id}
                  href={`/activities/${act.id}`}
                  className="flex items-center gap-3 px-4 sm:px-5 py-3 hover:bg-surface dark:hover:bg-gray-700 transition-colors"
                >
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0"
                    style={{ background: sport.color + "18" }}
                  >
                    {sport.emoji}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{act.name}</p>
                    <p className="text-xs text-gray-400">
                      {formatDate(act.start_time, lang)}
                      <span className="sm:hidden"> · {formatDistance(act.distance_m)}</span>
                    </p>
                  </div>
                  <div className="hidden sm:flex items-center gap-5 text-sm shrink-0">
                    <span className="tabular-nums text-gray-700 w-16 text-right">
                      {formatDistance(act.distance_m)}
                    </span>
                    <span className="tabular-nums text-gray-500 w-14 text-right">
                      {formatDuration(act.moving_time_s)}
                    </span>
                    <span className="tabular-nums text-gray-400 w-20 text-right text-xs">
                      {isRun
                        ? formatPace(act.distance_m, act.moving_time_s)
                        : formatSpeed(act.distance_m, act.moving_time_s)}
                    </span>
                  </div>
                  {act.tss != null && (
                    <span className="text-xs font-medium text-strava bg-strava/8 px-2 py-0.5 rounded-full tabular-nums shrink-0">
                      {Math.round(act.tss)} TSS
                    </span>
                  )}
                  <svg className="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              );
            })}
          </div>
        </div>

        {/* FTP + Greetings */}
        <div className="flex flex-col gap-4">
          {stats ? (
            <FtpCard
              ftp_w={stats.ftp_w}
              ftp_date={stats.ftp_date}
              ftp_source={stats.ftp_source}
              threshold_pace_ms={stats.threshold_pace_ms}
              threshold_pace_source={stats.threshold_pace_source}
              max_hr={stats.max_hr}
              max_hr_source={stats.max_hr_source}
            />
          ) : (
            <div className="bg-white border border-border rounded-xl p-5 animate-pulse h-40" />
          )}
          <GreetingsCard data={greetings} />
        </div>
      </div>
    </div>
  );
}
