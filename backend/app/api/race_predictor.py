import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.predictions import DISTANCES, format_time, predict_race
from app.db.models import Activity
from app.db.session import get_db_dep
from app.i18n import Lang

router = APIRouter(tags=["analytics"])


@router.get("/race-predictions")
def get_race_predictions(
    lookback_weeks: int = Query(8, ge=2, le=52),
    lang: Lang = Query("de"),
    db: Session = Depends(get_db_dep),
):
    rows = db.query(
        Activity.start_time, Activity.type,
        Activity.distance_m, Activity.moving_time_s,
    ).filter(
        Activity.moving_time_s > 0,
        Activity.distance_m > 500,
    ).all()

    df = pd.DataFrame(rows, columns=["start_time", "type", "distance_m", "moving_time_s"])

    results = []
    for label, dist_m in DISTANCES.items():
        pred = predict_race(df, target_distance_m=dist_m, target_label=label, lookback_weeks=lookback_weeks, lang=lang)
        results.append({
            "name": label,
            "distance_m": dist_m,
            "predicted_time": format_time(pred.predicted_s) if pred.predicted_s else None,
            "predicted_s": round(pred.predicted_s) if pred.predicted_s else None,
            "ci_lower": format_time(pred.ci_lower_s) if pred.ci_lower_s else None,
            "ci_upper": format_time(pred.ci_upper_s) if pred.ci_upper_s else None,
            "ci_lower_s": round(pred.ci_lower_s) if pred.ci_lower_s else None,
            "ci_upper_s": round(pred.ci_upper_s) if pred.ci_upper_s else None,
            "confidence": pred.confidence,
            "basis_description": pred.basis_description,
            "num_efforts": pred.num_efforts,
        })

    return results
