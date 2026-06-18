from __future__ import annotations

from datetime import datetime

from aquen.models import CalendarSlot

# Posting windows by clock hour (half-open [start, end)): midday 12:00–14:00, evening 19:00–21:00.
POSTING_WINDOWS: dict[str, tuple[int, int]] = {
    "midday": (12, 14),
    "evening": (19, 21),
}


class SchedulingError(Exception):
    pass


def window_for(dt: datetime) -> str | None:
    """Return the posting-window name a datetime falls in, or None if outside every window."""
    for name, (start, end) in POSTING_WINDOWS.items():
        if start <= dt.hour < end:
            return name
    return None


def in_posting_window(dt: datetime) -> bool:
    return window_for(dt) is not None


def audio_is_fresh(slot: CalendarSlot, now: datetime) -> bool:
    """A slot's trending audio is fresh until its shelf-life timer (audio_expires_at) elapses."""
    if slot.audio_expires_at is None:
        return True
    return now < slot.audio_expires_at
