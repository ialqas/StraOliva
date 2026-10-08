"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { TrainingLoadDay } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  data: TrainingLoadDay[];
}

// Monday-first, matches week rows
const DAYS = {
  de: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
  en: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
};

/** Local YYYY-MM-DD — must use local date parts, NOT toISOString() (UTC),
 *  so the date key matches the row computed from getDay() (also local).
 *  In UTC+ timezones toISOString() shifts to the previous day. */
function toLocalISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function tssColor(tss: number): string {
  if (tss <= 0) return "#F3F4F6";
  if (tss < 30) return "#FDE8DC";
  if (tss < 60) return "#FBBFA8";
  if (tss < 100) return "#F97316";
  return "#FC4C02";
}

export function CalendarHeatmap({ data }: Props) {
  const { lang, t, locale } = useLang();
  const [tooltip, setTooltip] = useState<{ date: string; tss: number; x: number; y: number } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { weeks, monthLabels } = useMemo(() => {
    const byDate = new Map(data.map((d) => [d.date, d.total_tss]));

    // Build 52 weeks ending today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dayOfWeek = (today.getDay() + 6) % 7; // 0 = Monday
    const endDate = new Date(today);
    endDate.setDate(today.getDate() - dayOfWeek + 6); // end on Sunday

    const startDate = new Date(endDate);
    startDate.setDate(endDate.getDate() - 52 * 7 + 1);

    const weeks: { date: string; tss: number }[][] = [];
    let currentWeek: { date: string; tss: number }[] = [];
    const labels: { month: number; col: number }[] = [];
    let seenMonths = new Set<string>();

    const cursor = new Date(startDate);
    let colIdx = 0;

    while (cursor <= endDate) {
      const iso = toLocalISO(cursor);
      const dow = (cursor.getDay() + 6) % 7; // 0 = Monday

      if (dow === 0 && currentWeek.length > 0) {
        weeks.push(currentWeek);
        currentWeek = [];
        colIdx++;
      }

      const monthKey = `${cursor.getFullYear()}-${cursor.getMonth()}`;
      if (!seenMonths.has(monthKey) && dow === 0) {
        seenMonths.add(monthKey);
        labels.push({ month: cursor.getMonth(), col: colIdx });
      }

      currentWeek.push({ date: iso, tss: byDate.get(iso) ?? 0 });
      cursor.setDate(cursor.getDate() + 1);
    }
    if (currentWeek.length) weeks.push(currentWeek);

    return { weeks, monthLabels: labels };
  }, [data]);

  // On narrow screens the year doesn't fit — start scrolled to the most recent weeks
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollLeft = el.scrollWidth;
  }, [weeks.length]);

  const CELL = 12;
  const GAP = 3;
  const LABEL_H = 16;
  const LABEL_W = 22; // left gutter for weekday labels

  return (
    <div className="relative">
      <div ref={scrollRef} className="overflow-x-auto pb-1">
        <svg
          width={LABEL_W + weeks.length * (CELL + GAP)}
          height={LABEL_H + 7 * (CELL + GAP)}
          style={{ display: "block" }}
        >
          {/* Weekday labels (Monday-first, one per row) */}
          {DAYS[lang].map((label, dIdx) => (
            <text
              key={label}
              x={0}
              y={LABEL_H + dIdx * (CELL + GAP) + CELL - 2}
              fontSize={9}
              fill="#9CA3AF"
            >
              {label}
            </text>
          ))}

          {/* Month labels */}
          {monthLabels.map((l) => (
            <text
              key={`${l.month}-${l.col}`}
              x={LABEL_W + l.col * (CELL + GAP)}
              y={10}
              fontSize={9}
              fill="#9CA3AF"
            >
              {new Date(2000, l.month, 1).toLocaleDateString(locale, { month: "short" })}
            </text>
          ))}

          {/* Cells */}
          {weeks.map((week, wIdx) =>
            week.map((day, dIdx) => (
              <rect
                key={day.date}
                x={LABEL_W + wIdx * (CELL + GAP)}
                y={LABEL_H + dIdx * (CELL + GAP)}
                width={CELL}
                height={CELL}
                rx={2}
                fill={tssColor(day.tss)}
                onMouseEnter={(e) => {
                  const rect = (e.target as SVGRectElement).getBoundingClientRect();
                  setTooltip({ date: day.date, tss: day.tss, x: rect.left, y: rect.top });
                }}
                onMouseLeave={() => setTooltip(null)}
                style={{ cursor: "default" }}
              />
            ))
          )}
        </svg>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 bg-gray-900 text-white text-xs rounded-lg px-2.5 py-1.5 pointer-events-none shadow-lg"
          style={{ left: tooltip.x + 16, top: tooltip.y - 8 }}
        >
          <p className="font-medium">{new Date(tooltip.date + "T12:00:00").toLocaleDateString(locale, { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}</p>
          <p className="text-gray-300">{tooltip.tss > 0 ? `${Math.round(tooltip.tss)} TSS` : t("Ruhetag", "Rest day")}</p>
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
        <span>{t("Weniger", "Less")}</span>
        {[0, 20, 50, 80, 120].map((v) => (
          <div key={v} className="w-3 h-3 rounded-sm" style={{ background: tssColor(v) }} />
        ))}
        <span>{t("Mehr", "More")}</span>
      </div>
    </div>
  );
}
