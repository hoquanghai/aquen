from aquen.config import get_settings
from aquen.models import Generation


def test_mira_identity_and_threshold_defaults():
    s = get_settings()
    assert s.mira_soul_id == "83c0591d-223f-461d-b4f2-0040fa029b8b"
    assert s.mira_element_id == "1972c3b9-1f3f-49fb-bcf0-104c7b171a23"
    assert s.virality_threshold == 0.6


def test_threshold_env_override(monkeypatch):
    monkeypatch.setenv("AQUEN_VIRALITY_THRESHOLD", "0.75")
    assert get_settings().virality_threshold == 0.75


def test_generation_roundtrip(session):
    g = Generation(
        kind="video",
        prompt="Mira explains beta-glucan",
        model="minimax_hailuo",
        external_job_id="job-1",
    )
    session.add(g)
    session.commit()
    session.refresh(g)
    assert g.id is not None
    assert g.status == "pending"
    assert g.result_url is None
    assert g.virality_score is None
    assert g.passed is None
    assert g.created_at is not None
