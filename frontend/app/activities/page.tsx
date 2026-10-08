"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  api, formatDate, formatDistance, formatDuration,
  formatPace, formatSpeed, sportLabel, sportName, type ActivityType,
} from "@/lib/api";
import { useLang } from "@/lib/i18n";

const PAGE_SIZE = 30;

export default function ActivitiesPage() {
  const { lang, t } = useLang();
  const [offset, setOffset] = useState(0);
  const [selectedType, setSelectedType] = useState<string | undefined>();

  const { data: types } = useQuery({ queryKey: ["activity-types"], queryFn: api.activityTypes });
  const { data, isFetching } = useQuery({
    queryKey: ["activities", { offset, type: selectedType }],
    queryFn: () => api.activities({ limit: PAGE_SIZE, offset, type: selectedType }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  function selectType(t: string | undefined) {
    setSelectedType(t);
    setOffset(0);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("Aktivitäten", "Activities")}</h1>
          <p className="text-sm text-gray-400 mt-0.5">{data?.total ?? "—"} {t("insgesamt", "total")}</p>
        </div>
      </div>

      {/* Sport filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => selectType(undefined)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            !selectedType
              ? "bg-strava text-white border-strava"
              : "border-border text-gray-600 hover:border-gray-300"
          }`}
        >
          {t("Alle", "All")}
        </button>
        {types?.slice(0, 8).map((type: ActivityType) => {
          const sport = sportLabel(type.type);
          return (
            <button
              key={type.type}
              onClick={() => selectType(type.type)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                selectedType === type.type
                  ? "text-white border-transparent"
                  : "border-border text-gray-600 hover:border-gray-300"
              }`}
              style={selectedType === type.type ? { background: sport.color } : undefined}
            >
              {sport.emoji} {sportName(type.type, lang)} <span className="opacity-60">({type.count})</span>
            </button>
          );
        })}
      </div>

      {/* Table */}
      <div className="bg-white border border-border rounded-xl overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-[auto_1fr_auto_auto] sm:grid-cols-[auto_1fr_auto_auto_auto] md:grid-cols-[auto_1fr_auto_auto_auto_auto] lg:grid-cols-[auto_1fr_auto_auto_auto_auto_auto] gap-3 sm:gap-4 px-4 py-2.5 bg-surface border-b border-border text-xs font-medium text-gray-500 uppercase tracking-wide">
          <span />
          <span>{t("Aktivität", "Activity")}</span>
          <span className="text-right">{t("Distanz", "Distance")}</span>
          <span className="text-right hidden sm:block">{t("Zeit", "Time")}</span>
          <span className="text-right hidden md:block">{t("Pace / Tempo", "Pace / Speed")}</span>
          <span className="text-right hidden lg:block">{t("Ø HF", "Avg HR")}</span>
          <span className="text-right">TSS</span>
        </div>

        {/* Rows */}
        {isFetching && !data && (
          <div className="py-12 text-center text-sm text-gray-400">{t("Laden…", "Loading…")}</div>
        )}
        {data?.items.map((act) => {
          const sport = sportLabel(act.type);
          const isRun = sport.label === "Run";
          return (
            <Link
              key={act.id}
              href={`/activities/${act.id}`}
              className="grid grid-cols-[auto_1fr_auto_auto] sm:grid-cols-[auto_1fr_auto_auto_auto] md:grid-cols-[auto_1fr_auto_auto_auto_auto] lg:grid-cols-[auto_1fr_auto_auto_auto_auto_auto] gap-3 sm:gap-4 items-center px-4 py-3 border-b border-border last:border-0 hover:bg-surface transition-colors"
            >
              {/* Icon */}
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                style={{ background: sport.color + "18" }}
              >
                {sport.emoji}
              </div>

              {/* Name + date */}
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{act.name}</p>
                <p className="text-xs text-gray-400">
                  {formatDate(act.start_time, lang)}
                  <span className="sm:hidden"> · {formatDuration(act.moving_time_s)}</span>
                </p>
              </div>

              {/* Distance */}
              <span className="text-sm tabular-nums text-right text-gray-700">
                {formatDistance(act.distance_m)}
              </span>

              {/* Time */}
              <span className="text-sm tabular-nums text-right text-gray-500 hidden sm:block">
                {formatDuration(act.moving_time_s)}
              </span>

              {/* Pace/Speed */}
              <span className="text-xs tabular-nums text-right text-gray-400 hidden md:block">
                {isRun
                  ? formatPace(act.distance_m, act.moving_time_s)
                  : formatSpeed(act.distance_m, act.moving_time_s)}
              </span>

              {/* Avg HR */}
              <span className="text-xs tabular-nums text-right text-gray-400 hidden lg:block">
                {act.avg_hr ? `${Math.round(act.avg_hr)} bpm` : "—"}
              </span>

              {/* TSS */}
              <span className="text-xs tabular-nums text-right font-medium text-strava">
                {act.tss != null ? Math.round(act.tss) : "—"}
              </span>
            </Link>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <button
            disabled={offset === 0}
            onClick={() => setOffset((p) => Math.max(0, p - PAGE_SIZE))}
            className="px-4 py-2 border border-border rounded-lg disabled:opacity-40 hover:bg-surface transition-colors"
          >
            ← {t("Zurück", "Previous")}
          </button>
          <span className="text-gray-500 tabular-nums">
            {t("Seite", "Page")} {currentPage} / {totalPages}
          </span>
          <button
            disabled={offset + PAGE_SIZE >= (data?.total ?? 0)}
            onClick={() => setOffset((p) => p + PAGE_SIZE)}
            className="px-4 py-2 border border-border rounded-lg disabled:opacity-40 hover:bg-surface transition-colors"
          >
            {t("Weiter", "Next")} →
          </button>
        </div>
      )}
    </div>
  );
}
