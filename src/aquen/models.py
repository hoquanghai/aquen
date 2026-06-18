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
    script: str | None = None
    originality_note: str | None = None
    # Compliance inputs (validated by the compliance gate before reaching `ready`).
    caption: str | None = None
    is_sponsored: bool = False
    ai_label_on_content: bool = False
    substantiation_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Competitor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    handle: str = Field(index=True, unique=True)
    platform: str = "meta"
    note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class AdInsight(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    competitor_handle: str = Field(index=True)
    ad_archive_id: str = Field(index=True)
    ad_text: str
    page_name: str | None = None
    source_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Hook(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    text: str
    archetype: str
    topic: str = "skincare"
    source_inspiration_url: str | None = None
    source_ad_archive_id: str | None = None
    source_ad_text: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Generation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content_item_id: int | None = Field(default=None, index=True)
    kind: str  # "image" | "video" | "audio"
    prompt: str
    model: str
    external_job_id: str = Field(index=True)
    status: str = "pending"  # pending | completed | failed
    result_url: str | None = None
    virality_score: float | None = None
    passed: bool | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ComplianceCheck(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content_item_id: int = Field(index=True)
    check: str  # ai_disclosure | ai_label | commercial_disclosure | no_prohibited_claims | substantiation
    passed: bool
    detail: str
    created_at: datetime = Field(default_factory=utcnow)
