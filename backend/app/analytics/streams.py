"""Stream-level computations — all pure functions on pandas Series/DataFrames."""

import numpy as np
import pandas as pd


def normalized_power(watts: pd.Series) -> float | None:
    """
    Coggan Normalized Power from a 1-Hz power stream.
    Requires at least 30 seconds of data.
    """
    clean = watts.dropna()
    if len(clean) < 30:
        return None
    rolling = watts.fillna(0).rolling(30, min_periods=1).mean()
    return float((rolling**4).mean() ** 0.25)


def best_avg_power(watts: pd.Series, duration_s: int) -> float | None:
    """Rolling mean max over a given window (seconds, assuming 1-Hz data)."""
    clean = watts.dropna()
    if len(clean) < duration_s:
        return None
    return float(watts.fillna(0).rolling(duration_s, min_periods=duration_s).mean().max())


def grade_adjusted_pace(
    velocity_ms: pd.Series,
    altitude_m: pd.Series,
    time_s: pd.Series,
) -> pd.Series:
    """
    Normalized Grade Pace (NGP) — adjusts running pace for elevation.
    Uses Strava's grade-adjustment curve (simplified polynomial approximation).
    Returns NGP in m/s (same shape as velocity_ms).
    """
    dt = time_s.diff().fillna(1).clip(lower=0.5)
    dz = altitude_m.diff().fillna(0)
    grade = (dz / (velocity_ms * dt)).fillna(0).clip(-0.45, 0.45)

    # Adjustment factor from empirical running economy data (simplified Minetti)
    factor = (
        1
        + 4.5 * grade
        - 3.5 * grade**2
        - 7.0 * grade**3
        + 4.5 * grade**4
    )
    return velocity_ms * factor.clip(0.5, 2.0)


def avg_speed_excluding_stops(
    velocity_ms: pd.Series,
    min_speed_ms: float = 0.5,
) -> float | None:
    """Moving average speed, ignoring stopped seconds."""
    moving = velocity_ms[velocity_ms >= min_speed_ms]
    return float(moving.mean()) if len(moving) > 0 else None
