from pathlib import Path

from aquen.config import get_settings
from aquen.models import ComplianceCheck, ContentItem


def test_export_dir_default():
    assert get_settings().export_dir == Path("exports")


def test_export_dir_env_override(monkeypatch):
    monkeypatch.setenv("AQUEN_EXPORT_DIR", "out/packs")
    assert get_settings().export_dir == Path("out/packs")


def test_content_item_compliance_field_defaults(session):
    item = ContentItem(title="Beta-glucan 101", pillar="derma_decode")
    session.add(item)
    session.commit()
    session.refresh(item)
    assert item.caption is None
    assert item.is_sponsored is False
    assert item.ai_label_on_content is False
    assert item.substantiation_url is None


def test_compliance_check_roundtrip(session):
    row = ComplianceCheck(
        content_item_id=1, check="ai_disclosure", passed=False, detail="missing"
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    assert row.id is not None
    assert row.passed is False
    assert row.created_at is not None
