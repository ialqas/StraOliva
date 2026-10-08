"""Tests for aerobic decoupling calculation."""

import pandas as pd
import pytest

from app.analytics.decoupling import DecouplingResult, aerobic_decoupling


def _make_streams(
    duration_s: int = 3600,
    warmup_s: int = 600,
    hr_drift: float = 5.0,       # % HR increase in second half
    power_drift: float = 0.0,    # % power decrease in second half
    ftp: float = 200.0,
) -> pd.DataFrame:
    """
    Synthetic stream: constant power, HR rises by hr_drift% in second half.
    Decoupling = power/HR ratio drops in second half.
    """
    n = duration_s
    t = list(range(n))
    mid = n // 2

    watts = [ftp] * n
    hr_base = 140.0
    # First half: hr_base, second half: hr_base × (1 + hr_drift/100)
    hr = [hr_base if i < mid else hr_base * (1 + hr_drift / 100) for i in range(n)]

    return pd.DataFrame({"time_s": t, "hr": hr, "watts": watts})


class TestAerobicDecoupling:
    def test_constant_effort_zero_drift(self):
        # Flat HR and power → decoupling ≈ 0
        df = _make_streams(hr_drift=0.0)
        result = aerobic_decoupling(df)
        assert result is not None
        assert abs(result.decoupling_pct) < 0.5

    def test_hr_drift_produces_positive_decoupling(self):
        # HR rises in second half → ratio drops → positive decoupling
        df = _make_streams(hr_drift=10.0)
        result = aerobic_decoupling(df)
        assert result is not None
        assert result.decoupling_pct > 0

    def test_known_decoupling_value(self):
        # After 600s warmup strip, median splits first/second differently:
        # first half contains some high-HR seconds → hr1 ≈ 141.4 (not pure 140)
        # second half is all drift HR → decoupling ≈ 3.8%
        df = _make_streams(hr_drift=5.0)
        result = aerobic_decoupling(df)
        assert result is not None
        assert result.decoupling_pct == pytest.approx(3.81, abs=0.2)

    def test_insufficient_data_returns_none(self):
        # Only 60 seconds after warmup — below 120 s minimum
        df = _make_streams(duration_s=650, warmup_s=600)
        result = aerobic_decoupling(df)
        assert result is None

    def test_uses_watts_column(self):
        df = _make_streams()
        result = aerobic_decoupling(df)
        assert result is not None
        assert result.effort_col == "watts"

    def test_falls_back_to_velocity(self):
        df = _make_streams()
        df = df.rename(columns={"watts": "velocity_smooth"})
        result = aerobic_decoupling(df)
        assert result is not None
        assert result.effort_col == "velocity_smooth"
