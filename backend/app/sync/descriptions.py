"""Backfill activity descriptions from the Strava detail endpoint.

The activity *list* endpoint (/athlete/activities) that `sync.api` uses does not
return the `description` field — only /activities/{id} does. That is one extra
API call per activity, so by default this only fetches activities we have never
fetched a description for (description IS NULL) — the same "new only" semantics
as `sync.api.sync`, so the automatic recompute pass doesn't burn API quota
re-checking activities on every run.

Descriptions can be edited on Strava after the fact (that is exactly how the
greeting counts in `app.analytics.greetings` are added), so a description once
fetched is never re-checked automatically. Pass `refresh_days` > 0 to also
re-fetch activities newer than that many days, e.g. to pick up a greeting count
added after the initial sync — intended as an explicit, occasional manual pass
(`strava-dash sync-descriptions --refresh-days 30`), not something run on every
recompute.

A fetched-but-empty description is stored as "" so it is not retried forever.
"""

from datetime import date, timedelta

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from app.db.models import Activity
from app.db.session import get_db
from app.strava.client import StravaClient

console = Console()

DEFAULT_DAYS = 180
DEFAULT_REFRESH_DAYS = 0
DEFAULT_MAX_ACTIVITIES = 150


def sync_descriptions(
    client: StravaClient,
    days: int = DEFAULT_DAYS,
    refresh_days: int = DEFAULT_REFRESH_DAYS,
    max_activities: int = DEFAULT_MAX_ACTIVITIES,
) -> dict[str, int]:
    stats = {"fetched": 0, "with_text": 0, "errors": 0}

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    refresh_cutoff = (
        (date.today() - timedelta(days=refresh_days)).isoformat() if refresh_days > 0 else None
    )

    with get_db() as db:
        rows = (
            db.query(Activity.id, Activity.name, Activity.start_time, Activity.description)
            .filter(Activity.start_time >= cutoff)
            .order_by(Activity.start_time.desc())
            .all()
        )

    targets = [
        (aid, name)
        for aid, name, start_time, desc in rows
        if desc is None or (refresh_cutoff is not None and start_time.isoformat() >= refresh_cutoff)
    ][:max_activities]

    if not targets:
        return stats

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching descriptions …", total=len(targets))

        for activity_id, name in targets:
            progress.update(task, description=f"{(name or str(activity_id))[:45]:<45}")
            try:
                raw = client.get_activity(activity_id)
                description = (raw.get("description") or "").strip()
                with get_db() as db:
                    db.query(Activity).filter(Activity.id == activity_id).update(
                        {"description": description}
                    )
                stats["fetched"] += 1
                if description:
                    stats["with_text"] += 1
            except Exception as exc:
                stats["errors"] += 1
                console.print(f"  [yellow]✗ {name}: {exc}[/yellow]")
            progress.advance(task)

    return stats
