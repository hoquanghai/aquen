import pytest

from aquen import service
from aquen.states import ContentState, InvalidTransition


def test_add_and_list(session):
    service.add_content(session, title="A", pillar="derma_decode")
    service.add_content(session, title="B", pillar="texture_asmr")

    items = service.list_content(session)
    assert [i.title for i in items] == ["A", "B"]
    assert all(i.state == ContentState.IDEA for i in items)


def test_list_filters_by_state(session):
    item = service.add_content(session, title="A", pillar="derma_decode")
    service.advance_content(session, item.id)  # IDEA -> SCRIPTED

    scripted = service.list_content(session, state=ContentState.SCRIPTED)
    assert [i.title for i in scripted] == ["A"]
    assert service.list_content(session, state=ContentState.IDEA) == []


def test_advance_to_next(session):
    item = service.add_content(session, title="A", pillar="derma_decode")
    advanced = service.advance_content(session, item.id)
    assert advanced.state == ContentState.SCRIPTED


def test_advance_invalid_target_raises(session):
    item = service.add_content(session, title="A", pillar="derma_decode")
    with pytest.raises(InvalidTransition):
        service.advance_content(session, item.id, target=ContentState.READY)


def test_advance_missing_item_raises(session):
    with pytest.raises(ValueError):
        service.advance_content(session, 999)
