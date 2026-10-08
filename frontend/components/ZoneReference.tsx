"use client";

import { InfoTooltip } from "@/components/InfoTooltip";
import { ZONE_COLORS } from "@/components/TimeInZoneChart";
import { useLang } from "@/lib/i18n";

interface Props {
  max_hr: number;
  threshold_pace_ms: number | null;   // m/s
}

interface ZoneDef {
  zone: string;
  lo: number;   // fraction (HR: of max HR, pace: of threshold pace in s/km)
  hi: number;
  de: string;
  en: string;
  hintDe: string;
  hintEn: string;
}

// Same bounds as backend/app/analytics/zones.py (HR_ZONE_BOUNDS) — keep in sync
const HR_ZONES: ZoneDef[] = [
  { zone: "Z1", lo: 0.50, hi: 0.60, de: "Sehr leicht", en: "Very light", hintDe: "Ganz locker, Erholung, Ein-/Auslaufen",  hintEn: "Very easy — recovery, warm-up, cool-down" },
  { zone: "Z2", lo: 0.60, hi: 0.70, de: "Grundlage",   en: "Endurance",  hintDe: "Locker — Unterhaltung problemlos möglich", hintEn: "Easy — you can chat freely" },
  { zone: "Z3", lo: 0.70, hi: 0.80, de: "Aerob",       en: "Aerobic",    hintDe: "Moderat — nur noch kurze Sätze",          hintEn: "Moderate — short sentences only" },
  { zone: "Z4", lo: 0.80, hi: 0.90, de: "Schwelle",    en: "Threshold",  hintDe: "Hart — Tempodauerlauf, Schwellenintervalle", hintEn: "Hard — tempo runs, threshold intervals" },
  { zone: "Z5", lo: 0.90, hi: 1.00, de: "VO₂max",      en: "VO₂max",     hintDe: "Maximal — kurze, harte Intervalle",       hintEn: "Maximum — short, hard intervals" },
];

// Run pace zones as % of threshold pace (time per km) — after Friel; > 100 % = slower
const PACE_ZONES: ZoneDef[] = [
  { zone: "Z1", lo: 1.29, hi: 9.99, de: "Regeneration", en: "Recovery",  hintDe: "Auslaufen, Erholungsläufe",          hintEn: "Cool-downs, recovery runs" },
  { zone: "Z2", lo: 1.14, hi: 1.29, de: "Aerob",        en: "Aerobic",   hintDe: "Lange Läufe, Grundlagenausdauer",    hintEn: "Long runs, aerobic base" },
  { zone: "Z3", lo: 1.06, hi: 1.14, de: "Tempo",        en: "Tempo",     hintDe: "Marathon- bis Halbmarathon-Tempo",   hintEn: "Marathon to half-marathon pace" },
  { zone: "Z4", lo: 0.97, hi: 1.06, de: "Schwelle",     en: "Threshold", hintDe: "Tempodauerlauf, 10-km-Tempo",        hintEn: "Tempo runs, ~10 km race pace" },
  { zone: "Z5", lo: 0.90, hi: 0.97, de: "VO₂max",       en: "VO₂max",    hintDe: "Intervalle 3–5 min, 5-km-Tempo",     hintEn: "3–5 min intervals, ~5 km race pace" },
  { zone: "Z6", lo: 0,    hi: 0.90, de: "Anaerob",      en: "Anaerobic", hintDe: "Kurze Sprints, < 2 min",             hintEn: "Short reps, < 2 min" },
];

function formatSecPerKm(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s === 60 ? `${m + 1}:00` : `${m}:${String(s).padStart(2, "0")}`;
}

function hrRange(z: ZoneDef, maxHr: number): string {
  return `${Math.round(maxHr * z.lo)}–${Math.round(maxHr * z.hi)} bpm`;
}

function paceRange(z: ZoneDef, thresholdSec: number): string {
  // lo/hi are fractions of threshold time per km: larger = slower
  const fast = thresholdSec * z.lo;
  const slow = thresholdSec * z.hi;
  if (z.hi >= 9) return `> ${formatSecPerKm(fast)} /km`;
  if (z.lo === 0) return `< ${formatSecPerKm(slow)} /km`;
  return `${formatSecPerKm(fast)}–${formatSecPerKm(slow)} /km`;
}

function ZoneRow({ z, range }: { z: ZoneDef; range: string }) {
  const { t } = useLang();
  return (
    <div className="flex items-center gap-3 py-2 border-b border-border dark:border-gray-700 last:border-b-0">
      <span className="w-1 self-stretch rounded-full shrink-0" style={{ background: ZONE_COLORS[z.zone] ?? "#ccc" }} />
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-gray-700 dark:text-gray-200">
          {z.zone} · {t(z.de, z.en)}
        </p>
        <p className="text-[11px] text-gray-400 truncate">{t(z.hintDe, z.hintEn)}</p>
      </div>
      <span className="text-[13px] font-medium tabular-nums whitespace-nowrap dark:text-white">{range}</span>
    </div>
  );
}

function PanelTitle({ title, tooltip, basis }: { title: string; tooltip: string; basis: string }) {
  return (
    <div className="flex items-center justify-between gap-2 mb-1">
      <p className="text-[13px] font-medium text-gray-700 dark:text-gray-200">
        <InfoTooltip text={tooltip}>{title}</InfoTooltip>
      </p>
      <span className="text-[11px] text-gray-400 tabular-nums">{basis}</span>
    </div>
  );
}

export function ZoneReference({ max_hr, threshold_pace_ms }: Props) {
  const { t } = useLang();
  const thresholdSec = threshold_pace_ms ? 1000 / threshold_pace_ms : null;

  return (
    <div className="grid md:grid-cols-2 gap-x-8 gap-y-6">
      <div>
        <PanelTitle
          title={t("Herzfrequenz-Zonen", "Heart rate zones")}
          tooltip={t(
            "Berechnet aus deiner max. HF — dieselben Grenzen wie in „Zeit in Zonen“, Z2-Erkennung und HF-TSS.",
            "Derived from your max HR — the same bounds used for Time in Zone, Z2 detection and HR-based TSS.",
          )}
          basis={`${t("Max. HF", "Max HR")} ${Math.round(max_hr)} bpm`}
        />
        {HR_ZONES.map((z) => (
          <ZoneRow key={z.zone} z={z} range={hrRange(z, max_hr)} />
        ))}
      </div>

      <div>
        <PanelTitle
          title={t("Pace-Zonen (Laufen)", "Pace zones (running)")}
          tooltip={t(
            "Berechnet aus deiner Schwellenpace (ca. das Tempo, das du ~1 h halten kannst). Auf flachem Terrain anwenden — bei Steigungen oder Hitze besser nach HF steuern.",
            "Derived from your threshold pace (roughly the pace you can hold for ~1 h). Use on flat ground — on hills or in heat, steer by HR instead.",
          )}
          basis={thresholdSec ? `${t("Schwelle", "Threshold")} ${formatSecPerKm(thresholdSec)} /km` : ""}
        />
        {thresholdSec ? (
          PACE_ZONES.map((z) => <ZoneRow key={z.zone} z={z} range={paceRange(z, thresholdSec)} />)
        ) : (
          <p className="text-[13px] text-gray-400 py-4">
            {t(
              "Noch keine Schwellenpace erkannt — dafür braucht es einen harten Lauf (≥ 20 min) in den letzten 60 Tagen.",
              "No threshold pace detected yet — this needs a hard run (≥ 20 min) in the last 60 days.",
            )}
          </p>
        )}
      </div>
    </div>
  );
}
