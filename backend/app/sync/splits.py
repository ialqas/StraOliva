"""Laps and per-kilometre splits for runs.

The /activities/{id}/laps endpoint only returns the watch laps. Strava's
automatic 1 km splits (`splits_metric`) are only on the activity detail
endpoint — which also contains the laps. So for runs a single detail request
replaces the laps request during sync and provides both.

`sync_splits` backfills runs synced before km splits were stored. It is
deliberately limited (default: the single most recent run) because each run
costs one Strava request.
"""

from rich.console import Console
from sqlalchemy import func

from app.db.models import Activity, KmSplit, Lap
from app.db.session import get_db
from app.strava.client import StravaClient
from app.sync.recompute import _RUN_TYPES

console = Console()


def is_run_type(activity_type: str | None) -> bool:
    return (activity_type or "").lower() in _RUN_TYPES


def store_laps(activity_id: int, raw_laps: list[dict]) -> None:
    rows = [
        Lap(
            activity_id=activity_id,
            lap_index=lap.get("lap_index", i),
            distance_m=lap.get("distance"),
            time_s=lap.get("elapsed_time"),
            moving_time_s=lap.get("moving_time"),
            avg_hr=lap.get("average_heartrate"),
            avg_watts=lap.get("average_watts"),
            avg_speed_ms=lap.get("average_speed"),
        )
        for i, lap in enumerate(raw_laps)
    ]
    with get_db() as db:
        db.query(Lap).filter(Lap.activity_id == activity_id).delete()
        db.add_all(rows)


def store_km_splits(activity_id: int, raw_splits: list[dict]) -> None:
    rows = [
        KmSplit(
            activity_id=activity_id,
            split_index=s.get("split", i + 1),
            distance_m=s.get("distance"),
            moving_time_s=s.get("moving_time"),
            elapsed_time_s=s.get("elapsed_time"),
            avg_speed_ms=s.get("average_speed"),
            avg_hr=s.get("average_heartrate"),
            elevation_diff_m=s.get("elevation_difference"),
        )
        for i, s in enumerate(raw_splits)
    ]
    with get_db() as db:
        db.query(KmSplit).filter(KmSplit.activity_id == activity_id).delete()
        db.add_all(rows)


def fetch_and_store_run_detail(client: StravaClient, activity_id: int) -> None:
    """One detail request → laps (with moving time) + km splits + description.

    Storing the description here means sync_descriptions (which only fetches
    activities whose description is still NULL) doesn't request it a second time.
    """
    detail = client.get_activity(activity_id)
    store_laps(activity_id, detail.get("laps") or [])
    store_km_splits(activity_id, detail.get("splits_metric") or [])
    with get_db() as db:
        db.query(Activity).filter(Activity.id == activity_id).update(
            {"description": (detail.get("description") or "").strip()}
        )


def sync_splits(client: StravaClient, limit: int = 1) -> dict[str, int]:
    """Fetch laps + km splits for the `limit` most recent runs that have no km splits yet."""
    stats = {"fetched": 0, "errors": 0}

    with get_db() as db:
        has_splits = db.query(KmSplit.activity_id).distinct()
        targets = (
            db.query(Activity.id, Activity.name)
            .filter(func.lower(Activity.type).in_(_RUN_TYPES))
            .filter(Activity.id.not_in(has_splits))
            .order_by(Activity.start_time.desc())
            .limit(limit)
            .all()
        )

    for activity_id, name in targets:
        try:
            fetch_and_store_run_detail(client, activity_id)
            stats["fetched"] += 1
            console.print(f"  ✓ {name}")
        except Exception as exc:
            stats["errors"] += 1
            console.print(f"  [yellow]✗ {name}: {exc}[/yellow]")

    return stats
