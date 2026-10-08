from app.analytics.splits import laps_are_manual
from app.db.models import Lap


class TestLapsAreManual:
    def test_single_lap_is_whole_activity(self):
        assert laps_are_manual([10212.0]) is False

    def test_km_auto_laps(self):
        assert laps_are_manual([1000.0, 1000.0, 998.0, 1004.0, 720.0]) is False

    def test_mile_auto_laps(self):
        assert laps_are_manual([1609.3, 1609.4, 800.0]) is False

    def test_manual_laps(self):
        assert laps_are_manual([16793.0, 3944.0, 1238.0, 1638.0, 3409.0]) is True

    def test_manual_lap_among_auto_laps(self):
        assert laps_are_manual([1000.0, 1000.0, 400.0, 1000.0, 300.0]) is True


class TestLapMovingTime:
    def test_stored_moving_time_wins(self):
        lap = Lap(distance_m=1000.0, time_s=565, moving_time_s=320, avg_speed_ms=3.1)
        assert lap.moving_s == 320

    def test_derived_from_avg_speed_for_old_rows(self):
        # elapsed 565 s includes a pause; avg speed is distance / moving time
        lap = Lap(distance_m=1000.0, time_s=565, avg_speed_ms=1000 / 323)
        assert lap.moving_s == 323

    def test_falls_back_to_elapsed(self):
        assert Lap(distance_m=1000.0, time_s=300).moving_s == 300
