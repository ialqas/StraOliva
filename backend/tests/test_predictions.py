"""Tests for race prediction (Riegel formula + confidence tiers)."""

import pandas as pd
import pytest

from app.analytics.predictions import (
    DISTANCES,
    RacePrediction,
    format_time,
    predict_all,
    predict_race,
    riegel,
)


class TestRiegel:
    def test_same_distance_returns_same_time(self):
        assert riegel(1800, 5000, 5000) == pytest.approx(1800.0)

    def test_double_distance_takes_more_than_double_time(self):
        t_5k = riegel(1200, 5000, 5000)
        t_10k = riegel(1200, 5000, 10000)
        assert t_10k > 2 * t_5k

    def test_known_result(self):
        # 20:00 5k → predicted 10k via Riegel ≈ 41:41 (2501.8 s)
        result = riegel(1200, 5000, 10000)
        assert result == pytest.approx(2501.8, abs=1.0)

    def test_marathon_from_half(self):
        hm_s = 105 * 60  # 1:45:00
        result = riegel(hm_s, 21097, 42195)
        assert 13_000 < result < 13_500

    def test_invalid_input_raises(self):
        with pytest.raises(ValueError):
            riegel(0, 5000, 10000)
        with pytest.raises(ValueError):
            riegel(1200, 0, 10000)


class TestFormatTime:
    def test_sub_hour(self):
        assert format_time(3661) == "1:01:01"

    def test_exact_hour(self):
        assert format_time(3600) == "1:00:00"

    def test_minutes_only(self):
        assert format_time(305) == "5:05"


def _make_df(runs: list[tuple]) -> pd.DataFrame:
    """Helper: list of (days_ago, distance_m, moving_time_s)."""
    rows = []
    for days_ago, dist, time_s in runs:
        rows.append({
            "id": len(rows) + 1,
            "start_time": pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days_ago),
            "type": "Run",
            "distance_m": float(dist),
            "moving_time_s": float(time_s),
            "name": f"Run {len(rows)}",
        })
    return pd.DataFrame(rows)


class TestPredictRace:
    def test_no_data_returns_no_data_tier(self):
        df = pd.DataFrame(columns=["id", "start_time", "type", "distance_m", "moving_time_s", "name"])
        pred = predict_race(df, 5000, "5k")
        assert pred.confidence == "no_data"
        assert pred.predicted_s is None

    def test_1k_not_in_distances(self):
        assert "1k" not in DISTANCES

    def test_hm_no_data_without_long_run(self):
        # Only short 5k runs — should return no_data for HM
        df = _make_df([(5, 5000, 1200), (10, 5000, 1210)])
        pred = predict_race(df, DISTANCES["HM"], "HM")
        assert pred.confidence == "no_data"

    def test_marathon_no_data_without_long_run(self):
        df = _make_df([(5, 17000, 5400)])  # 17km — below 25km threshold
        pred = predict_race(df, DISTANCES["Marathon"], "Marathon")
        assert pred.confidence == "no_data"

    def test_high_confidence_with_three_similar_runs(self):
        # Three 10k runs → predicting 10k → high confidence
        df = _make_df([(7, 10000, 2700), (14, 10000, 2720), (21, 10000, 2710)])
        pred = predict_race(df, 10000, "10k")
        assert pred.confidence == "high"
        assert pred.predicted_s is not None
        assert pred.predicted_s > 0

    def test_medium_confidence_with_one_run(self):
        df = _make_df([(5, 10000, 2700)])
        pred = predict_race(df, 10000, "10k")
        assert pred.confidence == "medium"

    def test_ci_lower_lt_predicted_lt_upper(self):
        df = _make_df([(7, 10000, 2700), (14, 9500, 2600)])
        pred = predict_race(df, 10000, "10k")
        assert pred.ci_lower_s < pred.predicted_s < pred.ci_upper_s  # type: ignore[operator]

    def test_predict_all_returns_four_distances(self):
        df = _make_df([(7, 10000, 2700), (14, 15000, 4200), (21, 8000, 2200)])
        results = predict_all(df)
        assert len(results) == 4
        labels = {r.distance_label for r in results}
        assert labels == {"5k", "10k", "HM", "Marathon"}
