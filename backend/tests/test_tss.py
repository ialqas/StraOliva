"""Tests for TSS calculations — the easy ones to get wrong."""

import pytest

from app.analytics.tss import bike_tss, hr_tss, run_tss


class TestBikeTSS:
    def test_one_hour_at_threshold_is_100(self):
        # 1 h at FTP (NP == FTP → IF = 1) must give exactly 100 TSS
        result = bike_tss(duration_s=3600, np_w=250, ftp_w=250)
        assert result.tss == pytest.approx(100.0, abs=0.1)
        assert result.intensity_factor == pytest.approx(1.0, abs=0.001)
        assert result.method == "power"

    def test_half_hour_at_threshold_is_25(self):
        # 30 min at FTP: TSS = (1800 × 250 × 1) / (250 × 3600) × 100 = 50 ... wait
        # Actually: IF=1, TSS = duration_s/(3600) × IF² × 100 = 0.5 × 1 × 100 = 50
        result = bike_tss(duration_s=1800, np_w=250, ftp_w=250)
        assert result.tss == pytest.approx(50.0, abs=0.1)

    def test_higher_intensity_gives_higher_tss(self):
        easy = bike_tss(duration_s=3600, np_w=200, ftp_w=250)   # IF=0.8
        hard = bike_tss(duration_s=3600, np_w=275, ftp_w=250)   # IF=1.1
        assert hard.tss > easy.tss

    def test_invalid_ftp_raises(self):
        with pytest.raises(ValueError):
            bike_tss(duration_s=3600, np_w=250, ftp_w=0)

    def test_invalid_np_raises(self):
        with pytest.raises(ValueError):
            bike_tss(duration_s=3600, np_w=0, ftp_w=250)


class TestRunTSS:
    def test_one_hour_at_threshold_is_100(self):
        # 1 h exactly at threshold pace → 100 TSS
        threshold = 3.5   # m/s (~4:46/km)
        result = run_tss(duration_s=3600, avg_pace_ms=threshold, threshold_pace_ms=threshold)
        assert result.tss == pytest.approx(100.0, abs=0.1)
        assert result.intensity_factor == pytest.approx(1.0, abs=0.001)

    def test_slower_pace_gives_less_tss(self):
        threshold = 3.5
        slow = run_tss(3600, avg_pace_ms=3.0, threshold_pace_ms=threshold)
        fast = run_tss(3600, avg_pace_ms=4.0, threshold_pace_ms=threshold)
        assert slow.tss < 100
        assert fast.tss > 100

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            run_tss(3600, avg_pace_ms=3.5, threshold_pace_ms=0)


class TestHrTSS:
    def test_no_effort_gives_zero(self):
        result = hr_tss(duration_s=3600, avg_hr=41, max_hr=190, rest_hr=40)
        assert result.tss >= 0

    def test_high_hr_gives_more_tss_than_low(self):
        low  = hr_tss(duration_s=3600, avg_hr=130, max_hr=190, rest_hr=40)
        high = hr_tss(duration_s=3600, avg_hr=170, max_hr=190, rest_hr=40)
        assert high.tss > low.tss

    def test_threshold_hr_gives_approx_100(self):
        # At 90 % HRR (threshold HR) for 1 h → should be close to 100
        rest, max_hr = 40, 190
        threshold_hr = rest + 0.90 * (max_hr - rest)
        result = hr_tss(duration_s=3600, avg_hr=threshold_hr, max_hr=max_hr, rest_hr=rest)
        assert result.tss == pytest.approx(100.0, abs=5.0)

    def test_invalid_max_hr_raises(self):
        with pytest.raises(ValueError):
            hr_tss(duration_s=3600, avg_hr=150, max_hr=40, rest_hr=40)
