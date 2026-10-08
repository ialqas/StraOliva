from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import Activity
from app.db.session import get_db_dep

router = APIRouter(tags=["analytics"])


@router.get("/monthly-stats")
def get_monthly_stats(
    months: int = Query(12, ge=3, le=60),
    db: Session = Depends(get_db_dep),
):
    today = date.today()
    cutoff_year = today.year
    cutoff_month = today.month - months
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff = date(cutoff_year, cutoff_month, 1).isoformat()

    rows = db.query(
        Activity.start_time, Activity.type,
        Activity.distance_m, Activity.total_elevation_gain_m,
        Activity.tss, Activity.moving_time_s,
    ).filter(Activity.start_time >= cutoff).all()

    monthly: dict[str, dict] = defaultdict(lambda: {
        "distance_km": 0.0, "elevation_m": 0.0,
        "tss": 0.0, "hours": 0.0, "count": 0,
        "run_km": 0.0, "ride_km": 0.0,
        "run_hours": 0.0, "ride_hours": 0.0,
        "run_elevation": 0.0, "ride_elevation": 0.0,
        "run_count": 0, "ride_count": 0,
    })

    for row in rows:
        key = row.start_time.strftime("%Y-%m")
        dist_km = (row.distance_m or 0) / 1000
        elev = row.total_elevation_gain_m or 0
        hours = (row.moving_time_s or 0) / 3600
        monthly[key]["distance_km"] += dist_km
        monthly[key]["elevation_m"] += elev
        monthly[key]["tss"] += row.tss or 0
        monthly[key]["hours"] += hours
        monthly[key]["count"] += 1
        t = (row.type or "").lower()
        if any(k in t for k in ("lauf", "run")):
            monthly[key]["run_km"] += dist_km
            monthly[key]["run_hours"] += hours
            monthly[key]["run_elevation"] += elev
            monthly[key]["run_count"] += 1
        elif any(k in t for k in ("rad", "ride", "bike")):
            monthly[key]["ride_km"] += dist_km
            monthly[key]["ride_hours"] += hours
            monthly[key]["ride_elevation"] += elev
            monthly[key]["ride_count"] += 1

    return [
        {
            "month": m,
            "distance_km": round(data["distance_km"], 1),
            "elevation_m": round(data["elevation_m"]),
            "tss": round(data["tss"]),
            "hours": round(data["hours"], 1),
            "count": data["count"],
            "run_km": round(data["run_km"], 1),
            "ride_km": round(data["ride_km"], 1),
            "run_hours": round(data["run_hours"], 1),
            "ride_hours": round(data["ride_hours"], 1),
            "run_elevation": round(data["run_elevation"]),
            "ride_elevation": round(data["ride_elevation"]),
            "run_count": data["run_count"],
            "ride_count": data["ride_count"],
        }
        for m, data in sorted(monthly.items())
    ]
