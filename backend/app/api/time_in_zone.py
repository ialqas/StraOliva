"""Weekly time-in-zone endpoint."""

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.zones import weekly_time_in_zone
from app.db.models import Activity, Stream
from app.analytics.athlete import athlete_max_hr
from app.db.session import get_db_dep
from app.i18n import Lang, tr

router = APIRouter(tags=["analytics"])


def _streams_getter(db: Session):
    def get(activity_id: int) -> pd.DataFrame | None:
        rows = (
            db.query(Stream.time_s, Stream.hr, Stream.watts)
            .filter(Stream.activity_id == activity_id)
            .order_by(Stream.time_s)
            .all()
        )
        if not rows:
            return None
        return pd.DataFrame(rows, columns=["time_s", "hr", "watts"])
    return get


@router.get("/time-in-zone")
def get_time_in_zone(
    sport: str = Query("all", pattern="^(all|run|bike)$"),
    weeks: int = Query(12, ge=4, le=52),
    ftp_w: float | None = Query(None, ge=50, le=600),
    hrmax: float | None = Query(None, ge=150, le=230, description="Override; defaults to the athlete max HR"),
    lang: Lang = Query("de"),
    db: Session = Depends(get_db_dep),
):
    rows = db.query(
        Activity.id, Activity.start_time, Activity.type,
    ).filter(
        Activity.has_streams.is_(True),
    ).all()

    df = pd.DataFrame(rows, columns=["id", "start_time", "type"])

    sport_filter = None if sport == "all" else sport

    result = weekly_time_in_zone(
        df,
        streams_getter=_streams_getter(db),
        sport_filter=sport_filter,
        ftp_w=ftp_w,
        hrmax=hrmax or athlete_max_hr(),
        lookback_weeks=weeks,
    )

    # Compute polarization summary for last 4 weeks
    if result:
        recent = result[-4:]
        total = sum(sum(w.zones.values()) for w in recent)
        z12 = sum(w.zones.get("Z1", 0) + w.zones.get("Z2", 0) for w in recent)
        z45 = sum(w.zones.get("Z4", 0) + w.zones.get("Z5", 0) for w in recent)
        pct12 = round(z12 / total * 100) if total > 0 else 0
        pct45 = round(z45 / total * 100) if total > 0 else 0
        if pct12 >= 70 and pct45 >= 10:
            summary = f"Z1+Z2: {pct12}% · Z4+Z5: {pct45}% — " + tr(
                lang, "nahe polarisierter Verteilung", "close to a polarized distribution"
            )
        elif pct12 >= 80:
            summary = f"Z1+Z2: {pct12}% · Z4+Z5: {pct45}% — " + tr(
                lang, "sehr aerobes Training", "very aerobic training"
            )
        else:
            summary = f"Z1+Z2: {pct12}% · Z4+Z5: {pct45}%"
    else:
        summary = ""

    return {
        "weeks": [w.model_dump() for w in result],
        "summary": summary,
    }
