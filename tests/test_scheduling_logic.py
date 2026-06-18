from datetime import datetime

from aquen.models import CalendarSlot
from aquen.scheduling import audio_is_fresh, in_posting_window, window_for


def test_window_for_midday():
    assert window_for(datetime(2026, 7, 1, 13, 0)) == "midday"


def test_window_for_evening():
    assert window_for(datetime(2026, 7, 1, 20, 30)) == "evening"


def test_window_for_outside_returns_none():
    assert window_for(datetime(2026, 7, 1, 9, 0)) is None


def test_in_posting_window():
    assert in_posting_window(datetime(2026, 7, 1, 12, 0)) is True
    assert in_posting_window(datetime(2026, 7, 1, 15, 0)) is False


def test_audio_is_fresh_when_no_expiry():
    slot = CalendarSlot(content_item_id=1, scheduled_for=datetime(2026, 7, 1, 13, 0), lane="x", window="midday")
    assert audio_is_fresh(slot, datetime(2026, 7, 1, 13, 0)) is True


def test_audio_freshness_respects_expiry():
    slot = CalendarSlot(
        content_item_id=1,
        scheduled_for=datetime(2026, 7, 1, 13, 0),
        lane="x",
        window="midday",
        audio_expires_at=datetime(2026, 7, 2, 13, 0),
    )
    assert audio_is_fresh(slot, datetime(2026, 7, 1, 18, 0)) is True
    assert audio_is_fresh(slot, datetime(2026, 7, 3, 0, 0)) is False
