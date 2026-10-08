"use client";

import type { CompletedActivity, PlannedWorkout } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  year: number;
  month: number;                       // 1-based
  planned: PlannedWorkout[];
  completed: CompletedActivity[];
  onSelectWorkout: (w: PlannedWorkout) => void;
}

const WEEKDAYS = {
  de: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
  en: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
};

const SPORT_COLOR: Record<string, string> = {
  run:      "#3B82F6",
  bike:     "#FC4C02",
  swim:     "#06B6D4",
  strength: "#8B5CF6",
  other:    "#9CA3AF",
};

const SPORT_EMOJI: Record<string, string> = {
  run: "🏃", bike: "🚴", swim: "🏊", strength: "💪", other: "🏋",
};

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

function getFirstWeekday(year: number, month: number) {
  // 0=Sun … 6=Sat → convert to Mon=0 … Sun=6
  const day = new Date(year, month - 1, 1).getDay();
  return (day + 6) % 7;
}

function formatCompletedDist(m: number | null): string {
  if (!m) return "";
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

function formatPlannedDist(m: number): string {
  const km = m / 1000;
  return `${Number.isInteger(km) ? km : km.toFixed(1)} km`;
}

export function TrainingCalendar({ year, month, planned, completed, onSelectWorkout }: Props) {
  const { lang, t, locale } = useLang();
  const daysInMonth = getDaysInMonth(year, month);
  const firstWeekday = getFirstWeekday(year, month);  // 0=Mon

  // Build lookup maps by date string
  const plannedByDate = new Map<string, PlannedWorkout[]>();
  for (const w of planned) {
    const key = w.date;
    if (!plannedByDate.has(key)) plannedByDate.set(key, []);
    plannedByDate.get(key)!.push(w);
  }

  const completedByDate = new Map<string, CompletedActivity[]>();
  for (const a of completed) {
    const key = a.date;
    if (!completedByDate.has(key)) completedByDate.set(key, []);
    completedByDate.get(key)!.push(a);
  }

  const today = new Date().toISOString().slice(0, 10);

  // Longest planned distance this month — bars are scaled against it so their
  // lengths are comparable across the whole calendar at a glance.
  const maxPlannedDist = Math.max(0, ...planned.map((w) => w.distance_m ?? 0));

  // Build the grid: leading empty cells + day cells
  const cells: (number | null)[] = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  // Pad to full weeks
  while (cells.length % 7 !== 0) cells.push(null);

  // Days shown in the mobile agenda: anything with entries, plus today
  const agendaDays = Array.from({ length: daysInMonth }, (_, i) => {
    const date = new Date(year, month - 1, i + 1);
    const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(i + 1).padStart(2, "0")}`;
    return {
      date,
      dateStr,
      planned: plannedByDate.get(dateStr) ?? [],
      completed: completedByDate.get(dateStr) ?? [],
    };
  }).filter((d) => d.planned.length > 0 || d.completed.length > 0 || d.dateStr === today);

  return (
    <div>
      {/* ── Mobile: agenda list (a 7-column grid is unreadable at phone width) ── */}
      <div className="md:hidden divide-y divide-border dark:divide-gray-700 -my-2">
        {agendaDays.length === 0 && (
          <p className="py-6 text-center text-sm text-gray-400">
            {t("Keine Einträge in diesem Monat.", "No entries this month.")}
          </p>
        )}
        {agendaDays.map(({ date, dateStr, planned: dayPlanned, completed: dayCompleted }) => {
          const isToday = dateStr === today;
          const isPast = dateStr < today;
          return (
            <div key={dateStr} className="flex gap-3 py-2.5">
              {/* Date column */}
              <div
                className={`w-11 shrink-0 text-center rounded-lg py-1 ${
                  isToday ? "bg-strava/10 text-strava" : isPast ? "text-gray-400" : "text-gray-700 dark:text-gray-200"
                }`}
              >
                <p className="text-[10px] font-medium uppercase tracking-wide">
                  {date.toLocaleDateString(locale, { weekday: "short" })}
                </p>
                <p className="text-lg font-semibold leading-tight tabular-nums">{date.getDate()}</p>
              </div>

              {/* Entries */}
              <div className="flex-1 min-w-0 flex flex-col gap-1.5">
                {dayPlanned.length === 0 && dayCompleted.length === 0 && (
                  <p className="text-sm text-gray-400 py-2">{t("Nichts geplant", "Nothing planned")}</p>
                )}
                {dayPlanned.map((w) => {
                  const color = SPORT_COLOR[w.sport] ?? "#9CA3AF";
                  return (
                    <button
                      key={w.id}
                      onClick={() => onSelectWorkout(w)}
                      className="w-full text-left rounded-lg px-3 py-2 text-sm font-medium leading-snug active:scale-[0.98] transition-transform flex items-center gap-2"
                      style={{ background: color + "18", color, borderLeft: `3px solid ${color}` }}
                    >
                      <span>{SPORT_EMOJI[w.sport] ?? "🏋"}</span>
                      <span className="flex-1 min-w-0 truncate">{w.title}</span>
                      {w.distance_m != null && w.distance_m > 0 && (
                        <span className="text-xs font-semibold tabular-nums shrink-0">{formatPlannedDist(w.distance_m)}</span>
                      )}
                      {w.tss_planned != null && (
                        <span className="text-[11px] tabular-nums opacity-70 shrink-0">{Math.round(w.tss_planned)} TSS</span>
                      )}
                    </button>
                  );
                })}
                {dayCompleted.map((a) => (
                  <div
                    key={a.id}
                    className="rounded-lg px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 flex items-center gap-2"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500 shrink-0" />
                    <span className="flex-1 min-w-0 truncate">{a.name}</span>
                    {a.distance_m ? <span className="tabular-nums shrink-0">{formatCompletedDist(a.distance_m)}</span> : null}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Desktop / tablet: month grid ── */}
      <div className="hidden md:block">
      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {WEEKDAYS[lang].map((d) => (
          <div key={d} className="text-[11px] font-medium text-gray-400 uppercase tracking-wide text-center py-1">
            {d}
          </div>
        ))}
      </div>

      {/* Day grid */}
      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, idx) => {
          if (day === null) return <div key={`empty-${idx}`} />;

          const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
          const isToday = dateStr === today;
          const isPast = dateStr < today;
          const dayPlanned = plannedByDate.get(dateStr) ?? [];
          const dayCompleted = completedByDate.get(dateStr) ?? [];

          return (
            <div
              key={dateStr}
              className={`min-h-[80px] rounded-xl p-1.5 flex flex-col gap-1 border transition-colors
                ${isToday
                  ? "border-strava bg-strava/5 dark:bg-strava/10"
                  : "border-border dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600"
                }
              `}
            >
              {/* Day number */}
              <span
                className={`text-[11px] font-medium self-start leading-none px-1 rounded
                  ${isToday ? "text-strava font-bold" : isPast ? "text-gray-400 dark:text-gray-500" : "text-gray-700 dark:text-gray-200"}
                `}
              >
                {day}
              </span>

              {/* Planned workouts */}
              {dayPlanned.map((w) => {
                const color = SPORT_COLOR[w.sport] ?? "#9CA3AF";
                return (
                  <button
                    key={w.id}
                    onClick={() => onSelectWorkout(w)}
                    className="w-full text-left rounded-lg px-1.5 py-1 text-[11px] font-medium leading-tight transition-all hover:opacity-80 active:scale-95"
                    style={{ background: color + "18", color, borderLeft: `2px solid ${color}` }}
                  >
                    <span className="mr-0.5">{SPORT_EMOJI[w.sport] ?? "🏋"}</span>
                    {w.title}

                    {/* Distance bar — length relative to the month's longest workout */}
                    {w.distance_m != null && w.distance_m > 0 && (
                      <span className="mt-1 flex items-center gap-1">
                        <span
                          className="h-1 flex-1 rounded-full overflow-hidden"
                          style={{ background: color + "26" }}
                        >
                          <span
                            className="block h-full rounded-full"
                            style={{
                              background: color,
                              width: `${Math.max(
                                8,
                                maxPlannedDist ? (w.distance_m / maxPlannedDist) * 100 : 100,
                              )}%`,
                            }}
                          />
                        </span>
                        <span className="text-[10px] font-semibold tabular-nums shrink-0">
                          {formatPlannedDist(w.distance_m)}
                        </span>
                      </span>
                    )}
                  </button>
                );
              })}

              {/* Completed activities (greyed out) */}
              {dayCompleted.map((a) => (
                <div
                  key={a.id}
                  className="w-full rounded-lg px-1.5 py-1 text-[11px] leading-tight bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 flex items-center gap-1"
                  title={`${a.name} — ${formatCompletedDist(a.distance_m)}`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500 shrink-0" />
                  <span className="truncate">{formatCompletedDist(a.distance_m) || a.name}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>

      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 text-[11px] text-gray-400">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-blue-100 border-l-2 border-blue-500 inline-block" />
          {t("Geplant (klickbar)", "Planned (clickable)")}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 inline-block" />
          {t("Absolviert (Strava)", "Completed (Strava)")}
        </span>
      </div>
    </div>
  );
}
