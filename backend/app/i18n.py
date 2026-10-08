"""Minimal localisation for user-facing strings returned by the API."""

from typing import Literal

Lang = Literal["de", "en"]


def tr(lang: Lang, de: str, en: str) -> str:
    """Pick the German or English variant of a string."""
    return de if lang == "de" else en
