"""Read/write access to the active training plan (planned_workouts table)."""

import json
from datetime import date, datetime, timedelta, timezone

from app.db.models import Activity, PlannedWorkout as PlannedWorkoutRow, TrainingPlan
from app.mcp_server.db import get_session
from app.mcp_server.errors import MCPToolError
from app.mcp_server.models import (
    BulkResult,
    NewWorkout,
    PlannedWorkout,
    PlannedWorkoutSummary,
    Sport,
    WorkoutStatus,
    WorkoutStep,
    WorkoutUpdate,
)

_SPORT_LABELS = {"run": "Run", "bike": "Ride", "ride": "Ride", "swim": "Swim"}
_SPORT_TO_DB = {"Run": "run", "Ride": "bike", "Swim": "swim", "Other": "other"}


def _sport_label(sport: str | None) -> str:
    return _SPORT_LABELS.get((sport or "").lower(), "Other")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_or_create_plan(session) -> TrainingPlan:
    plan = session.query(TrainingPlan).first()
    if not plan:
        plan = TrainingPlan(name="Mein Trainingsplan", created_at=_now())
        session.add(plan)
        session.flush()
    return plan


def _status(w: PlannedWorkoutRow) -> WorkoutStatus:
    if w.completed_activity_id is not None:
        return "completed"
    w_date = date.fromisoformat(w.date)
    today = date.today()
    if w_date < today:
        return "missed"
    if w_date == today:
        return "today"
    return "upcoming"


def _to_summary(w: PlannedWorkoutRow) -> PlannedWorkoutSummary:
    return PlannedWorkoutSummary(
        id=w.id,
        date=date.fromisoformat(w.date),
        sport=_sport_label(w.sport),
        title=w.title or "Training",
        estimated_tss=round(w.tss_planned) if w.tss_planned is not None else None,
        estimated_duration_min=w.duration_min,
        completed_activity_id=w.completed_activity_id,
        status=_status(w),
    )


def _to_detail(w: PlannedWorkoutRow) -> PlannedWorkout:
    steps: list[WorkoutStep] = []
    if w.steps_json:
        try:
            steps = [WorkoutStep(**s) for s in json.loads(w.steps_json)]
        except Exception:
            steps = []
    return PlannedWorkout(
        id=w.id,
        date=date.fromisoformat(w.date),
        sport=_sport_label(w.sport),
        title=w.title or "Training",
        description=w.description,
        duration_min=w.duration_min,
        distance_m=w.distance_m,
        tss_planned=w.tss_planned,
        steps=steps,
        notes=w.notes,
        completed_activity_id=w.completed_activity_id,
        status=_status(w),
    )


def _list_planned_workouts(
    date_from: date | None = None, date_to: date | None = None
) -> list[PlannedWorkoutSummary]:
    if date_from is None:
        date_from = date.today()
    if date_to is None:
        date_to = date_from + timedelta(weeks=4)

    if date_to < date_from:
        raise MCPToolError(
            f"date_to ({date_to.isoformat()}) is before date_from "
            f"({date_from.isoformat()}). Swap the dates so date_from <= date_to."
        )

    with get_session() as session:
        rows = (
            session.query(PlannedWorkoutRow)
            .filter(
                PlannedWorkoutRow.date >= date_from.isoformat(),
                PlannedWorkoutRow.date <= date_to.isoformat(),
            )
            .order_by(PlannedWorkoutRow.date)
            .all()
        )
        return [_to_summary(w) for w in rows]


def _get_planned_workout(workout_id: int) -> PlannedWorkout:
    with get_session() as session:
        w = session.query(PlannedWorkoutRow).filter(PlannedWorkoutRow.id == workout_id).first()
        if not w:
            raise MCPToolError(
                f"Planned workout {workout_id} not found. Use list_planned_workouts "
                f"to see valid workout ids."
            )
        return _to_detail(w)


# ── Write-tool helpers ───────────────────────────────────────────────────────

def _check_date_not_past(d: date, ref: str) -> None:
    today = date.today()
    if d < today:
        raise MCPToolError(
            f"{ref}: date {d.isoformat()} is in the past. Planned workouts must be "
            f"today or later (today is {today.isoformat()})."
        )


def _check_not_frozen(w: PlannedWorkoutRow, workout_id: int) -> None:
    if date.fromisoformat(w.date) < date.today():
        raise MCPToolError(
            f"Cannot modify past workout {workout_id} (date {w.date}). Past planned "
            f"workouts are frozen to preserve adherence history. Use "
            f"log_completed_workout to mark adherence."
        )


def _validate_steps(sport: Sport, steps: list[WorkoutStep], ref: str) -> str | None:
    """Validate steps for a workout. Returns an extra note to append to `notes`
    (or None), and raises MCPToolError for hard violations."""
    if not steps:
        raise MCPToolError(f"{ref}: must have at least one step.")

    for i, step in enumerate(steps, start=1):
        if step.duration_min is None and step.distance_m is None:
            raise MCPToolError(
                f"{ref}: step {i} ('{step.label}') must specify either "
                f"duration_min or distance_m."
            )
        if sport == "Run" and step.target_power_pct_ftp is not None:
            raise MCPToolError(
                f"{ref}: step {i} ('{step.label}') has target_power_pct_ftp set, "
                f"but Run workouts don't use power targets. Use target_hr_zone or "
                f"target_pace_min_km instead."
            )

    if sport == "Ride" and any(s.target_pace_min_km is not None for s in steps):
        return "Note: pace targets were specified for a Ride workout — verify this is intentional."
    return None


def _create_workout(
    workout_date: date,
    sport: Sport,
    title: str,
    steps: list[WorkoutStep],
    description: str | None = None,
    duration_min: int | None = None,
    distance_m: float | None = None,
    tss_planned: float | None = None,
    notes: str | None = None,
) -> PlannedWorkout:
    _check_date_not_past(workout_date, "Cannot create workout")

    extra_note = _validate_steps(sport, steps, "Workout")
    if extra_note:
        notes = f"{notes}\n{extra_note}" if notes else extra_note

    now = _now()
    with get_session() as session:
        plan = _get_or_create_plan(session)
        w = PlannedWorkoutRow(
            plan_id=plan.id,
            date=workout_date.isoformat(),
            title=title,
            sport=_SPORT_TO_DB[sport],
            description=description,
            duration_min=duration_min,
            distance_m=distance_m,
            tss_planned=tss_planned,
            steps_json=json.dumps([s.model_dump() for s in steps]),
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        session.add(w)
        session.commit()
        session.refresh(w)
        return _to_detail(w)


def _bulk_create_workouts(workouts: list[NewWorkout]) -> BulkResult:
    if not workouts:
        raise MCPToolError("workouts is empty. Provide at least one workout to create.")

    prepared: list[tuple[NewWorkout, str | None]] = []
    for i, nw in enumerate(workouts, start=1):
        ref = f"Workout #{i} ({nw.date.isoformat()})"
        _check_date_not_past(nw.date, ref)
        extra_note = _validate_steps(nw.sport, nw.steps, ref)
        notes = nw.notes
        if extra_note:
            notes = f"{notes}\n{extra_note}" if notes else extra_note
        prepared.append((nw, notes))

    now = _now()
    with get_session() as session:
        plan = _get_or_create_plan(session)
        rows = [
            PlannedWorkoutRow(
                plan_id=plan.id,
                date=nw.date.isoformat(),
                title=nw.title,
                sport=_SPORT_TO_DB[nw.sport],
                description=nw.description,
                duration_min=nw.duration_min,
                distance_m=nw.distance_m,
                tss_planned=nw.tss_planned,
                steps_json=json.dumps([s.model_dump() for s in nw.steps]),
                notes=notes,
                created_at=now,
                updated_at=now,
            )
            for nw, notes in prepared
        ]
        session.add_all(rows)
        session.commit()
        for r in rows:
            session.refresh(r)
        return BulkResult(created_ids=[r.id for r in rows], count=len(rows))


def _update_workout(
    workout_id: int,
    workout_date: date | None = None,
    title: str | None = None,
    sport: Sport | None = None,
    steps: list[WorkoutStep] | None = None,
    description: str | None = None,
    duration_min: int | None = None,
    distance_m: float | None = None,
    tss_planned: float | None = None,
    notes: str | None = None,
) -> PlannedWorkout:
    with get_session() as session:
        w = session.query(PlannedWorkoutRow).filter(PlannedWorkoutRow.id == workout_id).first()
        if not w:
            raise MCPToolError(
                f"Planned workout {workout_id} not found. Use list_planned_workouts "
                f"to see valid workout ids."
            )
        _check_not_frozen(w, workout_id)

        if workout_date is not None:
            _check_date_not_past(workout_date, f"Cannot move workout {workout_id}")
            w.date = workout_date.isoformat()
        if title is not None:
            w.title = title
        if sport is not None:
            w.sport = _SPORT_TO_DB[sport]
        if steps is not None:
            effective_sport = sport or _sport_label(w.sport)
            extra_note = _validate_steps(effective_sport, steps, f"Workout {workout_id}")
            w.steps_json = json.dumps([s.model_dump() for s in steps])
            if extra_note:
                notes = f"{notes}\n{extra_note}" if notes else extra_note
        if description is not None:
            w.description = description
        if duration_min is not None:
            w.duration_min = duration_min
        if distance_m is not None:
            w.distance_m = distance_m
        if tss_planned is not None:
            w.tss_planned = tss_planned
        if notes is not None:
            w.notes = notes

        w.updated_at = _now()
        session.commit()
        session.refresh(w)
        return _to_detail(w)


def _bulk_update_workouts(updates: list[WorkoutUpdate]) -> BulkResult:
    if not updates:
        raise MCPToolError("updates is empty. Provide at least one update.")

    with get_session() as session:
        prepared: list[tuple[PlannedWorkoutRow, WorkoutUpdate, str | None]] = []
        for u in updates:
            w = session.query(PlannedWorkoutRow).filter(PlannedWorkoutRow.id == u.id).first()
            if not w:
                raise MCPToolError(
                    f"Update for workout {u.id}: not found. Use list_planned_workouts "
                    f"to see valid workout ids."
                )
            _check_not_frozen(w, u.id)
            if u.date is not None:
                _check_date_not_past(u.date, f"Cannot move workout {u.id}")

            extra_note = None
            if u.steps is not None:
                effective_sport = u.sport or _sport_label(w.sport)
                extra_note = _validate_steps(effective_sport, u.steps, f"Workout {u.id}")
            prepared.append((w, u, extra_note))

        now = _now()
        for w, u, extra_note in prepared:
            if u.date is not None:
                w.date = u.date.isoformat()
            if u.title is not None:
                w.title = u.title
            if u.sport is not None:
                w.sport = _SPORT_TO_DB[u.sport]
            if u.steps is not None:
                w.steps_json = json.dumps([s.model_dump() for s in u.steps])
            if u.description is not None:
                w.description = u.description
            if u.duration_min is not None:
                w.duration_min = u.duration_min
            if u.distance_m is not None:
                w.distance_m = u.distance_m
            if u.tss_planned is not None:
                w.tss_planned = u.tss_planned

            notes = u.notes
            if extra_note:
                notes = f"{notes}\n{extra_note}" if notes else extra_note
            if notes is not None:
                w.notes = notes

            w.updated_at = now

        session.commit()
        return BulkResult(created_ids=[u.id for u in updates], count=len(updates))


def _delete_workout(workout_id: int) -> dict:
    with get_session() as session:
        w = session.query(PlannedWorkoutRow).filter(PlannedWorkoutRow.id == workout_id).first()
        if not w:
            raise MCPToolError(
                f"Planned workout {workout_id} not found. Use list_planned_workouts "
                f"to see valid workout ids."
            )
        if date.fromisoformat(w.date) < date.today():
            raise MCPToolError(
                f"Cannot delete past workout {workout_id} (date {w.date}). Past "
                f"planned workouts cannot be deleted — this would corrupt adherence history."
            )
        session.delete(w)
        session.commit()
        return {"deleted": workout_id}


def _delete_workouts_in_range(date_from: date, date_to: date) -> dict:
    today = date.today()
    if date_from < today:
        raise MCPToolError(
            f"date_from ({date_from.isoformat()}) is in the past. Only future planned "
            f"workouts can be deleted (today is {today.isoformat()})."
        )
    if date_to < date_from:
        raise MCPToolError(
            f"date_to ({date_to.isoformat()}) is before date_from "
            f"({date_from.isoformat()}). Swap the dates so date_from <= date_to."
        )

    with get_session() as session:
        rows = (
            session.query(PlannedWorkoutRow)
            .filter(
                PlannedWorkoutRow.date >= date_from.isoformat(),
                PlannedWorkoutRow.date <= date_to.isoformat(),
            )
            .all()
        )
        count = len(rows)
        for w in rows:
            session.delete(w)
        session.commit()
        return {"deleted_count": count}


def _log_completed_workout(planned_id: int, activity_id: int) -> dict:
    with get_session() as session:
        w = session.query(PlannedWorkoutRow).filter(PlannedWorkoutRow.id == planned_id).first()
        if not w:
            raise MCPToolError(
                f"Planned workout {planned_id} not found. Use list_planned_workouts "
                f"to see valid workout ids."
            )
        activity = session.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            raise MCPToolError(f"Activity {activity_id} not found in Strava activity history.")

        result: dict = {"linked": True, "planned_id": planned_id, "activity_id": activity_id}

        planned_date = date.fromisoformat(w.date)
        activity_date = activity.start_time.date()
        diff_days = abs((activity_date - planned_date).days)
        if diff_days > 2:
            result["warning"] = (
                f"Activity date {activity_date.isoformat()} is {diff_days} days away "
                f"from the planned date {planned_date.isoformat()}. Linked anyway, but "
                f"double-check this is the right activity."
            )

        w.completed_activity_id = activity_id
        w.updated_at = _now()
        session.commit()
        return result


def register(mcp):
    @mcp.tool()
    def list_planned_workouts(
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PlannedWorkoutSummary]:
        """
        List planned workouts in a date range. Defaults to today through 4
        weeks from now (the active forward-looking plan). Pass earlier dates
        to see past planned workouts for adherence review.

        Returns summary info only. Use get_planned_workout(id) for full step
        details.
        """
        return _list_planned_workouts(date_from, date_to)

    @mcp.tool()
    def get_planned_workout(workout_id: int) -> PlannedWorkout:
        """
        Full detail of a planned workout including all structured steps.
        Use this when you need the exact warmup/interval/cooldown structure
        of a specific session, e.g. to explain or adjust it.
        """
        return _get_planned_workout(workout_id)

    @mcp.tool()
    def create_workout(
        date: date,
        sport: Sport,
        title: str,
        steps: list[WorkoutStep],
        description: str | None = None,
        duration_min: int | None = None,
        distance_m: float | None = None,
        tss_planned: float | None = None,
        notes: str | None = None,
    ) -> PlannedWorkout:
        """
        Create a single planned workout. Date must be today or later. Use
        bulk_create_workouts to add an entire training block (faster, atomic).

        steps must be non-empty; each step needs duration_min and/or
        distance_m. Run steps cannot use target_power_pct_ftp.
        """
        return _create_workout(
            date, sport, title, steps, description, duration_min, distance_m, tss_planned, notes
        )

    @mcp.tool()
    def bulk_create_workouts(workouts: list[NewWorkout]) -> BulkResult:
        """
        Create many planned workouts in one call. Use this for creating an
        entire training plan (e.g. a 16-week marathon block). Atomic: if any
        workout fails validation, none are created and the error explains
        which workout (by position and date) was invalid.

        Typical usage: generate the full plan as a list, then call this once
        instead of many separate create_workout calls.
        """
        return _bulk_create_workouts(workouts)

    @mcp.tool()
    def update_workout(
        workout_id: int,
        date: date | None = None,
        title: str | None = None,
        sport: Sport | None = None,
        steps: list[WorkoutStep] | None = None,
        description: str | None = None,
        duration_min: int | None = None,
        distance_m: float | None = None,
        tss_planned: float | None = None,
        notes: str | None = None,
    ) -> PlannedWorkout:
        """
        Modify a future planned workout. Past workouts are frozen and cannot
        be changed — this preserves adherence history; use
        log_completed_workout to mark adherence instead. Only the fields you
        pass get updated; leave a field as None to keep it unchanged.
        """
        return _update_workout(
            workout_id, date, title, sport, steps, description, duration_min, distance_m,
            tss_planned, notes,
        )

    @mcp.tool()
    def bulk_update_workouts(updates: list[WorkoutUpdate]) -> BulkResult:
        """
        Update many planned workouts in one call. Atomic: if any update is
        invalid (not found, or targets a frozen past workout, or moves a
        workout into the past), none are applied. Use this for plan
        adjustments that span multiple sessions (e.g. "reduce next week,
        shift everything by a day").
        """
        return _bulk_update_workouts(updates)

    @mcp.tool()
    def delete_workout(workout_id: int) -> dict:
        """
        Delete a future planned workout. Past workouts cannot be deleted
        (would corrupt adherence history). Returns {"deleted": workout_id}.
        """
        return _delete_workout(workout_id)

    @mcp.tool()
    def delete_workouts_in_range(date_from: date, date_to: date) -> dict:
        """
        Delete all future planned workouts in [date_from, date_to]. Use this
        to wipe an old plan before creating a new one (e.g. "scrap the rest
        of my marathon plan, build me a new 10k block").

        date_from must be today or later. Returns {"deleted_count": N}.
        """
        return _delete_workouts_in_range(date_from, date_to)

    @mcp.tool()
    def log_completed_workout(planned_id: int, activity_id: int) -> dict:
        """
        Link a Strava activity to a planned workout, marking it completed.
        Use this when reviewing what was done vs what was planned. Returns
        {"linked": true, "planned_id": ..., "activity_id": ...}, with an
        added "warning" if the activity date is more than 2 days from the
        planned date (the link is still made).
        """
        return _log_completed_workout(planned_id, activity_id)
