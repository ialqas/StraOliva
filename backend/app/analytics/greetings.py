"""Greeting counts annotated in Strava activity descriptions.

Convention: the activity description contains *nothing but* an integer — the
number of people who greeted back on that run. Anything else (empty
description, a real note, "3 Leute", "ca. 3") is not an annotation and is
ignored, so a normal description never silently inflates the count.
"""

import re

_NUMBER_ONLY = re.compile(r"\d+")


def parse_greeting_count(description: str | None) -> int | None:
    """Return the annotated greeting count, or None if the description is not
    a bare number."""
    if not description:
        return None
    text = description.strip()
    if not _NUMBER_ONLY.fullmatch(text):
        return None
    return int(text)
