import pytest

from aquen import generation
from aquen.higgsfield import FakeHiggsfieldClient


def test_screen_passes_above_threshold(session):
    client = FakeHiggsfieldClient(score=0.8)
    gen = generation.submit_video(session, client, "clip")
    generation.refresh_generation(session, client, gen.id)  # -> completed
    screened = generation.screen_generation(session, client, gen.id, threshold=0.6)
    assert screened.virality_score == 0.8
    assert screened.passed is True


def test_screen_fails_below_threshold(session):
    client = FakeHiggsfieldClient(score=0.3)
    gen = generation.submit_video(session, client, "clip")
    generation.refresh_generation(session, client, gen.id)
    screened = generation.screen_generation(session, client, gen.id, threshold=0.6)
    assert screened.passed is False


def test_screen_uses_config_threshold_by_default(session, monkeypatch):
    monkeypatch.setenv("AQUEN_VIRALITY_THRESHOLD", "0.9")
    client = FakeHiggsfieldClient(score=0.8)
    gen = generation.submit_video(session, client, "clip")
    generation.refresh_generation(session, client, gen.id)
    screened = generation.screen_generation(session, client, gen.id)
    assert screened.passed is False  # 0.8 < 0.9


def test_screen_requires_completed(session):
    client = FakeHiggsfieldClient()
    gen = generation.submit_video(session, client, "clip")  # still pending
    with pytest.raises(ValueError):
        generation.screen_generation(session, client, gen.id)


def test_screen_missing_raises(session):
    client = FakeHiggsfieldClient()
    with pytest.raises(ValueError):
        generation.screen_generation(session, client, 999)
