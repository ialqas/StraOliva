"""
Power-based analytics: Power-Duration Curve, FTP estimation, and diagnostics.
All functions are pure — input is pandas Series/DataFrames.
"""

from datetime import datetime, timezone

import pandas as pd
from pydantic import BaseModel

# Standard durations for the power-duration curve (seconds)
PDC_DURATIONS = [1, 5, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600]


class PowerDurationPoint(BaseModel):
    duration_s: int
    power_w: float


class PowerDurationCurve(BaseModel):
    points: list[PowerDurationPoint]
    ftp_estimate_w: float | None   # best 20-min × 0.95


def best_power_for_duration(watts: pd.Series, duration_s: int) -> float | None:
    """Rolling mean max over a given window on a 1-Hz power stream."""
    filled = watts.fillna(0)
    if len(filled) < duration_s:
        return None
    return float(filled.rolling(duration_s, min_periods=duration_s).mean().max())


def power_duration_curve(watts: pd.Series) -> PowerDurationCurve:
    """
    Compute the power-duration curve for a single activity stream.
    watts: 1-Hz Series of power values.
    """
    points = []
    for dur in PDC_DURATIONS:
        p = best_power_for_duration(watts, dur)
        if p is not None and p > 0:
            points.append(PowerDurationPoint(duration_s=dur, power_w=round(p, 1)))

    best_20min = best_power_for_duration(watts, 1200)
    ftp = round(best_20min * 0.95, 1) if best_20min else None

    return PowerDurationCurve(points=points, ftp_estimate_w=ftp)


def all_time_pdc(streams_per_activity: list[pd.Series]) -> PowerDurationCurve:
    """
    Compute the all-time power-duration curve across multiple activity streams.
    streams_per_activity: list of 1-Hz watts Series, one per bike activity.
    """
    bests: dict[int, float] = {d: 0.0 for d in PDC_DURATIONS}

    for watts in streams_per_activity:
        for dur in PDC_DURATIONS:
            p = best_power_for_duration(watts, dur)
            if p is not None and p > bests[dur]:
                bests[dur] = p

    points = [
        PowerDurationPoint(duration_s=dur, power_w=round(p, 1))
        for dur, p in bests.items()
        if p > 0
    ]

    best_20min = bests.get(1200)
    ftp = round(best_20min * 0.95, 1) if best_20min and best_20min > 0 else None

    return PowerDurationCurve(points=points, ftp_estimate_w=ftp)


def estimate_ftp_from_activities(watts_series_list: list[pd.Series]) -> float | None:
    """
    Auto-estimate FTP as best 20-min average power × 0.95 across all bike activities.
    """
    best_20min = 0.0
    for watts in watts_series_list:
        p = best_power_for_duration(watts, 1200)
        if p and p > best_20min:
            best_20min = p
    return round(best_20min * 0.95, 1) if best_20min > 0 else None


class FTPDiagnostics(BaseModel):
    detected: bool
    ftp_w: float | None
    detection_date: str | None        # ISO date of the effort used
    reason: str                       # human-readable explanation
    last_20min_effort_days_ago: int | None


def ftp_detection_diagnostics(
    activities_df: pd.DataFrame,
    watts_series_by_id: dict[int, pd.Series],
    lookback_days: int = 90,
    min_intensity_factor: float = 0.85,
) -> FTPDiagnostics:
    """
    Explain why FTP auto-detection succeeded or failed.

    activities_df must have: id, start_time, type (Ride), moving_time_s.
    watts_series_by_id: {activity_id: 1-Hz watts Series}.
    """
    now = datetime.now(timezone.utc)
    cutoff = pd.Timestamp(now) - pd.Timedelta(days=lookback_days)

    rides = activities_df[
        activities_df["type"].str.lower().str.contains("ride|bike|velo", regex=True, na=False)
    ].copy()

    if rides.empty:
        return FTPDiagnostics(
            detected=False, ftp_w=None, detection_date=None,
            reason="Keine Rad-Aktivitäten gefunden.",
            last_20min_effort_days_ago=None,
        )

    # Find the last 20-min effort across all rides (not just recent window)
    best_all_time = 0.0
    best_all_date: str | None = None
    best_all_days_ago: int | None = None

    for _, row in rides.iterrows():
        watts = watts_series_by_id.get(int(row["id"]))
        if watts is None:
            continue
        p20 = best_power_for_duration(watts, 1200)
        if p20 and p20 > best_all_time:
            best_all_time = p20
            act_date = pd.to_datetime(row["start_time"])
            best_all_date = act_date.date().isoformat()
            best_all_days_ago = (pd.Timestamp(now) - pd.to_datetime(row["start_time"], utc=True)).days

    # Check recent window
    recent_rides = rides[pd.to_datetime(rides["start_time"], utc=True) >= cutoff]
    best_recent = 0.0
    best_recent_date: str | None = None

    for _, row in recent_rides.iterrows():
        watts = watts_series_by_id.get(int(row["id"]))
        if watts is None:
            continue
        p20 = best_power_for_duration(watts, 1200)
        if p20 and p20 > best_recent:
            best_recent = p20
            best_recent_date = pd.to_datetime(row["start_time"]).date().isoformat()

    if best_recent > 0:
        ftp = round(best_recent * 0.95, 1)
        return FTPDiagnostics(
            detected=True,
            ftp_w=ftp,
            detection_date=best_recent_date,
            reason=f"Auto-detected aus bestem 20-min-Effort ({round(best_recent)} W × 0.95).",
            last_20min_effort_days_ago=best_all_days_ago,
        )

    # Not enough recent data — explain why
    if best_all_days_ago is not None:
        reason = (
            f"FTP-Detection fehlgeschlagen — kein 20-min-Effort mit IF > {min_intensity_factor} "
            f"in den letzten {lookback_days} Tagen. "
            f"Letzter 20-min-Effort: {best_all_days_ago} Tage her."
        )
    else:
        reason = "FTP-Detection fehlgeschlagen — keine Power-Daten in Rad-Aktivitäten gefunden."

    return FTPDiagnostics(
        detected=False,
        ftp_w=None,
        detection_date=None,
        reason=reason,
        last_20min_effort_days_ago=best_all_days_ago,
    )
