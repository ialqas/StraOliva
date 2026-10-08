"""Greeting counter — how many people greeted back, summed over the runs where
the description is a bare number. See analytics/greetings.py for the rule."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.greetings import parse_greeting_count
from app.db.models import Activity
from app.db.session import get_db_dep

router = APIRouter(tags=["greetings"])


@router.get("/greetings")
def get_greetings(
    days: int | None = Query(None, ge=1, description="Only count the last N days (default: all)"),
    db: Session = Depends(get_db_dep),
):
    q = (
        db.query(Activity.id, Activity.name, Activity.start_time, Activity.description)
        .filter(Activity.description.isnot(None))
        .filter(Activity.description != "")
    )
    if days is not None:
        q = q.filter(Activity.start_time >= (date.today() - timedelta(days=days)).isoformat())

    items = []
    for activity_id, name, start_time, description in q.order_by(Activity.start_time.desc()).all():
        count = parse_greeting_count(description)
        if count is None:
            continue
        items.append({
            "activity_id": activity_id,
            "name": name,
            "start_time": start_time.isoformat(),
            "count": count,
        })

    total = sum(i["count"] for i in items)
    best = max(items, key=lambda i: i["count"]) if items else None

    return {
        "total": total,
        "activities": len(items),
        "avg_per_activity": round(total / len(items), 1) if items else 0.0,
        "best": best,
        "last": items[0] if items else None,
        "items": items,
    }
