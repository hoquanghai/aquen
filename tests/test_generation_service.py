import pytest

from aquen import generation
from aquen.higgsfield import COMPLETED, PENDING, FakeHiggsfieldClient


def test_submit_image_stores_pending_generation(session):
    client = FakeHiggsfieldClient()
    gen = generation.submit_image(session, client, "a clean Mira portrait", element_id="EL1")
    assert gen.id is not None
    assert gen.kind == "image"
    assert gen.status == PENDING
    assert gen.external_job_id


def test_submit_video_links_to_content(session):
    client = FakeHiggsfieldClient()
    gen = generation.submit_video(
        session, client, "she talks", content_item_id=7, start_image_url="https://x/y.png"
    )
    assert gen.kind == "video"
    assert gen.content_item_id == 7


def test_refresh_moves_pending_to_completed(session):
    client = FakeHiggsfieldClient()
    gen = generation.submit_image(session, client, "p")
    refreshed = generation.refresh_generation(session, client, gen.id)
    assert refreshed.status == COMPLETED
    assert refreshed.result_url is not None


def test_refresh_missing_raises(session):
    client = FakeHiggsfieldClient()
    with pytest.raises(ValueError):
        generation.refresh_generation(session, client, 999)


def test_list_generations_filters_by_content(session):
    client = FakeHiggsfieldClient()
    generation.submit_image(session, client, "p", content_item_id=1)
    generation.submit_image(session, client, "q", content_item_id=2)
    only_1 = generation.list_generations(session, content_item_id=1)
    assert [g.prompt for g in only_1] == ["p"]
    assert len(generation.list_generations(session)) == 2
