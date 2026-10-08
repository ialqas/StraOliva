"""Tools describing the athlete's current training state."""

import json
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func

from app.analytics.athlete import athlete_max_hr
from app.analytics.decoupling import aerobic_decoupling, decoupling_timeline
from app.analytics.power import ftp_detection_diagnostics
from app.analytics.training_load import (
    DailyLoad,
    classify_trajectory,
    interpret_form,
    ramp_rate,
)
from app.config import settings
from app.db.models import Activity, FtpHistory, Stream, TrainingLoadDaily
from app.mcp_server.db import get_session
from app.mcp_server.models import FtpStatus, KeyWorkout, RecentForm, TrainingState, WeekSummary
from app.mcp_server.util import sport_label

_BIKE_TYPES = {
    "ride", "virtualride", "ebikeride", "mountainbikeride", "gravelbikeride",
    "radfahrt", "virtuelle radfahrt", "e-bike-radfahrt",
}

def _form_zone(tsb: float) -> str:
    """Classify TSB into a zone. Thresholds mirror app.analytics.training_load.interpret_form."""
    if tsb < -30:
        return "burnout"
    if tsb < -10:
        return "high_fatigue"
    if tsb <= 5:
        return "optimal"
    if tsb <= 25:
        return "fresh"
    return "detrained"


def _ftp_status(session) -> FtpStatus:
    today = date.today()

    if settings.ftp_w > 0:
        return FtpStatus(
            value_w=settings.ftp_w,
            source="manual",
            last_updated=None,
            age_days=None,
            is_stale=False,
            diagnostic=None,
        )

    row = session.query(FtpHistory).order_by(FtpHistory.id.desc()).first()
    if row:
        last_updated = date.fromisoformat(row.date)
        age_days = (today - last_updated).days
        source = row.source if row.source in ("auto", "manual") else "auto"
        return FtpStatus(
            value_w=int(row.ftp_w),
            source=source,
            last_updated=last_updated,
            age_days=age_days,
            is_stale=age_days > 60,
            diagnostic=None,
        )

    diag = _ftp_diagnostics(session)
    return FtpStatus(
        value_w=None,
        source="none",
        last_updated=None,
        age_days=None,
        is_stale=True,
        diagnostic=diag.reason,
    )


def _ftp_diagnostics(session):
    rows = (
        session.query(Activity.id, Activity.start_time, Activity.type, Activity.has_streams)
        .filter(func.lower(Activity.type).in_(_BIKE_TYPES))
        .all()
    )
    activities_df = pd.DataFrame(
        rows, columns=["id", "start_time", "type", "has_streams"]
    )

    watts_series_by_id: dict[int, pd.Series] = {}
    for row in rows:
        if not row.has_streams:
            continue
        stream_rows = (
            session.query(Stream.watts)
            .filter(Stream.activity_id == row.id)
            .order_by(Stream.time_s)
            .all()
        )
        if stream_rows:
            watts_series_by_id[row.id] = pd.Series([r.watts for r in stream_rows], dtype=float)

    return ftp_detection_diagnostics(activities_df, watts_series_by_id)


def _get_training_state() -> TrainingState:
    with get_session() as session:
        latest = session.query(TrainingLoadDaily).order_by(TrainingLoadDaily.date.desc()).first()

        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday
        four_weeks_ago = week_start - timedelta(weeks=4)

        tss_this_week = session.query(func.sum(Activity.tss)).filter(
            Activity.start_time >= week_start.isoformat(),
            Activity.tss.isnot(None),
        ).scalar() or 0.0

        hours_this_week = (
            session.query(func.sum(Activity.moving_time_s)).filter(
                Activity.start_time >= week_start.isoformat(),
                Activity.moving_time_s.isnot(None),
            ).scalar() or 0.0
        ) / 3600

        tss_4w = session.query(func.sum(Activity.tss)).filter(
            Activity.start_time >= four_weeks_ago.isoformat(),
            Activity.start_time < week_start.isoformat(),
            Activity.tss.isnot(None),
        ).scalar() or 0.0
        tss_4week_avg = tss_4w / 4

        recent_tss_7d = session.query(func.sum(Activity.tss)).filter(
            Activity.start_time >= (today - timedelta(days=7)).isoformat(),
            Activity.tss.isnot(None),
        ).scalar() or 0.0

        # Ramp rate from the last ~5 weeks of daily loads (4-week CTL delta)
        loads_rows = (
            session.query(TrainingLoadDaily)
            .order_by(TrainingLoadDaily.date.desc())
            .limit(29)
            .all()
        )
        loads = [
            DailyLoad(date=r.date, ctl=r.ctl, atl=r.atl, tsb=r.tsb, total_tss=r.total_tss)
            for r in reversed(loads_rows)
        ]
        ramp = ramp_rate(loads, weeks=4)
        trajectory = classify_trajectory(ramp)

        last_activity = session.query(Activity).order_by(Activity.start_time.desc()).first()
        last_activity_date = last_activity.start_time.date() if last_activity else None

        ctl = latest.ctl if latest else 0.0
        atl = latest.atl if latest else 0.0
        tsb = latest.tsb if latest else 0.0

        form_interpretation = interpret_form(
            ctl=ctl, atl=atl, tsb=tsb, recent_tss_7d=float(recent_tss_7d),
        )

        if tss_4week_avg > 0:
            volume_vs_4w_avg = round((tss_this_week - tss_4week_avg) / tss_4week_avg * 100, 1)
        else:
            volume_vs_4w_avg = 0.0

        return TrainingState(
            ctl=round(ctl, 1),
            atl=round(atl, 1),
            tsb=round(tsb, 1),
            form_zone=_form_zone(tsb),
            form_interpretation=form_interpretation,
            ramp_rate_per_week=ramp,
            ramp_rate_classification=trajectory,
            weekly_tss=round(tss_this_week),
            weekly_hours=round(hours_this_week, 1),
            weekly_volume_vs_4w_avg_pct=volume_vs_4w_avg,
            last_activity_date=last_activity_date,
            ftp=_ftp_status(session),
        )


def _activity_decoupling_pct(session, activity: Activity) -> float | None:
    """Decoupling for a single activity, or None if too short / not enough data."""
    if not activity.has_streams or not activity.moving_time_s or activity.moving_time_s < 45 * 60:
        return None
    rows = (
        session.query(Stream.time_s, Stream.hr, Stream.watts, Stream.velocity_smooth)
        .filter(Stream.activity_id == activity.id)
        .order_by(Stream.time_s)
        .all()
    )
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["time_s", "hr", "watts", "velocity_smooth"])
    dec = aerobic_decoupling(df)
    return dec.decoupling_pct if dec else None


def _key_workout(session, activity: Activity) -> KeyWorkout:
    sport = sport_label(activity.type)
    distance_km = round((activity.distance_m or 0) / 1000, 1)
    duration_min = round((activity.moving_time_s or 0) / 60, 1)
    tss = round(activity.tss or 0)

    parts = [sport]
    if distance_km:
        parts.append(f"{distance_km} km")
    parts.append(f"TSS {tss}")

    dec = _activity_decoupling_pct(session, activity)
    if dec is not None:
        parts.append(f"decoupling {dec:+.1f}%")

    return KeyWorkout(
        activity_id=activity.id,
        date=activity.start_time.date(),
        sport=sport,
        distance_km=distance_km,
        duration_min=duration_min,
        tss=tss,
        summary=" · ".join(parts),
    )


def _decoupling_trend(session, weeks: int) -> tuple[float | None, float | None]:
    """Return (recent_avg_pct, trend_pct) comparing the last `weeks` to the 8 weeks before that."""
    lookback_days = weeks * 7 + 56
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()

    rows = (
        session.query(
            Activity.id, Activity.start_time, Activity.moving_time_s,
            Activity.avg_hr, Activity.type, Activity.name,
        )
        .filter(Activity.start_time >= cutoff)
        .all()
    )
    if not rows:
        return None, None

    activities_df = pd.DataFrame(
        rows, columns=["id", "start_time", "moving_time_s", "avg_hr", "type", "name"]
    )

    def streams_getter(activity_id: int) -> pd.DataFrame | None:
        srows = (
            session.query(Stream.time_s, Stream.hr, Stream.watts, Stream.velocity_smooth)
            .filter(Stream.activity_id == activity_id)
            .order_by(Stream.time_s)
            .all()
        )
        if not srows:
            return None
        return pd.DataFrame(srows, columns=["time_s", "hr", "watts", "velocity_smooth"])

    points = decoupling_timeline(activities_df, streams_getter, hrmax=athlete_max_hr(), lookback_days=lookback_days)
    if not points:
        return None, None

    recent_cutoff = date.today() - timedelta(weeks=weeks)
    recent = [p.decoupling_pct for p in points if date.fromisoformat(p.date) >= recent_cutoff]
    prior = [p.decoupling_pct for p in points if date.fromisoformat(p.date) < recent_cutoff]

    recent_avg = round(sum(recent) / len(recent), 2) if recent else None
    prior_avg = round(sum(prior) / len(prior), 2) if prior else None

    trend = round(recent_avg - prior_avg, 2) if recent_avg is not None and prior_avg is not None else None
    return recent_avg, trend


def _get_recent_form(weeks: int = 4) -> RecentForm:
    with get_session() as session:
        period_start = (date.today() - timedelta(weeks=weeks)).isoformat()

        activities = (
            session.query(Activity)
            .filter(Activity.start_time >= period_start)
            .order_by(Activity.start_time)
            .all()
        )

        # ── Volume by week ───────────────────────────────────────────────
        weekly: dict[date, dict] = {}
        for a in activities:
            week_start = a.start_time.date() - timedelta(days=a.start_time.weekday())
            wk = weekly.setdefault(week_start, {
                "tss": 0.0, "hours": 0.0, "distance_km": 0.0, "count": 0, "sports": {},
            })
            wk["tss"] += a.tss or 0
            wk["hours"] += (a.moving_time_s or 0) / 3600
            wk["distance_km"] += (a.distance_m or 0) / 1000
            wk["count"] += 1
            sport = sport_label(a.type)
            wk["sports"][sport] = wk["sports"].get(sport, 0) + 1

        volume_by_week = [
            WeekSummary(
                week_start=ws,
                tss=round(d["tss"]),
                hours=round(d["hours"], 1),
                distance_km=round(d["distance_km"], 1),
                activities_count=d["count"],
                sports=d["sports"],
            )
            for ws, d in sorted(weekly.items())
        ]

        # ── Key workouts: top 5 by TSS ──────────────────────────────────────
        ranked = sorted((a for a in activities if a.tss), key=lambda a: a.tss, reverse=True)
        key_workouts = [_key_workout(session, a) for a in ranked[:5]]

        # ── PR efforts ───────────────────────────────────────────────────
        pr_efforts: list[str] = []
        for a in activities:
            if not a.raw_json:
                continue
            try:
                raw = json.loads(a.raw_json)
            except Exception:
                continue
            count = raw.get("achievement_count") or 0
            if count:
                label = "segment achievement" if count == 1 else "segment achievements"
                pr_efforts.append(f"{count} {label} on {a.start_time.date().isoformat()} — {a.name}")

        # ── Decoupling trend ─────────────────────────────────────────────
        decoupling_recent_avg, decoupling_trend = _decoupling_trend(session, weeks)

        return RecentForm(
            weeks_covered=weeks,
            volume_by_week=volume_by_week,
            key_workouts=key_workouts,
            decoupling_trend_pct=decoupling_trend,
            decoupling_recent_avg_pct=decoupling_recent_avg,
            pr_efforts=pr_efforts,
        )


def register(mcp):
    @mcp.tool()
    def get_training_state() -> TrainingState:
        """
        Current training state at a glance: fitness, fatigue, form, ramp rate,
        weekly load, and current FTP. Call this first at the start of any
        coaching conversation to ground the discussion in real data.
        """
        return _get_training_state()

    @mcp.tool()
    def get_recent_form(weeks: int = 4) -> RecentForm:
        """
        Recent training history with weekly volume, key sessions, decoupling
        trend, and any PR efforts. Use this when discussing how the last
        training block went or whether to adjust the upcoming week.

        weeks: how many weeks back to summarize (default 4).
        """
        if weeks < 1:
            raise ValueError("weeks must be >= 1.")
        return _get_recent_form(weeks)
