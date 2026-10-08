"""
Recompute pipeline: DB → analytics → DB.

Steps:
  1. Auto-detect or use configured FTP / threshold pace.
  2. Compute TSS — only for activities without one, unless the TSS inputs
     changed (or `full=True`), then for all of them.
  3. Aggregate to daily TSS, compute CTL/ATL/TSB, write training_load_daily.
  4. Update the power-duration curve and heatmap caches (new activities only).
"""

import json
import time

import pandas as pd
from sqlalchemy import func
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from app.analytics import power as power_analytics
from app.analytics import tss as tss_calc
from app.analytics import training_load as tl
from app.analytics.streams import normalized_power
from app.analytics.athlete import (
    FALLBACK_MAX_HR,
    MAX_HR_STATE_KEY,
    THRESHOLD_PACE_STATE_KEY,
    best_sustained_speed,
    read_state,
    sustained_max_hr,
    write_state,
)
from app.config import settings
from app.db.models import Activity, AppState, FtpHistory, Stream, TrainingLoadDaily
from app.db.session import get_db

console = Console()

# Bump when a TSS formula changes — forces one full TSS recompute on the next run.
TSS_VERSION = 2  # 2: hrTSS uses the athlete max HR instead of the activity peak
_TSS_STATE_KEY = "tss_inputs"

# Activity types treated as cycling (English from API + German from bulk export)
_BIKE_TYPES = {
    "ride", "virtualride", "ebikeride", "mountainbikeride", "gravelbikeride",
    "radfahrt", "virtuelle radfahrt", "e-bike-radfahrt",
}
_RUN_TYPES = {
    "run", "virtualrun", "trailrun",
    "lauf", "virtueller lauf", "traillauf",
}


def sync_and_recompute(skip_sync: bool = False, full: bool = False) -> dict:
    """Full pipeline shared by the CLI and the dashboard sync button:
    sync new activities from Strava (best-effort), then recompute analytics.

    Incremental by default — only new activities are processed. `full=True`
    recomputes TSS, power curve and heatmap for all activities.
    Mirrors `strava-dash recompute` exactly.
    """
    from app.db.session import init_db

    init_db()

    sync_stats = {"new": 0, "updated": 0, "streams_ok": 0, "errors": 0}
    description_stats = {"fetched": 0, "with_text": 0, "errors": 0}
    sync_error: str | None = None
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    if not skip_sync:
        console.print("Syncing new activities from Strava …")
        try:
            from app.strava.client import StravaClient
            from app.sync.api import sync as run_sync
            from app.sync.descriptions import sync_descriptions

            client = StravaClient()
            sync_stats = run_sync(client, full=False)
            console.print(
                f"  New: {sync_stats['new']}  Updated: {sync_stats['updated']}  "
                f"Streams: {sync_stats['streams_ok']}  Errors: {sync_stats['errors']}"
            )

            # Descriptions need the per-activity detail endpoint, so they are a
            # separate pass over a recent window (see sync/descriptions.py).
            console.print("Fetching activity descriptions …")
            description_stats = sync_descriptions(client)
            console.print(
                f"  Descriptions: {description_stats['fetched']} fetched, "
                f"{description_stats['with_text']} non-empty"
            )
        except Exception as exc:
            sync_error = str(exc)
            console.print(f"[yellow]⚠ Sync failed (continuing with recompute): {exc}[/yellow]")
        timings["strava_sync"] = round(time.perf_counter() - t0, 2)

    recompute_stats = recompute_all(full=full)
    timings.update(recompute_stats.pop("timings"))
    timings["total"] = round(time.perf_counter() - t0, 2)
    console.print("Timings: " + "  ".join(f"{k} {v:.1f}s" for k, v in timings.items()))
    return {
        "sync": sync_stats,
        "descriptions": description_stats,
        "sync_error": sync_error,
        "timings": timings,
        **recompute_stats,
    }


def recompute_all(full: bool = False) -> dict:
    stats: dict = {
        "tss_computed": 0,
        "tss_skipped": 0,
        "tss_mode": "incremental",
        "days_written": 0,
        "ftp_w": None,
        "threshold_pace_ms": None,
    }
    timings: dict[str, float] = {}
    t = time.perf_counter()

    # ── Step 1: which activities need TSS ─────────────────────────────────────
    # Stored TSS only goes stale when its inputs change. The fingerprint holds the
    # *configured* values only: auto-detected FTP / threshold pace / max HR follow
    # your current form and apply to new activities, instead of silently rewriting
    # all past TSS (and with it the whole CTL history). Activities TSS can't be
    # computed for (no HR / power / pace) stay NULL and are retried — that's cheap.
    fingerprint = _tss_fingerprint()
    with get_db() as db:
        state = db.get(AppState, _TSS_STATE_KEY)
        full_tss = full or state is None or state.value != fingerprint
        query = db.query(Activity).order_by(Activity.start_time)
        if not full_tss:
            query = query.filter(Activity.tss.is_(None))
        activities = query.all()
    stats["tss_mode"] = "full" if full_tss else "incremental"
    batch_ids = [a.id for a in activities]

    # ── Step 2: athlete values (pinned in .env, or auto-detected) ─────────────
    max_hr = _resolve_max_hr(batch_ids)
    stats["max_hr"] = max_hr
    console.print(f"Max HR: [bold]{max_hr:.0f}[/bold]")

    ftp = _resolve_and_persist_ftp(batch_ids)
    stats["ftp_w"] = ftp
    if ftp:
        console.print(f"FTP: [bold]{ftp} W[/bold]")
    else:
        console.print("[yellow]FTP not set — bike TSS will use hr fallback.[/yellow]")

    threshold_pace = _resolve_threshold_pace(max_hr, batch_ids)
    stats["threshold_pace_ms"] = threshold_pace
    if threshold_pace:
        pace_per_km = 1000 / threshold_pace
        mm, ss = divmod(int(pace_per_km), 60)
        console.print(f"Threshold pace: [bold]{mm}:{ss:02d} /km[/bold]")
    else:
        console.print("[yellow]Threshold pace not set — run TSS will use hr fallback.[/yellow]")

    console.print(f"Computing TSS ({stats['tss_mode']}, {len(activities)} activities) …")
    updates: dict[int, float] = {}
    for act in activities:
        try:
            tss_val = _compute_tss(act, ftp, threshold_pace, max_hr)
        except Exception as exc:
            console.print(f"  [yellow]✗ {act.name}: {exc}[/yellow]")
            tss_val = None
        if tss_val is not None:
            updates[act.id] = tss_val
    stats["tss_computed"] = len(updates)
    stats["tss_skipped"] = len(activities) - len(updates)

    # One transaction for all writes (was one commit per activity)
    with get_db() as db:
        if updates:
            db.bulk_update_mappings(Activity, [{"id": aid, "tss": v} for aid, v in updates.items()])
        db.merge(AppState(key=_TSS_STATE_KEY, value=fingerprint))
    timings["tss"] = round(time.perf_counter() - t, 2)

    # ── Step 3: aggregate daily TSS and compute CTL/ATL/TSB ──────────────────
    # Always over the full history — cheap, and CTL/ATL are running averages.
    t = time.perf_counter()
    with get_db() as db:
        rows = db.query(Activity.start_time, Activity.tss).all()

    activities_df = pd.DataFrame(rows, columns=["start_time", "tss"])
    daily_tss = tl.compute_daily_tss(activities_df)
    loads = tl.compute_ctl_atl_tsb(daily_tss)

    with get_db() as db:
        db.query(TrainingLoadDaily).delete()
        db.add_all([
            TrainingLoadDaily(
                date=load.date,
                ctl=load.ctl,
                atl=load.atl,
                tsb=load.tsb,
                total_tss=load.total_tss,
            )
            for load in loads
        ])

    stats["days_written"] = len(loads)
    timings["training_load"] = round(time.perf_counter() - t, 2)

    # ── Step 4: power-duration curve (new rides only) ─────────────────────────
    t = time.perf_counter()
    from app.api.power_curve import update_pdc_cache

    with get_db() as db:
        pdc = update_pdc_cache(db, full=full)
    console.print(f"  Power curve: {pdc['rides_read']} of {pdc['rides_total']} rides read")
    timings["power_curve"] = round(time.perf_counter() - t, 2)

    # ── Step 5: heatmap GPS tracks (new activities only) ──────────────────────
    t = time.perf_counter()
    from app.api.heatmap import update_cache as update_heatmap

    with get_db() as db:
        hm = update_heatmap(db, full=full)
    console.print(f"  Heatmap: {hm['tracks_added']} new activities")
    timings["heatmap"] = round(time.perf_counter() - t, 2)

    stats["timings"] = timings
    return stats


def _tss_fingerprint() -> str:
    return json.dumps(
        {
            "version": TSS_VERSION,
            "ftp_w_config": settings.ftp_w,
            "threshold_pace_ms_config": settings.threshold_pace_ms,
            "max_hr_config": settings.max_hr,
            "rest_hr": settings.rest_hr,
        },
        sort_keys=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

_FTP_LOOKBACK_DAYS = 90
_FTP_STATE_KEY = "ftp_auto_initialized"
_THRESHOLD_LOOKBACK_DAYS = 60
_MAX_HR_LOOKBACK_DAYS = 365
_RUN_BEST20_STATE_KEY = "run_best20_cache"  # {activity_id: [best 20 min speed m/s, avg HR]}


def _cutoff(days: int):
    from datetime import datetime, timedelta, timezone

    return datetime.now(timezone.utc) - timedelta(days=days)


def _resolve_max_hr(batch_ids: list[int]) -> float:
    """MAX_HR from .env if set, else the highest HR held ≥ 10 s in the last 12 months.

    Only ever rises (a quiet period doesn't lower it). Because the value only rises
    and a sustained HR can't exceed an activity's peak, only activities in this batch
    whose peak HR beats the current value need their streams read.
    """
    if settings.max_hr > 0:
        return float(settings.max_hr)

    stored = read_state(MAX_HR_STATE_KEY)
    current = float(stored) if stored else 0.0

    with get_db() as db:
        query = (
            db.query(Activity.id)
            .filter(Activity.has_streams.is_(True))
            .filter(Activity.max_hr > current)
            .filter(Activity.start_time >= _cutoff(_MAX_HR_LOOKBACK_DAYS))
        )
        if stored is not None:  # first run scans the whole window, later runs only new activities
            query = query.filter(Activity.id.in_(batch_ids))
        candidate_ids = [r[0] for r in query.all()]

    best = current
    for act_id in candidate_ids:
        with get_db() as db:
            rows = db.query(Stream.time_s, Stream.hr).filter(Stream.activity_id == act_id).order_by(Stream.time_s).all()
        value = sustained_max_hr([r.time_s for r in rows], [r.hr for r in rows]) if rows else None
        if value and value > best:
            best = value

    if best > current:
        write_state(MAX_HR_STATE_KEY, str(round(best)))
        console.print(f"  Max HR updated: {current:.0f} → {best:.0f} (held ≥10 s)")
        return float(round(best))
    return current if current > 0 else FALLBACK_MAX_HR


def _resolve_and_persist_ftp(batch_ids: list[int]) -> float | None:
    """FTP_W from .env if set, else auto: best 20 min of the last 90 days × 0.95.

    Auto FTP only ever rises — rides without a hard 20 min effort keep the last
    (highest) value instead of dragging it down. Each new value is stored in
    ftp_history with the date of the effort it came from.
    """
    # 1. Manual config wins — persist it so the dashboard reflects it.
    if settings.ftp_w > 0:
        _persist_ftp(int(settings.ftp_w), source="manual")
        return float(settings.ftp_w)

    with get_db() as db:
        latest = db.query(FtpHistory).order_by(FtpHistory.id.desc()).first()
        current = int(latest.ftp_w) if latest else 0
        query = (
            db.query(Activity.id, Activity.start_time)
            .filter(func.lower(Activity.type).in_(_BIKE_TYPES))
            .filter(Activity.has_streams.is_(True))
            .filter(Activity.start_time >= _cutoff(_FTP_LOOKBACK_DAYS))
        )
        # Monotonic → after the first full scan of the window only new rides can raise it
        if db.get(AppState, _FTP_STATE_KEY) is not None:
            query = query.filter(Activity.id.in_(batch_ids))
        rides = query.all()

    best_20min, best_date = 0.0, None
    for act_id, start_time in rides:
        with get_db() as db:
            rows = db.query(Stream.watts).filter(Stream.activity_id == act_id).order_by(Stream.time_s).all()
        if not rows:
            continue
        p20 = power_analytics.best_power_for_duration(pd.Series([r.watts for r in rows], dtype=float), 1200)
        if p20 and p20 > best_20min:
            best_20min, best_date = p20, start_time
    write_state(_FTP_STATE_KEY, "1")

    detected = int(round(best_20min * 0.95))
    if detected > current:
        _persist_ftp(detected, source="auto", on_date=best_date.date().isoformat())
        console.print(f"  FTP updated: {current} → {detected} W (best 20 min × 0.95 on {best_date.date()})")
        return float(detected)
    return float(current) if current else None


def _persist_ftp(ftp_w: int, source: str, on_date: str | None = None) -> None:
    """Insert a new ftp_history row, but only if the value/source changed —
    avoids piling up an identical row on every recompute."""
    from datetime import date

    with get_db() as db:
        latest = db.query(FtpHistory).order_by(FtpHistory.id.desc()).first()
        if latest and int(latest.ftp_w) == int(ftp_w) and latest.source == source:
            return
        db.add(FtpHistory(date=on_date or date.today().isoformat(), ftp_w=int(ftp_w), source=source))


def _resolve_threshold_pace(max_hr: float, batch_ids: list[int]) -> float | None:
    """THRESHOLD_PACE_MS from .env if set, else auto: best 20 min of running speed
    in the last 60 days × 0.95 (analogous to FTP).

    Follows current form in both directions, but only hard efforts count (average HR
    over those 20 min ≥ 85 % of max HR). Without one in the window the last detected
    value is kept rather than falling back to hrTSS. Each run's best 20 min is
    computed once and cached, so only new runs have their streams read.
    """
    if settings.threshold_pace_ms > 0:
        return settings.threshold_pace_ms

    cutoff = _cutoff(_THRESHOLD_LOOKBACK_DAYS)
    with get_db() as db:
        runs = (
            db.query(Activity.id, Activity.start_time)
            .filter(func.lower(Activity.type).in_(_RUN_TYPES))
            .filter(Activity.has_streams.is_(True))
            .filter(Activity.moving_time_s >= 1200)
            .filter(Activity.start_time >= cutoff)
            .all()
        )

    raw = read_state(_RUN_BEST20_STATE_KEY)
    cache: dict[str, list] = json.loads(raw) if raw else {}
    in_window = {str(aid) for aid, _ in runs}
    cache = {aid: v for aid, v in cache.items() if aid in in_window}  # drop runs that left the window
    batch = set(batch_ids)
    for act_id, _ in runs:
        if str(act_id) in cache and act_id not in batch:
            continue
        with get_db() as db:
            rows = (
                db.query(Stream.time_s, Stream.velocity_smooth, Stream.hr)
                .filter(Stream.activity_id == act_id)
                .order_by(Stream.time_s)
                .all()
            )
        best = best_sustained_speed(
            [r.time_s for r in rows], [r.velocity_smooth for r in rows], [r.hr for r in rows]
        ) if rows else None
        cache[str(act_id)] = list(best) if best else [None, None]
    write_state(_RUN_BEST20_STATE_KEY, json.dumps(cache))

    hr_floor = max_hr * 0.85
    hard = [speed for speed, hr in cache.values() if speed and hr and hr >= hr_floor]
    if hard:
        threshold = round(max(hard) * 0.95, 2)
        write_state(THRESHOLD_PACE_STATE_KEY, str(threshold))
        console.print(
            f"  Threshold pace: best 20 min in {_THRESHOLD_LOOKBACK_DAYS} days × 0.95 "
            f"({len(hard)} hard efforts, HR ≥ {hr_floor:.0f})"
        )
        return threshold

    stored = read_state(THRESHOLD_PACE_STATE_KEY)
    return float(stored) if stored else None


def _compute_tss(
    act: Activity, ftp: float | None, threshold_pace: float | None, max_hr: float
) -> float | None:
    activity_type = (act.type or "").lower()
    is_bike = activity_type in _BIKE_TYPES
    is_run = activity_type in _RUN_TYPES

    # ── Bike: try NP from streams first, then weighted_avg_watts ─────────────
    if is_bike and ftp:
        np_w = None

        if act.has_streams:
            with get_db() as db:
                stream_rows = (
                    db.query(Stream.watts)
                    .filter(Stream.activity_id == act.id)
                    .order_by(Stream.time_s)
                    .all()
                )
            watts = pd.Series([r.watts for r in stream_rows], dtype=float)
            np_w = normalized_power(watts)

        if np_w is None:
            np_w = act.weighted_avg_watts or act.avg_watts

        if np_w and act.moving_time_s:
            return tss_calc.bike_tss(act.moving_time_s, float(np_w), ftp).tss

    # ── Run: pace-based rTSS ──────────────────────────────────────────────────
    if is_run and threshold_pace and act.distance_m and act.moving_time_s:
        avg_pace = act.distance_m / act.moving_time_s
        if avg_pace > 0:
            return tss_calc.run_tss(act.moving_time_s, avg_pace, threshold_pace).tss

    # ── Fallback: hrTSS ───────────────────────────────────────────────────────
    # Uses the athlete's max HR — not the activity's own peak, which made easy
    # sessions (hikes, skiing, strength) look near-maximal and inflated their TSS.
    if act.avg_hr and act.moving_time_s:
        try:
            return tss_calc.hr_tss(
                act.moving_time_s,
                float(act.avg_hr),
                float(max_hr),
                float(settings.rest_hr),
            ).tss
        except ValueError:
            pass

    return None
