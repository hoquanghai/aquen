from aquen.higgsfield import (
    COMPLETED,
    PENDING,
    FakeHiggsfieldClient,
    GenJob,
)


def test_generate_image_returns_pending_job():
    client = FakeHiggsfieldClient()
    job = client.generate_image("a clean portrait", element_id="EL1")
    assert isinstance(job, GenJob)
    assert job.status == PENDING
    assert job.result_url is None


def test_generate_video_returns_pending_job():
    client = FakeHiggsfieldClient()
    job = client.generate_video("she talks", start_image_url="https://x/y.png")
    assert job.status == PENDING


def test_job_ids_are_unique():
    client = FakeHiggsfieldClient()
    a = client.generate_image("p1")
    b = client.generate_image("p2")
    assert a.job_id != b.job_id


def test_job_status_completes_with_url():
    client = FakeHiggsfieldClient()
    job = client.generate_image("p")
    done = client.job_status(job.job_id)
    assert done.status == COMPLETED
    assert done.result_url is not None


def test_virality_score_is_configurable():
    client = FakeHiggsfieldClient(score=0.42)
    assert client.virality_score("any-job") == 0.42
