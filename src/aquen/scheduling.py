from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, select

from aquen.models import CalendarSlot, ContentItem, utcnow

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


def schedule_content(
    session: Session,
    content_item_id: int,
    scheduled_for: datetime,
    *,
    lane: str | None = None,
    trending_audio: str | None = None,
    audio_ttl_hours: int | None = None,
    note: str | None = None,
) -> CalendarSlot:
    """Book a content item into a posting-window slot. The window is derived from the time;
    the lane defaults to the item's pillar. An item can hold only one slot (reschedule to move)."""
    item = session.get(ContentItem, content_item_id)
    if item is None:
        raise ValueError(f"content item {content_item_id} not found")
    window = window_for(scheduled_for)
    if window is None:
        raise SchedulingError(
            f"{scheduled_for:%H:%M} is outside the posting windows (midday 12–14, evening 19–21)"
        )
    existing = session.exec(
        select(CalendarSlot).where(CalendarSlot.content_item_id == content_item_id)
    ).first()
    if existing is not None:
        raise SchedulingError(
            f"content {content_item_id} is already scheduled (slot #{existing.id}); reschedule instead"
        )
    audio_expires_at = None
    if trending_audio and audio_ttl_hours:
        audio_expires_at = scheduled_for + timedelta(hours=audio_ttl_hours)
    slot = CalendarSlot(
        content_item_id=content_item_id,
        scheduled_for=scheduled_for,
        lane=lane or item.pillar,
        window=window,
        trending_audio=trending_audio,
        audio_expires_at=audio_expires_at,
        note=note,
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def reschedule_content(
    session: Session, slot_id: int, new_scheduled_for: datetime
) -> CalendarSlot:
    slot = session.get(CalendarSlot, slot_id)
    if slot is None:
        raise ValueError(f"calendar slot {slot_id} not found")
    window = window_for(new_scheduled_for)
    if window is None:
        raise SchedulingError(
            f"{new_scheduled_for:%H:%M} is outside the posting windows (midday 12–14, evening 19–21)"
        )
    slot.scheduled_for = new_scheduled_for
    slot.window = window
    slot.updated_at = utcnow()
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def unschedule(session: Session, slot_id: int) -> None:
    slot = session.get(CalendarSlot, slot_id)
    if slot is None:
        raise ValueError(f"calendar slot {slot_id} not found")
    session.delete(slot)
    session.commit()


def list_calendar(session: Session, lane: str | None = None) -> list[CalendarSlot]:
    stmt = select(CalendarSlot).order_by(CalendarSlot.scheduled_for)
    if lane is not None:
        stmt = stmt.where(CalendarSlot.lane == lane)
    return list(session.exec(stmt))


def upcoming(
    session: Session, now: datetime, within_hours: int | None = None
) -> list[CalendarSlot]:
    """Slots scheduled at/after `now`, ordered; optionally only those within `within_hours`."""
    slots = list(
        session.exec(
            select(CalendarSlot)
            .where(CalendarSlot.scheduled_for >= now)
            .order_by(CalendarSlot.scheduled_for)
        )
    )
    if within_hours is not None:
        cutoff = now + timedelta(hours=within_hours)
        slots = [s for s in slots if s.scheduled_for <= cutoff]
    return slots


def expiring_audio(session: Session, now: datetime) -> list[CalendarSlot]:
    """Slots whose trending-audio shelf-life timer has elapsed at `now`."""
    slots = session.exec(select(CalendarSlot).order_by(CalendarSlot.scheduled_for))
    return [
        s for s in slots if s.audio_expires_at is not None and s.audio_expires_at <= now
    ]
