from __future__ import annotations

from sqlmodel import Session, select

from aquen.higgsfield import COMPLETED, HiggsfieldClient
from aquen.models import Generation, utcnow


def submit_image(
    session: Session,
    client: HiggsfieldClient,
    prompt: str,
    *,
    content_item_id: int | None = None,
    model: str = "soul_2",
    soul_id: str | None = None,
    element_id: str | None = None,
    aspect_ratio: str = "9:16",
) -> Generation:
    job = client.generate_image(
        prompt, soul_id=soul_id, element_id=element_id, aspect_ratio=aspect_ratio
    )
    gen = Generation(
        content_item_id=content_item_id,
        kind="image",
        prompt=prompt,
        model=model,
        external_job_id=job.job_id,
        status=job.status,
        result_url=job.result_url,
    )
    session.add(gen)
    session.commit()
    session.refresh(gen)
    return gen


def submit_video(
    session: Session,
    client: HiggsfieldClient,
    prompt: str,
    *,
    content_item_id: int | None = None,
    model: str = "minimax_hailuo",
    start_image_url: str | None = None,
    aspect_ratio: str = "9:16",
    duration: int = 6,
) -> Generation:
    job = client.generate_video(
        prompt,
        start_image_url=start_image_url,
        aspect_ratio=aspect_ratio,
        duration=duration,
    )
    gen = Generation(
        content_item_id=content_item_id,
        kind="video",
        prompt=prompt,
        model=model,
        external_job_id=job.job_id,
        status=job.status,
        result_url=job.result_url,
    )
    session.add(gen)
    session.commit()
    session.refresh(gen)
    return gen


def refresh_generation(
    session: Session, client: HiggsfieldClient, generation_id: int
) -> Generation:
    gen = session.get(Generation, generation_id)
    if gen is None:
        raise ValueError(f"generation {generation_id} not found")
    job = client.job_status(gen.external_job_id)
    gen.status = job.status
    if job.result_url:
        gen.result_url = job.result_url
    gen.updated_at = utcnow()
    session.add(gen)
    session.commit()
    session.refresh(gen)
    return gen


def list_generations(
    session: Session, content_item_id: int | None = None
) -> list[Generation]:
    stmt = select(Generation).order_by(Generation.id)
    if content_item_id is not None:
        stmt = stmt.where(Generation.content_item_id == content_item_id)
    return list(session.exec(stmt))
