"""Bearing, tailwind, and segment-shape utilities for wind correlation."""

import math

from app.i18n import Lang, tr


# ── Geometry ──────────────────────────────────────────────────────────────────

def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode Google encoded polyline to list of (lat, lng) tuples."""
    coords: list[tuple[float, float]] = []
    idx = lat = lng = 0
    while idx < len(encoded):
        for is_lng in (False, True):
            num = shift = 0
            while True:
                b = ord(encoded[idx]) - 63
                idx += 1
                num |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(num >> 1) if (num & 1) else (num >> 1)
            if is_lng:
                lng += delta
            else:
                lat += delta
        coords.append((lat / 1e5, lng / 1e5))
    return coords


def compute_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (start → end) in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_circular_segment(
    start_lat: float, start_lng: float,
    end_lat: float, end_lng: float,
    distance_m: float | None,
) -> bool:
    """
    True when start ≈ end, i.e. the segment is a loop.
    Uses the ratio of straight-line distance to total distance:
    if the crow-flies gap is less than 15 % of the route length, it's a loop.
    Falls back to an absolute 150 m threshold when distance_m is unavailable.
    """
    straight = haversine_m(start_lat, start_lng, end_lat, end_lng)
    if distance_m and distance_m > 0:
        return (straight / distance_m) < 0.15
    return straight < 150


# ── Tailwind ──────────────────────────────────────────────────────────────────

def tailwind_angle(wind_from_deg: float, segment_bearing_deg: float) -> float:
    """
    Angle difference [0, 180] where 0 = perfect tailwind, 180 = perfect headwind.
    wind_from_deg: meteorological convention — direction the wind is coming FROM.
    """
    wind_toward = (wind_from_deg + 180) % 360
    return abs((wind_toward - segment_bearing_deg + 180) % 360 - 180)


def wind_category(angle_diff: float, wind_speed_ms: float = 0.0) -> str:
    """
    Classify wind benefit for a segment.
    'strong_tailwind' requires both a good angle AND meaningful speed —
    light breezes should never be called 'stark'.
    """
    # Component of wind speed that acts as pure tailwind (positive = helps, negative = hinders)
    tw_component = math.cos(math.radians(angle_diff)) * wind_speed_ms

    if angle_diff < 45:
        # Needs ≥ 3 m/s (~11 km/h) effective tailwind component to be "stark"
        return "strong_tailwind" if tw_component >= 3.0 else "tailwind"
    elif angle_diff < 70:
        return "tailwind"
    elif angle_diff < 100:
        return "crosswind"
    elif angle_diff < 135:
        return "slight_headwind"
    else:
        return "headwind"


_WIND_LABELS: dict[str, tuple[str, str]] = {
    "strong_tailwind": ("Starker Rückenwind", "Strong tailwind"),
    "tailwind": ("Rückenwind", "Tailwind"),
    "crosswind": ("Seitenwind", "Crosswind"),
    "slight_headwind": ("Leichter Gegenwind", "Slight headwind"),
    "headwind": ("Gegenwind", "Headwind"),
}


def wind_label(angle_diff: float, wind_speed_ms: float = 0.0, lang: Lang = "de") -> str:
    de, en = _WIND_LABELS[wind_category(angle_diff, wind_speed_ms)]
    return tr(lang, de, en)


def wind_color(angle_diff: float, wind_speed_ms: float = 0.0) -> str:
    return {
        "strong_tailwind": "#16A34A",
        "tailwind": "#22C55E",
        "crosswind": "#EAB308",
        "slight_headwind": "#F97316",
        "headwind": "#EF4444",
    }[wind_category(angle_diff, wind_speed_ms)]
