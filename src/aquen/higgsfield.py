from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

PENDING = "pending"
COMPLETED = "completed"
FAILED = "failed"


@dataclass(frozen=True)
class GenJob:
    job_id: str
    status: str
    result_url: str | None = None


class HiggsfieldClient(Protocol):
    """Creative generation backend (image/video/audio + virality scoring). Implementations
    wrap the Higgsfield API; the Fake below keeps the toolkit testable offline."""

    def generate_image(
        self,
        prompt: str,
        *,
        soul_id: str | None = None,
        element_id: str | None = None,
        aspect_ratio: str = "9:16",
    ) -> GenJob: ...

    def generate_video(
        self,
        prompt: str,
        *,
        start_image_url: str | None = None,
        aspect_ratio: str = "9:16",
        duration: int = 6,
    ) -> GenJob: ...

    def job_status(self, job_id: str) -> GenJob: ...

    def virality_score(self, job_id: str) -> float: ...


class FakeHiggsfieldClient:
    """Deterministic offline client. Jobs come back PENDING from generate_*, then
    COMPLETED with a placeholder URL from job_status. Virality score is configurable."""

    def __init__(self, *, score: float = 0.8) -> None:
        self._counter = 0
        self._score = score

    def _next_id(self) -> str:
        self._counter += 1
        return f"fake-job-{self._counter}"

    def generate_image(
        self,
        prompt: str,
        *,
        soul_id: str | None = None,
        element_id: str | None = None,
        aspect_ratio: str = "9:16",
    ) -> GenJob:
        return GenJob(self._next_id(), PENDING, None)

    def generate_video(
        self,
        prompt: str,
        *,
        start_image_url: str | None = None,
        aspect_ratio: str = "9:16",
        duration: int = 6,
    ) -> GenJob:
        return GenJob(self._next_id(), PENDING, None)

    def job_status(self, job_id: str) -> GenJob:
        return GenJob(job_id, COMPLETED, f"https://fake.local/{job_id}.png")

    def virality_score(self, job_id: str) -> float:
        return self._score
