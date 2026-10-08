"use client";

import { Card, CardTitle } from "@/components/Card";
import { InfoTooltip } from "@/components/InfoTooltip";
import { useLang } from "@/lib/i18n";

interface Props {
  tsb: number;
  ctl: number;
  atl: number;
  interpretation: string;
}

const SCALE_MIN = -40;
const SCALE_MAX = 40;
const SCALE_RANGE = SCALE_MAX - SCALE_MIN; // 80

const BANDS = [
  { lo: -40, hi: -30, color: "#F7C1C1", de: "Burnout",            en: "Burnout" },
  { lo: -30, hi: -10, color: "#FAC775", de: "Hohe Belastung",     en: "High load" },
  { lo: -10, hi:   5, color: "#C0DD97", de: "Optimales Training", en: "Optimal training" },
  { lo:   5, hi:  25, color: "#B5D4F4", de: "Frisch",             en: "Fresh" },
  { lo:  25, hi:  40, color: "#D3D1C7", de: "Detraining",         en: "Detraining" },
] as const;

const SCALE_LABELS = [-40, -20, -10, 5, 25, 40];

function pct(val: number) {
  return ((val - SCALE_MIN) / SCALE_RANGE) * 100;
}

function currentBand(tsb: number) {
  return BANDS.find((b) => tsb >= b.lo && tsb < b.hi) ?? BANDS[BANDS.length - 1];
}

export function FormGaugeCard({ tsb, ctl, atl, interpretation }: Props) {
  const { t } = useLang();
  const markerPct = Math.max(0, Math.min(100, pct(tsb)));
  const band = currentBand(tsb);

  return (
    <Card className="flex flex-col gap-3">
      <CardTitle>
        <InfoTooltip
          text={t(
            "TSB (Training Stress Balance) = CTL − ATL. Positiv = frisch & erholt, negativ = müde. Ideal für Wettkämpfe: +5 bis +25.",
            "TSB (Training Stress Balance) = CTL − ATL. Positive = fresh & recovered, negative = tired. Ideal for races: +5 to +25.",
          )}
        >
          Form (TSB)
        </InfoTooltip>
      </CardTitle>

      {/* Big TSB value */}
      <div>
        <span className="text-[30px] font-medium tabular-nums" style={{ color: band.color === "#C0DD97" ? "#4A7C2A" : band.color === "#B5D4F4" ? "#2563EB" : band.color === "#FAC775" ? "#92400E" : band.color === "#F7C1C1" ? "#991B1B" : "#6B7280" }}>
          {tsb > 0 ? "+" : ""}{tsb.toFixed(1)}
        </span>
        <span className="text-[13px] text-gray-400 dark:text-gray-500 ml-2">
          <InfoTooltip
            text={t(
              "CTL (Chronic Training Load) = Fitness. Gewichteter 42-Tage-Durchschnitt deines täglichen TSS. Steigt langsam mit regelmäßigem Training.",
              "CTL (Chronic Training Load) = fitness. Weighted 42-day average of your daily TSS. Rises slowly with regular training.",
            )}
          >
            CTL
          </InfoTooltip>
          {" "}{ctl.toFixed(1)} ·{" "}
          <InfoTooltip
            text={t(
              "ATL (Acute Training Load) = Ermüdung. Gewichteter 7-Tage-Durchschnitt des TSS. Reagiert schnell auf intensives Training.",
              "ATL (Acute Training Load) = fatigue. Weighted 7-day average of TSS. Reacts quickly to intense training.",
            )}
          >
            ATL
          </InfoTooltip>
          {" "}{atl.toFixed(1)}
        </span>
      </div>

      {/* Banded gauge */}
      <div className="relative">
        <div className="flex h-5 rounded-full overflow-hidden w-full">
          {BANDS.map((b) => (
            <div
              key={b.lo}
              style={{
                width: `${((b.hi - b.lo) / SCALE_RANGE) * 100}%`,
                background: b.color,
              }}
            />
          ))}
        </div>

        {/* Marker */}
        <div
          className="absolute top-0 h-5 w-0.5 bg-gray-800 rounded-full shadow"
          style={{ left: `calc(${markerPct}% - 1px)` }}
        />
      </div>

      {/* Scale labels */}
      <div className="relative h-4 text-[10px] text-gray-400 select-none">
        {SCALE_LABELS.map((v) => (
          <span
            key={v}
            className="absolute -translate-x-1/2"
            style={{ left: `${pct(v)}%` }}
          >
            {v > 0 ? `+${v}` : v}
          </span>
        ))}
      </div>

      {/* Band label pill */}
      <div className="flex items-center gap-2">
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full"
          style={{ background: band.color, color: "#1F2937" }}
        >
          {t(band.de, band.en)}
        </span>
      </div>

      {interpretation && (
        <p className="text-[13px] text-gray-500 dark:text-gray-400 leading-relaxed border-t border-border dark:border-gray-700 pt-3">
          {interpretation}
        </p>
      )}
    </Card>
  );
}
