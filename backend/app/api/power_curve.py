import json
import time as _time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.critical_power import FIT_DURATIONS_S, confidence_band, fit_cp_model, model_curve
from app.analytics.power import PDC_DURATIONS, best_power_for_duration
from app.config import settings
from app.db.models import Activity, Stream
from app.db.session import get_db_dep
from app.i18n import Lang, tr

router = APIRouter(tags=["power-curve"])

_BIKE_TYPES = {
    "Radfahrt", "Ride", "VirtualRide", "Virtuelle Radfahrt",
    "E-Bike-Radfahrt", "EBikeRide", "MountainBikeRide", "GravelRide",
}
_CACHE_FILE = Path(settings.db_path).parent / "power_curve.json"
_mem_cache: dict | None = None
_mem_cache_mtime: float = 0


@router.get("/power-curve")
def get_power_curve(lang: Lang = Query("de"), db: Session = Depends(get_db_dep)):
    global _mem_cache, _mem_cache_mtime

    # Serve from file cache (written by recompute)
    if _CACHE_FILE.exists():
        mtime = _CACHE_FILE.stat().st_mtime
        if _mem_cache is None or mtime > _mem_cache_mtime:
            raw = json.loads(_CACHE_FILE.read_text())
            raw.pop("activity_ids", None)  # bookkeeping for incremental updates, not for the client
            _mem_cache = _add_cp_model(raw)
            _mem_cache_mtime = mtime
        return _mem_cache

    # Fallback: compute recent 6-week PDC on demand (fast)
    return _add_cp_model(_compute_recent_pdc(db, lang))


def _compute_recent_pdc(db: Session, lang: Lang = "de") -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=6)).strftime("%Y-%m-%d")
    recent_ids = [
        r[0] for r in db.query(Activity.id)
        .filter(Activity.type.in_(_BIKE_TYPES))
        .filter(Activity.has_streams.is_(True))
        .filter(Activity.start_time >= cutoff)
        .all()
    ]
    return {
        "all_time": [],
        "recent_6w": _best_powers(db, recent_ids),
        "note": tr(
            lang,
            "`strava-dash recompute` ausführen, um die Gesamtkurve zu berechnen",
            "Run `strava-dash recompute` to compute all-time curve",
        ),
    }


def _best_powers(db: Session, activity_ids: list[int]) -> list[dict]:
    bests: dict[int, float] = {d: 0.0 for d in PDC_DURATIONS}
    for act_id in activity_ids:
        rows = (
            db.query(Stream.watts)
            .filter(Stream.activity_id == act_id, Stream.watts.isnot(None))
            .order_by(Stream.time_s)
            .all()
        )
        if not rows:
            continue
        watts = pd.Series([r.watts for r in rows], dtype=float)
        for dur in PDC_DURATIONS:
            p = best_power_for_duration(watts, dur)
            if p and p > bests[dur]:
                bests[dur] = p
    return [
        {"duration_s": dur, "power_w": round(p, 1)}
        for dur, p in bests.items()
        if p > 0
    ]


def _add_cp_model(payload: dict) -> dict:
    """Fit CP/W' model to all_time PDC and add to payload."""
    all_time = payload.get("all_time", [])
    best_efforts = {p["duration_s"]: p["power_w"] for p in all_time if p["power_w"] > 0}
    fit = fit_cp_model(best_efforts)
    if fit is None:
        return {**payload, "cp_model": None}

    # Smooth model curve over all standard durations
    smooth_durations = [1, 5, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600]
    curve = model_curve(fit.cp_w, fit.w_prime_kj, smooth_durations)
    lo, hi = confidence_band(fit.cp_w, fit.w_prime_kj, fit.standard_error, smooth_durations)

    return {
        **payload,
        "cp_model": {
            "cp_w": fit.cp_w,
            "w_prime_kj": fit.w_prime_kj,
            "r_squared": fit.r_squared,
            "standard_error": fit.standard_error,
            "curve": [
                {"duration_s": t, "power_w": p, "ci_lower": l, "ci_upper": u}
                for t, p, l, u in zip(smooth_durations, curve, lo, hi)
            ],
        },
    }


def update_pdc_cache(db: Session, full: bool = False) -> dict[str, int]:
    """Called by recompute to persist the PDC.

    Incremental by default: the cache remembers which rides are already in the
    all-time curve, so only new rides are read and merged in (best-of per
    duration). The 6-week curve is always rebuilt — rides drop out of the window
    over time, and it only covers a handful of rides.
    """
    bike_rides = (
        db.query(Activity.id, Activity.start_time)
        .filter(Activity.type.in_(_BIKE_TYPES))
        .filter(Activity.has_streams.is_(True))
        .all()
    )
    all_ids = {aid for aid, _ in bike_rides}

    cached: dict = {}
    if not full and _CACHE_FILE.exists():
        try:
            cached = json.loads(_CACHE_FILE.read_text())
        except (OSError, ValueError):
            cached = {}
    if "activity_ids" not in cached:  # no cache / pre-incremental format → rebuild
        cached = {"all_time": [], "activity_ids": []}

    included = set(cached["activity_ids"]) & all_ids
    new_ids = sorted(all_ids - included)
    all_time = _merge_best(cached["all_time"], _best_powers(db, new_ids)) if new_ids else cached["all_time"]

    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=6)).strftime("%Y-%m-%d")
    recent_ids = [aid for aid, start in bike_rides if start.strftime("%Y-%m-%d") >= cutoff]
    recent_6w = _best_powers(db, recent_ids)

    data = {"all_time": all_time, "recent_6w": recent_6w, "activity_ids": sorted(included | set(new_ids))}
    _CACHE_FILE.write_text(json.dumps(data))
    return {"rides_total": len(all_ids), "rides_read": len(new_ids) + len(recent_ids)}


def _merge_best(a: list[dict], b: list[dict]) -> list[dict]:
    best: dict[int, float] = {}
    for p in [*a, *b]:
        best[p["duration_s"]] = max(best.get(p["duration_s"], 0.0), p["power_w"])
    return [{"duration_s": d, "power_w": best[d]} for d in sorted(best)]
