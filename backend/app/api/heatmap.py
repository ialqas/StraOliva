"""
GPS heatmap data endpoint.

First request: computes all tracks from DB (~2–5 s), writes to data/heatmap.json.
Subsequent requests: served from in-memory cache (instant).
Recompute updates the file via update_cache() — only new activities are read.
"""

import json
import time as _time
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Activity, Stream
from app.db.session import get_db_dep

router = APIRouter(tags=["heatmap"])

# Types with no meaningful outdoor GPS
_SKIP_TYPES = {
    "schwimmen", "swimming", "gewichtstraining", "weighttraining",
    "yoga", "training", "skilanglaufen", "crosscountryskiing",
}

_mem_cache: dict | None = None
_mem_cache_mtime: float = 0


def _cache_file() -> Path:
    return Path(settings.db_path).parent / "heatmap.json"


@router.get("/heatmap")
def get_heatmap(db: Session = Depends(get_db_dep)):
    global _mem_cache, _mem_cache_mtime

    cf = _cache_file()
    if cf.exists():
        mtime = cf.stat().st_mtime
        if _mem_cache is None or mtime > _mem_cache_mtime:
            _mem_cache = _public(json.loads(cf.read_text()))
            _mem_cache_mtime = mtime
        return _mem_cache

    # First time: compute on demand and persist
    update_cache(db, full=True)
    return _mem_cache


def update_cache(db: Session, full: bool = False) -> dict[str, int]:
    """Called by recompute. Incremental by default: the cache file remembers
    which activities it contains, so only new GPS activities are read and appended."""
    global _mem_cache, _mem_cache_mtime

    cf = _cache_file()
    cached: dict = {}
    if not full and cf.exists():
        try:
            cached = json.loads(cf.read_text())
        except (OSError, ValueError):
            cached = {}
    if "activity_ids" not in cached:  # no cache / pre-incremental format → rebuild
        cached = {"tracks": [], "activity_ids": []}

    candidates = [
        act_id
        for act_id, act_type in db.query(Activity.id, Activity.type).filter(Activity.has_streams.is_(True)).all()
        if not any(k in (act_type or "").lower() for k in _SKIP_TYPES)
    ]
    # activity_ids also lists activities checked but without usable GPS, so they aren't re-read
    checked = set(cached["activity_ids"])
    new_ids = [a for a in candidates if a not in checked]

    if new_ids or full or not cf.exists():
        tracks = cached["tracks"] + _tracks(db, new_ids)
        data = {
            "tracks": tracks,
            "count": len(tracks),
            "center": _center(tracks),
            "activity_ids": sorted(checked | set(new_ids)),
        }
        cf.write_text(json.dumps(data, separators=(",", ":")))
        _mem_cache = _public(data)
        _mem_cache_mtime = _time.time()

    return {"tracks_added": len(new_ids)}


def _public(data: dict) -> dict:
    # center is recomputed so caches written before the densest-area logic stay correct
    public = {k: v for k, v in data.items() if k != "activity_ids"}
    public["center"] = _center(data.get("tracks", []))
    return public


def _configured_center() -> list[float] | None:
    """HEATMAP_CENTER ("lat:lng") as [lng, lat], or None if unset/malformed."""
    try:
        lat, lng = (float(p) for p in settings.heatmap_center.split(":"))
    except ValueError:
        return None
    return [lng, lat]


def _center(tracks: list[list[list[float]]]) -> list[float]:
    """Configured HEATMAP_CENTER, else the center of the area with the most activities (a plain mean lands between
    two training areas). Track midpoints are binned on a ~10 km grid."""
    if (configured := _configured_center()) is not None:
        return configured
    mids = [t[len(t) // 2] for t in tracks if t]
    if not mids:
        return [10.0, 50.0]
    def cell(m: list[float]) -> tuple[float, float]:
        return round(m[0], 1), round(m[1], 1)

    busiest, _ = Counter(cell(m) for m in mids).most_common(1)[0]
    in_cell = [m for m in mids if cell(m) == busiest]
    return [
        round(sum(m[0] for m in in_cell) / len(in_cell), 4),
        round(sum(m[1] for m in in_cell) / len(in_cell), 4),
    ]


def _tracks(db: Session, activity_ids: list[int]) -> list[list[list[float]]]:
    tracks = []
    for act_id in activity_ids:
        rows = (
            db.query(Stream.lat, Stream.lng)
            .filter(
                Stream.activity_id == act_id,
                Stream.lat.isnot(None),
                Stream.lng.isnot(None),
            )
            .order_by(Stream.time_s)
            .all()
        )
        if len(rows) < 5:
            continue

        step = max(1, len(rows) // 120)
        tracks.append([[round(r.lng, 5), round(r.lat, 5)] for r in rows[::step]])
    return tracks
