"""Tests for CTL/ATL/TSB computation."""

from datetime import date

import pandas as pd
import pytest

from app.analytics.training_load import compute_ctl_atl_tsb, compute_daily_tss, form_trend


def _daily(pairs: list[tuple[str, float]]) -> pd.Series:
    idx = [date.fromisoformat(d) for d, _ in pairs]
    vals = [v for _, v in pairs]
    return pd.Series(vals, index=idx)


class TestDailyTSS:
    def test_aggregates_same_day(self):
        df = pd.DataFrame([
            {"start_time": "2024-01-01 08:00:00", "tss": 60.0},
            {"start_time": "2024-01-01 18:00:00", "tss": 40.0},
        ])
        result = compute_daily_tss(df)
        assert result[date(2024, 1, 1)] == pytest.approx(100.0)

    def test_ignores_null_tss(self):
        df = pd.DataFrame([
            {"start_time": "2024-01-01", "tss": None},
            {"start_time": "2024-01-02", "tss": 80.0},
        ])
        result = compute_daily_tss(df)
        assert date(2024, 1, 1) not in result.index
        assert result[date(2024, 1, 2)] == pytest.approx(80.0)


class TestCTLATLTSB:
    def test_empty_input(self):
        assert compute_ctl_atl_tsb(pd.Series(dtype=float)) == []

    def test_fills_gaps(self):
        # Two entries 3 days apart → result should have 3 days
        s = _daily([("2024-01-01", 100), ("2024-01-03", 100)])
        result = compute_ctl_atl_tsb(s)
        assert len(result) == 3

    def test_ctl_increases_with_consistent_load(self):
        # 30 days of consistent TSS → CTL should rise monotonically
        s = _daily([(f"2024-01-{d:02d}", 100.0) for d in range(1, 31)])
        result = compute_ctl_atl_tsb(s)
        ctls = [r.ctl for r in result]
        assert all(ctls[i] <= ctls[i + 1] for i in range(len(ctls) - 1))

    def test_atl_reacts_faster_than_ctl(self):
        # ATL (7-day window) must decay faster than CTL (42-day window) during rest.
        load_days = [(f"2024-01-{d:02d}", 150.0) for d in range(1, 21)]
        rest_days = [(f"2024-01-{d:02d}", 0.0) for d in range(21, 26)]
        s = _daily(load_days + rest_days)
        result = compute_ctl_atl_tsb(s)

        # Find the boundary between load and rest
        last_load = result[19]   # day 20
        last_rest = result[-1]   # day 25

        atl_drop_pct = (last_load.atl - last_rest.atl) / last_load.atl
        ctl_drop_pct = (last_load.ctl - last_rest.ctl) / last_load.ctl

        # ATL must drop proportionally faster than CTL during rest
        assert atl_drop_pct > ctl_drop_pct

        # TSB must improve (become less negative / more positive) during rest
        assert last_rest.tsb > last_load.tsb

    def test_tsb_equals_ctl_minus_atl(self):
        s = _daily([("2024-03-01", 80), ("2024-03-05", 120)])
        result = compute_ctl_atl_tsb(s)
        for r in result:
            assert r.tsb == pytest.approx(r.ctl - r.atl, abs=0.01)


class TestFormTrend:
    def test_positive_trend_after_rest(self):
        s = _daily([(f"2024-01-{d:02d}", 150) for d in range(1, 15)]
                   + [(f"2024-01-{d:02d}", 0) for d in range(15, 22)])
        loads = compute_ctl_atl_tsb(s)
        trend = form_trend(loads, days=7)
        assert trend > 0   # TSB rising during rest week
