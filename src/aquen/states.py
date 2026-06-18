from __future__ import annotations

from enum import Enum


class ContentState(str, Enum):
    IDEA = "idea"
    SCRIPTED = "scripted"
    GENERATING = "generating"
    RENDERED = "rendered"
    SCREENED = "screened"
    REVIEW = "review"
    READY = "ready"
    PUBLISHED = "published"
    MEASURED = "measured"


_ORDER = [
    ContentState.IDEA,
    ContentState.SCRIPTED,
    ContentState.GENERATING,
    ContentState.RENDERED,
    ContentState.SCREENED,
    ContentState.REVIEW,
    ContentState.READY,
    ContentState.PUBLISHED,
    ContentState.MEASURED,
]

ALLOWED_TRANSITIONS: dict[ContentState, list[ContentState]] = {
    state: ([_ORDER[i + 1]] if i + 1 < len(_ORDER) else [])
    for i, state in enumerate(_ORDER)
}


class InvalidTransition(Exception):
    pass


def next_state(current: ContentState) -> ContentState:
    nxt = ALLOWED_TRANSITIONS[current]
    if not nxt:
        raise InvalidTransition(f"{current.value} is a terminal state")
    return nxt[0]


def can_transition(current: ContentState, target: ContentState) -> bool:
    return target in ALLOWED_TRANSITIONS[current]
