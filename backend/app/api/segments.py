"""Segment wind correlation endpoint."""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

import httpx

from app.analytics.wind import (
    compute_bearing,
    decode_polyline,
    is_circular_segment,
    tailwind_angle,
    wind_category,
    wind_color,
    wind_label,
)
from app.config import settings
from app.db.models import Segment
from app.db.session import get_db_dep
from app.i18n import Lang, tr

router = APIRouter(tags=["segments"])

_BRIGHTSKY = "https://api.brightsky.dev/weather"



class WindCity(BaseModel):
    key: str
    name: str
    lat: float
    lng: float


def _wind_cities() -> list[WindCity]:
    """Parse WIND_CITIES ("Name:lat:lng,…"); malformed entries are skipped."""
    cities = []
    for entry in settings.wind_cities.split(","):
        parts = [p.strip() for p in entry.split(":")]
        if len(parts) != 3 or not parts[0]:
            continue
        try:
            cities.append(WindCity(key=parts[0].lower(), name=parts[0], lat=float(parts[1]), lng=float(parts[2])))
        except ValueError:
            continue
    return cities


class WindInfo(BaseModel):
    speed_ms: float | None
    speed_kmh: float | None
    direction_from: int | None
    gust_speed_ms: float | None
    station_name: str | None
    station_distance_km: float | None


class SegmentWind(BaseModel):
    id: int
    name: str
    distance_m: float | None
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    avg_grade: float | None
    bearing_deg: float
    tailwind_angle: float
    category: str
    label: str
    color: str
    coords: list[list[float]]  # [[lng, lat], ...] GeoJSON order


class SegmentsWindResponse(BaseModel):
    segments: list[SegmentWind]
    wind: WindInfo | None          # representative wind (nearest station to centroid)
    error: str | None = None


def _grid_key(lat: float, lng: float) -> tuple[float, float]:
    """Round to ~33 km grid so nearby segments share one API call."""
    return round(lat / 0.3) * 0.3, round(lng / 0.3) * 0.3


async def _fetch_wind(lat: float, lng: float) -> WindInfo | None:
    """Fetch current wind from brightsky (DWD MOSMIX/observation) for a location."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00+00:00")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                _BRIGHTSKY,
                params={"lat": lat, "lon": lng, "date": now, "last_date": now},
            )
            resp.raise_for_status()
            data = resp.json()

        weather_list = data.get("weather") or []
        w = weather_list[0] if weather_list else {}
        sources = data.get("sources") or [{}]
        src = next(
            (s for s in sources if s.get("id") == w.get("source_id")),
            sources[0] if sources else {},
        )

        speed_ms = w.get("wind_speed")
        return WindInfo(
            speed_ms=speed_ms,
            speed_kmh=round(speed_ms * 3.6, 1) if speed_ms is not None else None,
            direction_from=w.get("wind_direction"),
            gust_speed_ms=w.get("wind_gust_speed"),
            station_name=src.get("station_name"),
            station_distance_km=round(src.get("distance", 0) / 1000, 1)
            if src.get("distance")
            else None,
        )
    except Exception:
        return None


@router.get("/segments/cities", response_model=list[WindCity])
def segments_cities():
    return _wind_cities()


@router.get("/segments/wind", response_model=SegmentsWindResponse)
async def segments_wind(
    db: Session = Depends(get_db_dep),
    city: str | None = None,
    lang: Lang = Query("de"),
):
    segments = db.query(Segment).all()
    valid = [s for s in segments if s.start_lat is not None and s.end_lat is not None]

    # Filter out loop segments (start ≈ end) — wind direction is meaningless for them
    valid = [
        s for s in valid
        if not is_circular_segment(s.start_lat, s.start_lng, s.end_lat, s.end_lng, s.distance_m)
    ]

    if not valid:
        return SegmentsWindResponse(segments=[], wind=None)

    # ── Wind fetch: fixed city coord or per-segment grid ─────────────────────
    city_match = next((c for c in _wind_cities() if city and c.key == city.lower()), None)
    if city_match:
        representative_wind = await _fetch_wind(city_match.lat, city_match.lng)
        shared_wind = representative_wind
    else:
        grid_keys = {_grid_key((s.start_lat + s.end_lat) / 2, (s.start_lng + s.end_lng) / 2) for s in valid}
        wind_results: dict[tuple, WindInfo | None] = dict(
            zip(
                grid_keys,
                await asyncio.gather(*[_fetch_wind(lat, lng) for lat, lng in grid_keys]),
            )
        )
        centroid_lat = sum((s.start_lat + s.end_lat) / 2 for s in valid) / len(valid)
        centroid_lng = sum((s.start_lng + s.end_lng) / 2 for s in valid) / len(valid)
        rep_key = _grid_key(centroid_lat, centroid_lng)
        representative_wind = wind_results.get(rep_key) or next(
            (w for w in wind_results.values() if w is not None), None
        )
        shared_wind = None  # per-segment lookup below

    # ── Build per-segment results ────────────────────────────────────────────
    result: list[SegmentWind] = []
    errors: list[str] = []

    for seg in valid:
        if shared_wind is not None:
            wind = shared_wind
        else:
            mid_lat = (seg.start_lat + seg.end_lat) / 2
            mid_lng = (seg.start_lng + seg.end_lng) / 2
            wind = wind_results.get(_grid_key(mid_lat, mid_lng))  # type: ignore[possibly-undefined]

        # Overall bearing: first → last GPS point of the segment
        if seg.polyline:
            pts = decode_polyline(seg.polyline)
            if len(pts) >= 2:
                bearing = compute_bearing(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1])
            else:
                bearing = compute_bearing(seg.start_lat, seg.start_lng, seg.end_lat, seg.end_lng)
            # GeoJSON coords: [lng, lat]
            coords = [[pt[1], pt[0]] for pt in pts]
        else:
            bearing = compute_bearing(seg.start_lat, seg.start_lng, seg.end_lat, seg.end_lng)
            coords = [
                [seg.start_lng, seg.start_lat],
                [seg.end_lng, seg.end_lat],
            ]

        speed_ms = wind.speed_ms if wind else None
        if wind and wind.direction_from is not None:
            tw_angle = tailwind_angle(wind.direction_from, bearing)
            spd = speed_ms or 0.0
            cat = wind_category(tw_angle, spd)
            label = wind_label(tw_angle, spd, lang)
            color = wind_color(tw_angle, spd)
        else:
            tw_angle = 90.0
            cat = "unknown"
            label = tr(lang, "Keine Winddaten", "No wind data")
            color = "#9CA3AF"
            if wind is None:
                errors.append(seg.name)

        result.append(
            SegmentWind(
                id=seg.id,
                name=seg.name,
                distance_m=seg.distance_m,
                start_lat=seg.start_lat,
                start_lng=seg.start_lng,
                end_lat=seg.end_lat,
                end_lng=seg.end_lng,
                avg_grade=seg.avg_grade,
                bearing_deg=round(bearing, 1),
                tailwind_angle=round(tw_angle, 1),
                category=cat,
                label=label,
                color=color,
                coords=coords,
            )
        )

    result.sort(key=lambda x: x.tailwind_angle)

    return SegmentsWindResponse(
        segments=result,
        wind=representative_wind,
        error=tr(lang, "Kein Wind für: ", "No wind for: ") + ", ".join(errors) if errors else None,
    )
