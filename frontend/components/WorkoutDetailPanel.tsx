"use client";

import type { PlannedWorkout, WorkoutStep } from "@/lib/api";
import { formatDistance, sportLabel } from "@/lib/api";
import { useLang } from "@/lib/i18n";

// ── Step type config ──────────────────────────────────────────────────────────

const STEP_CONFIG: Record<string, { icon: string; color: string; bg: string }> = {
  warmup:   { icon: "↗", color: "#D97706", bg: "#FEF3C7" },
  interval: { icon: "⚡", color: "#DC2626", bg: "#FEE2E2" },
  recovery: { icon: "↘", color: "#16A34A", bg: "#DCFCE7" },
  cooldown: { icon: "↙", color: "#2563EB", bg: "#DBEAFE" },
  steady:   { icon: "→", color: "#7C3AED", bg: "#EDE9FE" },
  rest:     { icon: "○", color: "#9CA3AF", bg: "#F3F4F6" },
};

const STEP_LABELS: Record<string, { de: string; en: string }> = {
  warmup:   { de: "Einlaufen / Aufwärmen", en: "Warm-up" },
  interval: { de: "Intervall",             en: "Interval" },
  recovery: { de: "Pause / Erholung",      en: "Recovery" },
  cooldown: { de: "Auslaufen / Abwärmen",  en: "Cool-down" },
  steady:   { de: "Gleichmäßig",           en: "Steady" },
  rest:     { de: "Pause",                 en: "Rest" },
};

function formatPaceTarget(minKm: number): string {
  const m = Math.floor(minKm);
  const s = Math.round((minKm - m) * 60);
  return `${m}:${String(s).padStart(2, "0")} /km`;
}

function StepRow({ step }: { step: WorkoutStep }) {
  const { t } = useLang();
  const stepLabel = STEP_LABELS[step.type];
  const cfg = STEP_CONFIG[step.type] ?? STEP_CONFIG.steady;
  const repsLabel = step.reps && step.reps > 1 ? `${step.reps}×` : null;

  return (
    <div className="flex gap-3 items-start">
      {/* Icon + connector */}
      <div className="flex flex-col items-center gap-0 shrink-0">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-sm font-medium"
          style={{ background: cfg.bg, color: cfg.color }}
        >
          {cfg.icon}
        </div>
        <div className="w-px flex-1 bg-border mt-1" style={{ minHeight: 8 }} />
      </div>

      {/* Content */}
      <div className="pb-4 flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: cfg.color }}>
            {stepLabel ? t(stepLabel.de, stepLabel.en) : step.type}
          </span>
          {repsLabel && (
            <span
              className="text-[11px] font-bold px-1.5 py-0.5 rounded-full"
              style={{ background: cfg.bg, color: cfg.color }}
            >
              {repsLabel}
            </span>
          )}
        </div>
        <p className="text-sm font-medium mt-0.5">{step.label}</p>
        {step.description && (
          <p className="text-[13px] text-gray-500 dark:text-gray-400 mt-0.5">{step.description}</p>
        )}
        {/* Targets row */}
        <div className="flex flex-wrap gap-3 mt-1.5">
          {step.distance_m != null && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              📏 {step.distance_m >= 1000
                ? `${(step.distance_m / 1000).toFixed(step.distance_m % 1000 === 0 ? 0 : 1)} km`
                : `${Math.round(step.distance_m)} m`}
            </span>
          )}
          {step.duration_min != null && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              ⏱ {step.duration_min < 1
                ? `${Math.round(step.duration_min * 60)} s`
                : `${step.duration_min} min`}
            </span>
          )}
          {step.target_pace_min_km != null && (
            <span className="text-xs font-medium" style={{ color: cfg.color }}>
              🎯 {formatPaceTarget(step.target_pace_min_km)}
            </span>
          )}
          {step.target_hr_zone && (
            <span className="text-xs font-medium" style={{ color: cfg.color }}>
              ♡ {step.target_hr_zone}
            </span>
          )}
          {step.target_power_pct_ftp != null && (
            <span className="text-xs font-medium" style={{ color: cfg.color }}>
              ⚡ {step.target_power_pct_ftp}% FTP
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sport badge color ─────────────────────────────────────────────────────────

const SPORT_COLOR: Record<string, string> = {
  run:      "#3B82F6",
  bike:     "#FC4C02",
  swim:     "#06B6D4",
  strength: "#8B5CF6",
  other:    "#9CA3AF",
};

interface Props {
  workout: PlannedWorkout | null;
  onClose: () => void;
  onDelete?: (id: number) => void;
}

export function WorkoutDetailPanel({ workout, onClose, onDelete }: Props) {
  const { t, locale } = useLang();
  if (!workout) return null;

  const sport = sportLabel(workout.sport === "bike" ? "Ride" : workout.sport === "run" ? "Run" : workout.sport === "swim" ? "Swim" : "Other");
  const color = SPORT_COLOR[workout.sport] ?? "#9CA3AF";
  const dateLabel = new Date(workout.date + "T12:00:00").toLocaleDateString(locale, {
    weekday: "long", day: "numeric", month: "long",
  });

  const totalDist = workout.steps.reduce((s, st) => s + (st.distance_m ?? 0) * (st.reps ?? 1), 0);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40 backdrop-blur-[2px]"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full h-[100dvh] w-full max-w-md bg-white dark:bg-gray-900 shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-start gap-3 p-5 pt-[calc(1.25rem+env(safe-area-inset-top))] border-b border-border dark:border-gray-700">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0"
            style={{ background: color + "20" }}
          >
            {sport.emoji}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[11px] text-gray-400 uppercase tracking-wide">{dateLabel}</p>
            <h2 className="text-lg font-semibold leading-tight mt-0.5 dark:text-white">{workout.title}</h2>
            {workout.description && (
              <p className="text-[13px] text-gray-500 dark:text-gray-400 mt-1">{workout.description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label={t("Schließen", "Close")}
            className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors shrink-0"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Quick stats */}
        <div className="flex divide-x divide-border dark:divide-gray-700 border-b border-border dark:border-gray-700">
          {[
            { label: t("Dauer", "Duration"), value: workout.duration_min ? `${workout.duration_min} min` : "—" },
            { label: t("Distanz", "Distance"), value: totalDist > 0 ? formatDistance(totalDist) : workout.distance_m ? formatDistance(workout.distance_m) : "—" },
            { label: t("TSS geplant", "Planned TSS"), value: workout.tss_planned != null ? String(Math.round(workout.tss_planned)) : "—" },
          ].map(({ label, value }) => (
            <div key={label} className="flex-1 px-4 py-3 text-center">
              <p className="text-[11px] text-gray-400 uppercase tracking-wide">{label}</p>
              <p className="text-base font-semibold tabular-nums mt-0.5 dark:text-white">{value}</p>
            </div>
          ))}
        </div>

        {/* Steps */}
        <div className="flex-1 overflow-y-auto p-5">
          {workout.steps.length > 0 ? (
            <div>
              <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-4">{t("Einheiten-Struktur", "Workout structure")}</p>
              <div>
                {workout.steps.map((step, i) => (
                  <StepRow key={i} step={step} />
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-gray-400 text-sm gap-2">
              <span className="text-3xl">📋</span>
              <p>{t("Keine Struktur hinterlegt.", "No structure defined.")}</p>
              <p className="text-xs text-center max-w-[220px]">
                {t(
                  "Der MCP-Server kann hier Schritt-für-Schritt-Anweisungen eintragen.",
                  "The MCP server can add step-by-step instructions here.",
                )}
              </p>
            </div>
          )}

          {workout.notes && (
            <div className="mt-4 pt-4 border-t border-border dark:border-gray-700">
              <p className="text-[11px] text-gray-400 uppercase tracking-wide mb-2">{t("Notizen", "Notes")}</p>
              <p className="text-[13px] text-gray-600 dark:text-gray-300 leading-relaxed">{workout.notes}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {onDelete && (
          <div className="p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] border-t border-border dark:border-gray-700">
            <button
              onClick={() => { onDelete(workout.id); onClose(); }}
              className="w-full text-sm text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950 py-2 rounded-lg transition-colors"
            >
              {t("Einheit löschen", "Delete workout")}
            </button>
          </div>
        )}
      </div>
    </>
  );
}
