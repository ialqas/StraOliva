from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class StravaAuth(Base):
    """Singleton row — one athlete, one token set."""

    __tablename__ = "strava_auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)  # Unix timestamp
    athlete_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    scope: Mapped[str] = mapped_column(String, nullable=False, default="")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Strava activity ID
    type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moving_time_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    elapsed_time_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_elevation_gain_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weighted_avg_watts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    np: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kilojoules: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    has_streams: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Strava activity description. NULL = never fetched (the /athlete/activities list
    # endpoint omits it), "" = fetched and empty. See sync/descriptions.py.
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    streams: Mapped[list["Stream"]] = relationship("Stream", back_populates="activity", cascade="all, delete-orphan")
    laps: Mapped[list["Lap"]] = relationship("Lap", back_populates="activity", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_activities_start_time", "start_time"),)


class Stream(Base):
    __tablename__ = "streams"

    activity_id: Mapped[int] = mapped_column(Integer, ForeignKey("activities.id"), primary_key=True)
    time_s: Mapped[int] = mapped_column(Integer, primary_key=True)
    hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cadence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altitude_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    velocity_smooth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    activity: Mapped["Activity"] = relationship("Activity", back_populates="streams")

    __table_args__ = (Index("ix_streams_activity_id", "activity_id"),)


class Lap(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(Integer, ForeignKey("activities.id"), nullable=False)
    lap_index: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # elapsed — includes pauses
    # Timer time without pauses (Strava lap `moving_time` / FIT `total_timer_time`).
    # NULL for laps stored before this column existed — use `moving_s` instead.
    moving_time_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_speed_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    activity: Mapped["Activity"] = relationship("Activity", back_populates="laps")

    @property
    def moving_s(self) -> int | None:
        """Lap time without pauses. Older rows lack `moving_time_s`, but their
        average speed is already distance / moving time (both Strava and FIT),
        so it can be recovered from that."""
        if self.moving_time_s is not None:
            return self.moving_time_s
        if self.distance_m and self.avg_speed_ms and self.avg_speed_ms > 0:
            return round(self.distance_m / self.avg_speed_ms)
        return self.time_s


class KmSplit(Base):
    """Strava's automatic per-kilometre splits (`splits_metric` on the activity detail)."""

    __tablename__ = "km_splits"

    activity_id: Mapped[int] = mapped_column(Integer, ForeignKey("activities.id"), primary_key=True)
    split_index: Mapped[int] = mapped_column(Integer, primary_key=True)  # 1-based, as Strava
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    moving_time_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    elapsed_time_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_speed_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_diff_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class TrainingLoadDaily(Base):
    __tablename__ = "training_load_daily"

    date: Mapped[str] = mapped_column(String, primary_key=True)  # ISO date YYYY-MM-DD
    ctl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    atl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tsb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_tss: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (Index("ix_training_load_daily_date", "date"),)


class FtpHistory(Base):
    __tablename__ = "ftp_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Date of the effort the value came from (auto) or when it was set (manual).
    # The *current* FTP is the most recently inserted row (highest id), not the latest date.
    date: Mapped[str] = mapped_column(String, nullable=False)
    ftp_w: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)  # 'auto' | 'manual'


class TrainingPlan(Base):
    """Container for a training plan (one default plan is auto-created)."""
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="Mein Trainingsplan")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_event: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default="")

    planned_workouts: Mapped[list["PlannedWorkout"]] = relationship(
        "PlannedWorkout", back_populates="plan", cascade="all, delete-orphan"
    )


class PlannedWorkout(Base):
    """A single planned training session, with structured steps stored as JSON."""
    __tablename__ = "planned_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("training_plans.id"), nullable=True
    )
    date: Mapped[str] = mapped_column(String, nullable=False)          # ISO YYYY-MM-DD
    title: Mapped[str] = mapped_column(String, nullable=False, default="Training")
    sport: Mapped[str] = mapped_column(String, nullable=False, default="run")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tss_planned: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # JSON list of WorkoutStep dicts — see api/training_plan.py for schema
    steps_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completed_activity_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("activities.id"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False, default="")
    updated_at: Mapped[str] = mapped_column(String, nullable=False, default="")

    plan: Mapped[Optional["TrainingPlan"]] = relationship(
        "TrainingPlan", back_populates="planned_workouts"
    )


class Segment(Base):
    """Strava starred segments — synced via `strava-dash sync-segments`."""

    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Strava segment ID
    name: Mapped[str] = mapped_column(String, nullable=False)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    end_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_grade: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    climb_category: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    polyline: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class AppState(Base):
    """Small key/value store for pipeline bookkeeping (e.g. the inputs the stored TSS values were computed with)."""

    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
