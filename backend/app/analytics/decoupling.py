"""
Aerobic Decoupling — measures cardiac drift over an activity.

  < 5 %  → good aerobic base
  5–7 %  → acceptable
  > 7 %  → limited aerobic base / too hard for the conditions

Reference: Friel, "The Triathlete's Training Bible".
"""

from typing import Callable

import pandas as pd
from pydantic import BaseModel

from app.analytics.zones import AEROBIC_HR_HI, AEROBIC_HR_LO


class DecouplingResult(BaseModel):
    decoupling_pct: float    # positive = drift (fatigue)
    effort_col: str          # 'watts' | 'velocity_smooth'
    ratio_first: float
    ratio_second: float


def aerobic_decoupling(
    streams_df: pd.DataFrame,
    warmup_s: int = 600,
) -> DecouplingResult | None:
    """
    Calculate aerobic decoupling from a stream DataFrame.

    streams_df columns required: time_s, hr, and either watts or velocity_smooth.
    warmup_s: seconds to skip at the start (default 10 min).

    Returns None if insufficient data.
    """
    df = streams_df[streams_df["time_s"] >= warmup_s].copy()

    if len(df) < 120:   # need at least 2 min after warmup
        return None

    # Choose effort metric: prefer power for bikes, speed for runs
    effort_col = _pick_effort_col(df)
    if effort_col is None:
        return None

    if "hr" not in df.columns or df["hr"].notna().mean() < 0.5:
        return None

    mid = df["time_s"].median()
    first = df[df["time_s"] <= mid]
    second = df[df["time_s"] > mid]

    if len(first) < 30 or len(second) < 30:
        return None

    hr1 = first["hr"].mean()
    hr2 = second["hr"].mean()
    e1 = first[effort_col].mean()
    e2 = second[effort_col].mean()

    if hr1 <= 0 or hr2 <= 0 or e1 <= 0:
        return None

    ratio_first = e1 / hr1
    ratio_second = e2 / hr2
    decoupling = (ratio_first - ratio_second) / ratio_first * 100

    return DecouplingResult(
        decoupling_pct=round(decoupling, 2),
        effort_col=effort_col,
        ratio_first=round(ratio_first, 4),
        ratio_second=round(ratio_second, 4),
    )


def _pick_effort_col(df: pd.DataFrame) -> str | None:
    for col in ("watts", "velocity_smooth"):
        if col in df.columns and df[col].notna().mean() >= 0.5:
            return col
    return None


class DecouplingTimelinePoint(BaseModel):
    date: str               # ISO YYYY-MM-DD
    activity_id: int
    activity_name: str
    decoupling_pct: float
    duration_min: float
    sport: str


def decoupling_timeline(
    activities_df: pd.DataFrame,
    streams_getter: Callable[[int], pd.DataFrame | None],
    hrmax: float,
    min_duration_min: float = 45.0,
    lookback_days: int = 180,
) -> list[DecouplingTimelinePoint]:
    """
    Compute a decoupling timeline for aerobic activities ≥45 min over the last 6 months.

    activities_df must have: id, start_time, moving_time_s, avg_hr, type, name.
    streams_getter: callable(activity_id) -> DataFrame with time_s, hr, watts/velocity_smooth.
    Only includes activities where avg_hr is in Z2–Z3 (60–80% HRmax).
    """
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=lookback_days)
    z2_lo = hrmax * AEROBIC_HR_LO
    z2_hi = hrmax * AEROBIC_HR_HI
    min_duration_s = min_duration_min * 60

    df = activities_df[
        (activities_df["moving_time_s"] >= min_duration_s)
        & (pd.to_datetime(activities_df["start_time"], utc=True) >= cutoff)
        & activities_df["avg_hr"].between(z2_lo, z2_hi)
    ].copy()

    df = df.sort_values("start_time")

    results: list[DecouplingTimelinePoint] = []
    for _, row in df.iterrows():
        streams = streams_getter(int(row["id"]))
        if streams is None:
            continue
        result = aerobic_decoupling(streams)
        if result is None:
            continue
        results.append(DecouplingTimelinePoint(
            date=pd.to_datetime(row["start_time"]).date().isoformat(),
            activity_id=int(row["id"]),
            activity_name=str(row.get("name", "")),
            decoupling_pct=result.decoupling_pct,
            duration_min=round(row["moving_time_s"] / 60, 1),
            sport=str(row.get("type", "")),
        ))

    return results
