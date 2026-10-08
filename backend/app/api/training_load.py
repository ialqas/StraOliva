from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import TrainingLoadDaily
from app.db.session import get_db_dep

router = APIRouter(tags=["training-load"])


@router.get("/training-load")
def get_training_load(
    days: int = Query(180, ge=7, le=1825),
    db: Session = Depends(get_db_dep),
):
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = (
        db.query(TrainingLoadDaily)
        .filter(TrainingLoadDaily.date >= cutoff)
        .order_by(TrainingLoadDaily.date)
        .all()
    )
    return [
        {
            "date": r.date,
            "ctl": round(r.ctl, 1),
            "atl": round(r.atl, 1),
            "tsb": round(r.tsb, 1),
            "total_tss": round(r.total_tss, 1),
        }
        for r in rows
    ]
