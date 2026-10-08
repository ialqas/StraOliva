import math
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.splits import laps_are_manual
from app.db.models import Activity, KmSplit, Lap, Stream
from app.db.session import get_db_dep

router = APIRouter(tags=["streams"])

_SMOOTH_WINDOW = 33  # samples (~11 s for 1 Hz GPS)


def _velocity_from_gps(streams: list[Stream]) -> list[float | None]:
    """Derive smoothed velocity (m/s) from consecutive GPS points."""
    n = len(streams)
    raw: list[float | None] = [None] * n
    for i in range(1, n):
        s0, s1 = streams[i - 1], streams[i]
        if s0.lat and s0.lng and s1.lat and s1.lng:
            dt = s1.time_s - s0.time_s
            if dt > 0:
                dlat = math.radians(s1.lat - s0.lat)
                dlng = math.radians(s1.lng - s0.lng)
                a = (math.sin(dlat / 2) ** 2
                     + math.cos(math.radians(s0.lat))
                     * math.cos(math.radians(s1.lat))
                     * math.sin(dlng / 2) ** 2)
                dist = 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                raw[i] = dist / dt

    half = _SMOOTH_WINDOW // 2
    smoothed: list[float | None] = [None] * n
    for i in range(n):
        vals = [raw[j] for j in range(max(0, i - half), min(n, i + half + 1)) if raw[j] is not None]
        smoothed[i] = sum(vals) / len(vals) if vals else None
    return smoothed


@router.get("/activities/{activity_id}/streams")
def get_activity_streams(activity_id: int, db: Session = Depends(get_db_dep)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if not activity.has_streams:
        return {"time_s": [], "hr": [], "watts": [], "velocity_smooth": [], "altitude_m": [], "cadence": [], "lat": [], "lng": []}

    streams = (
        db.query(Stream)
        .filter(Stream.activity_id == activity_id)
        .order_by(Stream.time_s)
        .all()
    )

    velocity = [s.velocity_smooth for s in streams]
    if all(v is None for v in velocity):
        velocity = _velocity_from_gps(streams)

    return {
        "time_s": [s.time_s for s in streams],
        "hr": [s.hr for s in streams],
        "watts": [s.watts for s in streams],
        "velocity_smooth": velocity,
        "altitude_m": [s.altitude_m for s in streams],
        "cadence": [s.cadence for s in streams],
        "lat": [s.lat for s in streams],
        "lng": [s.lng for s in streams],
    }


@router.get("/activities/{activity_id}/laps")
def get_activity_laps(activity_id: int, db: Session = Depends(get_db_dep)):
    laps = (
        db.query(Lap)
        .filter(Lap.activity_id == activity_id)
        .order_by(Lap.lap_index)
        .all()
    )
    return [
        {
            "lap_index": lap.lap_index,
            "distance_m": lap.distance_m,
            "time_s": lap.time_s,          # elapsed (incl. pauses) — matches the stream timeline
            "moving_time_s": lap.moving_s,  # without pauses — what the watch shows
            "avg_hr": lap.avg_hr,
            "avg_watts": lap.avg_watts,
            "avg_speed_ms": lap.avg_speed_ms,
        }
        for lap in laps
    ]


@router.get("/activities/{activity_id}/splits")
def get_activity_splits(activity_id: int, db: Session = Depends(get_db_dep)):
    """Watch laps + Strava's automatic km splits, both with pause-free times.

    `laps_are_manual` is False when the watch laps are just auto-laps (every 1 km)
    or a single lap for the whole activity — the frontend then shows only the km splits.
    """
    laps = get_activity_laps(activity_id, db)
    km_splits = (
        db.query(KmSplit)
        .filter(KmSplit.activity_id == activity_id)
        .order_by(KmSplit.split_index)
        .all()
    )
    return {
        "laps": laps,
        "laps_are_manual": laps_are_manual([lap["distance_m"] for lap in laps]),
        "km_splits": [
            {
                "split_index": s.split_index,
                "distance_m": s.distance_m,
                "moving_time_s": s.moving_time_s,
                "elapsed_time_s": s.elapsed_time_s,
                "avg_speed_ms": s.avg_speed_ms,
                "avg_hr": s.avg_hr,
                "elevation_diff_m": s.elevation_diff_m,
            }
            for s in km_splits
        ],
    }
