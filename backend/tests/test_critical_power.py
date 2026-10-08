"""Tests for CP/W' model fitting."""

import pytest

from app.analytics.critical_power import (
    FIT_DURATIONS_S,
    confidence_band,
    fit_cp_model,
    model_curve,
)


def _synthetic_efforts(cp: float = 280.0, w_prime: float = 20_000.0) -> dict[int, float]:
    """Generate perfect hyperbolic efforts for known CP and W'."""
    return {t: cp + w_prime / t for t in FIT_DURATIONS_S}


class TestFitCPModel:
    def test_recovers_known_parameters(self):
        efforts = _synthetic_efforts(cp=280.0, w_prime=20_000.0)
        result = fit_cp_model(efforts)
        assert result is not None
        assert result.cp_w == pytest.approx(280.0, abs=1.0)
        assert result.w_prime_kj == pytest.approx(20.0, abs=0.5)

    def test_r_squared_near_one_for_perfect_data(self):
        efforts = _synthetic_efforts()
        result = fit_cp_model(efforts)
        assert result is not None
        assert result.r_squared > 0.99

    def test_returns_none_for_single_point(self):
        result = fit_cp_model({300: 320.0})
        assert result is None

    def test_returns_none_for_empty(self):
        result = fit_cp_model({})
        assert result is None

    def test_model_curve_matches_fit(self):
        efforts = _synthetic_efforts(cp=260.0, w_prime=18_000.0)
        result = fit_cp_model(efforts)
        assert result is not None
        curve = model_curve(result.cp_w, result.w_prime_kj, [300, 1200])
        assert len(curve) == 2
        # Model at 5min should be close to measured
        assert curve[0] == pytest.approx(efforts[300], abs=2.0)

    def test_confidence_band_widens_outside_anchors(self):
        # Use a fixed non-zero SE so the extrapolation multiplier is visible
        se = 10.0
        lo, hi = confidence_band(280.0, 20.0, se, [10, 300, 7200])
        # Band at 10s (well below anchor_min=180s) should be wider than at 300s (within range)
        width_10s = hi[0] - lo[0]
        width_300s = hi[1] - lo[1]
        assert width_10s > width_300s

    def test_cp_within_realistic_range(self):
        efforts = _synthetic_efforts(cp=250.0, w_prime=22_000.0)
        result = fit_cp_model(efforts)
        assert result is not None
        assert 50 <= result.cp_w <= 600
        assert 0.5 <= result.w_prime_kj <= 50
