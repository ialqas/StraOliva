"use client";

import type { RacePrediction } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  predictions: RacePrediction[];
  lookbackWeeks?: number;
}

const ICONS: Record<string, string> = {
  "5k": "🏃", "10k": "🏃", HM: "🏅", Marathon: "🏆",
};

const CONFIDENCE_STYLE: Record<string, { de: string; en: string; cls: string }> = {
  high:    { de: "Hoch",    en: "High",    cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  medium:  { de: "Mittel",  en: "Medium",  cls: "bg-amber-50 text-amber-700 border-amber-200" },
  low:     { de: "Niedrig", en: "Low",     cls: "bg-gray-50 text-gray-500 border-gray-200" },
  no_data: { de: "—",       en: "—",       cls: "bg-gray-50 text-gray-400 border-gray-200" },
};

export function RacePredictor({ predictions, lookbackWeeks = 8 }: Props) {
  const { t } = useLang();
  const hasAny = predictions.some((p) => p.predicted_time !== null);
  if (!hasAny) return (
    <div className="py-8 text-center text-sm text-gray-400">
      {t(
        `Keine aktuellen Laufdaten (mindestens eine Aktivität in den letzten ${lookbackWeeks} Wochen nötig).`,
        `No recent running data (at least one activity in the last ${lookbackWeeks} weeks required).`,
      )}
    </div>
  );

  return (
    <div className="space-y-0">
      {predictions.map((p) => {
        const conf = CONFIDENCE_STYLE[p.confidence] ?? CONFIDENCE_STYLE.low;
        return (
          <div
            key={p.name}
            className="flex items-center justify-between py-3 border-b border-border last:border-0"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-lg w-7 text-center">{ICONS[p.name] ?? "🏃"}</span>
              <div>
                <p className="text-sm font-semibold">{p.name}</p>
                <p className="text-xs text-gray-400 max-w-[140px] sm:max-w-[180px] truncate">{p.basis_description}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-3 shrink-0">
              <span
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full border ${conf.cls}`}
              >
                {t(conf.de, conf.en)}
              </span>
              <div className="text-right">
                {p.predicted_time ? (
                  <>
                    <p className="text-base font-bold tabular-nums text-strava">{p.predicted_time}</p>
                    {p.ci_lower && p.ci_upper && (
                      <p className="text-[10px] text-gray-400 tabular-nums">
                        {p.ci_lower} – {p.ci_upper}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-gray-300 font-medium">—</p>
                )}
              </div>
            </div>
          </div>
        );
      })}
      <p className="text-xs text-gray-400 pt-2">
        {t(`Riegel-Formel · Basis: letzte ${lookbackWeeks} Wochen`, `Riegel formula · based on the last ${lookbackWeeks} weeks`)}
      </p>
    </div>
  );
}
