"""Per-activity analytics computed on demand from stored streams."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.decoupling import aerobic_decoupling
from app.analytics.splits import detect_split_anomalies
from app.analytics.zones import HR_ZONE_BOUNDS, hr_zones_time, power_zones_time
from app.db.models import Activity, FtpHistory, Lap, Stream
from app.analytics.athlete import athlete_max_hr
from app.db.session import get_db_dep
from app.i18n import Lang

router = APIRouter(tags=["analytics"])

_WARMUP_S = 600


def _hr_drift(df: pd.DataFrame) -> float | None:
    """% HR increase from first half to second half (after warmup). Positive = drift."""
    trimmed = df[df["time_s"] >= _WARMUP_S]
    if "hr" not in trimmed.columns or trimmed["hr"].notna().sum() < 60:
        return None
    mid = trimmed["time_s"].median()
    hr1 = trimmed.loc[trimmed["time_s"] <= mid, "hr"].mean()
    hr2 = trimmed.loc[trimmed["time_s"] > mid, "hr"].mean()
    if not hr1 or hr1 <= 0:
        return None
    return round((hr2 - hr1) / hr1 * 100, 2)


def _avg_hr_zone(avg_hr: float | None, hrmax: float) -> str | None:
    if avg_hr is None:
        return None
    pct = avg_hr / hrmax
    for zone, lo, hi in HR_ZONE_BOUNDS:
        if lo <= pct < hi:
            return zone
    return "Z5"


@router.get("/activities/{activity_id}/analytics")
def get_activity_analytics(
    activity_id: int,
    lang: Lang = Query("de"),
    db: Session = Depends(get_db_dep),
):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(404, "Activity not found")

    ftp_row = db.query(FtpHistory).order_by(FtpHistory.id.desc()).first()
    ftp_w = ftp_row.ftp_w if ftp_row else None

    is_ride = any(k in (activity.type or "").lower()
                  for k in ("ride", "bike", "velo", "rad"))

    np_w = activity.weighted_avg_watts
    intensity_factor: float | None = None
    if np_w and ftp_w and ftp_w > 0:
        intensity_factor = round(np_w / ftp_w, 3)
    elif not is_ride and activity.tss and activity.moving_time_s and activity.moving_time_s > 0:
        # Equivalent IF from rTSS: IF² × hours = TSS/100 → IF = sqrt(TSS / (hours × 100))
        hours = activity.moving_time_s / 3600
        if hours > 0:
            intensity_factor = round((activity.tss / (hours * 100)) ** 0.5, 3)

    result: dict = {
        "decoupling_pct": None,
        "decoupling_effort": None,
        "hr_drift_pct": None,
        "np_w": np_w,
        "intensity_factor": intensity_factor,
        "avg_hr_zone": _avg_hr_zone(activity.avg_hr, athlete_max_hr()),
        "ftp_w": ftp_w,
        "zones_hr": None,
        "zones_power": None,
        "split_anomalies": [],
    }

    # Split anomalies (from laps, no streams needed)
    laps = (
        db.query(Lap).filter(Lap.activity_id == activity_id).order_by(Lap.lap_index).all()
    )
    if laps:
        laps_dicts = [
            {
                "lap_index": lap.lap_index,
                "distance_m": lap.distance_m,
                "time_s": lap.time_s,
                "avg_watts": lap.avg_watts,
                "avg_speed_ms": lap.avg_speed_ms,
            }
            for lap in laps
        ]
        result["split_anomalies"] = detect_split_anomalies(laps_dicts, is_ride, lang=lang)

    if not activity.has_streams:
        return result

    rows = (
        db.query(Stream.time_s, Stream.hr, Stream.watts, Stream.velocity_smooth)
        .filter(Stream.activity_id == activity_id)
        .order_by(Stream.time_s)
        .all()
    )
    if not rows:
        return result

    df = pd.DataFrame(rows, columns=["time_s", "hr", "watts", "velocity_smooth"])

    dec = aerobic_decoupling(df)
    if dec:
        result["decoupling_pct"] = dec.decoupling_pct
        result["decoupling_effort"] = dec.effort_col

    result["hr_drift_pct"] = _hr_drift(df)
    result["zones_hr"] = hr_zones_time(df, hrmax=athlete_max_hr())
    if is_ride and ftp_w and ftp_w > 0:
        result["zones_power"] = power_zones_time(df, ftp_w=ftp_w)

    return result
