"""Pydantic response models for MCP tool outputs."""

import datetime as dt
from datetime import date
from typing import Literal

from pydantic import BaseModel


class FtpStatus(BaseModel):
    value_w: int | None  # None if no detection succeeded
    source: Literal["auto", "manual", "none"]
    last_updated: date | None
    age_days: int | None
    is_stale: bool  # True if > 60 days old or no FTP known
    diagnostic: str | None  # if value_w is None: why detection failed


class TrainingState(BaseModel):
    ctl: float  # 42-day fitness
    atl: float  # 7-day fatigue
    tsb: float  # form (CTL - ATL)
    form_zone: Literal["burnout", "high_fatigue", "optimal", "fresh", "detrained"]
    form_interpretation: str  # full sentence, same as dashboard
    ramp_rate_per_week: float | None  # CTL change per week (last 4w)
    ramp_rate_classification: Literal["rapid_build", "building", "stagnant", "detraining", "unknown"]
    weekly_tss: int
    weekly_hours: float
    weekly_volume_vs_4w_avg_pct: float  # +/- compared to 4-week average
    last_activity_date: date | None
    ftp: FtpStatus


# ── Recent form ────────────────────────────────────────────────────────────

class WeekSummary(BaseModel):
    week_start: date
    tss: int
    hours: float
    distance_km: float
    activities_count: int
    sports: dict[str, int]  # {"Run": 3, "Ride": 2}


class KeyWorkout(BaseModel):
    activity_id: int
    date: date
    sport: str
    distance_km: float
    duration_min: float
    tss: int
    summary: str  # one-liner: "Long run, decoupling 3.1%"


class RecentForm(BaseModel):
    weeks_covered: int
    volume_by_week: list[WeekSummary]
    key_workouts: list[KeyWorkout]  # 3-5 highest-quality sessions
    decoupling_trend_pct: float | None  # change vs 8w ago, negative = better
    decoupling_recent_avg_pct: float | None
    pr_efforts: list[str]  # human-readable list


# ── Activity summaries ────────────────────────────────────────────────────

class ActivitySummary(BaseModel):
    id: int
    date: date
    sport: str
    name: str
    distance_km: float
    duration_min: float
    tss: int
    summary_line: str  # "5k tempo · 4:18/km · TSS 62"


# ── Workout analysis ──────────────────────────────────────────────────────

class WorkoutAnalysis(BaseModel):
    activity_id: int
    date: date
    sport: str
    name: str
    distance_km: float
    duration_min: float
    elevation_gain_m: int

    # Intensity
    avg_hr: int | None
    max_hr: int | None
    avg_power_w: int | None  # bike only
    np_w: int | None  # bike only
    avg_pace_per_km: str | None  # run only, "4:32"
    intensity_factor: float | None
    tss: int

    # Aerobic quality
    decoupling_pct: float | None  # None if duration < 45min or not aerobic
    hr_drift_pct: float | None

    # Zones (minutes)
    hr_zones_min: dict[str, float] | None  # {"Z1": 12.5, "Z2": 38.0, ...}
    power_zones_min: dict[str, float] | None  # bike only

    # Anomalies
    split_anomalies: list[str]  # human-readable descriptions

    # Narrative
    interpretation: str  # 2-3 sentences synthesizing the above


class ActivityStreams(BaseModel):
    activity_id: int
    time_s: list[int]
    hr: list[float | None]
    power_w: list[float | None]
    pace_per_km: list[float | None]  # seconds per km
    altitude_m: list[float | None]


# ── Predictions ────────────────────────────────────────────────────────────

class RacePrediction(BaseModel):
    distance_m: int
    predicted_time_s: int | None
    ci_lower_s: int | None
    ci_upper_s: int | None
    confidence: Literal["high", "medium", "low", "no_data"]
    basis: str  # "5 runs >=3km in 8 weeks, fastest 4:21/km"
    target_assessment: str | None  # if target_date given


class PowerPoint(BaseModel):
    duration_s: int
    power_w: int
    activity_id: int | None  # only on all-time bests
    date: date | None


class PowerCurve(BaseModel):
    all_time_best: list[PowerPoint]
    last_6_weeks_best: list[PowerPoint]
    cp_w: int | None
    w_prime_kj: float | None
    model_fit_quality: Literal["good", "moderate", "poor", "insufficient_data"]
    interpretation: str  # narrative based on CP and W'


# ── Training plan ──────────────────────────────────────────────────────────

WorkoutStatus = Literal["upcoming", "completed", "missed", "today"]


class WorkoutStep(BaseModel):
    type: str  # warmup | interval | recovery | cooldown | steady | rest
    label: str
    description: str | None = None
    distance_m: float | None = None
    duration_min: float | None = None
    reps: int | None = None
    target_pace_min_km: float | None = None
    target_hr_zone: str | None = None
    target_power_pct_ftp: float | None = None


class PlannedWorkoutSummary(BaseModel):
    id: int
    date: date
    sport: str
    title: str
    estimated_tss: int | None
    estimated_duration_min: float | None
    completed_activity_id: int | None
    status: WorkoutStatus


class PlannedWorkout(BaseModel):
    id: int
    date: date
    sport: str
    title: str
    description: str | None
    duration_min: int | None
    distance_m: float | None
    tss_planned: float | None
    steps: list[WorkoutStep]
    notes: str | None
    completed_activity_id: int | None
    status: WorkoutStatus


Sport = Literal["Run", "Ride", "Swim", "Other"]


class NewWorkout(BaseModel):
    date: date
    sport: Sport
    title: str
    steps: list[WorkoutStep]
    description: str | None = None
    duration_min: int | None = None
    distance_m: float | None = None
    tss_planned: float | None = None
    notes: str | None = None


class WorkoutUpdate(BaseModel):
    id: int
    date: dt.date | None = None
    title: str | None = None
    sport: Sport | None = None
    steps: list[WorkoutStep] | None = None
    description: str | None = None
    duration_min: int | None = None
    distance_m: float | None = None
    tss_planned: float | None = None
    notes: str | None = None


class BulkResult(BaseModel):
    created_ids: list[int]
    count: int


class WeekAssessment(BaseModel):
    planned_tss_total: int
    planned_workouts_count: int
    current_tsb: float
    current_form_zone: str
    warnings: list[str]  # human-readable concerns
    observations: list[str]  # neutral observations
