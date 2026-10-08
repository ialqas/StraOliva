import typer
from rich.console import Console

app = typer.Typer(name="strava-dash", help="StraOliva CLI — manage your local Strava dashboard.")
console = Console()


@app.command()
def auth():
    """Authenticate with Strava via OAuth (one-time setup)."""
    from app.db.session import init_db
    from app.strava.auth import run_oauth_flow, store_tokens

    if not _check_credentials():
        raise typer.Exit(1)

    init_db()
    try:
        token_data = run_oauth_flow()
        store_tokens(token_data)
        athlete = token_data.get("athlete", {})
        name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
        console.print(f"[green]✓ Authenticated as {name or 'unknown athlete'}[/green]")
    except Exception as exc:
        console.print(f"[red]Authentication failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command()
def sync(
    full: bool = typer.Option(False, "--full", help="Re-sync all activities, not just new ones."),
):
    """Sync activities from Strava API (incremental by default)."""
    from app.db.session import init_db
    from app.strava.client import StravaClient
    from app.sync.api import sync as run_sync

    if not _check_credentials():
        raise typer.Exit(1)

    init_db()
    client = StravaClient()
    try:
        stats = run_sync(client, full=full)
        console.print(
            f"\n[green]✓ Done.[/green] "
            f"New: {stats['new']}  Updated: {stats['updated']}  "
            f"Streams: {stats['streams_ok']}  Errors: {stats['errors']}"
        )
    except Exception as exc:
        console.print(f"[red]Sync failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command("sync-descriptions")
def sync_descriptions_cmd(
    days: int = typer.Option(180, "--days", help="Look back this many days."),
    refresh_days: int = typer.Option(
        14,
        "--refresh-days",
        help=(
            "Also re-fetch activities newer than this many days, to pick up "
            "descriptions edited after the initial sync (e.g. greeting counts "
            "added after the run). 0 disables the refresh and only fetches "
            "activities never checked before."
        ),
    ),
):
    """Fetch activity descriptions from Strava (needed for the greeting counter)."""
    from app.db.session import init_db
    from app.strava.client import StravaClient
    from app.sync.descriptions import sync_descriptions

    if not _check_credentials():
        raise typer.Exit(1)

    init_db()
    try:
        stats = sync_descriptions(StravaClient(), days=days, refresh_days=refresh_days)
        console.print(
            f"\n[green]✓ Done.[/green] "
            f"Fetched: {stats['fetched']}  Non-empty: {stats['with_text']}  "
            f"Errors: {stats['errors']}"
        )
    except Exception as exc:
        console.print(f"[red]Description sync failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command("sync-splits")
def sync_splits_cmd(
    limit: int = typer.Option(
        1, "--limit", help="How many of the most recent runs without km splits to fetch (1 Strava request each)."
    ),
):
    """Fetch laps (pause-free times) + automatic km splits for recent runs synced before these were stored."""
    from app.db.session import init_db
    from app.strava.client import StravaClient
    from app.sync.splits import sync_splits

    if not _check_credentials():
        raise typer.Exit(1)

    init_db()
    try:
        stats = sync_splits(StravaClient(), limit=limit)
        console.print(f"\n[green]✓ Done.[/green] Fetched: {stats['fetched']}  Errors: {stats['errors']}")
    except Exception as exc:
        console.print(f"[red]Split sync failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command("import-bulk")
def import_bulk(
    zip_path: str = typer.Argument(..., help="Path to the Strava bulk export ZIP file."),
):
    """Import full activity history from a Strava bulk export ZIP."""
    import os
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

    from app.db.session import init_db
    from app.sync.bulk import import_zip

    if not os.path.isfile(zip_path):
        console.print(f"[red]File not found: {zip_path}[/red]")
        raise typer.Exit(1)

    init_db()
    console.print(f"Importing from [bold]{zip_path}[/bold] …")

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Reading …", total=None)

        def on_progress(i: int, total: int, name: str) -> None:
            progress.update(task, total=total, completed=i, description=f"{name[:50]:<50}")

        stats = import_zip(zip_path, on_progress=on_progress)
        progress.update(task, completed=stats["imported"] + stats["skipped"] + stats["errors"])

    console.print(
        f"\n[green]✓ Done.[/green] "
        f"Imported: {stats['imported']}  Skipped: {stats['skipped']}  Errors: {stats['errors']}"
    )


@app.command()
def recompute(
    skip_sync: bool = typer.Option(False, "--skip-sync", help="Skip Strava API sync and only recalculate analytics."),
    full: bool = typer.Option(
        False, "--full", help="Recompute TSS, power curve and heatmap for all activities, not just new ones."
    ),
):
    """Sync new activities from Strava, then recompute TSS/CTL/ATL/TSB/FTP/PDC/heatmap (incremental by default)."""
    from app.sync.recompute import sync_and_recompute

    if not _check_credentials():
        raise typer.Exit(1)

    try:
        stats = sync_and_recompute(skip_sync=skip_sync, full=full)
        console.print(
            f"\n[green]✓ Done.[/green] "
            f"TSS computed: {stats['tss_computed']} ({stats['tss_mode']})  "
            f"Skipped: {stats['tss_skipped']}  "
            f"Days written: {stats['days_written']}"
        )
    except Exception as exc:
        console.print(f"[red]Recompute failed: {exc}[/red]")
        raise typer.Exit(1)


@app.command("sync-segments")
def sync_segments():
    """Sync starred Strava segments to the local DB."""
    from app.db.models import Segment
    from app.db.session import get_db, init_db
    from app.strava.client import StravaClient

    if not _check_credentials():
        raise typer.Exit(1)

    init_db()
    client = StravaClient()

    console.print("Fetching starred segments from Strava …")
    try:
        raw_segments = client.get_starred_segments()
    except Exception as exc:
        console.print(f"[red]Failed to fetch segments: {exc}[/red]")
        raise typer.Exit(1)

    if not raw_segments:
        console.print("[yellow]No starred segments found. Star segments on Strava first.[/yellow]")
        return

    console.print(f"Found {len(raw_segments)} starred segment(s). Fetching details for GPS tracks …")

    upserted = 0
    with get_db() as db:
        for raw in raw_segments:
            seg_id = raw.get("id")
            if not seg_id:
                continue

            # The starred-list endpoint returns SummarySegment (no polyline).
            # Fetch the detailed segment to get the full GPS polyline.
            polyline = None
            try:
                detail = client.get_segment(seg_id)
                detail_map = detail.get("map") or {}
                polyline = detail_map.get("polyline") or detail_map.get("summary_polyline")
            except Exception as exc:
                console.print(f"  [yellow]⚠ Could not fetch detail for {raw.get('name')}: {exc}[/yellow]")

            seg = db.query(Segment).filter(Segment.id == seg_id).first() or Segment(id=seg_id)
            seg.name = raw.get("name", "")
            seg.distance_m = raw.get("distance")
            sl = raw.get("start_latlng") or []
            el = raw.get("end_latlng") or []
            seg.start_lat = sl[0] if len(sl) >= 2 else None
            seg.start_lng = sl[1] if len(sl) >= 2 else None
            seg.end_lat = el[0] if len(el) >= 2 else None
            seg.end_lng = el[1] if len(el) >= 2 else None
            seg.avg_grade = raw.get("average_grade")
            seg.city = raw.get("city")
            seg.climb_category = raw.get("climb_category")
            seg.polyline = polyline
            db.merge(seg)
            upserted += 1

    console.print(f"[green]✓ Synced {upserted} segment(s).[/green]")


def _check_credentials() -> bool:
    from app.config import settings

    if not settings.strava_client_id or not settings.strava_client_secret:
        console.print(
            "[red]STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set.\n"
            "Copy .env.example to .env and fill in your Strava API credentials.[/red]"
        )
        return False
    return True


if __name__ == "__main__":
    app()
