"""
Effective Pace — Z2–Z3 pace trend over time.

Tracks how pace at a given HR (Zone 2) improves as aerobic fitness builds.
Improvement in Z2–Z3 pace at the same HR = clearest evidence of aerobic adaptation.
"""

import math
from typing import Literal

import pandas as pd
from pydantic import BaseModel

from app.analytics.zones import AEROBIC_HR_HI, AEROBIC_HR_LO
from app.i18n import Lang, tr

DistanceCategory = Literal["5-10km", "10-15km", "15km+"]


class Z2PacePoint(BaseModel):
    date: str                    # ISO YYYY-MM-DD
    activity_id: int
    activity_name: str
    pace_sec_per_km: float       # avg pace over the activity (s/km)
    avg_hr: float
    distance_km: float
    distance_category: DistanceCategory


class Z2PaceTimeline(BaseModel):
    points: list[Z2PacePoint]
    trend_slope_sec_per_km_per_month: float | None   # negative = improving
    interpretation: str


def _distance_category(distance_km: float) -> DistanceCategory:
    if distance_km < 10:
        return "5-10km"
    if distance_km < 15:
        return "10-15km"
    return "15km+"


def z2_pace_timeline(
    activities_df: pd.DataFrame,
    hrmax: float,
    lookback_days: int = 180,
    min_distance_km: float = 4.0,
    lang: Lang = "de",
) -> Z2PaceTimeline:
    """
    Build a timeline of Z2–Z3 run pace for the last N months.

    activities_df must have: id, start_time, type, distance_m, moving_time_s, avg_hr, name.
    Only includes runs where avg_hr is in Z2–Z3 (60–80% HRmax) and distance ≥ min_distance_km.
    """
    z2_lo = hrmax * AEROBIC_HR_LO
    z2_hi = hrmax * AEROBIC_HR_HI
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=lookback_days)

    df = activities_df[
        activities_df["type"].str.lower().str.contains("run|lauf", regex=True, na=False)
        & (activities_df["distance_m"] >= min_distance_km * 1000)
        & (activities_df["moving_time_s"] > 0)
        & activities_df["avg_hr"].between(z2_lo, z2_hi)
        & (pd.to_datetime(activities_df["start_time"], utc=True) >= cutoff)
    ].copy()

    df = df.sort_values("start_time")

    points: list[Z2PacePoint] = []
    for _, row in df.iterrows():
        dist_km = row["distance_m"] / 1000
        pace_s_km = row["moving_time_s"] / dist_km
        points.append(Z2PacePoint(
            date=pd.to_datetime(row["start_time"]).date().isoformat(),
            activity_id=int(row["id"]),
            activity_name=str(row.get("name", "")),
            pace_sec_per_km=round(pace_s_km, 1),
            avg_hr=round(float(row["avg_hr"]), 1),
            distance_km=round(dist_km, 2),
            distance_category=_distance_category(dist_km),
        ))

    if len(points) < 2:
        return Z2PaceTimeline(
            points=points,
            trend_slope_sec_per_km_per_month=None,
            interpretation=tr(
                lang,
                "Zu wenig Z2–Z3-Läufe für eine Trendanalyse.",
                "Too few Z2–Z3 runs for a trend analysis.",
            ),
        )

    # Linear regression on pace vs. days-since-first
    first_date = pd.to_datetime(points[0].date)
    x = [(pd.to_datetime(p.date) - first_date).days for p in points]
    y = [p.pace_sec_per_km for p in points]

    n = len(x)
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    slope_per_day = ss_xy / ss_xx if ss_xx > 0 else 0.0
    slope_per_month = slope_per_day * 30.44

    # Interpretation
    total_change = slope_per_day * max(x)
    months = lookback_days // 30
    if total_change < -10:
        interp = tr(
            lang,
            f"Z2–Z3-Pace hat sich um {abs(total_change):.0f} s/km über {months} Monate "
            f"verbessert — deutliche aerobe Adaptation.",
            f"Z2–Z3 pace improved by {abs(total_change):.0f} s/km over {months} months "
            f"— clear aerobic adaptation.",
        )
    elif total_change < 0:
        interp = tr(
            lang,
            f"Leichte Verbesserung der Z2–Z3-Pace ({abs(total_change):.0f} s/km). "
            f"Mehr Z2–Z3-Volumen für schnellere Entwicklung.",
            f"Slight improvement in Z2–Z3 pace ({abs(total_change):.0f} s/km). "
            f"More Z2–Z3 volume for faster progress.",
        )
    elif total_change < 5:
        interp = tr(
            lang,
            "Z2–Z3-Pace stagniert. Aerobe Basis bleibt konstant.",
            "Z2–Z3 pace is stagnating. Aerobic base remains steady.",
        )
    else:
        interp = tr(
            lang,
            f"Z2–Z3-Pace hat sich um {total_change:.0f} s/km verschlechtert — "
            f"mögliche Überbelastung oder zu viele Läufe außerhalb Z2–Z3.",
            f"Z2–Z3 pace worsened by {total_change:.0f} s/km — "
            f"possible overload or too many runs outside Z2–Z3.",
        )

    return Z2PaceTimeline(
        points=points,
        trend_slope_sec_per_km_per_month=round(slope_per_month, 2),
        interpretation=interp,
    )
