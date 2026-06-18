from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from aquen.states import ContentState


def utcnow() -> datetime:
    """Return the current UTC time as a tz-naive datetime.

    Convention: every datetime stored by AQUEN is UTC and tz-naive. SQLite has no
    timezone support and would silently drop an offset, so we standardize on naive
    UTC to keep writes and reads loss-free and to avoid mixing aware/naive datetimes
    in comparisons.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ContentItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    pillar: str
    hook_archetype: str | None = None
    # Note: SQLAlchemy persists this str-enum by member NAME (e.g. "SCRIPTED"); it
    # round-trips correctly through the ORM. Use ContentState(...) / .value at the
    # edges rather than matching the lowercase value in raw SQL.
    state: ContentState = Field(default=ContentState.IDEA)
    source_inspiration_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
