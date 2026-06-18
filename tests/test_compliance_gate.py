import pytest

from aquen import compliance, service
from aquen.compliance import ComplianceError
from aquen.models import ContentItem
from aquen.states import ContentState, InvalidTransition


def _compliant_item(session) -> ContentItem:
    item = ContentItem(
        title="Beta-glucan 101",
        pillar="derma_decode",
        state=ContentState.REVIEW,
        caption="Created with AI. The honest science on beta-glucan. #ad",
        is_sponsored=True,
        ai_label_on_content=True,
        script="A calm explainer in Mira's voice.",
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def _noncompliant_item(session) -> ContentItem:
    item = ContentItem(
        title="Quick promo",
        pillar="derma_decode",
        state=ContentState.REVIEW,
        caption="Check out this serum #ad",  # no AI disclosure
        is_sponsored=True,
        ai_label_on_content=False,  # no AI label
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_record_checks_persists_five_rows(session):
    item = _compliant_item(session)
    rows = compliance.record_checks(session, item.id)
    assert len(rows) == 5
    assert all(r.id is not None for r in rows)
    assert compliance.list_checks(session, item.id) == rows


def test_assert_compliant_passes_for_compliant_item(session):
    item = _compliant_item(session)
    rows = compliance.assert_compliant(session, item.id)
    assert all(r.passed for r in rows)


def test_assert_compliant_raises_and_still_logs(session):
    item = _noncompliant_item(session)
    with pytest.raises(ComplianceError):
        compliance.assert_compliant(session, item.id)
    # The audit trail is recorded even on failure.
    assert len(compliance.list_checks(session, item.id)) == 5


def test_record_checks_missing_item_raises(session):
    with pytest.raises(ValueError):
        compliance.record_checks(session, 999)


def test_advance_to_ready_blocked_when_noncompliant(session):
    item = _noncompliant_item(session)
    with pytest.raises(ComplianceError):
        service.advance_content(session, item.id, target=ContentState.READY)
    session.refresh(item)
    assert item.state == ContentState.REVIEW  # not advanced


def test_advance_to_ready_succeeds_when_compliant(session):
    item = _compliant_item(session)
    advanced = service.advance_content(session, item.id, target=ContentState.READY)
    assert advanced.state == ContentState.READY


def test_non_ready_transitions_skip_the_gate(session):
    # An empty IDEA item would fail compliance, but moving idea -> scripted must not run it.
    item = ContentItem(title="t", pillar="derma_decode", state=ContentState.IDEA)
    session.add(item)
    session.commit()
    session.refresh(item)
    advanced = service.advance_content(session, item.id)  # -> scripted
    assert advanced.state == ContentState.SCRIPTED
    assert compliance.list_checks(session, item.id) == []
