"""
CTL / ATL / TSB (Chronic Training Load, Acute Training Load, Training Stress Balance).

All functions are pure — input is a dict/Series of {date: tss}, output is a DataFrame.
"""

import math
from datetime import date, timedelta

import pandas as pd
from pydantic import BaseModel

from app.i18n import Lang, tr


# Decay constants: 1 - exp(-1/tau)
_CTL_K = 1 - math.exp(-1 / 42)   # 42-day fitness
_ATL_K = 1 - math.exp(-1 / 7)    # 7-day fatigue


class DailyLoad(BaseModel):
    date: str          # ISO YYYY-MM-DD
    ctl: float         # fitness
    atl: float         # fatigue
    tsb: float         # form = CTL - ATL
    total_tss: float


def compute_daily_tss(activities_df: pd.DataFrame) -> pd.Series:
    """
    Aggregate activity TSS values to daily totals.

    activities_df must have columns: start_time (datetime), tss (float).
    Returns a pd.Series indexed by date (date objects), values = total TSS.
    """
    df = activities_df.copy()
    df = df[df["tss"].notna() & (df["tss"] > 0)]
    if df.empty:
        return pd.Series(dtype=float)

    df["date"] = pd.to_datetime(df["start_time"]).dt.date
    return df.groupby("date")["tss"].sum()


def compute_ctl_atl_tsb(daily_tss: pd.Series) -> list[DailyLoad]:
    """
    Compute CTL/ATL/TSB from a daily TSS series.

    daily_tss: pd.Series indexed by date objects (no gaps required — this fills them).
    Returns list of DailyLoad from first activity day to last, one entry per calendar day.
    """
    if daily_tss.empty:
        return []

    start = min(daily_tss.index)
    end = max(daily_tss.index)
    idx = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    ctl = 0.0
    atl = 0.0
    result: list[DailyLoad] = []

    for d in idx:
        tss = float(daily_tss.get(d, 0.0))
        ctl += (tss - ctl) * _CTL_K
        atl += (tss - atl) * _ATL_K
        result.append(DailyLoad(
            date=d.isoformat(),
            ctl=round(ctl, 2),
            atl=round(atl, 2),
            tsb=round(ctl - atl, 2),
            total_tss=round(tss, 2),
        ))

    return result


def current_form(loads: list[DailyLoad]) -> DailyLoad | None:
    """Return the most recent DailyLoad entry."""
    return loads[-1] if loads else None


def form_trend(loads: list[DailyLoad], days: int = 7) -> float | None:
    """TSB change over the last N days (positive = improving form)."""
    if len(loads) < 2:
        return None
    recent = loads[-min(days, len(loads)):]
    return round(recent[-1].tsb - recent[0].tsb, 2)


def ramp_rate(loads: list[DailyLoad], weeks: int = 4) -> float | None:
    """CTL change per week over the last N weeks (positive = building fitness)."""
    if len(loads) < 2:
        return None
    days = weeks * 7
    past = loads[-min(days, len(loads))]
    now = loads[-1]
    elapsed_weeks = max(1, days / 7)
    return round((now.ctl - past.ctl) / elapsed_weeks, 2)


def classify_trajectory(ramp_per_week: float | None) -> str:
    """Classify fitness trajectory from weekly CTL ramp rate."""
    if ramp_per_week is None:
        return "unknown"
    if ramp_per_week > 1.5:
        return "rapid_build"
    if ramp_per_week > 0.5:
        return "building"
    if ramp_per_week >= -0.5:
        return "stagnant"
    return "detraining"


def interpret_form(
    ctl: float,
    atl: float,
    tsb: float,
    recent_tss_7d: float,
    lang: Lang = "de",
) -> str:
    """
    Return a 1-2 sentence human-readable interpretation of the current
    training form (TSB / CTL / ATL).
    """
    # Zone description
    if tsb < -30:
        zone = tr(lang, "Übertraining-Risiko", "Overtraining risk")
        advice = tr(
            lang,
            "Reduziere die Belastung sofort — Erholungswoche einplanen.",
            "Reduce load immediately — plan a recovery week.",
        )
    elif tsb < -10:
        zone = tr(lang, "Produktive Überlastung", "Productive overload")
        target_tss = round(recent_tss_7d * 1.05 / 7, 0)
        advice = tr(
            lang,
            f"Guter Aufbaubereich. Für weitere Steigerung: TSS-Schnitt auf ~{target_tss:.0f}/Tag halten.",
            f"Good build zone. To keep progressing: hold an average of ~{target_tss:.0f} TSS/day.",
        )
    elif tsb <= 5:
        zone = tr(lang, "Optimales Training", "Optimal training")
        target_tss = round(recent_tss_7d * 1.15 / 7, 0)
        advice = tr(
            lang,
            f"Training und Erholung im Gleichgewicht. Für Aufbau: Tages-TSS von ~{target_tss:.0f} anstreben.",
            f"Training and recovery are balanced. To build: aim for ~{target_tss:.0f} TSS per day.",
        )
    elif tsb <= 25:
        zone = tr(lang, "Frisch / wettkampfbereit", "Fresh / race ready")
        advice = tr(
            lang,
            "Gute Form für einen Wettkampf oder eine Testeinheit. Belastung erhöhen, um die Fitness zu halten.",
            "Good form for a race or test session. Increase load to maintain fitness.",
        )
    else:
        zone = "Detraining"
        advice = tr(
            lang,
            "Zu wenig Training in den letzten Wochen. Belastung schrittweise erhöhen.",
            "Too little training in recent weeks. Increase load gradually.",
        )

    return f"{zone}. {advice}"
