"""Tools for inspecting individual workouts and recent activity history."""

import math
from typing import Literal

import pandas as pd

from app.analytics.athlete import athlete_max_hr
from app.analytics.decoupling import aerobic_decoupling
from app.analytics.splits import detect_split_anomalies
from app.analytics.zones import hr_zones_time, power_zones_time
from app.config import settings
from app.db.models import Activity, FtpHistory, Lap, Stream
from app.mcp_server.db import get_session
from app.mcp_server.errors import MCPToolError
from app.mcp_server.models import ActivityStreams, ActivitySummary, WorkoutAnalysis
from app.mcp_server.util import format_pace, hr_drift_pct, sport_label


def _activity_summary(activity: Activity) -> ActivitySummary:
    sport = sport_label(activity.type)
    distance_km = round((activity.distance_m or 0) / 1000, 2)
    duration_min = round((activity.moving_time_s or 0) / 60, 1)
    tss = round(activity.tss or 0)

    parts = []
    if distance_km:
        parts.append(f"{distance_km} km")
    if sport == "Run" and activity.moving_time_s and activity.distance_m:
        pace = activity.moving_time_s / (activity.distance_m / 1000)
        parts.append(f"{format_pace(pace)}/km")
    elif sport == "Ride" and activity.avg_watts:
        parts.append(f"{round(activity.avg_watts)} W")
    parts.append(f"TSS {tss}")

    return ActivitySummary(
        id=activity.id,
        date=activity.start_time.date(),
        sport=sport,
        name=activity.name,
        distance_km=distance_km,
        duration_min=duration_min,
        tss=tss,
        summary_line=f"{activity.name} · " + " · ".join(parts),
    )


def _get_recent_activities(n: int = 10, sport: str | None = None) -> list[ActivitySummary]:
    with get_session() as session:
        results: list[ActivitySummary] = []
        offset = 0
        batch_size = max(n, 20)
        while len(results) < n:
            batch = (
                session.query(Activity)
                .order_by(Activity.start_time.desc())
                .offset(offset)
                .limit(batch_size)
                .all()
            )
            if not batch:
                break
            for activity in batch:
                if sport and sport_label(activity.type) != sport:
                    continue
                results.append(_activity_summary(activity))
                if len(results) >= n:
                    break
            offset += batch_size
        return results


def _intensity_factor(activity: Activity, np_w: int | None, ftp_w: float | None, is_ride: bool) -> float | None:
    if np_w and ftp_w and ftp_w > 0:
        return round(np_w / ftp_w, 3)
    if not is_ride and activity.tss and activity.moving_time_s:
        hours = activity.moving_time_s / 3600
        if hours > 0:
            return round((activity.tss / (hours * 100)) ** 0.5, 3)
    return None


def _interpret_workout(
    sport: str,
    tss: int,
    intensity_factor: float | None,
    decoupling_pct: float | None,
    hr_drift: float | None,
    split_anomalies: list[str],
) -> str:
    parts: list[str] = []

    if intensity_factor is not None:
        if intensity_factor >= 0.95:
            parts.append(f"Hard effort (IF {intensity_factor:.2f}, TSS {tss}).")
        elif intensity_factor >= 0.75:
            parts.append(f"Moderate effort (IF {intensity_factor:.2f}, TSS {tss}).")
        else:
            parts.append(f"Easy effort (IF {intensity_factor:.2f}, TSS {tss}).")
    else:
        parts.append(f"TSS {tss}.")

    if decoupling_pct is not None:
        if decoupling_pct < 5:
            parts.append(f"Decoupling {decoupling_pct:.1f}% — good aerobic control.")
        elif decoupling_pct <= 7:
            parts.append(f"Decoupling {decoupling_pct:.1f}% — acceptable, near the upper end of aerobic.")
        else:
            parts.append(f"Decoupling {decoupling_pct:.1f}% — significant cardiac drift, suggests pacing too hard or limited aerobic base.")
    elif hr_drift is not None and abs(hr_drift) >= 5:
        parts.append(f"HR drift {hr_drift:+.1f}% over the session.")

    if split_anomalies:
        n = len(split_anomalies)
        parts.append(f"{n} lap{'s' if n != 1 else ''} flagged as pacing outlier{'s' if n != 1 else ''}.")

    return " ".join(parts)


def _analyze_workout(activity_id: int) -> WorkoutAnalysis:
    with get_session() as session:
        activity = session.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            raise MCPToolError(
                f"Activity {activity_id} not found in activities. "
                "Use get_recent_activities to find valid activity ids."
            )

        ftp_row = session.query(FtpHistory).order_by(FtpHistory.id.desc()).first()
        ftp_w: float | None = settings.ftp_w if settings.ftp_w > 0 else (ftp_row.ftp_w if ftp_row else None)

        sport = sport_label(activity.type)
        is_ride = sport == "Ride"
        distance_km = round((activity.distance_m or 0) / 1000, 2)
        duration_min = round((activity.moving_time_s or 0) / 60, 1)
        tss = round(activity.tss or 0)

        avg_pace_per_km: str | None = None
        if sport == "Run" and activity.moving_time_s and activity.distance_m:
            avg_pace_per_km = format_pace(activity.moving_time_s / (activity.distance_m / 1000))

        np_w = round(activity.weighted_avg_watts) if activity.weighted_avg_watts else None
        avg_power_w = round(activity.avg_watts) if activity.avg_watts else None
        intensity_factor = _intensity_factor(activity, np_w, ftp_w, is_ride)

        # Split anomalies from laps (no streams needed)
        split_anomalies: list[str] = []
        laps = (
            session.query(Lap)
            .filter(Lap.activity_id == activity_id)
            .order_by(Lap.lap_index)
            .all()
        )
        if laps:
            laps_dicts = [
                {
                    "lap_index": lap.lap_index,
                    "distance_m": lap.distance_m,
                    "time_s": lap.time_s,
                    "avg_watts": lap.avg_watts,
                    "avg_speed_ms": lap.avg_speed_ms,
                }
                for lap in laps
            ]
            for result in detect_split_anomalies(laps_dicts, is_ride):
                if result["tooltip"]:
                    split_anomalies.append(f"Lap {result['lap_index']}: {result['tooltip']}")

        decoupling_pct: float | None = None
        drift_pct: float | None = None
        hr_zones_min: dict[str, float] | None = None
        power_zones_min: dict[str, float] | None = None

        if activity.has_streams:
            rows = (
                session.query(Stream.time_s, Stream.hr, Stream.watts, Stream.velocity_smooth)
                .filter(Stream.activity_id == activity_id)
                .order_by(Stream.time_s)
                .all()
            )
            if rows:
                df = pd.DataFrame(rows, columns=["time_s", "hr", "watts", "velocity_smooth"])

                dec = aerobic_decoupling(df)
                if dec:
                    decoupling_pct = dec.decoupling_pct

                drift_pct = hr_drift_pct(df)

                hr_zones_sec = hr_zones_time(df, hrmax=athlete_max_hr())
                hr_zones_min = {z: round(s / 60, 1) for z, s in hr_zones_sec.items()}

                if is_ride and ftp_w and ftp_w > 0:
                    power_zones_sec = power_zones_time(df, ftp_w=ftp_w)
                    power_zones_min = {z: round(s / 60, 1) for z, s in power_zones_sec.items()}

        interpretation = _interpret_workout(
            sport=sport,
            tss=tss,
            intensity_factor=intensity_factor,
            decoupling_pct=decoupling_pct,
            hr_drift=drift_pct,
            split_anomalies=split_anomalies,
        )

        return WorkoutAnalysis(
            activity_id=activity.id,
            date=activity.start_time.date(),
            sport=sport,
            name=activity.name,
            distance_km=distance_km,
            duration_min=duration_min,
            elevation_gain_m=round(activity.total_elevation_gain_m or 0),
            avg_hr=round(activity.avg_hr) if activity.avg_hr else None,
            max_hr=activity.max_hr,
            avg_power_w=avg_power_w if is_ride else None,
            np_w=np_w if is_ride else None,
            avg_pace_per_km=avg_pace_per_km,
            intensity_factor=intensity_factor,
            tss=tss,
            decoupling_pct=decoupling_pct,
            hr_drift_pct=drift_pct,
            hr_zones_min=hr_zones_min,
            power_zones_min=power_zones_min,
            split_anomalies=split_anomalies,
            interpretation=interpretation,
        )


def _get_activity_streams(activity_id: int, downsample_to: int = 200) -> ActivityStreams:
    if downsample_to < 1:
        raise MCPToolError("downsample_to must be >= 1.")
    downsample_to = min(downsample_to, 1000)

    with get_session() as session:
        activity = session.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            raise MCPToolError(
                f"Activity {activity_id} not found in activities. "
                "Use get_recent_activities to find valid activity ids."
            )
        if not activity.has_streams:
            raise MCPToolError(f"Activity {activity_id} has no stream data recorded.")

        rows = (
            session.query(Stream)
            .filter(Stream.activity_id == activity_id)
            .order_by(Stream.time_s)
            .all()
        )

    n = len(rows)
    stride = max(1, math.ceil(n / downsample_to))
    sampled = rows[::stride]

    pace_per_km: list[float | None] = [
        (1000 / r.velocity_smooth) if r.velocity_smooth and r.velocity_smooth > 0 else None
        for r in sampled
    ]

    return ActivityStreams(
        activity_id=activity_id,
        time_s=[r.time_s for r in sampled],
        hr=[r.hr for r in sampled],
        power_w=[r.watts for r in sampled],
        pace_per_km=pace_per_km,
        altitude_m=[r.altitude_m for r in sampled],
    )


def register(mcp):
    @mcp.tool()
    def analyze_workout(activity_id: int) -> WorkoutAnalysis:
        """
        Full analysis of a single workout: NP/IF/TSS, decoupling, HR drift,
        time in zones, split anomalies, and a narrative summary. Does NOT
        include raw stream data — use get_activity_streams for that.
        """
        return _analyze_workout(activity_id)

    @mcp.tool()
    def get_activity_streams(activity_id: int, downsample_to: int = 200) -> ActivityStreams:
        """
        Downsampled time-series streams for a single activity. Use ONLY when
        you need to inspect the shape of HR/power/pace within a workout (e.g.
        to explain a specific anomaly). For routine workout analysis, use
        analyze_workout which returns aggregates.

        The default downsample_to=200 keeps responses small. Maximum 1000.
        """
        return _get_activity_streams(activity_id, downsample_to)

    @mcp.tool()
    def get_recent_activities(
        n: int = 10,
        sport: Literal["Run", "Ride", "Swim", "Other"] | None = None,
    ) -> list[ActivitySummary]:
        """
        Most recent activities as summaries (one line each, no streams).
        Filter by sport if specified. Use to scan what the athlete has been
        doing without pulling full details.
        """
        if n < 1:
            raise MCPToolError("n must be >= 1.")
        return _get_recent_activities(n, sport)
