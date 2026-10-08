"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PlannedWorkout } from "@/lib/api";
import { TrainingCalendar } from "@/components/TrainingCalendar";
import { WorkoutDetailPanel } from "@/components/WorkoutDetailPanel";
import { useLang } from "@/lib/i18n";

function chevron(dir: "left" | "right") {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d={dir === "left" ? "M15 19l-7-7 7-7" : "M9 5l7 7-7 7"} />
    </svg>
  );
}

export default function TrainingsplanPage() {
  const qc = useQueryClient();
  const { t, locale } = useLang();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);   // 1-based
  const [selected, setSelected] = useState<PlannedWorkout | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["training-calendar", year, month],
    queryFn: () => api.trainingCalendar(year, month),
  });

  const deleteMut = useMutation({
    mutationFn: api.deleteWorkout,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["training-calendar"] }),
  });

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
  }

  function nextMonth() {
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
  }

  function goToday() {
    setYear(now.getFullYear());
    setMonth(now.getMonth() + 1);
  }

  const planned = data?.planned ?? [];
  const completed = data?.completed ?? [];

  // Monthly summary numbers
  const totalPlanned = planned.length;
  const totalDist = planned.reduce((s, w) => s + (w.distance_m ?? 0), 0);
  const totalTss = planned.reduce((s, w) => s + (w.tss_planned ?? 0), 0);
  const completedCount = completed.length;
  const monthName = new Date(year, month - 1, 1).toLocaleDateString(locale, { month: "long" });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("Trainingsplan", "Training Plan")}</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {t(
              "Geplante Einheiten · der MCP-Server kann hier Workouts anlegen und bearbeiten",
              "Planned sessions · the MCP server can create and edit workouts here",
            )}
          </p>
        </div>
      </div>

      {/* Month navigator */}
      <div className="flex items-center gap-3">
        <button
          onClick={prevMonth}
          className="w-8 h-8 rounded-lg border border-border dark:border-gray-700 flex items-center justify-center text-gray-500 hover:bg-surface dark:hover:bg-gray-700 transition-colors"
        >
          {chevron("left")}
        </button>
        <h2 className="text-lg font-semibold min-w-[150px] sm:min-w-[200px] text-center dark:text-white">
          {monthName} {year}
        </h2>
        <button
          onClick={nextMonth}
          className="w-8 h-8 rounded-lg border border-border dark:border-gray-700 flex items-center justify-center text-gray-500 hover:bg-surface dark:hover:bg-gray-700 transition-colors"
        >
          {chevron("right")}
        </button>
        <button
          onClick={goToday}
          className="ml-2 text-xs font-medium text-strava hover:underline"
        >
          {t("Heute", "Today")}
        </button>
      </div>

      {/* Month summary chips */}
      {!isLoading && (totalPlanned > 0 || completedCount > 0) && (
        <div className="flex flex-wrap gap-2 text-xs">
          {totalPlanned > 0 && (
            <span className="bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 px-2.5 py-1 rounded-full font-medium">
              {totalPlanned} {t("geplant", "planned")}
            </span>
          )}
          {completedCount > 0 && (
            <span className="bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2.5 py-1 rounded-full font-medium">
              {completedCount} {t("absolviert", "completed")}
            </span>
          )}
          {totalTss > 0 && (
            <span className="bg-orange-50 dark:bg-orange-950 text-orange-700 dark:text-orange-300 px-2.5 py-1 rounded-full font-medium">
              {Math.round(totalTss)} {t("TSS geplant", "TSS planned")}
            </span>
          )}
          {totalDist > 0 && (
            <span className="bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 px-2.5 py-1 rounded-full font-medium">
              {(totalDist / 1000).toFixed(0)} {t("km geplant", "km planned")}
            </span>
          )}
        </div>
      )}

      {/* Calendar */}
      <div className="bg-white dark:bg-gray-800 border border-border dark:border-gray-700 rounded-xl p-4 sm:p-5">
        {isLoading ? (
          <div className="h-96 flex items-center justify-center text-sm text-gray-400">
            <div className="flex flex-col items-center gap-2">
              <div className="w-6 h-6 border-2 border-strava border-t-transparent rounded-full animate-spin" />
              {t("Lade Kalender…", "Loading calendar…")}
            </div>
          </div>
        ) : (
          <TrainingCalendar
            year={year}
            month={month}
            planned={planned}
            completed={completed}
            onSelectWorkout={setSelected}
          />
        )}
      </div>

      {/* Empty state */}
      {!isLoading && totalPlanned === 0 && (
        <div className="bg-white dark:bg-gray-800 border border-dashed border-border dark:border-gray-700 rounded-xl p-8 text-center text-gray-400">
          <p className="text-4xl mb-3">📅</p>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {t(`Keine Einheiten für ${monthName} geplant.`, `No sessions planned for ${monthName}.`)}
          </p>
          <p className="text-xs mt-1 max-w-sm mx-auto">
            {t(
              "Der MCP-Server kann hier Trainingseinheiten anlegen — oder du fügst sie direkt über die API hinzu.",
              "The MCP server can create training sessions here — or add them directly via the API.",
            )}
          </p>
        </div>
      )}

      {/* Workout detail panel */}
      <WorkoutDetailPanel
        workout={selected}
        onClose={() => setSelected(null)}
        onDelete={(id) => deleteMut.mutate(id)}
      />
    </div>
  );
}
