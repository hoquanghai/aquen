from datetime import datetime

from aquen.models import CalendarSlot


def test_calendar_slot_defaults(session):
    slot = CalendarSlot(
        content_item_id=1,
        scheduled_for=datetime(2026, 7, 1, 13, 0),
        lane="derma_decode",
        window="midday",
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    assert slot.id is not None
    assert slot.trending_audio is None
    assert slot.audio_expires_at is None
    assert slot.note is None
    assert slot.created_at is not None


def test_calendar_slot_with_audio_roundtrip(session):
    slot = CalendarSlot(
        content_item_id=2,
        scheduled_for=datetime(2026, 7, 1, 20, 0),
        lane="myth_bust",
        window="evening",
        trending_audio="trend-123",
        audio_expires_at=datetime(2026, 7, 3, 20, 0),
        note="pair with hook #4",
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    assert slot.trending_audio == "trend-123"
    assert slot.audio_expires_at == datetime(2026, 7, 3, 20, 0)
    assert slot.note == "pair with hook #4"
