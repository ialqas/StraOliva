"""
TSS (Training Stress Score) calculations.

Three methods in priority order:
  1. power  — bike with Normalized Power + FTP
  2. pace   — run with average/normalized pace + threshold pace
  3. hr     — any activity with average HR (TRIMP-based fallback)
"""

import math

from pydantic import BaseModel


class TSSResult(BaseModel):
    tss: float
    method: str          # 'power' | 'pace' | 'hr'
    intensity_factor: float | None = None


# ── Bike TSS (Coggan) ─────────────────────────────────────────────────────────

def bike_tss(duration_s: float, np_w: float, ftp_w: float) -> TSSResult:
    """
    TSS = (duration_s × NP × IF) / (FTP × 3600) × 100
    IF  = NP / FTP
    """
    if ftp_w <= 0:
        raise ValueError("FTP must be > 0")
    if np_w <= 0:
        raise ValueError("NP must be > 0")
    if_val = np_w / ftp_w
    tss = (duration_s * np_w * if_val) / (ftp_w * 3600) * 100
    return TSSResult(tss=round(tss, 1), method="power", intensity_factor=round(if_val, 3))


# ── Running rTSS ──────────────────────────────────────────────────────────────

def run_tss(duration_s: float, avg_pace_ms: float, threshold_pace_ms: float) -> TSSResult:
    """
    rTSS = (duration_s × NGP² / threshold_pace²) / 3600 × 100
    NGP and threshold_pace in m/s — higher = faster.
    """
    if threshold_pace_ms <= 0:
        raise ValueError("Threshold pace must be > 0")
    if avg_pace_ms <= 0:
        raise ValueError("Average pace must be > 0")
    if_val = avg_pace_ms / threshold_pace_ms
    tss = (duration_s * avg_pace_ms**2 / threshold_pace_ms**2) / 3600 * 100
    return TSSResult(tss=round(tss, 1), method="pace", intensity_factor=round(if_val, 3))


# ── hrTSS (Banister TRIMP, normalized to TSS scale) ──────────────────────────

def hr_tss(
    duration_s: float,
    avg_hr: float,
    max_hr: float,
    rest_hr: float = 40.0,
) -> TSSResult:
    """
    TRIMP-based hrTSS.  Normalized so 1 h at threshold HR ≈ 100 TSS.

    Threshold HR is approximated at 90 % of HRR (heart-rate reserve).
    """
    if max_hr <= rest_hr:
        raise ValueError("max_hr must be > rest_hr")
    if avg_hr <= rest_hr:
        return TSSResult(tss=0.0, method="hr", intensity_factor=0.0)

    def trimp_rate(hr: float) -> float:
        hrr = (hr - rest_hr) / (max_hr - rest_hr)
        hrr = max(0.0, min(1.0, hrr))
        return hrr * 0.64 * math.exp(1.92 * hrr)

    threshold_hr = rest_hr + 0.90 * (max_hr - rest_hr)
    threshold_rate_per_hour = trimp_rate(threshold_hr) * 60  # per-minute → per-hour

    duration_min = duration_s / 60
    trimp = trimp_rate(avg_hr) * duration_min
    tss = trimp / threshold_rate_per_hour * 100
    if_val = trimp_rate(avg_hr) / trimp_rate(threshold_hr)

    return TSSResult(tss=round(tss, 1), method="hr", intensity_factor=round(if_val, 3))
