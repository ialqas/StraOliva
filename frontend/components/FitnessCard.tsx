"use client";

import { Card, CardTitle } from "@/components/Card";
import { InfoTooltip } from "@/components/InfoTooltip";
import type { TrainingLoadDay } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  ctl: number;
  ramp_rate: number;
  trajectory: string;
  loadHistory: TrainingLoadDay[];
}

const TRAJECTORY_LABEL: Record<string, { de: string; en: string }> = {
  rapid_build: { de: "Schneller Aufbau", en: "Rapid build" },
  building:    { de: "Aufbau",           en: "Building" },
  stagnant:    { de: "Stagnierend",      en: "Stagnant" },
  detraining:  { de: "Detraining",       en: "Detraining" },
  unknown:     { de: "—",                en: "—" },
};

const TRAJECTORY_COLOR: Record<string, string> = {
  rapid_build: "#16A34A",
  building:    "#22C55E",
  stagnant:    "#9CA3AF",
  detraining:  "#EF4444",
  unknown:     "#9CA3AF",
};

function Sparkline({ data }: { data: number[] }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const W = 120;
  const H = 36;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - ((v - min) / range) * H;
    return `${x},${y}`;
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ overflow: "visible" }}>
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke="#D85A30"
        strokeWidth="1.8"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function FitnessCard({ ctl, ramp_rate, trajectory, loadHistory }: Props) {
  const { t } = useLang();
  // Sample weekly CTL from load history (last 12 weeks, one per week)
  const weeklyCtl: number[] = [];
  if (loadHistory.length > 0) {
    const step = Math.max(1, Math.floor(loadHistory.length / 12));
    for (let i = 0; i < loadHistory.length; i += step) {
      weeklyCtl.push(loadHistory[i].ctl);
    }
    weeklyCtl.push(loadHistory[loadHistory.length - 1].ctl);
  }

  const sign = ramp_rate >= 0 ? "+" : "";
  const color = TRAJECTORY_COLOR[trajectory] ?? "#9CA3AF";
  const labelEntry = TRAJECTORY_LABEL[trajectory];
  const label = labelEntry ? t(labelEntry.de, labelEntry.en) : "—";

  return (
    <Card className="flex flex-col gap-3">
      <CardTitle>
        <InfoTooltip
          text={t(
            "CTL (Chronic Training Load) = Fitness. Gewichteter 42-Tage-Durchschnitt deines täglichen TSS. Steigt mit konsistentem Training — typisch 20–100+.",
            "CTL (Chronic Training Load) = fitness. Weighted 42-day average of your daily TSS. Rises with consistent training — typically 20–100+.",
          )}
        >
          Fitness (CTL)
        </InfoTooltip>
      </CardTitle>

      <div className="flex items-end justify-between">
        <div>
          <span className="text-3xl font-medium tabular-nums" style={{ color: "#D85A30" }}>
            {ctl.toFixed(1)}
          </span>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="text-sm font-medium tabular-nums" style={{ color }}>
              {sign}{ramp_rate.toFixed(1)}/{t("Woche", "week")}
            </span>
            <span
              className="text-xs px-1.5 py-0.5 rounded-full"
              style={{ background: color + "20", color }}
            >
              {label}
            </span>
          </div>
        </div>
        <Sparkline data={weeklyCtl} />
      </div>

      <p className="text-[13px] text-gray-400 dark:text-gray-500 border-t border-border dark:border-gray-700 pt-3">
        {t(
          "Ramp Rate letzte 4 Wochen · Optimal: +0.5 bis +1.5 CTL/Woche",
          "Ramp rate last 4 weeks · Optimal: +0.5 to +1.5 CTL/week",
        )}
      </p>
    </Card>
  );
}
