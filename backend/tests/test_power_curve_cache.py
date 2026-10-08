from app.api.power_curve import _merge_best


def test_merge_keeps_best_per_duration():
    cached = [{"duration_s": 5, "power_w": 800.0}, {"duration_s": 1200, "power_w": 250.0}]
    new = [{"duration_s": 5, "power_w": 750.0}, {"duration_s": 1200, "power_w": 262.0}, {"duration_s": 60, "power_w": 400.0}]
    assert _merge_best(cached, new) == [
        {"duration_s": 5, "power_w": 800.0},
        {"duration_s": 60, "power_w": 400.0},
        {"duration_s": 1200, "power_w": 262.0},
    ]


def test_merge_with_empty_cache():
    new = [{"duration_s": 5, "power_w": 750.0}]
    assert _merge_best([], new) == new
