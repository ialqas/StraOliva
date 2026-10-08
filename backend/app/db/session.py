from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base


def _make_engine():
    return create_engine(
        f"sqlite:///{settings.db_path}",
        connect_args={"check_same_thread": False},
    )


engine = _make_engine()


@event.listens_for(engine, "connect")
def _enable_wal(dbapi_conn, _):
    """WAL mode allows the FastAPI backend and MCP server to access the DB concurrently."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Add columns introduced after the initial schema creation (SQLite can't ALTER via create_all)."""
    migrations = [
        ("segments",          "ALTER TABLE segments ADD COLUMN polyline TEXT"),
        ("activities",        "ALTER TABLE activities ADD COLUMN description TEXT"),
        ("laps",              "ALTER TABLE laps ADD COLUMN moving_time_s INTEGER"),
        # training_plans new columns
        ("training_plans",    "ALTER TABLE training_plans ADD COLUMN description TEXT"),
        ("training_plans",    "ALTER TABLE training_plans ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"),
        # planned_workouts new columns
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN title TEXT NOT NULL DEFAULT 'Training'"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN sport TEXT NOT NULL DEFAULT 'run'"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN description TEXT"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN duration_min INTEGER"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN distance_m REAL"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN tss_planned REAL"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN steps_json TEXT"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN notes TEXT"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"),
        ("planned_workouts",  "ALTER TABLE planned_workouts ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"),
    ]
    with engine.connect() as conn:
        existing = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        for table, stmt in migrations:
            if table not in existing:
                continue
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_dep() -> Generator[Session, None, None]:
    """FastAPI dependency."""
    with get_db() as db:
        yield db
