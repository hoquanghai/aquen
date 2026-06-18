from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from aquen.states import ContentState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ContentItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    pillar: str
    hook_archetype: str | None = None
    state: ContentState = Field(default=ContentState.IDEA)
    source_inspiration_url: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
