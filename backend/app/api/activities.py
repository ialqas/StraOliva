import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Activity
from app.db.session import get_db_dep

router = APIRouter(tags=["activities"])


@router.get("/activities")
def list_activities(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: str | None = None,
    db: Session = Depends(get_db_dep),
):
    q = db.query(Activity).order_by(Activity.start_time.desc())
    if type:
        q = q.filter(Activity.type == type)

    total = q.count()
    activities = q.offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [_serialize(a) for a in activities],
    }


@router.get("/activities/types")
def get_activity_types(db: Session = Depends(get_db_dep)):
    """Returns distinct activity types with counts."""
    rows = (
        db.query(Activity.type, func.count(Activity.id).label("count"))
        .group_by(Activity.type)
        .order_by(func.count(Activity.id).desc())
        .all()
    )
    return [{"type": t, "count": c} for t, c in rows]


@router.get("/activities/{activity_id}")
def get_activity(activity_id: int, db: Session = Depends(get_db_dep)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return _serialize(activity, include_raw=True)


def _serialize(a: Activity, include_raw: bool = False) -> dict:
    d = {
        "id": a.id,
        "name": a.name,
        "type": a.type,
        "start_time": a.start_time.isoformat() if a.start_time else None,
        "distance_m": a.distance_m,
        "moving_time_s": a.moving_time_s,
        "elapsed_time_s": a.elapsed_time_s,
        "total_elevation_gain_m": a.total_elevation_gain_m,
        "avg_hr": a.avg_hr,
        "max_hr": a.max_hr,
        "avg_watts": a.avg_watts,
        "weighted_avg_watts": a.weighted_avg_watts,
        "kilojoules": a.kilojoules,
        "tss": a.tss,
        "has_streams": a.has_streams,
    }
    if include_raw and a.raw_json:
        try:
            raw = json.loads(a.raw_json)
            d["kudos_count"] = raw.get("kudos_count")
            d["achievement_count"] = raw.get("achievement_count")
            d["map_polyline"] = raw.get("map", {}).get("summary_polyline")
        except Exception:
            pass
    return d
