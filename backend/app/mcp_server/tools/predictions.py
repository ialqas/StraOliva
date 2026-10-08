"""Race time predictions and power-duration analysis."""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from app.analytics.critical_power import fit_cp_model
from app.analytics.predictions import DISTANCES, _MIN_LONG_RUN_M, format_time
from app.analytics.predictions import predict_race as _predict_race_analytics
from app.config import settings
from app.db.models import Activity
from app.mcp_server.db import get_session
from app.mcp_server.errors import MCPToolError
from app.mcp_server.models import PowerCurve, PowerPoint, RacePrediction

_DISTANCE_TOLERANCE_M = 50


def _distance_label(distance_m: int) -> str:
    for label, d in DISTANCES.items():
        if abs(d - distance_m) <= _DISTANCE_TOLERANCE_M:
            return label
    return f"{distance_m}m"


def _predict_race(distance_m: int, target_date: date | None = None) -> RacePrediction:
    if distance_m <= 0:
        raise MCPToolError("distance_m must be positive. Common distances: 5000, 10000, 21097 (HM), 42195 (Marathon).")

    if target_date is not None and target_date < date.today():
        raise MCPToolError(f"target_date {target_date.isoformat()} is in the past. Use today or a future date.")

    with get_session() as session:
        rows = (
            session.query(Activity.start_time, Activity.type, Activity.distance_m, Activity.moving_time_s)
            .filter(Activity.moving_time_s > 0, Activity.distance_m > 500)
            .all()
        )

    df = pd.DataFrame(rows, columns=["start_time", "type", "distance_m", "moving_time_s"])
    label = _distance_label(distance_m)
    pred = _predict_race_analytics(df, target_distance_m=distance_m, target_label=label)

    target_assessment: str | None = None
    if target_date is not None:
        weeks_to_go = (target_date - date.today()).days / 7
        if pred.predicted_s is None:
            target_assessment = (
                f"{weeks_to_go:.1f} weeks until {target_date.isoformat()}, but there isn't enough "
                f"recent data to project a time yet ({pred.basis_description})."
            )
        else:
            target_assessment = (
                f"{weeks_to_go:.1f} weeks until {target_date.isoformat()}. "
                f"At current fitness, projected time is {format_time(pred.predicted_s)} "
                f"({pred.confidence} confidence)."
            )
            min_long_run_m = _MIN_LONG_RUN_M.get(label)
            if min_long_run_m:
                target_assessment += (
                    f" Make sure your longest run reaches at least {min_long_run_m / 1000:.0f} km "
                    f"a few weeks before race day."
                )

    return RacePrediction(
        distance_m=distance_m,
        predicted_time_s=round(pred.predicted_s) if pred.predicted_s is not None else None,
        ci_lower_s=round(pred.ci_lower_s) if pred.ci_lower_s is not None else None,
        ci_upper_s=round(pred.ci_upper_s) if pred.ci_upper_s is not None else None,
        confidence=pred.confidence,
        basis=pred.basis_description,
        target_assessment=target_assessment,
    )


def _model_fit_quality(r_squared: float) -> str:
    if r_squared > 0.95:
        return "good"
    if r_squared > 0.85:
        return "moderate"
    return "poor"


def _get_power_curve() -> PowerCurve:
    cache_file = Path(settings.db_path).parent / "power_curve.json"
    if cache_file.exists():
        raw = json.loads(cache_file.read_text())
    else:
        raw = {"all_time": [], "recent_6w": []}

    all_time = raw.get("all_time", [])
    recent_6w = raw.get("recent_6w", [])

    best_efforts = {p["duration_s"]: p["power_w"] for p in all_time if p["power_w"] > 0}
    fit = fit_cp_model(best_efforts)

    if fit is None:
        return PowerCurve(
            all_time_best=[
                PowerPoint(duration_s=p["duration_s"], power_w=round(p["power_w"]), activity_id=None, date=None)
                for p in all_time
            ],
            last_6_weeks_best=[
                PowerPoint(duration_s=p["duration_s"], power_w=round(p["power_w"]), activity_id=None, date=None)
                for p in recent_6w
            ],
            cp_w=None,
            w_prime_kj=None,
            model_fit_quality="insufficient_data",
            interpretation=(
                "Not enough power data across durations to fit a CP/W' model. "
                "Ride efforts of varying lengths (3-20 min) with power data to enable this."
            ),
        )

    quality = _model_fit_quality(fit.r_squared)
    interpretation = (
        f"Critical Power ~{round(fit.cp_w)} W with W' of {fit.w_prime_kj} kJ "
        f"(fit quality: {quality}, R²={fit.r_squared:.2f}). "
        f"CP approximates sustainable threshold power; W' is the finite anaerobic "
        f"capacity available above CP before exhaustion."
    )

    return PowerCurve(
        all_time_best=[
            PowerPoint(duration_s=p["duration_s"], power_w=round(p["power_w"]), activity_id=None, date=None)
            for p in all_time
        ],
        last_6_weeks_best=[
            PowerPoint(duration_s=p["duration_s"], power_w=round(p["power_w"]), activity_id=None, date=None)
            for p in recent_6w
        ],
        cp_w=round(fit.cp_w),
        w_prime_kj=fit.w_prime_kj,
        model_fit_quality=quality,
        interpretation=interpretation,
    )


def register(mcp):
    @mcp.tool()
    def predict_race(distance_m: int, target_date: date | None = None) -> RacePrediction:
        """
        Predict race time for a given distance using Riegel formula on recent
        training data. Returns a confidence tier and the basis for the
        prediction. If target_date is provided, also returns what training
        is needed to reach that goal.

        Distances should be in meters: 5000, 10000, 21097 (HM), 42195 (Marathon).
        """
        return _predict_race(distance_m, target_date)

    @mcp.tool()
    def get_power_curve() -> PowerCurve:
        """
        Power-Duration Curve with all-time bests, last-6-week bests, and the
        fitted CP/W' hyperbolic model. Bike-only. Use when discussing
        cycling-specific fitness, intervals, or anaerobic capacity.
        """
        return _get_power_curve()
