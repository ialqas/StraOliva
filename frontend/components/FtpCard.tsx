"use client";

import { Card, CardTitle } from "@/components/Card";
import { InfoTooltip } from "@/components/InfoTooltip";
import { useLang } from "@/lib/i18n";

type Source = "auto" | "manual" | "default" | null;

interface Props {
  ftp_w: number | null;
  ftp_date: string | null;
  ftp_source?: "auto" | "manual" | null;
  threshold_pace_ms: number | null;
  threshold_pace_source: Source;
  max_hr: number;
  max_hr_source: Source;
}

function formatPace(speedMs: number): string {
  const secPerKm = 1000 / speedMs;
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return s === 60 ? `${m + 1}:00` : `${m}:${String(s).padStart(2, "0")}`;
}

function SourceBadge({ source }: { source: Source }) {
  const { t } = useLang();
  if (!source) return null;
  const label =
    source === "auto" ? "auto" : source === "manual" ? t("manuell", "manual") : t("Standard", "default");
  return (
    <span className="text-[10px] font-medium uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
      {label}
    </span>
  );
}

function ValueRow({
  label,
  tooltip,
  value,
  source,
}: {
  label: string;
  tooltip: string;
  value: React.ReactNode;
  source: Source;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[13px] text-gray-500 dark:text-gray-400">
        <InfoTooltip text={tooltip}>{label}</InfoTooltip>
      </span>
      <span className="flex items-center gap-2">
        <span className="text-[15px] font-medium tabular-nums">{value}</span>
        <SourceBadge source={source} />
      </span>
    </div>
  );
}

function formatDetectionDate(iso: string, locale: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(locale, { day: "2-digit", month: "short", year: "numeric" });
}

export function FtpCard({
  ftp_w, ftp_date, ftp_source, threshold_pace_ms, threshold_pace_source, max_hr, max_hr_source,
}: Props) {
  const { t, locale } = useLang();
  return (
    <Card className="flex flex-col gap-3">
      <CardTitle>{t("Leistungswerte", "Performance values")}</CardTitle>
      <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 -mb-2">FTP</p>

      {ftp_w ? (
        <>
          <div>
            <span className="text-[30px] font-medium tabular-nums">{ftp_w}</span>
            <span className="text-base text-gray-400 dark:text-gray-500 ml-1">W</span>
          </div>
          <p className="text-[13px] text-gray-400 dark:text-gray-500">
            {ftp_source === "manual" || !ftp_date
              ? t("Manuell gesetzt", "Set manually")
              : t(
                  `Automatisch erkannt · letzter 20-min-Effort am ${formatDetectionDate(ftp_date, locale)}`,
                  `Auto-detected · last 20-min effort on ${formatDetectionDate(ftp_date, locale)}`,
                )}
          </p>
        </>
      ) : (
        <>
          <div className="text-[30px] font-medium text-gray-300 dark:text-gray-600">—</div>
          <p className="text-[13px] text-gray-500 dark:text-gray-400 leading-snug">
            {t(
              "FTP konnte nicht ermittelt werden. Kein 20-min-Effort mit ausreichender Intensität in den letzten 90 Tagen.",
              "FTP could not be determined. No 20-min effort of sufficient intensity in the last 90 days.",
            )}
          </p>
          <button className="text-[13px] font-medium text-strava hover:underline text-left">
            {t("FTP manuell setzen →", "Set FTP manually →")}
          </button>
        </>
      )}

      {/* Run threshold + max HR — the other inputs for TSS and HR zones */}
      <div className="flex flex-col gap-2 border-t border-border dark:border-gray-700 pt-3">
        <ValueRow
          label={t("Schwellenpace", "Threshold pace")}
          tooltip={t(
            "Grundlage für den Lauf-TSS. Automatisch: schnellste 20 min der letzten 60 Tage × 0,95 — nur harte Efforts (≥ 85 % der max. HF). Mit THRESHOLD_PACE_MS in der .env fest einstellbar.",
            "Basis for run TSS. Auto: fastest 20 min of the last 60 days × 0.95 — hard efforts only (≥ 85% of max HR). Pin it with THRESHOLD_PACE_MS in .env.",
          )}
          value={threshold_pace_ms ? `${formatPace(threshold_pace_ms)} /km` : "—"}
          source={threshold_pace_ms ? threshold_pace_source : null}
        />
        <ValueRow
          label={t("Max. HF", "Max HR")}
          tooltip={t(
            "Grundlage für HF-Zonen, Z2-Erkennung und HF-basierten TSS. Automatisch: höchste mind. 10 s gehaltene HF der letzten 12 Monate (steigt nur). Mit MAX_HR in der .env fest einstellbar.",
            "Basis for HR zones, Z2 detection and HR-based TSS. Auto: highest HR held ≥ 10 s in the last 12 months (only rises). Pin it with MAX_HR in .env.",
          )}
          value={`${Math.round(max_hr)} bpm`}
          source={max_hr_source}
        />
      </div>
    </Card>
  );
}
