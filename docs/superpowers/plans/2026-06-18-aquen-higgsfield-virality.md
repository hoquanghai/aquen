# AQUEN Higgsfield Engine + Virality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Higgsfield creative-generation layer to the AQUEN toolkit: a swappable `HiggsfieldClient` adapter (image/video/audio + virality score), a `Generation` table that tracks each job through submit → poll → screen, a virality pre-screen gate with a configurable threshold, the locked Mira identity refs (trained Soul + Element) in config, and CLI commands to generate, refresh, list, and screen generations.

**Architecture:** Builds on Plan 1+2. Mirrors the Meta-adapter pattern: a `HiggsfieldClient` Protocol with an offline `FakeHiggsfieldClient` keeps the whole pipeline testable with zero network/credits. A `Generation` SQLModel row records the external job id, status, result url, virality score, and pass/fail. A `generation.py` service orchestrates submit/refresh/screen and links generations to `ContentItem`s. Config carries Mira's `soul_id`/`element_id` and the virality threshold. The live HTTP Higgsfield client is deferred (the Fake ships now), consistent with how the live Meta client was deferred — actual pixel generation is still done via the Higgsfield MCP/agent until the HTTP adapter lands.

**Tech Stack:** Python 3.11+, Typer, SQLModel/SQLite, pytest. No new dependencies.

**Known Mira identity (locked 2026-06-18):** trained Soul `83c0591d-223f-461d-b4f2-0040fa029b8b` (model `soul_2`) and reusable Element `1972c3b9-1f3f-49fb-bcf0-104c7b171a23` (for clean Nano-Banana stills). These become config defaults so the toolkit always generates the right character.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/aquen/config.py` | (modify) add `mira_soul_id`, `mira_element_id`, `virality_threshold` |
| `src/aquen/models.py` | (modify) add `Generation` table |
| `src/aquen/higgsfield.py` | (create) `GenJob`, `HiggsfieldClient` Protocol, `FakeHiggsfieldClient`, status constants |
| `src/aquen/generation.py` | (create) submit/refresh/list/screen services |
| `src/aquen/cli.py` | (modify) add `gen` sub-app (image/video/refresh/list/screen) |
| `tests/test_generation_foundation.py` | (create) config + Generation model tests |
| `tests/test_higgsfield.py` | (create) adapter tests |
| `tests/test_generation_service.py` | (create) service + virality gate tests |
| `tests/test_cli_generation.py` | (create) CLI tests |

---

## Task 1: Config + Generation model

**Files:**
- Modify: `src/aquen/config.py`
- Modify: `src/aquen/models.py`
- Test: `tests/test_generation_foundation.py`

- [ ] **Step 1: Write the failing test** — `tests/test_generation_foundation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_generation_foundation.py -v` — Expected: FAIL (`mira_soul_id` not on Settings / `cannot import name 'Generation'`).

- [ ] **Step 3: Replace the ENTIRE contents of `src/aquen/config.py`**:

```python
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="AQUEN_", extra="ignore"
    )

    db_path: Path = Path("aquen.sqlite")
    higgsfield_api_key: str = ""
    meta_ad_library_token: str = ""
    # Locked Mira identity references (see docs/brand/mira-kol.md)
    mira_soul_id: str = "83c0591d-223f-461d-b4f2-0040fa029b8b"
    mira_element_id: str = "1972c3b9-1f3f-49fb-bcf0-104c7b171a23"
    virality_threshold: float = 0.6


def get_settings() -> Settings:
    """Build settings fresh each call so env overrides apply in tests."""
    return Settings()
```

- [ ] **Step 4: Append the `Generation` class to the END of `src/aquen/models.py`** (do not change existing classes):

```python


class Generation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content_item_id: int | None = Field(default=None, index=True)
    kind: str  # "image" | "video" | "audio"
    prompt: str
    model: str
    external_job_id: str = Field(index=True)
    status: str = "pending"  # pending | completed | failed
    result_url: str | None = None
    virality_score: float | None = None
    passed: bool | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 5: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_generation_foundation.py -v` — Expected: PASS (3 passed).

- [ ] **Step 6: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (46 passed: 43 prior + 3).

- [ ] **Step 7: Commit**

```bash
git add src/aquen/config.py src/aquen/models.py tests/test_generation_foundation.py
git commit -m "feat: add Mira identity config and Generation model"
```

---

## Task 2: Higgsfield adapter

**Files:**
- Create: `src/aquen/higgsfield.py`
- Test: `tests/test_higgsfield.py`

- [ ] **Step 1: Write the failing test** — `tests/test_higgsfield.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_higgsfield.py -v` — Expected: FAIL (`ModuleNotFoundError: No module named 'aquen.higgsfield'`).

- [ ] **Step 3: Write `src/aquen/higgsfield.py`**:

```python
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
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_higgsfield.py -v` — Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/higgsfield.py tests/test_higgsfield.py
git commit -m "feat: add Higgsfield adapter (interface + fake)"
```

---

## Task 3: Generation service (submit / refresh / list)

**Files:**
- Create: `src/aquen/generation.py`
- Test: `tests/test_generation_service.py`

- [ ] **Step 1: Write the failing test** — `tests/test_generation_service.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_generation_service.py -v` — Expected: FAIL (`ModuleNotFoundError: No module named 'aquen.generation'`).

- [ ] **Step 3: Write `src/aquen/generation.py`** (the `screen_generation` function is added in Task 4; this task ships submit/refresh/list):

```python
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
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_generation_service.py -v` — Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/generation.py tests/test_generation_service.py
git commit -m "feat: add generation service (submit/refresh/list)"
```

---

## Task 4: Virality pre-screen gate

**Files:**
- Modify: `src/aquen/generation.py`
- Test: `tests/test_virality_gate.py`

- [ ] **Step 1: Write the failing test** — `tests/test_virality_gate.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_virality_gate.py -v` — Expected: FAIL (`module 'aquen.generation' has no attribute 'screen_generation'`).

- [ ] **Step 3: Append to `src/aquen/generation.py`** — add the import for settings and the `screen_generation` function. Change the existing top import block by adding this line after the existing imports:

```python
from aquen.config import get_settings
```

Append this function to the end of the file:

```python
def screen_generation(
    session: Session,
    client: HiggsfieldClient,
    generation_id: int,
    threshold: float | None = None,
) -> Generation:
    """Run the virality pre-screen on a COMPLETED generation, store the score, and mark it
    passed/failed against the threshold (defaults to the configured virality_threshold)."""
    gen = session.get(Generation, generation_id)
    if gen is None:
        raise ValueError(f"generation {generation_id} not found")
    if gen.status != COMPLETED:
        raise ValueError(
            f"generation {generation_id} is {gen.status}; can only screen a completed generation"
        )
    cutoff = threshold if threshold is not None else get_settings().virality_threshold
    score = client.virality_score(gen.external_job_id)
    gen.virality_score = score
    gen.passed = score >= cutoff
    gen.updated_at = utcnow()
    session.add(gen)
    session.commit()
    session.refresh(gen)
    return gen
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_virality_gate.py -v` — Expected: PASS (5 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (all green: Plan 1+2+3 so far).

- [ ] **Step 6: Commit**

```bash
git add src/aquen/generation.py tests/test_virality_gate.py
git commit -m "feat: add virality pre-screen gate"
```

---

## Task 5: CLI `gen` commands

**Files:**
- Modify: `src/aquen/cli.py`
- Test: `tests/test_cli_generation.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cli_generation.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_gen_image_then_list(tmp_path):
    env = _env(tmp_path)
    out = runner.invoke(app, ["gen", "image", "a clean Mira portrait"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "image" in out.stdout
    listed = runner.invoke(app, ["gen", "list"], env=env)
    assert "#1" in listed.stdout


def test_gen_video_refresh_screen(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["gen", "video", "she explains beta-glucan"], env=env)
    refreshed = runner.invoke(app, ["gen", "refresh", "1"], env=env)
    assert refreshed.exit_code == 0
    assert "completed" in refreshed.stdout
    screened = runner.invoke(app, ["gen", "screen", "1"], env=env)
    assert screened.exit_code == 0
    assert "score" in screened.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_generation.py -v` — Expected: FAIL (no `gen` command).

- [ ] **Step 3: Modify `src/aquen/cli.py`** — three edits, do NOT touch existing commands:

(a) Add these imports alongside the existing imports near the top:

```python
from aquen import generation
from aquen.config import get_settings
from aquen.higgsfield import FakeHiggsfieldClient
```

(If `from aquen.config import get_settings` is already imported, do not duplicate it.)

(b) After the existing `app.add_typer(hooks_app, name="hooks")` line, add:

```python
gen_app = typer.Typer(help="Generate and screen Higgsfield creative", no_args_is_help=True)
app.add_typer(gen_app, name="gen")
```

(c) Append these commands to the END of the file. The CLI uses the offline `FakeHiggsfieldClient` until a live Higgsfield HTTP client is configured; `gen image` defaults to Mira's Element id from config:

```python
def _higgsfield_client() -> FakeHiggsfieldClient:
    # TODO(live): swap for a token-backed HttpHiggsfieldClient when AQUEN_HIGGSFIELD_API_KEY
    # generation is wired. Offline Fake keeps the pipeline runnable now.
    return FakeHiggsfieldClient()


@gen_app.command("image")
def gen_image(
    prompt: str,
    content: int = typer.Option(None, help="Link to a content item id"),
    element: str = typer.Option(None, help="Element id (defaults to Mira)"),
    aspect: str = typer.Option("9:16", help="Aspect ratio"),
) -> None:
    element_id = element or get_settings().mira_element_id
    client = _higgsfield_client()
    with _session_scope() as sess:
        g = generation.submit_image(
            sess, client, prompt, content_item_id=content, element_id=element_id, aspect_ratio=aspect
        )
        typer.echo(f"#{g.id} [{g.status}] {g.kind} job={g.external_job_id}")


@gen_app.command("video")
def gen_video(
    prompt: str,
    content: int = typer.Option(None, help="Link to a content item id"),
    start_url: str = typer.Option(None, help="Start image URL"),
    aspect: str = typer.Option("9:16", help="Aspect ratio"),
    duration: int = typer.Option(6, help="Seconds"),
) -> None:
    client = _higgsfield_client()
    with _session_scope() as sess:
        g = generation.submit_video(
            sess, client, prompt, content_item_id=content,
            start_image_url=start_url, aspect_ratio=aspect, duration=duration,
        )
        typer.echo(f"#{g.id} [{g.status}] {g.kind} job={g.external_job_id}")


@gen_app.command("refresh")
def gen_refresh(generation_id: int) -> None:
    client = _higgsfield_client()
    with _session_scope() as sess:
        g = generation.refresh_generation(sess, client, generation_id)
        typer.echo(f"#{g.id} [{g.status}] {g.result_url or ''}")


@gen_app.command("list")
def gen_list(
    content: int = typer.Option(None, help="Filter by content item id"),
) -> None:
    with _session_scope() as sess:
        for g in generation.list_generations(sess, content_item_id=content):
            score = "" if g.virality_score is None else f" score={g.virality_score}"
            typer.echo(f"#{g.id} [{g.status}] {g.kind}{score}")


@gen_app.command("screen")
def gen_screen(
    generation_id: int,
    threshold: float = typer.Option(None, help="Override virality threshold"),
) -> None:
    client = _higgsfield_client()
    with _session_scope() as sess:
        g = generation.screen_generation(sess, client, generation_id, threshold=threshold)
        verdict = "PASS" if g.passed else "FAIL"
        typer.echo(f"#{g.id} score={g.virality_score} -> {verdict}")
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_generation.py -v` — Expected: PASS (2 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (all green).

- [ ] **Step 6: Manual smoke check** (PowerShell) — delete any stale dev DB first:
```powershell
if (Test-Path aquen.sqlite) { Remove-Item aquen.sqlite }
.\.venv\Scripts\aquen.exe gen video "Mira explains beta-glucan"
.\.venv\Scripts\aquen.exe gen refresh 1
.\.venv\Scripts\aquen.exe gen screen 1
.\.venv\Scripts\aquen.exe gen list
```
Expected: a `#1 [pending] video job=fake-job-1` line, a `#1 [completed] https://fake.local/...` line, a `#1 score=0.8 -> PASS` line, then a list line. (`aquen.sqlite` is gitignored — do not commit.)

- [ ] **Step 7: Commit**

```bash
git add src/aquen/cli.py tests/test_cli_generation.py
git commit -m "feat: add gen CLI commands (image/video/refresh/list/screen)"
```

---

## Subsequent plans

- **Plan 4 — Compliance gate + Publisher export** (FTC dual disclosure + AI label + prohibited-claim
  scan; export a manual-upload post pack with disclosures baked into caption + overlay notes).
- **Live `HttpHiggsfieldClient`** (token-backed image/video/audio + real virality predictor) and the
  live `MetaAdLibraryClient` — both deferred until credentials/endpoints are wired and verified.

---

## Self-Review

**1. Spec coverage:** Implements spec §5.2 module 3 (Higgsfield Creative Engine — generation +
job tracking, with the locked Mira Soul/Element refs) and module 4 (Virality Pre-Screen Gate —
threshold gate logged on the generation). The live HTTP client is explicitly deferred (Fake ships
now), consistent with the §9 deferral of live external clients.

**2. Placeholder scan:** No TBD in shipped behaviour; the single `TODO(live)` comment marks the
deliberate, documented seam for the future HTTP client (the Fake is a working stand-in, like the
Sample Meta client). Every code step is complete and runnable; every run step has an exact command
and expected result.

**3. Type consistency:** `GenJob` fields and `HiggsfieldClient` method signatures match across
Tasks 2–5; `generation.submit_image/submit_video/refresh_generation/list_generations/screen_generation`
signatures match their tests and the CLI calls; `Generation` columns (`status`, `result_url`,
`virality_score`, `passed`) match the model in Task 1; `PENDING`/`COMPLETED` constants are used
consistently.
