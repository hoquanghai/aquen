from datetime import datetime

import pytest

from aquen import scheduling
from aquen.models import ContentItem
from aquen.scheduling import SchedulingError


def _item(session, pillar="derma_decode") -> ContentItem:
    item = ContentItem(title="Beta-glucan 101", pillar=pillar)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_schedule_derives_window_and_defaults_lane_to_pillar(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    assert slot.id is not None
    assert slot.window == "midday"
    assert slot.lane == "derma_decode"


def test_schedule_lane_override(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 20, 0), lane="myth_bust")
    assert slot.lane == "myth_bust"
    assert slot.window == "evening"


def test_schedule_outside_window_raises(session):
    item = _item(session)
    with pytest.raises(SchedulingError):
        scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 9, 0))


def test_schedule_missing_item_raises(session):
    with pytest.raises(ValueError):
        scheduling.schedule_content(session, 999, datetime(2026, 7, 1, 13, 0))


def test_schedule_double_booking_raises(session):
    item = _item(session)
    scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    with pytest.raises(SchedulingError):
        scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 20, 0))


def test_schedule_sets_audio_expiry_from_ttl(session):
    item = _item(session)
    slot = scheduling.schedule_content(
        session, item.id, datetime(2026, 7, 1, 13, 0), trending_audio="trend-1", audio_ttl_hours=48
    )
    assert slot.trending_audio == "trend-1"
    assert slot.audio_expires_at == datetime(2026, 7, 3, 13, 0)


def test_reschedule_moves_and_revalidates_window(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    moved = scheduling.reschedule_content(session, slot.id, datetime(2026, 7, 2, 20, 0))
    assert moved.window == "evening"
    assert moved.scheduled_for == datetime(2026, 7, 2, 20, 0)


def test_reschedule_outside_window_raises(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    with pytest.raises(SchedulingError):
        scheduling.reschedule_content(session, slot.id, datetime(2026, 7, 2, 9, 0))


def test_reschedule_missing_raises(session):
    with pytest.raises(ValueError):
        scheduling.reschedule_content(session, 999, datetime(2026, 7, 2, 13, 0))


def test_unschedule_removes_slot(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    scheduling.unschedule(session, slot.id)
    assert scheduling.list_calendar(session) == []


def test_unschedule_missing_raises(session):
    with pytest.raises(ValueError):
        scheduling.unschedule(session, 999)


def test_list_calendar_orders_and_filters_by_lane(session):
    a = _item(session, pillar="derma_decode")
    b = _item(session, pillar="myth_bust")
    scheduling.schedule_content(session, b.id, datetime(2026, 7, 2, 20, 0), lane="myth_bust")
    scheduling.schedule_content(session, a.id, datetime(2026, 7, 1, 13, 0), lane="derma_decode")
    ordered = scheduling.list_calendar(session)
    assert [s.scheduled_for for s in ordered] == [datetime(2026, 7, 1, 13, 0), datetime(2026, 7, 2, 20, 0)]
    only = scheduling.list_calendar(session, lane="myth_bust")
    assert [s.lane for s in only] == ["myth_bust"]


def test_upcoming_returns_future_only_within_window(session):
    a = _item(session)
    b = _item(session)
    scheduling.schedule_content(session, a.id, datetime(2026, 7, 1, 13, 0))
    scheduling.schedule_content(session, b.id, datetime(2026, 7, 5, 20, 0))
    now = datetime(2026, 7, 2, 0, 0)
    assert [s.scheduled_for for s in scheduling.upcoming(session, now)] == [datetime(2026, 7, 5, 20, 0)]
    assert scheduling.upcoming(session, now, within_hours=24) == []


def test_expiring_audio_lists_expired_only(session):
    a = _item(session)
    b = _item(session)
    scheduling.schedule_content(session, a.id, datetime(2026, 7, 1, 13, 0), trending_audio="fresh", audio_ttl_hours=48)
    scheduling.schedule_content(session, b.id, datetime(2026, 7, 1, 20, 0), trending_audio="stale", audio_ttl_hours=1)
    now = datetime(2026, 7, 1, 23, 0)
    expired = scheduling.expiring_audio(session, now)
    assert [s.trending_audio for s in expired] == ["stale"]
