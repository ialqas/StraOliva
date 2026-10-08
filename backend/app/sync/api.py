"""Incremental sync from the Strava API — activities + streams + laps."""

import json
import time
from datetime import datetime, timezone

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from app.db.models import Activity, Stream
from app.db.session import get_db
from app.strava.client import StravaClient
from app.sync.splits import fetch_and_store_run_detail, is_run_type, store_laps

console = Console()


def sync(client: StravaClient, full: bool = False) -> dict[str, int]:
    stats = {"new": 0, "updated": 0, "streams_ok": 0, "errors": 0}

    after = _last_synced_ts() if not full else None
    if after:
        dt = datetime.fromtimestamp(after, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        console.print(f"Syncing activities after {dt} …")
    else:
        console.print("Full sync — fetching all activities …")

    # ── Step 1: collect activity list (cheap: 1 API call per 50 activities) ──
    all_raw: list[dict] = []
    page = 1
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as p:
        t = p.add_task("Fetching activity list …")
        while True:
            batch = client.get_activities(after=after, page=page, per_page=50)
            if not batch:
                break
            all_raw.extend(batch)
            p.update(t, description=f"Fetching activity list … {len(all_raw)} found")
            page += 1

    if not all_raw:
        console.print("No new activities found.")
        return stats

    console.print(f"Found [bold]{len(all_raw)}[/bold] activities to sync.")
    if len(all_raw) > 30:
        console.print(
            f"[yellow]Note: {len(all_raw)} activities × ~2 stream calls each may take "
            f"~{len(all_raw) * 2 // 6} min due to Strava rate limits (100 req/15 min).[/yellow]"
        )

    # ── Step 2: upsert each activity + fetch streams + laps ──────────────────
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Syncing …", total=len(all_raw))

        for raw in all_raw:
            name = raw.get("name", str(raw["id"]))
            progress.update(task, description=f"{name[:45]:<45}")
            try:
                is_new = _upsert_activity(raw)
                stats["new" if is_new else "updated"] += 1
                _fetch_and_store_streams(client, raw["id"])
                if is_run_type(raw.get("sport_type") or raw.get("type")):
                    # Detail request carries laps *and* km splits — replaces the laps request
                    try:
                        fetch_and_store_run_detail(client, raw["id"])
                    except Exception:
                        pass  # like laps before: missing splits shouldn't fail the activity
                else:
                    _fetch_and_store_laps(client, raw["id"])
                stats["streams_ok"] += 1
            except Exception as exc:
                stats["errors"] += 1
                console.print(f"  [yellow]✗ {name}: {exc}[/yellow]")
            progress.advance(task)

    return stats


# ── Helpers ───────────────────────────────────────────────────────────────────

def _last_synced_ts() -> int | None:
    with get_db() as db:
        row = db.query(Activity.start_time).order_by(Activity.start_time.desc()).first()
        return int(row[0].timestamp()) if row else None


def _upsert_activity(raw: dict) -> bool:
    """Insert or update an activity row. Returns True if newly created."""
    with get_db() as db:
        existing = db.query(Activity).filter(Activity.id == raw["id"]).first()
        a = existing or Activity(id=raw["id"])

        a.name = raw.get("name", "")
        a.type = raw.get("sport_type") or raw.get("type", "")
        a.start_time = datetime.fromisoformat(raw["start_date"])
        a.distance_m = raw.get("distance")
        a.moving_time_s = raw.get("moving_time")
        a.elapsed_time_s = raw.get("elapsed_time")
        a.total_elevation_gain_m = raw.get("total_elevation_gain")
        a.avg_hr = raw.get("average_heartrate")
        a.max_hr = raw.get("max_heartrate")
        a.avg_watts = raw.get("average_watts")
        a.weighted_avg_watts = raw.get("weighted_average_watts")
        a.kilojoules = raw.get("kilojoules")
        a.raw_json = json.dumps(raw)
        a.tss = None  # (re)compute on the next recompute — it only processes activities without TSS

        if existing is None:
            db.add(a)

        return existing is None


def _fetch_and_store_streams(client: StravaClient, activity_id: int) -> None:
    try:
        raw = client.get_activity_streams(activity_id)
    except Exception:
        return

    times = raw.get("time", {}).get("data", [])
    if not times:
        return

    def col(key: str) -> list:
        return raw.get(key, {}).get("data", [])

    hr = col("heartrate")
    watts = col("watts")
    cadence = col("cadence")
    latlng = col("latlng")
    altitude = col("altitude")
    velocity = col("velocity_smooth")

    rows = []
    seen_times: set[int] = set()
    for i, t in enumerate(times):
        # Strava occasionally repeats a timestamp (usually a duplicated t=0
        # sample). (activity_id, time_s) is the primary key, so keeping both
        # would abort the whole insert and leave the activity without streams.
        if t in seen_times:
            continue
        seen_times.add(t)
        ll = latlng[i] if i < len(latlng) else None
        rows.append(Stream(
            activity_id=activity_id,
            time_s=t,
            hr=hr[i] if i < len(hr) else None,
            watts=watts[i] if i < len(watts) else None,
            cadence=cadence[i] if i < len(cadence) else None,
            lat=ll[0] if ll else None,
            lng=ll[1] if ll else None,
            altitude_m=altitude[i] if i < len(altitude) else None,
            velocity_smooth=velocity[i] if i < len(velocity) else None,
        ))

    with get_db() as db:
        db.query(Stream).filter(Stream.activity_id == activity_id).delete()
        db.add_all(rows)
        db.query(Activity).filter(Activity.id == activity_id).update({"has_streams": True})


def _fetch_and_store_laps(client: StravaClient, activity_id: int) -> None:
    try:
        raw_laps = client.get_activity_laps(activity_id)
    except Exception:
        return
    store_laps(activity_id, raw_laps)
