"""Weekly check-in: assess the upcoming plan against current training state."""

import json
from datetime import date, timedelta

from app.db.models import PlannedWorkout as PlannedWorkoutRow
from app.mcp_server.db import get_session
from app.mcp_server.models import WeekAssessment
from app.mcp_server.tools.plan import _sport_label
from app.mcp_server.tools.state import _get_training_state

_HARD_TSS_THRESHOLD = 70


def _is_hard(w: PlannedWorkoutRow) -> bool:
    if (w.tss_planned or 0) >= _HARD_TSS_THRESHOLD:
        return True
    if w.steps_json:
        try:
            steps = json.loads(w.steps_json)
        except Exception:
            steps = []
        if any(s.get("type") == "interval" for s in steps):
            return True
    return False


def _assess_upcoming_week() -> WeekAssessment:
    today = date.today()
    week_end = today + timedelta(days=6)

    state = _get_training_state()

    with get_session() as session:
        rows = (
            session.query(PlannedWorkoutRow)
            .filter(
                PlannedWorkoutRow.date >= today.isoformat(),
                PlannedWorkoutRow.date <= week_end.isoformat(),
            )
            .order_by(PlannedWorkoutRow.date)
            .all()
        )

    planned_tss_total = round(sum(w.tss_planned or 0 for w in rows))
    planned_workouts_count = len(rows)

    warnings: list[str] = []
    observations: list[str] = []

    hard_workouts = [w for w in rows if _is_hard(w)]

    if state.tsb < -30:
        warnings.append(
            f"TSB is {state.tsb} (burnout zone). Consider a lighter week regardless "
            f"of what's currently planned."
        )
    elif state.tsb < -10 and hard_workouts:
        for w in hard_workouts:
            warnings.append(
                f"TSB is {state.tsb} ({state.form_zone}), but {w.date} '{w.title}' "
                f"is a hard session — consider easing intensity, swapping it for an "
                f"easy day, or moving it later in the week."
            )

    if (
        state.ramp_rate_classification == "rapid_build"
        and state.weekly_tss > 0
        and planned_tss_total > state.weekly_tss * 1.2
    ):
        warnings.append(
            f"CTL is already ramping rapidly ({state.ramp_rate_per_week:+.1f}/week) "
            f"and this week plans {planned_tss_total} TSS vs {state.weekly_tss} last "
            f"week — injury/illness risk rises with fast load increases on top of a "
            f"rapid build."
        )

    distinct_dates = {w.date for w in rows}
    if len(distinct_dates) >= 7:
        warnings.append(
            "No rest day in the next 7 days — every day currently has a planned session."
        )

    if planned_workouts_count == 0:
        observations.append("No workouts are currently planned for the next 7 days.")
    else:
        sports: dict[str, int] = {}
        for w in rows:
            label = _sport_label(w.sport)
            sports[label] = sports.get(label, 0) + 1
        sports_str = ", ".join(f"{count}x {sport}" for sport, count in sports.items())
        observations.append(
            f"{planned_workouts_count} workout(s) planned ({sports_str}), "
            f"totaling {planned_tss_total} TSS."
        )

        if not hard_workouts:
            observations.append(
                "No hard/interval sessions planned this week — mostly aerobic/recovery load."
            )

    observations.append(f"Current form: {state.form_interpretation}")

    if state.ftp.is_stale:
        observations.append(
            "FTP estimate is stale or missing — power-based targets in the plan "
            "may be inaccurate. " + (state.ftp.diagnostic or "")
        )

    return WeekAssessment(
        planned_tss_total=planned_tss_total,
        planned_workouts_count=planned_workouts_count,
        current_tsb=state.tsb,
        current_form_zone=state.form_zone,
        warnings=warnings,
        observations=observations,
    )


def register(mcp):
    @mcp.tool()
    def assess_upcoming_week() -> WeekAssessment:
        """
        Look at the upcoming 7 days of planned workouts and assess them
        against current training state (TSB, form zone, ramp rate). Returns
        warnings (e.g. "TSB is -22, but Tuesday is still a hard interval
        session — consider rest") and neutral observations. Use this for the
        weekly check-in conversation.

        Does NOT modify the plan — read-only analysis.
        """
        return _assess_upcoming_week()
