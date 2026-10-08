"""Small shared helpers for shaping MCP tool output."""

import pandas as pd


def sport_label(type_str: str | None) -> str:
    """Map a raw Strava activity type (German or English) to a canonical sport label."""
    t = (type_str or "").lower()
    if any(k in t for k in ("lauf", "run")):
        return "Run"
    if any(k in t for k in ("rad", "ride", "bike", "velo")):
        return "Ride"
    if any(k in t for k in ("schwimm", "swim")):
        return "Swim"
    return "Other"


def format_pace(sec_per_km: float) -> str:
    """e.g. 270.3 -> '4:30'"""
    total = int(round(sec_per_km))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def hr_drift_pct(df: pd.DataFrame, warmup_s: int = 600) -> float | None:
    """% HR increase from first half to second half (after warmup). Positive = drift."""
    trimmed = df[df["time_s"] >= warmup_s]
    if "hr" not in trimmed.columns or trimmed["hr"].notna().sum() < 60:
        return None
    mid = trimmed["time_s"].median()
    hr1 = trimmed.loc[trimmed["time_s"] <= mid, "hr"].mean()
    hr2 = trimmed.loc[trimmed["time_s"] > mid, "hr"].mean()
    if not hr1 or hr1 <= 0:
        return None
    return round((hr2 - hr1) / hr1 * 100, 2)
