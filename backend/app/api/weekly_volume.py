from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import Activity
from app.db.session import get_db_dep

router = APIRouter(tags=["analytics"])


def _sport(type_str: str) -> str:
    t = type_str.lower()
    if any(k in t for k in ("lauf", "run")): return "run"
    if any(k in t for k in ("rad", "ride", "bike")): return "ride"
    if any(k in t for k in ("schwimm", "swim")): return "swim"
    return "other"


@router.get("/weekly-volume")
def get_weekly_volume(
    weeks: int = Query(20, ge=4, le=104),
    db: Session = Depends(get_db_dep),
):
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
    rows = db.query(
        Activity.start_time, Activity.type,
        Activity.distance_m, Activity.moving_time_s,
        Activity.total_elevation_gain_m, Activity.tss,
    ).filter(Activity.start_time >= cutoff).all()

    # Aggregate by ISO week start (Monday)
    weekly: dict[str, dict] = defaultdict(lambda: {
        "run_km": 0.0, "ride_km": 0.0, "swim_km": 0.0, "other_km": 0.0,
        "total_tss": 0.0, "total_hours": 0.0, "count": 0,
    })

    for row in rows:
        dt = row.start_time
        week_start = (dt.date() - timedelta(days=dt.weekday())).isoformat()
        sport = _sport(row.type or "")
        weekly[week_start][f"{sport}_km"] += (row.distance_m or 0) / 1000
        weekly[week_start]["total_tss"] += row.tss or 0
        weekly[week_start]["total_hours"] += (row.moving_time_s or 0) / 3600
        weekly[week_start]["count"] += 1

    return [
        {
            "week": w,
            **{k: round(v, 1) for k, v in data.items() if k != "count"},
            "count": data["count"],
        }
        for w, data in sorted(weekly.items())
    ]
