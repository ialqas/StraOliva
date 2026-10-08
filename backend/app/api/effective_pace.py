"""Effective Z2–Z3 pace timeline endpoint."""

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.effective_pace import z2_pace_timeline
from app.db.models import Activity
from app.analytics.athlete import athlete_max_hr
from app.db.session import get_db_dep
from app.i18n import Lang

router = APIRouter(tags=["analytics"])


@router.get("/effective-pace")
def get_effective_pace(
    hrmax: float | None = Query(None, ge=150, le=230, description="Override; defaults to the athlete max HR"),
    lookback_days: int = Query(180, ge=30, le=365),
    lang: Lang = Query("de"),
    db: Session = Depends(get_db_dep),
):
    rows = db.query(
        Activity.id, Activity.start_time, Activity.type,
        Activity.distance_m, Activity.moving_time_s,
        Activity.avg_hr, Activity.name,
    ).filter(
        Activity.avg_hr.isnot(None),
        Activity.moving_time_s > 0,
        Activity.distance_m >= 4000,
    ).all()

    df = pd.DataFrame(
        rows,
        columns=["id", "start_time", "type", "distance_m", "moving_time_s", "avg_hr", "name"],
    )

    result = z2_pace_timeline(df, hrmax=hrmax or athlete_max_hr(), lookback_days=lookback_days, lang=lang)

    return {
        "points": [p.model_dump() for p in result.points],
        "trend_slope_sec_per_km_per_month": result.trend_slope_sec_per_km_per_month,
        "interpretation": result.interpretation,
    }
