from aquen.models import AdInsight, Competitor, ContentItem, Hook
from aquen.states import ContentState


def test_competitor_roundtrip(session):
    c = Competitor(handle="rivalskin", platform="meta", note="watch")
    session.add(c)
    session.commit()
    session.refresh(c)
    assert c.id is not None
    assert c.platform == "meta"
    assert c.created_at is not None


def test_ad_insight_roundtrip(session):
    a = AdInsight(
        competitor_handle="rivalskin",
        ad_archive_id="AD123",
        ad_text="Stop believing this hydration myth.",
        page_name="RivalSkin",
        source_url="https://example.com/ad/123",
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    assert a.id is not None


def test_hook_roundtrip(session):
    h = Hook(
        text="The one hydration step almost everyone skips.",
        archetype="curiosity",
        topic="hydration",
        source_ad_archive_id="AD123",
        source_ad_text="Stop believing this hydration myth.",
    )
    session.add(h)
    session.commit()
    session.refresh(h)
    assert h.id is not None


def test_content_item_has_optional_script(session):
    item = ContentItem(title="x", pillar="derma_decode", script="Hello barrier.")
    session.add(item)
    session.commit()
    session.refresh(item)
    assert item.script == "Hello barrier."
    assert item.state == ContentState.IDEA
