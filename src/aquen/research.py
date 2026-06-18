from __future__ import annotations

from sqlmodel import Session, select

from aquen.adapters import MetaAdLibraryClient
from aquen.analysis import OriginalityError, check_originality, derive_hook
from aquen.models import AdInsight, Competitor, ContentItem, Hook
from aquen.states import ContentState


def add_competitor(
    session: Session, handle: str, platform: str = "meta", note: str | None = None
) -> Competitor:
    existing = session.exec(
        select(Competitor).where(Competitor.handle == handle)
    ).first()
    if existing is not None:
        raise ValueError(f"competitor '{handle}' is already on the watch-list")
    competitor = Competitor(handle=handle, platform=platform, note=note)
    session.add(competitor)
    session.commit()
    session.refresh(competitor)
    return competitor


def list_competitors(session: Session) -> list[Competitor]:
    return list(session.exec(select(Competitor).order_by(Competitor.id)))


def list_hooks(session: Session) -> list[Hook]:
    return list(session.exec(select(Hook).order_by(Hook.id)))


def _ad_exists(session: Session, competitor_handle: str, ad_archive_id: str) -> bool:
    stmt = select(AdInsight).where(
        AdInsight.competitor_handle == competitor_handle,
        AdInsight.ad_archive_id == ad_archive_id,
    )
    return session.exec(stmt).first() is not None


def run_research(
    session: Session, client: MetaAdLibraryClient, limit: int = 10
) -> dict[str, int]:
    """For every competitor in the watch-list, pull public ads via the client, store new
    AdInsights, and derive one ORIGINAL house Hook per new ad. Ads are deduped per
    (competitor, ad_archive_id) so the same ad seen under two competitors counts as two
    observations. Returns counts."""
    ads_added = 0
    hooks_added = 0
    for competitor in list_competitors(session):
        for record in client.search(competitor.handle, limit=limit):
            if _ad_exists(session, competitor.handle, record.ad_archive_id):
                continue
            session.add(
                AdInsight(
                    competitor_handle=competitor.handle,
                    ad_archive_id=record.ad_archive_id,
                    ad_text=record.ad_text,
                    page_name=record.page_name,
                    source_url=record.url,
                )
            )
            text, archetype, topic = derive_hook(record.ad_text)
            session.add(
                Hook(
                    text=text,
                    archetype=archetype,
                    topic=topic,
                    source_inspiration_url=record.url,
                    source_ad_archive_id=record.ad_archive_id,
                    source_ad_text=record.ad_text,
                )
            )
            ads_added += 1
            hooks_added += 1
    session.commit()
    return {"ads": ads_added, "hooks": hooks_added}


def ideate(
    session: Session, hook_id: int, pillar: str, script: str
) -> ContentItem:
    """Turn a hook into a SCRIPTED ContentItem, enforcing the anti-plagiarism gate against
    the source ad text and recording the originality sign-off."""
    hook = session.get(Hook, hook_id)
    if hook is None:
        raise ValueError(f"hook {hook_id} not found")

    note = "original"
    if hook.source_ad_text:
        ok, reason = check_originality(hook.source_ad_text, script)
        if not ok:
            raise OriginalityError(f"script rejected: {reason}")
        note = reason

    item = ContentItem(
        title=hook.text[:80],
        pillar=pillar,
        hook_archetype=hook.archetype,
        state=ContentState.SCRIPTED,
        source_inspiration_url=hook.source_inspiration_url,
        script=script,
        originality_note=note,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
