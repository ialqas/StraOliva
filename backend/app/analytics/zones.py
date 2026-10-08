"""
Time-in-Zone analytics.

Power zones: Coggan % of FTP — Z1–Z7.
HR zones:    % of HRmax     — Z1–Z5.
Weekly aggregation for stacked-bar charts.
"""

from collections import defaultdict
from typing import Callable

import pandas as pd
from pydantic import BaseModel

# ── Zone definitions ──────────────────────────────────────────────────────────

# Coggan power zones (% of FTP), upper bound exclusive (Z7 = open-ended)
POWER_ZONE_BOUNDS: list[tuple[str, float, float]] = [
    ("Z1", 0.0,  0.55),
    ("Z2", 0.55, 0.75),
    ("Z3", 0.75, 0.90),
    ("Z4", 0.90, 1.05),
    ("Z5", 1.05, 1.20),
    ("Z6", 1.20, 1.50),
    ("Z7", 1.50, 9.99),
]

# HR zones (% of HRmax) — 5-zone model: 50–60 / 60–70 / 70–80 / 80–90 / 90–100 %.
# Z1 also takes everything below 50 % and Z5 anything above max HR, so no time is dropped.
HR_ZONE_BOUNDS: list[tuple[str, float, float]] = [
    ("Z1", 0.00, 0.60),
    ("Z2", 0.60, 0.70),
    ("Z3", 0.70, 0.80),
    ("Z4", 0.80, 0.90),
    ("Z5", 0.90, 9.99),
]

# Aerobic band Z2–Z3 as fractions of HRmax — used to pick aerobic activities (decoupling, effective pace).
# Z2 alone (60–70 %) is narrower than the avg HR of most easy runs, so Z3 is included.
_BOUNDS = {z: (lo, hi) for z, lo, hi in HR_ZONE_BOUNDS}
AEROBIC_HR_LO, AEROBIC_HR_HI = _BOUNDS["Z2"][0], _BOUNDS["Z3"][1]

ZONE_COLORS: dict[str, str] = {
    "Z1": "#9CA3AF",  # gray
    "Z2": "#60A5FA",  # blue
    "Z3": "#34D399",  # green
    "Z4": "#FBBF24",  # amber
    "Z5": "#F87171",  # red
    "Z6": "#A78BFA",  # purple
    "Z7": "#F43F5E",  # rose
}


class WeeklyZoneRow(BaseModel):
    week: str                        # ISO week start YYYY-MM-DD (Monday)
    zones: dict[str, float]         # zone label → hours


def power_zones_time(streams_df: pd.DataFrame, ftp_w: float) -> dict[str, float]:
    """
    Compute seconds per power zone for a single activity stream.
    streams_df must have a 'watts' column (1-Hz samples).
    Returns {zone_label: seconds}.
    """
    result: dict[str, float] = {z: 0.0 for z, _, _ in POWER_ZONE_BOUNDS}
    if "watts" not in streams_df.columns or ftp_w <= 0:
        return result
    watts = streams_df["watts"].fillna(0)
    for zone, lo_pct, hi_pct in POWER_ZONE_BOUNDS:
        lo = ftp_w * lo_pct
        hi = ftp_w * hi_pct
        result[zone] = float(((watts >= lo) & (watts < hi)).sum())
    return result


def hr_zones_time(streams_df: pd.DataFrame, hrmax: float) -> dict[str, float]:
    """
    Compute seconds per HR zone for a single activity stream.
    streams_df must have an 'hr' column (1-Hz samples).
    Returns {zone_label: seconds}.
    """
    result: dict[str, float] = {z: 0.0 for z, _, _ in HR_ZONE_BOUNDS}
    if "hr" not in streams_df.columns or hrmax <= 0:
        return result
    hr = streams_df["hr"].fillna(0)
    for zone, lo_pct, hi_pct in HR_ZONE_BOUNDS:
        lo = hrmax * lo_pct
        hi = hrmax * hi_pct
        result[zone] = float(((hr >= lo) & (hr < hi)).sum())
    return result


def weekly_time_in_zone(
    activities_df: pd.DataFrame,
    streams_getter: Callable[[int], pd.DataFrame | None],
    sport_filter: str | None,          # "run", "bike", or None (all)
    ftp_w: float | None,
    hrmax: float,
    lookback_weeks: int = 12,
) -> list[WeeklyZoneRow]:
    """
    Aggregate time-in-zone by ISO week for the last N weeks.

    activities_df must have: id, start_time, type.
    sport_filter: "run" → HR zones only; "bike" → power zones (fallback to HR);
                  None → HR zones for all.
    """
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(weeks=lookback_weeks)

    df = activities_df[
        pd.to_datetime(activities_df["start_time"], utc=True) >= cutoff
    ].copy()

    if sport_filter == "run":
        df = df[df["type"].str.lower().str.contains("run|lauf", regex=True, na=False)]
    elif sport_filter == "bike":
        df = df[df["type"].str.lower().str.contains("ride|bike|velo", regex=True, na=False)]

    # Determine zone scheme
    use_power = sport_filter == "bike" and ftp_w and ftp_w > 0
    zone_labels = [z for z, _, _ in (POWER_ZONE_BOUNDS if use_power else HR_ZONE_BOUNDS)]

    # Aggregate by week
    weekly: dict[str, dict[str, float]] = defaultdict(lambda: {z: 0.0 for z in zone_labels})

    for _, row in df.iterrows():
        streams = streams_getter(int(row["id"]))
        if streams is None:
            continue

        if use_power:
            zone_secs = power_zones_time(streams, ftp_w)  # type: ignore[arg-type]
        else:
            zone_secs = hr_zones_time(streams, hrmax)

        act_ts = pd.to_datetime(row["start_time"], utc=True)
        week_start = (act_ts - pd.Timedelta(days=act_ts.weekday())).date().isoformat()

        for z, secs in zone_secs.items():
            if z in weekly[week_start]:
                weekly[week_start][z] += secs

    # Fill missing weeks with zeros
    all_weeks = pd.date_range(
        end=pd.Timestamp.now().normalize() - pd.Timedelta(days=pd.Timestamp.now().weekday()),
        periods=lookback_weeks,
        freq="W-MON",
    )
    for w in all_weeks:
        key = w.date().isoformat()
        if key not in weekly:
            weekly[key] = {z: 0.0 for z in zone_labels}

    return [
        WeeklyZoneRow(
            week=w,
            zones={z: round(secs / 3600, 3) for z, secs in zones.items()},
        )
        for w, zones in sorted(weekly.items())
    ]
