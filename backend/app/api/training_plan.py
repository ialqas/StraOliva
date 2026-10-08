"""
Training Plan CRUD API.

A single default TrainingPlan is auto-created per DB.
PlannedWorkouts are attached to that plan and exposed via date-based queries.

Workout step JSON schema (each element in steps_json):
{
  "type": "warmup" | "interval" | "recovery" | "cooldown" | "steady" | "rest",
  "label": "Einlaufen",
  "description": "2 km locker einlaufen",
  "distance_m": 2000,
  "duration_min": null,
  "reps": null,
  "target_pace_min_km": null,
  "target_hr_zone": "Z2",
  "target_power_pct_ftp": null
}
"""

import json
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Activity, PlannedWorkout, TrainingPlan
from app.db.session import get_db_dep

router = APIRouter(tags=["training-plan"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class WorkoutStep(BaseModel):
    type: str                          # warmup | interval | recovery | cooldown | steady | rest
    label: str
    description: str | None = None
    distance_m: float | None = None
    duration_min: float | None = None
    reps: int | None = None
    target_pace_min_km: float | None = None
    target_hr_zone: str | None = None
    target_power_pct_ftp: float | None = None


class WorkoutCreate(BaseModel):
    date: str                          # ISO YYYY-MM-DD
    title: str
    sport: str = "run"
    description: str | None = None
    duration_min: int | None = None
    distance_m: float | None = None
    tss_planned: float | None = None
    steps: list[WorkoutStep] = []
    notes: str | None = None


class WorkoutUpdate(BaseModel):
    date: str | None = None
    title: str | None = None
    sport: str | None = None
    description: str | None = None
    duration_min: int | None = None
    distance_m: float | None = None
    tss_planned: float | None = None
    steps: list[WorkoutStep] | None = None
    notes: str | None = None


class WorkoutOut(BaseModel):
    id: int
    date: str
    title: str
    sport: str
    description: str | None
    duration_min: int | None
    distance_m: float | None
    tss_planned: float | None
    steps: list[WorkoutStep]
    notes: str | None
    completed_activity_id: int | None
    created_at: str
    updated_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_or_create_plan(db: Session) -> TrainingPlan:
    plan = db.query(TrainingPlan).first()
    if not plan:
        plan = TrainingPlan(name="Mein Trainingsplan", created_at=_now())
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


def _to_out(w: PlannedWorkout) -> WorkoutOut:
    steps: list[WorkoutStep] = []
    if w.steps_json:
        try:
            steps = [WorkoutStep(**s) for s in json.loads(w.steps_json)]
        except Exception:
            steps = []
    return WorkoutOut(
        id=w.id,
        date=w.date,
        title=w.title or "Training",
        sport=w.sport or "run",
        description=w.description,
        duration_min=w.duration_min,
        distance_m=w.distance_m,
        tss_planned=w.tss_planned,
        steps=steps,
        notes=w.notes,
        completed_activity_id=w.completed_activity_id,
        created_at=w.created_at or "",
        updated_at=w.updated_at or "",
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/training-plan/workouts", response_model=list[WorkoutOut])
def list_workouts(
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db_dep),
):
    """Return workouts, optionally filtered to a specific month."""
    q = db.query(PlannedWorkout).order_by(PlannedWorkout.date)
    if year and month:
        prefix = f"{year:04d}-{month:02d}"
        q = q.filter(PlannedWorkout.date.like(f"{prefix}%"))
    return [_to_out(w) for w in q.all()]


@router.get("/training-plan/workouts/{workout_id}", response_model=WorkoutOut)
def get_workout(workout_id: int, db: Session = Depends(get_db_dep)):
    w = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()
    if not w:
        raise HTTPException(404, "Workout not found")
    return _to_out(w)


@router.post("/training-plan/workouts", response_model=WorkoutOut, status_code=201)
def create_workout(body: WorkoutCreate, db: Session = Depends(get_db_dep)):
    plan = _get_or_create_plan(db)
    now = _now()
    w = PlannedWorkout(
        plan_id=plan.id,
        date=body.date,
        title=body.title,
        sport=body.sport,
        description=body.description,
        duration_min=body.duration_min,
        distance_m=body.distance_m,
        tss_planned=body.tss_planned,
        steps_json=json.dumps([s.model_dump() for s in body.steps]),
        notes=body.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return _to_out(w)


@router.patch("/training-plan/workouts/{workout_id}", response_model=WorkoutOut)
def update_workout(workout_id: int, body: WorkoutUpdate, db: Session = Depends(get_db_dep)):
    w = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()
    if not w:
        raise HTTPException(404, "Workout not found")
    if body.date is not None:      w.date = body.date
    if body.title is not None:     w.title = body.title
    if body.sport is not None:     w.sport = body.sport
    if body.description is not None: w.description = body.description
    if body.duration_min is not None: w.duration_min = body.duration_min
    if body.distance_m is not None: w.distance_m = body.distance_m
    if body.tss_planned is not None: w.tss_planned = body.tss_planned
    if body.steps is not None:
        w.steps_json = json.dumps([s.model_dump() for s in body.steps])
    if body.notes is not None:     w.notes = body.notes
    w.updated_at = _now()
    db.commit()
    db.refresh(w)
    return _to_out(w)


@router.delete("/training-plan/workouts/{workout_id}", status_code=204)
def delete_workout(workout_id: int, db: Session = Depends(get_db_dep)):
    w = db.query(PlannedWorkout).filter(PlannedWorkout.id == workout_id).first()
    if not w:
        raise HTTPException(404, "Workout not found")
    db.delete(w)
    db.commit()


@router.get("/training-plan/calendar")
def calendar_month(
    year: int,
    month: int,
    db: Session = Depends(get_db_dep),
):
    """
    Return planned workouts + completed Strava activities for a given month.
    Used by the calendar view to show both planned and actual training.
    """
    prefix = f"{year:04d}-{month:02d}"

    workouts = db.query(PlannedWorkout).filter(
        PlannedWorkout.date.like(f"{prefix}%")
    ).order_by(PlannedWorkout.date).all()

    # Strava activities for the same month (for overlay)
    month_start = f"{prefix}-01"
    if month == 12:
        next_prefix = f"{year + 1:04d}-01"
    else:
        next_prefix = f"{year:04d}-{month + 1:02d}"
    month_end = f"{next_prefix}-01"

    activities = db.query(
        Activity.id, Activity.name, Activity.type,
        Activity.start_time, Activity.distance_m,
        Activity.moving_time_s, Activity.tss,
    ).filter(
        Activity.start_time >= month_start,
        Activity.start_time < month_end,
    ).order_by(Activity.start_time).all()

    return {
        "planned": [_to_out(w) for w in workouts],
        "completed": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "date": a.start_time.strftime("%Y-%m-%d"),
                "distance_m": a.distance_m,
                "moving_time_s": a.moving_time_s,
                "tss": round(a.tss, 1) if a.tss else None,
            }
            for a in activities
        ],
    }
