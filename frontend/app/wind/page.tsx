"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, formatDistance } from "@/lib/api";
import type { SegmentWind } from "@/lib/api";
import { WindCompass } from "@/components/WindCompass";
import { useLang } from "@/lib/i18n";

const WindMapInner = dynamic(
  () => import("@/components/WindMapInner").then((m) => ({ default: m.WindMapInner })),
  {
    ssr: false,
    loading: () => <div className="w-full h-full bg-gray-100 rounded-xl animate-pulse" />,
  }
);

const CATEGORY_SORT: Record<string, number> = {
  strong_tailwind: 0,
  tailwind: 1,
  crosswind: 2,
  slight_headwind: 3,
  headwind: 4,
  unknown: 5,
};

function CategoryBadge({ category, label, color }: { category: string; label: string; color: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: color + "20", color }}
    >
      {category === "strong_tailwind" || category === "tailwind" ? "↑" :
       category === "headwind" ? "↓" : "→"}
      {label}
    </span>
  );
}

function BearingArrow({ deg }: { deg: number }) {
  return (
    <span
      title={`${deg}°`}
      style={{ display: "inline-block", transform: `rotate(${deg}deg)`, fontSize: 14 }}
    >
      ↑
    </span>
  );
}

export default function WindPage() {
  const { lang, t } = useLang();
  // Cities come from WIND_CITIES in .env; none configured = wind per segment location
  const { data: cities = [], isFetched: citiesReady } = useQuery({
    queryKey: ["wind-cities"],
    queryFn: api.windCities,
    staleTime: Infinity,
  });
  const [picked, setPicked] = useState<string | null>(null);
  const city = cities.find((c) => c.key === picked) ?? cities[0];

  const { data, isLoading, error } = useQuery({
    queryKey: ["segments-wind", city?.key, lang],
    queryFn: () => api.segmentsWind(city?.key, lang),
    enabled: citiesReady,
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  });

  const segments = data?.segments ?? [];
  const wind = data?.wind ?? null;

  const hasTailwind = segments.some(
    (s) => s.category === "strong_tailwind" || s.category === "tailwind"
  );

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("Wind & Segmente", "Wind & Segments")}</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {t("Aktuelle DWD-Winddaten × deine markierten Strava-Segmente", "Current DWD wind data × your starred Strava segments")}
          </p>
        </div>
        <div className="flex flex-row-reverse sm:flex-col items-center sm:items-end gap-2 sm:gap-2">
          {cities.length > 1 && (
            <div className="flex rounded-lg border border-border overflow-hidden text-sm font-medium">
              {cities.map((c) => (
                <button
                  key={c.key}
                  onClick={() => setPicked(c.key)}
                  className={`px-3 py-1.5 transition-colors ${
                    city?.key === c.key
                      ? "bg-strava text-white"
                      : "bg-white text-gray-500 hover:bg-surface"
                  }`}
                >
                  {c.name}
                </button>
              ))}
            </div>
          )}
          {data && (
            <span className="tabular-nums text-sm text-gray-400">
              {segments.length} {t("Segmente", "segments")}
            </span>
          )}
        </div>
      </div>

      {/* Tailwind banner */}
      {segments.length > 0 && wind && hasTailwind && (
        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3 text-sm text-emerald-700 font-medium">
          <span className="text-lg">🚀</span>
          {t("Rückenwind-Tag! Gute Chancen auf eine neue Bestzeit.", "Tailwind day! Good chances for a new PR.")}
        </div>
      )}

      {/* Map — relative wrapper lets compass float above the overflow:hidden map div */}
      <div className="relative">
        <div className="border border-border rounded-xl overflow-hidden h-[60dvh] min-h-[340px] md:h-[calc(100vh-320px)] md:min-h-[400px]">
          {isLoading && (
            <div className="w-full h-full bg-gray-50 flex flex-col items-center justify-center gap-2 text-sm text-gray-400">
              <div className="w-8 h-8 border-2 border-strava border-t-transparent rounded-full animate-spin" />
              <p>{t("Wind & Segmente werden geladen…", "Loading wind & segments…")}</p>
            </div>
          )}
          {error && (
            <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">
              <div className="text-center space-y-2">
                <p>{t("Fehler beim Laden der Daten.", "Failed to load data.")}</p>
                <p className="text-xs">
                  {t("Backend läuft? Segmente mit", "Backend running? Sync segments with")}{" "}
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded">strava-dash sync-segments</code>
                  {t(" syncen.", ".")}
                </p>
              </div>
            </div>
          )}
          {!isLoading && !error && segments.length === 0 && (
            <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">
              <div className="text-center space-y-2 max-w-xs">
                <p className="text-base">{t("Keine Segmente gefunden.", "No segments found.")}</p>
                <p className="text-xs leading-relaxed">
                  {t("Markiere Segmente auf Strava (Stern-Symbol) und führe dann", "Star segments on Strava, then run")}
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded mx-1">strava-dash sync-segments</code>
                  {t("aus.", "")}
                </p>
              </div>
            </div>
          )}
          {!isLoading && segments.length > 0 && (
            <WindMapInner segments={segments} center={city ? [city.lng, city.lat] : undefined} />
          )}
        </div>
        {/* Compass floats above map — must be inside relative wrapper but outside overflow:hidden div */}
        {!isLoading && wind && (
          <div className="absolute top-2 left-2 sm:top-3 sm:left-3 z-20 pointer-events-none origin-top-left scale-[0.85] sm:scale-100">
            <WindCompass wind={wind} />
          </div>
        )}
      </div>

      {/* Segment table */}
      {segments.length > 0 && (
        <div className="bg-white border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <h2 className="font-semibold text-sm">{t("Segmente nach Windvorteil", "Segments by wind advantage")}</h2>
            <span className="text-xs text-gray-400">
              {segments.length} {segments.length !== 1 ? t("Segmente", "segments") : t("Segment", "segment")}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-2 text-left font-medium">Segment</th>
                  <th className="px-4 py-2 text-right font-medium">{t("Distanz", "Distance")}</th>
                  <th className="px-4 py-2 text-right font-medium">{t("Steigung", "Grade")}</th>
                  <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">{t("Richtung", "Bearing")}</th>
                  <th className="px-4 py-2 text-right font-medium hidden sm:table-cell">{t("Winkel", "Angle")}</th>
                  <th className="px-4 py-2 text-right font-medium">Wind</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[...segments]
                  .sort((a, b) => (CATEGORY_SORT[a.category] ?? 5) - (CATEGORY_SORT[b.category] ?? 5))
                  .map((seg: SegmentWind) => (
                    <tr key={seg.id} className="hover:bg-surface transition-colors">
                      <td className="px-4 py-2.5 font-medium max-w-[180px] truncate">{seg.name}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-gray-600">
                        {formatDistance(seg.distance_m)}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-gray-500">
                        {seg.avg_grade != null
                          ? `${seg.avg_grade > 0 ? "+" : ""}${seg.avg_grade.toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-gray-400 hidden sm:table-cell">
                        <BearingArrow deg={seg.bearing_deg} />
                        <span className="ml-1 text-xs">{Math.round(seg.bearing_deg)}°</span>
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-gray-400 hidden sm:table-cell">
                        {Math.round(seg.tailwind_angle)}°
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <CategoryBadge
                          category={seg.category}
                          label={seg.label}
                          color={seg.color}
                        />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {data?.error && (
            <div className="px-5 py-2 border-t border-border text-xs text-amber-600 bg-amber-50">
              {t("Windabfrage fehlgeschlagen", "Wind lookup failed")}: {data.error} — {t("Winkelberechnung mit neutralem Wind.", "angles computed with neutral wind.")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
