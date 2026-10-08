import { localeFor, type Lang } from "@/lib/i18n";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error(`API ${res.status}: ${path}`);
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Activity {
  id: number;
  name: string;
  type: string;
  start_time: string;
  distance_m: number | null;
  moving_time_s: number | null;
  elapsed_time_s: number | null;
  total_elevation_gain_m: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  avg_watts: number | null;
  weighted_avg_watts: number | null;
  tss: number | null;
  has_streams: boolean;
  map_polyline?: string | null;
}

export interface ActivitiesResponse {
  total: number;
  items: Activity[];
}

export interface TrainingLoadDay {
  date: string;
  ctl: number;
  atl: number;
  tsb: number;
  total_tss: number;
}

export interface Stats {
  ctl: number;
  atl: number;
  tsb: number;
  tss_this_week: number;
  tss_last_week: number;
  tss_4week_avg: number;
  hours_this_week: number;
  activities_this_week: number;
  avg_hr_this_week: number | null;
  ramp_rate: number;
  fitness_trajectory: string;
  form_interpretation: string;
  ftp_w: number | null;
  ftp_date: string | null;
  ftp_source: "auto" | "manual" | null;
  threshold_pace_ms: number | null;                   // m/s
  threshold_pace_source: "auto" | "manual" | null;
  max_hr: number;
  max_hr_source: "auto" | "manual" | "default";       // default = no HR data analysed yet
  type_counts_this_week: Record<string, number>;
}

export interface GreetingItem {
  activity_id: number;
  name: string;
  start_time: string;
  count: number;
}

export interface Greetings {
  total: number;
  activities: number;
  avg_per_activity: number;
  best: GreetingItem | null;
  last: GreetingItem | null;
  items: GreetingItem[];
}

export interface Streams {
  time_s: (number | null)[];
  hr: (number | null)[];
  watts: (number | null)[];
  velocity_smooth: (number | null)[];
  altitude_m: (number | null)[];
  cadence: (number | null)[];
  lat: (number | null)[];
  lng: (number | null)[];
}

export interface Lap {
  lap_index: number;
  distance_m: number | null;
  time_s: number | null;         // elapsed, incl. pauses (matches the stream timeline)
  moving_time_s: number | null;  // without pauses — what the watch shows
  avg_hr: number | null;
  avg_watts: number | null;
  avg_speed_ms: number | null;
}

export interface KmSplit {
  split_index: number;
  distance_m: number | null;
  moving_time_s: number | null;
  elapsed_time_s: number | null;
  avg_speed_ms: number | null;
  avg_hr: number | null;
  elevation_diff_m: number | null;
}

export interface ActivitySplits {
  laps: Lap[];
  laps_are_manual: boolean;  // false = watch auto-laps (every km) or a single lap
  km_splits: KmSplit[];
}

export interface PDCPoint {
  duration_s: number;
  power_w: number;
}

export interface CPModelPoint {
  duration_s: number;
  power_w: number;
  ci_lower: number;
  ci_upper: number;
}

export interface CPModel {
  cp_w: number;
  w_prime_kj: number;
  r_squared: number;
  standard_error: number;
  curve: CPModelPoint[];
}

export interface PowerCurve {
  all_time: PDCPoint[];
  recent_6w: PDCPoint[];
  cp_model: CPModel | null;
  note?: string;
}

export interface WeeklyVolume {
  week: string;
  run_km: number;
  ride_km: number;
  swim_km: number;
  other_km: number;
  total_tss: number;
  total_hours: number;
  count: number;
}

export interface RacePrediction {
  name: string;
  distance_m: number;
  predicted_time: string | null;
  predicted_s: number | null;
  ci_lower: string | null;
  ci_upper: string | null;
  ci_lower_s: number | null;
  ci_upper_s: number | null;
  confidence: "high" | "medium" | "low" | "no_data";
  basis_description: string;
  num_efforts: number;
}

export interface MonthlyStats {
  month: string;
  distance_km: number;
  elevation_m: number;
  tss: number;
  hours: number;
  count: number;
  run_km: number;
  ride_km: number;
  run_hours: number;
  ride_hours: number;
  run_elevation: number;
  ride_elevation: number;
  run_count: number;
  ride_count: number;
}

export interface HeatmapData {
  tracks: [number, number][][]; // [[lng, lat], ...]
  count: number;
  center: [number, number];    // [lng, lat]
}

export interface SplitAnomaly {
  lap_index: number;
  anomaly: "fast" | "slow" | null;
  pct_from_median: number | null;
  tooltip: string | null;
}

export interface ActivityAnalytics {
  decoupling_pct: number | null;
  decoupling_effort: string | null;
  hr_drift_pct: number | null;
  np_w: number | null;
  intensity_factor: number | null;
  avg_hr_zone: string | null;
  ftp_w: number | null;
  zones_hr: Record<string, number> | null;
  zones_power: Record<string, number> | null;
  split_anomalies: SplitAnomaly[];
}

export interface ActivityType {
  type: string;
  count: number;
}

export interface WindInfo {
  speed_ms: number | null;
  speed_kmh: number | null;
  direction_from: number | null;
  gust_speed_ms: number | null;
  station_name: string | null;
  station_distance_km: number | null;
}

export interface SegmentWind {
  id: number;
  name: string;
  distance_m: number | null;
  start_lat: number;
  start_lng: number;
  end_lat: number;
  end_lng: number;
  avg_grade: number | null;
  bearing_deg: number;
  tailwind_angle: number;
  category: string;
  label: string;
  color: string;
  coords: [number, number][]; // [lng, lat] GeoJSON order
}

export interface WindCity {
  key: string;
  name: string;
  lat: number;
  lng: number;
}

export interface SegmentsWindResponse {
  segments: SegmentWind[];
  wind: WindInfo | null;
  error: string | null;
}

export interface DecouplingPoint {
  date: string;
  activity_id: number;
  activity_name: string;
  decoupling_pct: number;
  duration_min: number;
  sport: string;
}

export interface DecouplingTimeline {
  points: DecouplingPoint[];
  trend_slope_per_activity: number | null;
  interpretation: string;
}

export interface WeekZone {
  week: string;
  zones: Record<string, number>;
}

export interface TimeInZoneData {
  weeks: WeekZone[];
  summary: string;
}

export interface EffectivePacePoint {
  date: string;
  activity_id: number;
  activity_name: string;
  pace_sec_per_km: number;
  avg_hr: number;
  distance_km: number;
  distance_category: "5-10km" | "10-15km" | "15km+";
}

export interface EffectivePaceData {
  points: EffectivePacePoint[];
  trend_slope_sec_per_km_per_month: number | null;
  interpretation: string;
}

// ── Training Plan ──────────────────────────────────────────────────────────────

export interface WorkoutStep {
  type: "warmup" | "interval" | "recovery" | "cooldown" | "steady" | "rest";
  label: string;
  description?: string | null;
  distance_m?: number | null;
  duration_min?: number | null;
  reps?: number | null;
  target_pace_min_km?: number | null;
  target_hr_zone?: string | null;
  target_power_pct_ftp?: number | null;
}

export interface PlannedWorkout {
  id: number;
  date: string;             // YYYY-MM-DD
  title: string;
  sport: string;
  description: string | null;
  duration_min: number | null;
  distance_m: number | null;
  tss_planned: number | null;
  steps: WorkoutStep[];
  notes: string | null;
  completed_activity_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CompletedActivity {
  id: number;
  name: string;
  type: string;
  date: string;
  distance_m: number | null;
  moving_time_s: number | null;
  tss: number | null;
}

export interface CalendarMonth {
  planned: PlannedWorkout[];
  completed: CompletedActivity[];
}

export interface WorkoutCreate {
  date: string;
  title: string;
  sport?: string;
  description?: string | null;
  duration_min?: number | null;
  distance_m?: number | null;
  tss_planned?: number | null;
  steps?: WorkoutStep[];
  notes?: string | null;
}

export interface RecomputeResult {
  sync: { new: number; updated: number; streams_ok: number; errors: number };
  sync_error: string | null;
  tss_computed: number;
  tss_skipped: number;
  tss_mode: "full" | "incremental";
  timings: Record<string, number>;  // seconds per step, incl. "total"
  days_written: number;
  ftp_w: number | null;
  threshold_pace_ms: number | null;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const api = {
  health: () => get<{ status: string; timestamp: string }>("/healthz"),

  stats: (lang: Lang = "de") => get<Stats>(`/api/stats?lang=${lang}`),

  greetings: (days?: number) =>
    get<Greetings>(`/api/greetings${days ? `?days=${days}` : ""}`),

  trainingLoad: (days = 180) =>
    get<TrainingLoadDay[]>(`/api/training-load?days=${days}`),

  activities: (params: { limit?: number; offset?: number; type?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.type) q.set("type", params.type);
    return get<ActivitiesResponse>(`/api/activities?${q}`);
  },

  activity: (id: number) => get<Activity>(`/api/activities/${id}`),

  activityTypes: () => get<ActivityType[]>("/api/activities/types"),

  streams: (id: number) => get<Streams>(`/api/activities/${id}/streams`),

  laps: (id: number) => get<Lap[]>(`/api/activities/${id}/laps`),

  splits: (id: number) => get<ActivitySplits>(`/api/activities/${id}/splits`),

  powerCurve: (lang: Lang = "de") => get<PowerCurve>(`/api/power-curve?lang=${lang}`),

  weeklyVolume: (weeks = 20) => get<WeeklyVolume[]>(`/api/weekly-volume?weeks=${weeks}`),

  racePredictions: (lookbackWeeks = 8, lang: Lang = "de") =>
    get<RacePrediction[]>(`/api/race-predictions?lookback_weeks=${lookbackWeeks}&lang=${lang}`),

  monthlyStats: (months = 12) => get<MonthlyStats[]>(`/api/monthly-stats?months=${months}`),

  activityAnalytics: (id: number, lang: Lang = "de") =>
    get<ActivityAnalytics>(`/api/activities/${id}/analytics?lang=${lang}`),

  heatmap: () => get<HeatmapData>("/api/heatmap"),

  windCities: () => get<WindCity[]>("/api/segments/cities"),

  segmentsWind: (city?: string, lang: Lang = "de") => {
    const q = new URLSearchParams({ lang });
    if (city) q.set("city", city);
    return get<SegmentsWindResponse>(`/api/segments/wind?${q}`);
  },

  // Max HR is not sent — the backend uses the athlete's configured max HR
  decouplingTimeline: (lang: Lang = "de", lookbackDays = 180) =>
    get<DecouplingTimeline>(`/api/decoupling-timeline?lookback_days=${lookbackDays}&lang=${lang}`),

  timeInZone: (sport = "all", weeks = 12, ftpW?: number, lang: Lang = "de") => {
    const q = new URLSearchParams({ sport, weeks: String(weeks), lang });
    if (ftpW) q.set("ftp_w", String(ftpW));
    return get<TimeInZoneData>(`/api/time-in-zone?${q}`);
  },

  effectivePace: (lang: Lang = "de", lookbackDays = 180) =>
    get<EffectivePaceData>(`/api/effective-pace?lookback_days=${lookbackDays}&lang=${lang}`),

  // Training Plan
  trainingCalendar: (year: number, month: number) =>
    get<CalendarMonth>(`/api/training-plan/calendar?year=${year}&month=${month}`),

  trainingWorkout: (id: number) =>
    get<PlannedWorkout>(`/api/training-plan/workouts/${id}`),

  createWorkout: (body: WorkoutCreate) =>
    post<PlannedWorkout>("/api/training-plan/workouts", body),

  updateWorkout: (id: number, body: Partial<WorkoutCreate>) =>
    patch<PlannedWorkout>(`/api/training-plan/workouts/${id}`, body),

  deleteWorkout: (id: number) =>
    del(`/api/training-plan/workouts/${id}`),

  // Sync + recompute everything (same as `strava-dash recompute`)
  recompute: () => post<RecomputeResult>("/api/recompute", {}),
};

// ── Formatters ────────────────────────────────────────────────────────────────

export function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function formatDistance(meters: number | null): string {
  if (!meters) return "—";
  return meters >= 1000
    ? `${(meters / 1000).toFixed(2)} km`
    : `${Math.round(meters)} m`;
}

export function formatPace(meters: number | null, seconds: number | null): string {
  if (!meters || !seconds || meters < 100) return "—";
  const secPerKm = (seconds / meters) * 1000;
  const min = Math.floor(secPerKm / 60);
  const sec = Math.round(secPerKm % 60);
  return `${min}:${String(sec).padStart(2, "0")} /km`;
}

export function formatSpeed(meters: number | null, seconds: number | null): string {
  if (!meters || !seconds) return "—";
  return `${((meters / seconds) * 3.6).toFixed(1)} km/h`;
}

export function formatDate(iso: string, lang: Lang = "de"): string {
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diffDays === 0) return lang === "de" ? "Heute" : "Today";
  if (diffDays === 1) return lang === "de" ? "Gestern" : "Yesterday";
  if (diffDays < 7) return lang === "de" ? `vor ${diffDays} Tagen` : `${diffDays} days ago`;
  return d.toLocaleDateString(localeFor(lang), { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function sportLabel(type: string): { label: string; color: string; emoji: string } {
  const t = type.toLowerCase();
  if (t.includes("lauf") || t.includes("run")) return { label: "Run", color: "#3B82F6", emoji: "🏃" };
  if (t.includes("rad") || t.includes("ride") || t.includes("bike")) return { label: "Ride", color: "#FC4C02", emoji: "🚴" };
  if (t.includes("schwimm") || t.includes("swim")) return { label: "Swim", color: "#06B6D4", emoji: "🏊" };
  if (t.includes("ski") || t.includes("alpin")) return { label: "Ski", color: "#8B5CF6", emoji: "⛷️" };
  if (t.includes("wander") || t.includes("hike")) return { label: "Hike", color: "#10B981", emoji: "🥾" };
  return { label: type, color: "#6B7280", emoji: "🏋️" };
}

// Display names for Strava activity types (raw type string stays the filter key)
const SPORT_NAMES: Record<string, { de: string; en: string }> = {
  Run:             { de: "Laufen",          en: "Run" },
  TrailRun:        { de: "Traillauf",       en: "Trail Run" },
  VirtualRun:      { de: "Virtueller Lauf", en: "Virtual Run" },
  Ride:            { de: "Radfahren",       en: "Ride" },
  VirtualRide:     { de: "Virtuelle Fahrt", en: "Virtual Ride" },
  GravelRide:      { de: "Gravel",          en: "Gravel Ride" },
  MountainBikeRide:{ de: "Mountainbike",    en: "Mountain Bike" },
  EBikeRide:       { de: "E-Bike",          en: "E-Bike Ride" },
  Swim:            { de: "Schwimmen",       en: "Swim" },
  Walk:            { de: "Gehen",           en: "Walk" },
  Hike:            { de: "Wandern",         en: "Hike" },
  AlpineSki:       { de: "Ski alpin",       en: "Alpine Ski" },
  BackcountrySki:  { de: "Skitour",         en: "Backcountry Ski" },
  NordicSki:       { de: "Langlauf",        en: "Nordic Ski" },
  WeightTraining:  { de: "Krafttraining",   en: "Weight Training" },
  Workout:         { de: "Workout",         en: "Workout" },
  Yoga:            { de: "Yoga",            en: "Yoga" },
  Rowing:          { de: "Rudern",          en: "Rowing" },
};

export function sportName(type: string, lang: Lang = "de"): string {
  return SPORT_NAMES[type]?.[lang] ?? type;
}
