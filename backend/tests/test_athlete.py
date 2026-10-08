from app.analytics.athlete import sustained_max_hr

T = list(range(60))


def test_single_sample_spike_is_ignored():
    hr = [150.0] * 60
    hr[40] = 199.0
    assert sustained_max_hr(T, hr) == 150.0


def test_implausible_values_are_dropped():
    hr = [150.0] * 20 + [240.0] * 15 + [150.0] * 25
    assert sustained_max_hr(T, hr) == 150.0


def test_value_held_ten_seconds_counts():
    hr = [150.0] * 20 + [188.0] * 12 + [150.0] * 28
    assert sustained_max_hr(T, hr) == 188.0


def test_value_held_too_briefly_does_not_count():
    hr = [150.0] * 20 + [188.0] * 6 + [150.0] * 34
    assert sustained_max_hr(T, hr) == 150.0


def test_recording_gap_does_not_bridge_a_window():
    # two 5 s bursts separated by a 60 s gap must not form one 10 s window
    t = list(range(0, 30)) + list(range(90, 95)) + list(range(150, 155))
    hr = [150.0] * 30 + [190.0] * 10
    assert sustained_max_hr(t, hr) == 150.0


def test_too_little_data():
    assert sustained_max_hr([0, 1, 2], [150.0, 151.0, 152.0]) is None


from app.analytics.athlete import best_sustained_speed


def test_best_sustained_speed_finds_hardest_20_min():
    # 10 min easy (3.0 m/s), 20 min hard (4.0 m/s, HR 180), 10 min easy
    t = list(range(2400))
    v = [3.0] * 600 + [4.0] * 1200 + [3.0] * 600
    hr = [140.0] * 600 + [180.0] * 1200 + [140.0] * 600
    speed, avg_hr = best_sustained_speed(t, v, hr)
    assert speed == 4.0
    assert avg_hr == 180.0


def test_best_sustained_speed_needs_20_minutes():
    t = list(range(900))
    assert best_sustained_speed(t, [4.0] * 900, [180.0] * 900) is None
