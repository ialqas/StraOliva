"""
Split anomaly detection.

Compares each lap's pace/power against the median of all laps.
Flags outliers beyond 1.5 × stddev as "fast" or "slow".
"""

import math
import statistics
from typing import Literal

from app.i18n import Lang, tr

Anomaly = Literal["fast", "slow"] | None


_AUTO_LAP_DISTANCES_M = (1000.0, 1609.34)  # watch auto-lap: every km or every mile
_AUTO_LAP_TOLERANCE_M = 15.0


def laps_are_manual(distances_m: list[float | None]) -> bool:
    """True if the watch laps were (at least partly) created by pressing the lap button.

    Strava doesn't say how a lap was triggered, so it's inferred from distances:
    a single lap is just the whole activity, and laps that are all exactly
    1 km / 1 mile (the last one may be shorter) are the watch's auto-laps.
    """
    if len(distances_m) < 2:
        return False
    full_laps = distances_m[:-1]
    for auto_m in _AUTO_LAP_DISTANCES_M:
        if all(d is not None and abs(d - auto_m) <= _AUTO_LAP_TOLERANCE_M for d in full_laps):
            return False
    return True


def detect_split_anomalies(
    laps: list[dict],
    is_ride: bool,
    lang: Lang = "en",
) -> list[dict]:
    """
    Return a list with one entry per lap including anomaly classification.

    laps: list of dicts with keys: lap_index, distance_m, time_s,
          avg_watts (optional), avg_speed_ms (optional).
    is_ride: True = compare by avg_watts; False = compare by pace (sec/km).

    Each result dict has:
      lap_index, anomaly: "fast" | "slow" | None, pct_from_median: float | None,
      tooltip: str | None.
    """
    metrics: list[float | None] = []
    for lap in laps:
        if is_ride:
            metrics.append(float(lap["avg_watts"]) if lap.get("avg_watts") else None)
        else:
            spd = lap.get("avg_speed_ms")
            dist = lap.get("distance_m", 0) or 0
            t = lap.get("time_s", 0) or 0
            if spd and spd > 0:
                metrics.append(1000.0 / spd)            # sec / km
            elif dist > 0 and t > 0:
                metrics.append(t / (dist / 1000.0))     # sec / km fallback
            else:
                metrics.append(None)

    valid = [m for m in metrics if m is not None]
    if len(valid) < 3:
        return [
            {"lap_index": lap["lap_index"], "anomaly": None, "pct_from_median": None, "tooltip": None}
            for lap in laps
        ]

    median = statistics.median(valid)
    stdev = statistics.stdev(valid)

    results = []
    for lap, metric in zip(laps, metrics):
        if metric is None or stdev == 0:
            results.append({"lap_index": lap["lap_index"], "anomaly": None, "pct_from_median": None, "tooltip": None})
            continue

        deviation = abs(metric - median)
        if deviation <= 1.5 * stdev:
            results.append({"lap_index": lap["lap_index"], "anomaly": None, "pct_from_median": None, "tooltip": None})
            continue

        pct = round((metric - median) / median * 100, 1)

        # Power: higher = faster (green), lower = slower (amber)
        # Pace (sec/km): higher = slower (amber), lower = faster (green)
        if is_ride:
            anomaly: Anomaly = "fast" if metric > median else "slow"
        else:
            anomaly = "slow" if metric > median else "fast"

        if anomaly == "slow":
            tooltip = tr(
                lang,
                f"{abs(pct):.0f}% langsamer als Median — evtl. Verkehr/Anstieg/Ermüdung",
                f"{abs(pct):.0f}% slower than median — possibly traffic/hill/fatigue",
            )
        else:
            tooltip = tr(
                lang,
                f"{abs(pct):.0f}% schneller als Median — evtl. Gefälle/Rückenwind",
                f"{abs(pct):.0f}% faster than median — possibly downhill/tailwind",
            )

        results.append({
            "lap_index": lap["lap_index"],
            "anomaly": anomaly,
            "pct_from_median": pct,
            "tooltip": tooltip,
        })

    return results
