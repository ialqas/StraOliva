"""Importer for Strava bulk export ZIPs (German locale CSV)."""

import csv
import gzip
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Callable

import gpxpy
from fitparse import FitFile

from app.db.models import Activity, Lap, Stream
from app.db.session import get_db

# FIT stores lat/lng in semicircles
_SEMICIRCLES = 180.0 / (2**31)

# TCX XML namespaces
_TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
_AX_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"


def import_zip(
    zip_path: str,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, int]:
    stats = {"imported": 0, "skipped": 0, "errors": 0}

    with zipfile.ZipFile(zip_path) as zf:
        csv_entries = [n for n in zf.namelist() if n.endswith("activities.csv")]
        if not csv_entries:
            raise FileNotFoundError("activities.csv not found in ZIP")

        with zf.open(csv_entries[0]) as f:
            # Strava German export uses comma as decimal separator inside quoted fields,
            # so standard csv parsing still works — no special dialect needed.
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
            rows = list(reader)

        for i, row in enumerate(rows):
            name = row.get("Name der Aktivität", "")
            if on_progress:
                on_progress(i, len(rows), name)
            try:
                if _import_row(zf, row):
                    stats["imported"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as exc:
                stats["errors"] += 1
                print(f"  [!] Skipped {name!r}: {exc}")

    return stats


# ── Row → DB ─────────────────────────────────────────────────────────────────

def _import_row(zf: zipfile.ZipFile, row: dict) -> bool:
    """Returns True if newly imported, False if already in DB."""
    activity_id_str = row.get("Aktivitäts-ID", "").strip()
    if not activity_id_str:
        return False

    activity_id = int(activity_id_str)

    with get_db() as db:
        if db.query(Activity).filter(Activity.id == activity_id).first():
            return False

        # CSV has duplicate column names; DictReader gives us the LAST value for
        # each key, which happens to be the more precise one (meters, not km).
        activity = Activity(
            id=activity_id,
            name=row.get("Name der Aktivität", ""),
            type=row.get("Aktivitätsart", ""),
            start_time=_parse_date(row.get("Aktivitätsdatum", "")),
            elapsed_time_s=_safe_int(row.get("Verstrichene Zeit")),
            moving_time_s=_safe_int(row.get("Bewegungszeit")),
            distance_m=_safe_float(row.get("Distanz")),  # last occurrence = meters
            total_elevation_gain_m=_safe_float(row.get("Höhenzunahme")),
            avg_hr=_safe_float(row.get("Durchschnittliche Herzfrequenz")),
            max_hr=_safe_int(row.get("Max. Herzfrequenz")),  # last occurrence
            avg_watts=_safe_float(row.get("Durchschnittliche Watt")),
            weighted_avg_watts=_safe_int(row.get("Gewichtete durchschnittliche Leistung")),
        )

        filename = row.get("Dateiname", "").strip()
        streams, laps = [], []

        if filename and filename in zf.namelist():
            try:
                raw_bytes = _read_entry(zf, filename)
                ext = filename.lower().removesuffix(".gz")
                if ext.endswith(".fit"):
                    streams, laps = _parse_fit(raw_bytes, activity_id)
                elif ext.endswith(".gpx"):
                    streams = _parse_gpx(raw_bytes, activity_id)
                elif ext.endswith(".tcx"):
                    streams, laps = _parse_tcx(raw_bytes, activity_id)
                activity.has_streams = bool(streams)
            except Exception as exc:
                print(f"  [!] Stream parse failed for {filename}: {exc}")

        db.add(activity)
        db.flush()  # get the PK before inserting dependents

        if streams:
            # Deduplicate by time_s — some files have repeated timestamps
            unique = {s.time_s: s for s in streams}
            db.add_all(unique.values())
        if laps:
            db.add_all(laps)

    return True


# ── File parsers ──────────────────────────────────────────────────────────────

def _read_entry(zf: zipfile.ZipFile, name: str) -> bytes:
    raw = zf.read(name)
    return gzip.decompress(raw) if name.endswith(".gz") else raw


def _parse_fit(data: bytes, activity_id: int) -> tuple[list[Stream], list[Lap]]:
    fit = FitFile(io.BytesIO(data))
    streams: list[Stream] = []
    laps: list[Lap] = []
    start_ts = None

    for msg in fit.get_messages("record"):
        fields = {f.name: f.value for f in msg if f.value is not None}
        ts = fields.get("timestamp")
        if ts is None:
            continue
        if start_ts is None:
            start_ts = ts
        time_s = int((ts - start_ts).total_seconds())

        lat = fields.get("position_lat")
        lng = fields.get("position_long")
        streams.append(Stream(
            activity_id=activity_id,
            time_s=time_s,
            hr=_scalar(fields.get("heart_rate")),
            watts=_scalar(fields.get("power")),
            cadence=_scalar(fields.get("cadence")),
            lat=_scalar(lat) * _SEMICIRCLES if lat is not None else None,
            lng=_scalar(lng) * _SEMICIRCLES if lng is not None else None,
            altitude_m=_scalar(fields.get("enhanced_altitude") or fields.get("altitude")),
            velocity_smooth=_scalar(fields.get("enhanced_speed") or fields.get("speed")),
        ))

    for i, msg in enumerate(fit.get_messages("lap")):
        fields = {f.name: f.value for f in msg if f.value is not None}
        laps.append(Lap(
            activity_id=activity_id,
            lap_index=i,
            distance_m=fields.get("total_distance"),
            time_s=fields.get("total_elapsed_time"),
            moving_time_s=_safe_int(fields.get("total_timer_time")),
            avg_hr=fields.get("avg_heart_rate"),
            avg_watts=fields.get("avg_power"),
            avg_speed_ms=fields.get("enhanced_avg_speed") or fields.get("avg_speed"),
        ))

    return streams, laps


def _parse_gpx(data: bytes, activity_id: int) -> list[Stream]:
    gpx = gpxpy.parse(io.StringIO(data.decode("utf-8")))
    streams: list[Stream] = []
    t0 = None

    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                if t0 is None:
                    t0 = pt.time
                time_s = int((pt.time - t0).total_seconds()) if pt.time and t0 else len(streams)

                hr = cadence = None
                for ext in (pt.extensions or []):
                    for child in ext:
                        tag = child.tag.split("}")[-1].lower()
                        if tag in ("hr", "heartrate"):
                            try:
                                hr = int(child.text)
                            except (TypeError, ValueError):
                                pass
                        elif tag in ("cad", "cadence", "runcadence"):
                            try:
                                cadence = int(child.text)
                            except (TypeError, ValueError):
                                pass

                streams.append(Stream(
                    activity_id=activity_id,
                    time_s=time_s,
                    hr=hr,
                    watts=None,
                    cadence=cadence,
                    lat=pt.latitude,
                    lng=pt.longitude,
                    altitude_m=pt.elevation,
                    velocity_smooth=None,
                ))

    return streams


def _parse_tcx(data: bytes, activity_id: int) -> tuple[list[Stream], list[Lap]]:
    # Handle UTF-16 encoding (common in Garmin TCX exports)
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16")
        text = re.sub(r"<\?xml[^?]*\?>\s*", "", text, count=1)
        data = text.encode("utf-8")
    elif data[:3] == b"\xef\xbb\xbf":
        data = data[3:]  # strip UTF-8 BOM

    data = data.lstrip()  # some exports have leading whitespace before <?xml

    # Strip namespace prefixes so we can use simple tag names
    root = ET.fromstring(data)
    _strip_ns(root)

    streams: list[Stream] = []
    laps: list[Lap] = []
    t0 = None

    for lap_el in root.findall(".//Lap"):
        time_s_el = lap_el.find("TotalTimeSeconds")
        dist_el = lap_el.find("DistanceMeters")
        hr_avg_el = lap_el.find(".//AverageHeartRateBpm/Value")
        speed_avg_el = lap_el.find(".//Extensions//AvgSpeed")
        watts_avg_el = lap_el.find(".//Extensions//AvgWatts")
        cad_el = lap_el.find(".//Extensions//AvgRunCadence") or lap_el.find(".//Extensions//AvgCadence")

        laps.append(Lap(
            activity_id=activity_id,
            lap_index=len(laps),
            time_s=_safe_int(time_s_el.text if time_s_el is not None else None),
            distance_m=_safe_float(dist_el.text if dist_el is not None else None),
            avg_hr=_safe_float(hr_avg_el.text if hr_avg_el is not None else None),
            avg_speed_ms=_safe_float(speed_avg_el.text if speed_avg_el is not None else None),
            avg_watts=_safe_float(watts_avg_el.text if watts_avg_el is not None else None),
        ))

        for tp in lap_el.findall(".//Trackpoint"):
            time_el = tp.find("Time")
            if time_el is None:
                continue
            t = datetime.fromisoformat(time_el.text.replace("Z", "+00:00"))
            if t0 is None:
                t0 = t
            time_s = int((t - t0).total_seconds())

            lat = lng = altitude = hr = speed = watts = cadence = None

            pos = tp.find("Position")
            if pos is not None:
                lat_el = pos.find("LatitudeDegrees")
                lng_el = pos.find("LongitudeDegrees")
                lat = _safe_float(lat_el.text if lat_el is not None else None)
                lng = _safe_float(lng_el.text if lng_el is not None else None)

            alt_el = tp.find("AltitudeMeters")
            altitude = _safe_float(alt_el.text if alt_el is not None else None)

            hr_el = tp.find(".//HeartRateBpm/Value")
            hr = _safe_int(hr_el.text if hr_el is not None else None)

            for tpx in tp.findall(".//TPX"):
                s_el = tpx.find("Speed")
                w_el = tpx.find("Watts")
                c_el = tpx.find("RunCadence") or tpx.find("Cadence")
                if s_el is not None:
                    speed = _safe_float(s_el.text)
                if w_el is not None:
                    watts = _safe_float(w_el.text)
                if c_el is not None:
                    cadence = _safe_int(c_el.text)

            streams.append(Stream(
                activity_id=activity_id,
                time_s=time_s,
                hr=hr,
                watts=watts,
                cadence=cadence,
                lat=lat,
                lng=lng,
                altitude_m=altitude,
                velocity_smooth=speed,
            ))

    return streams, laps


def _strip_ns(el: ET.Element) -> None:
    """Remove XML namespace prefixes from all tags in-place."""
    if el.tag.startswith("{"):
        el.tag = el.tag.split("}", 1)[1]
    for child in el:
        _strip_ns(child)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(s: str) -> datetime:
    s = s.strip()
    for fmt in (
        "%d.%m.%Y, %H:%M:%S",   # Strava German: "15.05.2026, 16:28:37"
        "%b %d, %Y, %I:%M:%S %p",  # Strava English: "May 1, 2024, 7:30:00 AM"
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date: {s!r}")


def _scalar(v: object) -> object:
    """Return the first element if fitparse gave us a tuple/list, else v as-is."""
    if isinstance(v, (tuple, list)):
        return v[0] if v else None
    return v


def _safe_float(v: object) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _safe_int(v: object) -> int | None:
    f = _safe_float(v)
    return int(f) if f is not None else None
