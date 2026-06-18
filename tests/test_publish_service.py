import pytest

from aquen import publish
from aquen.models import ContentItem, Generation
from aquen.states import ContentState


def _ready_item(session, **kw) -> ContentItem:
    item = ContentItem(
        title="Beta-glucan 101",
        pillar="derma_decode",
        state=ContentState.READY,
        caption="Created with AI. The honest science on beta-glucan. #ad",
        is_sponsored=True,
        ai_label_on_content=True,
        **kw,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_export_requires_ready_state(session, tmp_path):
    item = ContentItem(title="t", pillar="derma_decode", state=ContentState.REVIEW)
    session.add(item)
    session.commit()
    session.refresh(item)
    with pytest.raises(ValueError):
        publish.export_pack(session, item.id, out_dir=tmp_path)


def test_export_missing_item_raises(session, tmp_path):
    with pytest.raises(ValueError):
        publish.export_pack(session, 999, out_dir=tmp_path)


def test_export_writes_pack_files(session, tmp_path):
    item = _ready_item(session)
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    assert pack.is_dir()
    assert (pack / "caption.txt").exists()
    assert (pack / "post_pack.md").exists()


def test_caption_file_carries_caption_and_hashtags(session, tmp_path):
    item = _ready_item(session)
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    caption = (pack / "caption.txt").read_text(encoding="utf-8")
    assert "Created with AI" in caption
    assert "#AQUEN" in caption


def test_pack_includes_asset_urls(session, tmp_path):
    item = _ready_item(session)
    session.add(
        Generation(
            content_item_id=item.id,
            kind="video",
            prompt="p",
            model="minimax_hailuo",
            external_job_id="job-1",
            status="completed",
            result_url="https://fake.local/job-1.png",
        )
    )
    session.commit()
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    body = (pack / "post_pack.md").read_text(encoding="utf-8")
    assert "https://fake.local/job-1.png" in body


def test_pack_has_ai_label_overlay_note(session, tmp_path):
    item = _ready_item(session)
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    body = (pack / "post_pack.md").read_text(encoding="utf-8")
    assert "AI-generated" in body
