"""Small, dependency-free helper functions."""

from __future__ import annotations

import math
from datetime import datetime


def now_iso() -> str:
    """Return the current local time as an ISO-8601 string (seconds precision)."""
    return datetime.now().isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp produced by :func:`now_iso`."""
    return datetime.fromisoformat(value)


def format_timestamp(value: str | None) -> str:
    """Format an ISO timestamp for display, or an em dash when missing/invalid."""
    if not value:
        return "—"
    try:
        return parse_iso(value).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return "—"


def format_duration(seconds: float | None) -> str:
    """Format a duration in seconds as e.g. ``1h 05m 09s``, ``4m 02s`` or ``7s``."""
    if seconds is None or (isinstance(seconds, float) and math.isnan(seconds)):
        return "—"
    total = int(round(max(0.0, float(seconds))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"
