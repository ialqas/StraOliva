"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useLang } from "@/lib/i18n";

const HeatmapMapInner = dynamic(
  () => import("@/components/HeatmapMapInner").then((m) => ({ default: m.HeatmapMapInner })),
  {
    ssr: false,
    loading: () => <div className="w-full h-full bg-gray-100 rounded-xl animate-pulse" />,
  }
);

export default function HeatmapPage() {
  const { t } = useLang();
  const { data, isLoading, error } = useQuery({
    queryKey: ["heatmap"],
    queryFn: api.heatmap,
    staleTime: 60 * 60 * 1000, // 1 hour
  });

  const tracks = data?.tracks ?? [];
  const center = (data?.center as [number, number]) ?? [10, 50];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">{t("Aktivitäts-Heatmap", "Activity Heatmap")}</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {t(
              "Alle GPS-Tracks übereinandergelegt — häufig genutzte Strecken leuchten orange",
              "All your GPS tracks overlaid — frequently used routes glow orange",
            )}
          </p>
        </div>
        {data && (
          <div className="text-right">
            <p className="text-2xl font-bold tabular-nums text-strava">{data.count}</p>
            <p className="text-xs text-gray-400">{t("Aktivitäten mit GPS", "activities with GPS")}</p>
          </div>
        )}
      </div>

      {/* Map */}
      {/* Phones: fill the screen between header and bottom tab bar (dvh tracks the collapsing browser UI) */}
      <div className="border border-border rounded-xl overflow-hidden h-[calc(100dvh-16rem-env(safe-area-inset-bottom))] min-h-[360px] md:h-[calc(100vh-180px)] md:min-h-[480px]">
        {isLoading && (
          <div className="w-full h-full bg-gray-50 flex flex-col items-center justify-center gap-2 text-sm text-gray-400">
            <div className="w-8 h-8 border-2 border-strava border-t-transparent rounded-full animate-spin" />
            <p>{t("GPS-Tracks werden berechnet…", "Computing GPS tracks…")}</p>
            <p className="text-xs">{t("Der erste Aufruf kann einige Sekunden dauern", "First load may take a few seconds")}</p>
          </div>
        )}
        {error && (
          <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">
            <div className="text-center space-y-2">
              <p>{t("Heatmap-Daten konnten nicht geladen werden.", "Could not load heatmap data.")}</p>
              <p className="text-xs">
                {t("Läuft das Backend? Dann", "Make sure the backend is running and run")}{" "}
                <code className="bg-gray-100 px-1.5 py-0.5 rounded">strava-dash recompute</code>
                {t(" ausführen.", "")}
              </p>
            </div>
          </div>
        )}
        {!isLoading && !error && tracks.length === 0 && (
          <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">
            <div className="text-center space-y-2">
              <p>{t("Keine GPS-Tracks gefunden.", "No GPS tracks found.")}</p>
              <p className="text-xs">{t("Importiere zuerst Aktivitäten mit GPS-Daten.", "Import activities with GPS data first.")}</p>
            </div>
          </div>
        )}
        {!isLoading && tracks.length > 0 && (
          <HeatmapMapInner tracks={tracks} center={center} />
        )}
      </div>
    </div>
  );
}
