"""Trigger the full sync + recompute pipeline from the dashboard.

This exposes the same work as the `strava-dash recompute` CLI command so the
dashboard "Sync" button can run it. It's a blocking, potentially slow job
(Strava rate limits + analytics), so it runs in a threadpool to avoid blocking
the event loop.
"""

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

router = APIRouter(tags=["recompute"])


@router.post("/recompute")
async def trigger_recompute(skip_sync: bool = False, full: bool = False):
    """Sync new activities from Strava, then recompute TSS/CTL/ATL/TSB/FTP/
    threshold pace/PDC/heatmap — only for new activities unless `full`.
    Returns the combined stats incl. per-step timings."""
    from app.sync.recompute import sync_and_recompute

    return await run_in_threadpool(sync_and_recompute, skip_sync, full)
