"""Aerobic decoupling timeline endpoint."""

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.decoupling import decoupling_timeline
from app.db.models import Activity, Stream
from app.analytics.athlete import athlete_max_hr
from app.db.session import get_db_dep
from app.i18n import Lang, tr

router = APIRouter(tags=["analytics"])


def _streams_getter(db: Session):
    def get(activity_id: int) -> pd.DataFrame | None:
        rows = (
            db.query(Stream.time_s, Stream.hr, Stream.watts, Stream.velocity_smooth)
            .filter(Stream.activity_id == activity_id)
            .order_by(Stream.time_s)
            .all()
        )
        if not rows:
            return None
        return pd.DataFrame(rows, columns=["time_s", "hr", "watts", "velocity_smooth"])
    return get


@router.get("/decoupling-timeline")
def get_decoupling_timeline(
    lookback_days: int = Query(180, ge=30, le=365),
    hrmax: float | None = Query(None, ge=150, le=230, description="Override; defaults to the athlete max HR"),
    lang: Lang = Query("de"),
    db: Session = Depends(get_db_dep),
):
    rows = db.query(
        Activity.id, Activity.start_time, Activity.type, Activity.name,
        Activity.moving_time_s, Activity.avg_hr,
    ).filter(
        Activity.has_streams.is_(True),
        Activity.avg_hr.isnot(None),
        Activity.moving_time_s >= 45 * 60,
    ).all()

    df = pd.DataFrame(rows, columns=["id", "start_time", "type", "name", "moving_time_s", "avg_hr"])

    points = decoupling_timeline(
        df,
        streams_getter=_streams_getter(db),
        lookback_days=lookback_days,
        hrmax=hrmax or athlete_max_hr(),
    )

    # Linear regression for trend line
    trend_slope = None
    if len(points) >= 3:
        x = list(range(len(points)))
        y = [p.decoupling_pct for p in points]
        xm = sum(x) / len(x)
        ym = sum(y) / len(y)
        ss_xy = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y))
        ss_xx = sum((xi - xm) ** 2 for xi in x)
        trend_slope = round(ss_xy / ss_xx, 4) if ss_xx > 0 else 0.0

    return {
        "points": [p.model_dump() for p in points],
        "trend_slope_per_activity": trend_slope,
        "interpretation": _interpret(points, lang),
    }


def _interpret(points: list, lang: Lang = "de") -> str:
    if len(points) < 3:
        return tr(
            lang,
            "Zu wenige Z2–Z3-Aktivitäten für eine Trendanalyse (mind. 3 nötig).",
            "Too few Z2–Z3 activities for a trend analysis (at least 3 needed).",
        )
    first3 = sum(p.decoupling_pct for p in points[:3]) / 3
    last3  = sum(p.decoupling_pct for p in points[-3:]) / 3
    delta  = last3 - first3
    if delta < -1.0:
        return tr(
            lang,
            f"Durchschnittliche Entkopplung von {first3:.1f}% auf {last3:.1f}% gesunken — aerobe Basis verbessert sich.",
            f"Average decoupling dropped from {first3:.1f}% to {last3:.1f}% — aerobic base is improving.",
        )
    if delta > 1.0:
        return tr(
            lang,
            f"Entkopplung von {first3:.1f}% auf {last3:.1f}% gestiegen — mehr Z2–Z3-Volumen empfohlen.",
            f"Decoupling rose from {first3:.1f}% to {last3:.1f}% — more Z2–Z3 volume recommended.",
        )
    return tr(
        lang,
        f"Entkopplung stabil bei ~{last3:.1f}% — aerobe Basis konstant.",
        f"Decoupling stable at ~{last3:.1f}% — aerobic base is steady.",
    )
