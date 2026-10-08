"""
Race time predictions.

Primary model: Riegel formula  T2 = T1 × (D2/D1)^1.06
Confidence tiers based on count and proximity of base efforts to target distance.
1k excluded — Riegel is unreliable at anaerobic distances.
"""

import math
from typing import Literal

import pandas as pd
from pydantic import BaseModel

from app.i18n import Lang, tr

# Standard race distances — no 1k (Riegel unsuitable for anaerobic distances)
DISTANCES: dict[str, int] = {
    "5k":       5_000,
    "10k":      10_000,
    "HM":       21_097,
    "Marathon": 42_195,
}

# Longest run required in the lookback window before we attempt to predict
_MIN_LONG_RUN_M: dict[str, int] = {
    "HM":       15_000,
    "Marathon": 25_000,
}

ConfidenceTier = Literal["high", "medium", "low", "no_data"]

_TIER_LABEL: dict[ConfidenceTier, str] = {
    "high":    "High",
    "medium":  "Medium",
    "low":     "Low",
    "no_data": "Nicht genug Daten",
}


class RacePrediction(BaseModel):
    distance_label: str
    distance_m: float
    predicted_s: float | None
    ci_lower_s: float | None
    ci_upper_s: float | None
    confidence: ConfidenceTier
    basis_description: str
    num_efforts: int


def riegel(t1_s: float, d1_m: float, d2_m: float) -> float:
    """T2 = T1 × (D2 / D1)^1.06"""
    if d1_m <= 0 or d2_m <= 0 or t1_s <= 0:
        raise ValueError("All arguments must be positive")
    return t1_s * (d2_m / d1_m) ** 1.06


def _tier(num_in_range: int, max_base_m: float, target_m: float) -> ConfidenceTier:
    if num_in_range >= 3:
        return "high"
    if num_in_range >= 1:
        return "medium"
    # Fell back to wider filter — judge by extrapolation distance
    ratio = target_m / max_base_m if max_base_m > 0 else 99.0
    return "medium" if ratio < 2.0 else "low"


def predict_race(
    activities_df: pd.DataFrame,
    target_distance_m: float,
    target_label: str,
    lookback_weeks: int = 8,
    lang: Lang = "de",
) -> RacePrediction:
    """
    Predict race time at target_distance_m using recent best efforts.

    activities_df must have: start_time, distance_m, moving_time_s, type.
    Always returns a RacePrediction (confidence="no_data" when insufficient data).
    """
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(weeks=lookback_weeks)

    recent_runs = activities_df[
        activities_df["type"].str.lower().str.contains("run|lauf", regex=True, na=False)
        & (activities_df["moving_time_s"] > 0)
        & (pd.to_datetime(activities_df["start_time"], utc=True) >= cutoff)
    ]

    # Guard: HM and Marathon need a minimum long run in the window
    if target_label in _MIN_LONG_RUN_M:
        min_km = _MIN_LONG_RUN_M[target_label]
        longest_m = int(recent_runs["distance_m"].max()) if not recent_runs.empty else 0
        if longest_m < min_km:
            return RacePrediction(
                distance_label=target_label,
                distance_m=target_distance_m,
                predicted_s=None,
                ci_lower_s=None,
                ci_upper_s=None,
                confidence="no_data",
                basis_description=tr(
                    lang,
                    f"Längster Lauf {longest_m / 1000:.0f} km · mind. {min_km / 1000:.0f} km nötig",
                    f"Longest run {longest_m / 1000:.0f} km · at least {min_km / 1000:.0f} km needed",
                ),
                num_efforts=0,
            )

    # Primary window: efforts within [0.5×, 2×] target distance
    lo = target_distance_m * 0.5
    hi = target_distance_m * 2.0
    df = recent_runs[
        (recent_runs["distance_m"] >= lo) & (recent_runs["distance_m"] <= hi)
    ].copy()
    in_range_count = len(df)

    # Fallback: any recent run ≥ 3 km
    if df.empty:
        df = recent_runs[recent_runs["distance_m"] >= 3_000].copy()

    if df.empty:
        return RacePrediction(
            distance_label=target_label,
            distance_m=target_distance_m,
            predicted_s=None,
            ci_lower_s=None,
            ci_upper_s=None,
            confidence="no_data",
            basis_description=tr(
                lang,
                f"Keine Laufdaten in den letzten {lookback_weeks} Wochen",
                f"No running data in the last {lookback_weeks} weeks",
            ),
            num_efforts=0,
        )

    df["predicted_s"] = df.apply(
        lambda r: riegel(r["moving_time_s"], r["distance_m"], target_distance_m),
        axis=1,
    )
    df["days_ago"] = (
        pd.Timestamp.now(tz="UTC") - pd.to_datetime(df["start_time"], utc=True)
    ).dt.days
    df["weight"] = df["days_ago"].apply(lambda d: math.exp(-d / 30))

    weighted_mean = (df["predicted_s"] * df["weight"]).sum() / df["weight"].sum()

    # CI: std dev of predictions + extrapolation penalty for distant base efforts
    std = df["predicted_s"].std() if len(df) > 1 else weighted_mean * 0.03
    max_base_m = df["distance_m"].max()
    extrap_ratio = max(0.0, target_distance_m / max_base_m - 1.0) if max_base_m > 0 else 1.0
    extrap_penalty = weighted_mean * extrap_ratio * 0.05
    ci_half = std + extrap_penalty

    tier = _tier(in_range_count, max_base_m, target_distance_m)

    best = df.loc[df["predicted_s"].idxmin()]
    best_ts = pd.to_datetime(best["start_time"])
    best_km = best["distance_m"] / 1000
    basis = tr(
        lang,
        f"{len(df)} Läufe ≥{lo / 1000:.0f} km · bester {best_km:.1f} km am {best_ts.day}.{best_ts.month}.",
        f"{len(df)} runs ≥{lo / 1000:.0f} km · best {best_km:.1f} km on {best_ts.strftime('%b')} {best_ts.day}",
    )

    return RacePrediction(
        distance_label=target_label,
        distance_m=target_distance_m,
        predicted_s=round(weighted_mean, 1),
        ci_lower_s=round(max(1.0, weighted_mean - ci_half), 1),
        ci_upper_s=round(weighted_mean + ci_half, 1),
        confidence=tier,
        basis_description=basis,
        num_efforts=len(df),
    )


def predict_all(
    activities_df: pd.DataFrame,
    lookback_weeks: int = 8,
) -> list[RacePrediction]:
    return [
        predict_race(activities_df, dist, label, lookback_weeks)
        for label, dist in DISTANCES.items()
    ]


def format_time(seconds: float) -> str:
    """Convert seconds to H:MM:SS or M:SS string."""
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
