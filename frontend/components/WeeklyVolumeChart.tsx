"use client";

import {
  Bar, BarChart, CartesianGrid, Legend,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { useLang } from "@/lib/i18n";

interface WeeklyEntry {
  week: string;
  run_km: number;
  ride_km: number;
  swim_km: number;
  other_km: number;
  total_tss: number;
  total_hours: number;
  count: number;
}

interface Props {
  data: WeeklyEntry[];
  metric?: "km" | "tss" | "hours";
  sport?: "all" | "run" | "bike";
}

function shortWeek(iso: string, locale: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString(locale, { month: "short", day: "numeric" });
}

const SPORT_COLORS = {
  run:   "#3B82F6",
  ride:  "#FC4C02",
  swim:  "#06B6D4",
  other: "#9CA3AF",
};

export function WeeklyVolumeChart({ data, metric = "km", sport = "all" }: Props) {
  const { t, locale } = useLang();
  if (!data.length) return (
    <div className="h-56 flex items-center justify-center text-sm text-gray-400">{t("Keine Daten", "No data")}</div>
  );

  const seriesName: Record<string, string> = {
    TSS: "TSS",
    Hours: t("Stunden", "Hours"),
    Run: t("Laufen", "Run"),
    Ride: t("Rad", "Ride"),
    Swim: t("Schwimmen", "Swim"),
    Other: t("Sonstige", "Other"),
  };

  const chartData = data.map((w) => {
    if (metric === "tss")   return { week: w.week, TSS: Math.round(w.total_tss) };
    if (metric === "hours") return { week: w.week, Hours: Math.round(w.total_hours * 10) / 10 };
    // km — filter by sport
    if (sport === "run")  return { week: w.week, Run:  Math.round(w.run_km  * 10) / 10 };
    if (sport === "bike") return { week: w.week, Ride: Math.round(w.ride_km * 10) / 10 };
    return {
      week:  w.week,
      Run:   Math.round(w.run_km  * 10) / 10,
      Ride:  Math.round(w.ride_km * 10) / 10,
      Swim:  Math.round(w.swim_km * 10) / 10,
      Other: Math.round(w.other_km * 10) / 10,
    };
  });

  type BarDef = { key: string; color: string };
  let bars: BarDef[];
  if (metric === "tss") {
    bars = [{ key: "TSS", color: "#FC4C02" }];
  } else if (metric === "hours") {
    bars = [{ key: "Hours", color: "#8B5CF6" }];
  } else if (sport === "run") {
    bars = [{ key: "Run",  color: SPORT_COLORS.run  }];
  } else if (sport === "bike") {
    bars = [{ key: "Ride", color: SPORT_COLORS.ride }];
  } else {
    bars = [
      { key: "Run",   color: SPORT_COLORS.run   },
      { key: "Ride",  color: SPORT_COLORS.ride  },
      { key: "Swim",  color: SPORT_COLORS.swim  },
      { key: "Other", color: SPORT_COLORS.other },
    ];
  }

  const unit = metric === "hours" ? "h" : metric === "km" ? " km" : "";

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 8 }} barCategoryGap="20%">
        <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="week"
          tickFormatter={(v) => shortWeek(v, locale)}
          tick={{ fontSize: 10, fill: "#9CA3AF" }}
          tickLine={false}
          axisLine={false}
          interval={Math.floor(data.length / 6)}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#9CA3AF" }}
          tickLine={false}
          axisLine={false}
          width={40}
          unit={unit}
        />
        <Tooltip
          contentStyle={{ fontSize: 11, borderRadius: 8, border: "1px solid #E5E7EB" }}
          labelFormatter={(v) => shortWeek(v, locale)}
          cursor={{ fill: "#F9FAFB" }}
        />
        {bars.map((b) => (
          <Bar key={b.key} dataKey={b.key} name={seriesName[b.key]} stackId="a" fill={b.color} maxBarSize={20} />
        ))}
        {metric === "km" && sport === "all" && (
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}
