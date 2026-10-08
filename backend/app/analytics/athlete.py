"""Athlete physiology values shared by all analytics.

Single place to resolve them, so the API, recompute and the MCP server can't
drift apart (previously several endpoints hard-coded a max HR of 195).

A value set in .env pins it. Otherwise recompute auto-detects it and stores the
result in the app_state table (FTP lives in ftp_history), read back from here.
"""

import pandas as pd

from app.config import settings
from app.db.models import AppState
from app.db.session import get_db

MAX_HR_STATE_KEY = "max_hr_auto"
THRESHOLD_PACE_STATE_KEY = "threshold_pace_auto"
FALLBACK_MAX_HR = 190.0  # only until the first HR data has been analysed

_MAX_HR_WINDOW_S = 10                # HR must be held this long to count — filters sensor spikes
_PLAUSIBLE_HR = (100.0, 225.0)


def read_state(key: str) -> str | None:
    with get_db() as db:
        row = db.get(AppState, key)
        return row.value if row else None


def write_state(key: str, value: str) -> None:
    with get_db() as db:
        db.merge(AppState(key=key, value=value))


def max_hr_info() -> tuple[float, str]:
    """(max HR, source) — source is "manual" (.env), "auto" (detected) or "default" (no data yet)."""
    if settings.max_hr > 0:
        return float(settings.max_hr), "manual"
    stored = read_state(MAX_HR_STATE_KEY)
    return (float(stored), "auto") if stored else (FALLBACK_MAX_HR, "default")


def athlete_max_hr() -> float:
    """Max heart rate used for HR zones, Z2 detection and hrTSS."""
    return max_hr_info()[0]


def threshold_pace_info() -> tuple[float | None, str | None]:
    """(threshold pace in m/s, source "manual" | "auto") — (None, None) until one is detected."""
    if settings.threshold_pace_ms > 0:
        return settings.threshold_pace_ms, "manual"
    stored = read_state(THRESHOLD_PACE_STATE_KEY)
    return (float(stored), "auto") if stored else (None, None)


def sustained_max_hr(time_s: list[int], hr: list[float | None]) -> float | None:
    """Highest heart rate held for ≥ 10 s (max of the rolling 10 s minimum)."""
    s = pd.Series(hr, index=pd.to_timedelta(time_s, unit="s"), dtype=float)
    lo, hi = _PLAUSIBLE_HR
    s = s.where((s >= lo) & (s <= hi)).dropna()
    if len(s) < _MAX_HR_WINDOW_S:
        return None
    window = f"{_MAX_HR_WINDOW_S}s"
    held = s.rolling(window).min()
    # Only count windows that really span 10 s (not the start of a stream or a recording gap)
    t = pd.Series(s.index.total_seconds(), index=s.index)
    covered = (t - t.rolling(window).min()) >= _MAX_HR_WINDOW_S - 1
    held = held[covered]
    return float(held.max()) if not held.empty else None


def best_sustained_speed(
    time_s: list[int], velocity_ms: list[float | None], hr: list[float | None], window_s: int = 1200
) -> tuple[float, float | None] | None:
    """Best average speed over any `window_s` stretch of a run, plus the average HR in it.

    Used for threshold pace (best 20 min × 0.95, analogous to FTP). Pauses are
    left out of the average; a window needs ~80 % of its expected samples.
    """
    idx = pd.to_timedelta(time_s, unit="s")
    v = pd.Series(velocity_ms, index=idx, dtype=float)
    v = v.where(v > 0.5)  # standing / paused samples don't count as effort
    if v.notna().sum() < 10:
        return None
    dt = pd.Series(time_s, dtype=float).diff().median() or 1.0
    min_samples = max(10, int(0.8 * window_s / dt))

    window = f"{window_s}s"
    speed = v.rolling(window, min_periods=min_samples).mean()
    if speed.notna().sum() == 0:
        return None
    end = speed.idxmax()
    in_window = (idx > end - pd.Timedelta(seconds=window_s)) & (idx <= end)
    hr_s = pd.Series(hr, index=idx, dtype=float)[in_window]
    return float(speed.max()), (float(hr_s.mean()) if hr_s.notna().any() else None)
