from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.training_load import (
    classify_trajectory,
    interpret_form,
    ramp_rate,
)
from app.db.models import Activity, FtpHistory, TrainingLoadDaily
from app.analytics.athlete import max_hr_info, threshold_pace_info
from app.db.session import get_db_dep
from app.i18n import Lang

router = APIRouter(tags=["stats"])


@router.get("/stats")
def get_stats(lang: Lang = Query("de"), db: Session = Depends(get_db_dep)):
    latest = db.query(TrainingLoadDaily).order_by(TrainingLoadDaily.date.desc()).first()

    today = date.today()
    week_start = today - timedelta(days=today.weekday())       # Monday
    last_week_start = week_start - timedelta(days=7)

    # ── This week ────────────────────────────────────────────────────────────
    tss_this_week = db.query(func.sum(Activity.tss)).filter(
        Activity.start_time >= week_start.isoformat(),
        Activity.tss.isnot(None),
    ).scalar() or 0.0

    tss_last_week = db.query(func.sum(Activity.tss)).filter(
        Activity.start_time >= last_week_start.isoformat(),
        Activity.start_time < week_start.isoformat(),
        Activity.tss.isnot(None),
    ).scalar() or 0.0

    hours_this_week = (
        db.query(func.sum(Activity.moving_time_s)).filter(
            Activity.start_time >= week_start.isoformat(),
            Activity.moving_time_s.isnot(None),
        ).scalar() or 0.0
    ) / 3600

    acts_this_week = db.query(func.count(Activity.id)).filter(
        Activity.start_time >= week_start.isoformat(),
    ).scalar() or 0

    avg_hr_this_week = db.query(func.avg(Activity.avg_hr)).filter(
        Activity.start_time >= week_start.isoformat(),
        Activity.avg_hr.isnot(None),
    ).scalar()

    # ── 4-week average weekly TSS ─────────────────────────────────────────────
    four_weeks_ago = week_start - timedelta(weeks=4)
    tss_4w = db.query(func.sum(Activity.tss)).filter(
        Activity.start_time >= four_weeks_ago.isoformat(),
        Activity.start_time < week_start.isoformat(),
        Activity.tss.isnot(None),
    ).scalar() or 0.0
    tss_4week_avg = round(tss_4w / 4, 1)

    # ── Ramp rate & trajectory (from last 28 days of TrainingLoadDaily) ──────
    loads_28 = (
        db.query(TrainingLoadDaily)
        .order_by(TrainingLoadDaily.date.desc())
        .limit(28)
        .all()
    )
    loads_28 = list(reversed(loads_28))

    ctl_now = latest.ctl if latest else 0.0
    ctl_28d_ago = loads_28[0].ctl if loads_28 else ctl_now
    ramp = round((ctl_now - ctl_28d_ago) / 4, 2)   # CTL change per week
    trajectory = classify_trajectory(ramp)

    # ── Form interpretation ──────────────────────────────────────────────────
    recent_tss_7d = db.query(func.sum(Activity.tss)).filter(
        Activity.start_time >= (today - timedelta(days=7)).isoformat(),
        Activity.tss.isnot(None),
    ).scalar() or 0.0

    form_text = ""
    if latest:
        form_text = interpret_form(
            ctl=latest.ctl,
            atl=latest.atl,
            tsb=latest.tsb,
            recent_tss_7d=float(recent_tss_7d),
            lang=lang,
        )

    # ── FTP ──────────────────────────────────────────────────────────────────
    ftp_row = db.query(FtpHistory).order_by(FtpHistory.id.desc()).first()
    threshold_pace, threshold_source = threshold_pace_info()
    max_hr, max_hr_source = max_hr_info()

    # Activity type breakdown this week
    type_counts = (
        db.query(Activity.type, func.count(Activity.id))
        .filter(Activity.start_time >= week_start.isoformat())
        .group_by(Activity.type)
        .all()
    )

    return {
        "ctl": round(latest.ctl, 1) if latest else 0.0,
        "atl": round(latest.atl, 1) if latest else 0.0,
        "tsb": round(latest.tsb, 1) if latest else 0.0,
        "tss_this_week": round(tss_this_week, 1),
        "tss_last_week": round(tss_last_week, 1),
        "tss_4week_avg": tss_4week_avg,
        "hours_this_week": round(hours_this_week, 1),
        "activities_this_week": acts_this_week,
        "avg_hr_this_week": round(avg_hr_this_week, 0) if avg_hr_this_week else None,
        "ramp_rate": ramp,
        "fitness_trajectory": trajectory,
        "form_interpretation": form_text,
        "ftp_w": ftp_row.ftp_w if ftp_row else None,
        "ftp_date": ftp_row.date if ftp_row and ftp_row.date else None,
        "ftp_source": ftp_row.source if ftp_row else None,
        "threshold_pace_ms": threshold_pace,
        "threshold_pace_source": threshold_source,
        "max_hr": max_hr,
        "max_hr_source": max_hr_source,
        "type_counts_this_week": {t: c for t, c in type_counts},
    }
