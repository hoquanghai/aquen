from __future__ import annotations

from sqlmodel import Session, select

from aquen import compliance
from aquen.models import ContentItem, utcnow
from aquen.states import (
    ContentState,
    InvalidTransition,
    can_transition,
    next_state,
)


def add_content(
    session: Session,
    title: str,
    pillar: str,
    hook_archetype: str | None = None,
    source_inspiration_url: str | None = None,
) -> ContentItem:
    item = ContentItem(
        title=title,
        pillar=pillar,
        hook_archetype=hook_archetype,
        source_inspiration_url=source_inspiration_url,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def list_content(
    session: Session, state: ContentState | None = None
) -> list[ContentItem]:
    stmt = select(ContentItem).order_by(ContentItem.id)
    if state is not None:
        stmt = stmt.where(ContentItem.state == state)
    return list(session.exec(stmt))


def advance_content(
    session: Session, item_id: int, target: ContentState | None = None
) -> ContentItem:
    item = session.get(ContentItem, item_id)
    if item is None:
        raise ValueError(f"content item {item_id} not found")

    tgt = target or next_state(item.state)
    if not can_transition(item.state, tgt):
        raise InvalidTransition(
            f"cannot move content {item_id} from {item.state.value} to {tgt.value}"
        )

    # Compliance gate: a content item cannot reach `ready` until every check passes.
    if tgt == ContentState.READY:
        compliance.assert_compliant(session, item_id)

    item.state = tgt
    item.updated_at = utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def set_content_fields(
    session: Session,
    item_id: int,
    *,
    caption: str | None = None,
    is_sponsored: bool | None = None,
    ai_label_on_content: bool | None = None,
    substantiation_url: str | None = None,
) -> ContentItem:
    """Update the compliance-relevant fields on a content item. Only non-None args change."""
    item = session.get(ContentItem, item_id)
    if item is None:
        raise ValueError(f"content item {item_id} not found")
    if caption is not None:
        item.caption = caption
    if is_sponsored is not None:
        item.is_sponsored = is_sponsored
    if ai_label_on_content is not None:
        item.ai_label_on_content = ai_label_on_content
    if substantiation_url is not None:
        item.substantiation_url = substantiation_url
    item.updated_at = utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
