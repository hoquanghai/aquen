import pytest

from aquen.states import (
    ContentState,
    InvalidTransition,
    can_transition,
    next_state,
)


def test_linear_progression():
    assert next_state(ContentState.IDEA) == ContentState.SCRIPTED
    assert next_state(ContentState.READY) == ContentState.PUBLISHED


def test_terminal_state_has_no_next():
    with pytest.raises(InvalidTransition):
        next_state(ContentState.MEASURED)


def test_can_transition_only_to_immediate_next():
    assert can_transition(ContentState.IDEA, ContentState.SCRIPTED) is True
    assert can_transition(ContentState.IDEA, ContentState.READY) is False
    assert can_transition(ContentState.RENDERED, ContentState.IDEA) is False
