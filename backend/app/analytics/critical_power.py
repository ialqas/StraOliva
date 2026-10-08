"""
Critical Power (CP) / W' model fitting.

Hyperbolic 2-parameter model:  P(t) = CP + W' / t

CP  = Critical Power in Watts (sustainable threshold proxy)
W'  = Anaerobic capacity in Joules (energy above CP before exhaustion)

Reference: Monod & Scherrer (1965), Morton (1996).
"""

import math

import numpy as np
from pydantic import BaseModel
from scipy.optimize import curve_fit  # type: ignore[import-untyped]

# Anchor durations used for the model fit (seconds)
FIT_DURATIONS_S: list[int] = [180, 300, 720, 1200, 3600]   # 3, 5, 12, 20, 60 min


class CPFitResult(BaseModel):
    cp_w: float                   # Critical Power in Watts
    w_prime_kj: float             # W' in kJ
    standard_error: float         # residual std error of the fit (Watts)
    r_squared: float
    fit_durations_s: list[int]    # durations used in fit
    fit_powers_w: list[float]     # measured best powers at those durations
    model_powers_w: list[float]   # model-predicted powers at same durations


def _hyperbolic(t: np.ndarray, cp: float, w_prime: float) -> np.ndarray:
    """P(t) = CP + W' / t  (vectorised)."""
    return cp + w_prime / t


def fit_cp_model(best_efforts: dict[int, float]) -> CPFitResult | None:
    """
    Fit the CP/W' model to a dict of {duration_s: best_power_w}.

    Uses FIT_DURATIONS_S as anchor points — returns None if fewer than 2
    data points are available.
    """
    t_vals, p_vals = [], []
    for dur in FIT_DURATIONS_S:
        p = best_efforts.get(dur)
        if p and p > 0:
            t_vals.append(float(dur))
            p_vals.append(float(p))

    if len(t_vals) < 2:
        return None

    t_arr = np.array(t_vals)
    p_arr = np.array(p_vals)

    try:
        # Initial guess: CP ≈ power at longest duration, W' ≈ 20 kJ
        p0 = [p_arr[-1], 20_000.0]
        popt, pcov = curve_fit(
            _hyperbolic, t_arr, p_arr,
            p0=p0,
            bounds=([50, 1_000], [600, 200_000]),
            maxfev=5000,
        )
    except (RuntimeError, ValueError):
        return None

    cp, w_prime = popt
    perr = float(np.sqrt(np.diag(pcov)).mean())

    predicted = _hyperbolic(t_arr, cp, w_prime)
    ss_res = float(np.sum((p_arr - predicted) ** 2))
    ss_tot = float(np.sum((p_arr - p_arr.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return CPFitResult(
        cp_w=round(float(cp), 1),
        w_prime_kj=round(float(w_prime) / 1000, 2),
        standard_error=round(math.sqrt(ss_res / max(1, len(t_vals) - 2)), 1),
        r_squared=round(r2, 4),
        fit_durations_s=t_vals,
        fit_powers_w=[round(p, 1) for p in p_vals],
        model_powers_w=[round(float(p), 1) for p in predicted],
    )


def model_curve(
    cp_w: float,
    w_prime_kj: float,
    durations_s: list[int],
) -> list[float]:
    """Evaluate the fitted CP/W' curve at arbitrary durations."""
    w_prime = w_prime_kj * 1000
    return [round(cp_w + w_prime / t, 1) for t in durations_s]


def confidence_band(
    cp_w: float,
    w_prime_kj: float,
    standard_error: float,
    durations_s: list[int],
    sigma: float = 1.0,
) -> tuple[list[float], list[float]]:
    """
    Return (lower, upper) confidence band around the CP/W' curve.

    Band widens for durations far from the fit anchors (extrapolation).
    sigma: multiplier for the standard error (1.0 = ±1 SE).
    """
    w_prime = w_prime_kj * 1000
    anchor_min = min(FIT_DURATIONS_S)
    anchor_max = max(FIT_DURATIONS_S)

    lower, upper = [], []
    for t in durations_s:
        predicted = cp_w + w_prime / t
        # Extrapolation multiplier: widens band outside anchor range
        if t < anchor_min:
            extrap = 1.0 + (anchor_min - t) / anchor_min
        elif t > anchor_max:
            extrap = 1.0 + (t - anchor_max) / anchor_max
        else:
            extrap = 1.0
        half = standard_error * sigma * extrap
        lower.append(round(predicted - half, 1))
        upper.append(round(predicted + half, 1))

    return lower, upper
