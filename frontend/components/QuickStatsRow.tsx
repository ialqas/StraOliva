"use client";

import { Card } from "@/components/Card";
import { InfoTooltip } from "@/components/InfoTooltip";
import { useLang } from "@/lib/i18n";

interface Props {
  tss: number;
  tss4wAvg: number;
  hours: number;
  activities: number;
  avgHr: number | null;
}

function StatItem({
  label,
  value,
  sub,
  subColor,
  className = "",
}: {
  label: React.ReactNode;
  value: string | number;
  sub?: string;
  subColor?: string;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-0.5 px-4 py-3 min-w-0 border-border dark:border-gray-700 ${className}`}>
      <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
        {label}
      </span>
      <span className="text-[22px] font-medium tabular-nums leading-tight dark:text-gray-100">{value}</span>
      {sub && (
        <span className="text-[11px] tabular-nums" style={{ color: subColor ?? "#9CA3AF" }}>
          {sub}
        </span>
      )}
    </div>
  );
}

export function QuickStatsRow({ tss, tss4wAvg, hours, activities, avgHr }: Props) {
  const { t } = useLang();
  const tssDiff = tss4wAvg > 0 ? ((tss - tss4wAvg) / tss4wAvg) * 100 : null;
  const tssSubColor =
    tssDiff == null ? "#9CA3AF" : tssDiff > 10 ? "#D85A30" : tssDiff < -10 ? "#EF4444" : "#22C55E";
  const tssSub =
    tssDiff != null
      ? `${tssDiff > 0 ? "+" : ""}${tssDiff.toFixed(0)}% ${t("vs. 4-Wochen-Ø", "vs 4-week avg")}`
      : tss4wAvg > 0 ? `Ø ${tss4wAvg} / ${t("Woche", "week")}` : undefined;

  return (
    <Card noPad>
      {/* 2×2 on phones, one row from sm up */}
      <div className="grid grid-cols-2 sm:grid-cols-4">
        <StatItem
          label={
            <InfoTooltip
              text={t(
                "TSS (Training Stress Score) = Belastung einer Einheit. 100 TSS ≈ 1h bei FTP-Intensität. Basis für CTL, ATL und TSB.",
                "TSS (Training Stress Score) = load of a session. 100 TSS ≈ 1h at FTP intensity. Basis for CTL, ATL and TSB.",
              )}
            >
              {t("TSS diese Woche", "TSS this week")}
            </InfoTooltip>
          }
          value={Math.round(tss)}
          sub={tssSub}
          subColor={tssSubColor}
          className="border-r border-b sm:border-b-0"
        />
        <StatItem
          label={t("Stunden", "Hours")}
          value={hours.toFixed(1) + " h"}
          sub={`${(hours * 60).toFixed(0)} min`}
          className="border-b sm:border-b-0 sm:border-r"
        />
        <StatItem label={t("Aktivitäten", "Activities")} value={activities} className="border-r" />
        <StatItem
          label={t("Ø Herzfreq.", "Avg HR")}
          value={avgHr != null ? `${Math.round(avgHr)} bpm` : "—"}
          sub={avgHr != null ? t("diese Woche", "this week") : t("keine Daten", "no data")}
        />
      </div>
    </Card>
  );
}
