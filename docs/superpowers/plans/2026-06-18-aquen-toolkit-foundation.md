# AQUEN Toolkit Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python package skeleton, configuration, SQLite data layer, content state machine, and CLI entrypoint for the AQUEN content-ops toolkit — a working `aquen` CLI that can create, list, and advance content items through their lifecycle.

**Architecture:** A `src/`-layout Python package. Pure-Python domain logic (state machine, services) is unit-tested with TDD; persistence uses SQLModel over SQLite; the CLI is a thin Typer layer over the service functions. External integrations (Higgsfield, Meta) are out of scope here and arrive in later plans behind adapter interfaces, so this plan has no network calls and is fully testable offline.

**Tech Stack:** Python 3.11+, Typer (CLI), SQLModel + SQLAlchemy (DB), pydantic-settings (config), pytest (tests), hatchling (build).

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, deps, `aquen` script entrypoint, pytest config |
| `.env.example` | Documented env vars (no secrets committed) |
| `src/aquen/__init__.py` | Package marker + version |
| `src/aquen/config.py` | `Settings` (pydantic-settings) — DB path + API keys from env |
| `src/aquen/states.py` | `ContentState` enum + allowed transitions (pure logic) |
| `src/aquen/db.py` | Engine factory, `init_db`, session helper |
| `src/aquen/models.py` | `ContentItem` SQLModel table |
| `src/aquen/service.py` | `add_content` / `list_content` / `advance_content` |
| `src/aquen/cli.py` | Typer app: `aquen init`, `aquen content add/list/advance` |
| `tests/conftest.py` | In-memory engine + session fixtures (StaticPool) |
| `tests/test_states.py` | State-machine unit tests |
| `tests/test_service.py` | Service-layer unit tests |
| `tests/test_cli.py` | CLI smoke tests (Typer `CliRunner`) |

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/aquen/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

`tests/test_smoke.py`:

```python
def test_package_imports():
    import aquen

    assert aquen.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen'` (and pytest may error before collection).

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "aquen"
version = "0.1.0"
description = "AQUEN skincare content-ops toolkit"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "sqlmodel>=0.0.22",
    "pydantic-settings>=2.4",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
aquen = "aquen.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/aquen"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 4: Write `src/aquen/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Create a virtual environment and install dev deps**

Run (PowerShell):
```powershell
python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
Expected: ends with `Successfully installed aquen-0.1.0 ...`.

- [ ] **Step 6: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_smoke.py -v`
Expected: PASS (1 passed).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/aquen/__init__.py tests/test_smoke.py
git commit -m "feat: scaffold aquen package"
```

---

## Task 2: Configuration

**Files:**
- Create: `src/aquen/config.py`
- Create: `.env.example`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:

```python
from pathlib import Path

from aquen.config import get_settings


def test_defaults():
    settings = get_settings()
    assert settings.db_path == Path("aquen.sqlite")
    assert settings.higgsfield_api_key == ""


def test_env_override(monkeypatch):
    monkeypatch.setenv("AQUEN_DB_PATH", "custom.sqlite")
    monkeypatch.setenv("AQUEN_HIGGSFIELD_API_KEY", "secret")
    settings = get_settings()
    assert settings.db_path == Path("custom.sqlite")
    assert settings.higgsfield_api_key == "secret"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.config'`.

- [ ] **Step 3: Write `src/aquen/config.py`**

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


def get_settings() -> Settings:
    """Build settings fresh each call so env overrides apply in tests."""
    return Settings()
```

- [ ] **Step 4: Write `.env.example`**

```dotenv
# Copy to .env and fill in. Never commit .env.
AQUEN_DB_PATH=aquen.sqlite
AQUEN_HIGGSFIELD_API_KEY=
AQUEN_META_AD_LIBRARY_TOKEN=
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_config.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/aquen/config.py .env.example tests/test_config.py
git commit -m "feat: add settings config"
```

---

## Task 3: Content state machine

**Files:**
- Create: `src/aquen/states.py`
- Test: `tests/test_states.py`

- [ ] **Step 1: Write the failing test**

`tests/test_states.py`:

```python
import pytest

from aquen.states import (
    ContentState,
    InvalidTransition,
    can_transition,
    next_state,
)


def test_linear_progression():
    assert next_state(ContentState.IDEA) == ContentState.SCRIPTED
    assert next_state(ContentState.READY) == ContentState.PUBLISHED


def test_terminal_state_has_no_next():
    with pytest.raises(InvalidTransition):
        next_state(ContentState.MEASURED)


def test_can_transition_only_to_immediate_next():
    assert can_transition(ContentState.IDEA, ContentState.SCRIPTED) is True
    assert can_transition(ContentState.IDEA, ContentState.READY) is False
    assert can_transition(ContentState.RENDERED, ContentState.IDEA) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_states.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.states'`.

- [ ] **Step 3: Write `src/aquen/states.py`**

```python
from __future__ import annotations

from enum import Enum


class ContentState(str, Enum):
    IDEA = "idea"
    SCRIPTED = "scripted"
    GENERATING = "generating"
    RENDERED = "rendered"
    SCREENED = "screened"
    REVIEW = "review"
    READY = "ready"
    PUBLISHED = "published"
    MEASURED = "measured"


_ORDER = [
    ContentState.IDEA,
    ContentState.SCRIPTED,
    ContentState.GENERATING,
    ContentState.RENDERED,
    ContentState.SCREENED,
    ContentState.REVIEW,
    ContentState.READY,
    ContentState.PUBLISHED,
    ContentState.MEASURED,
]

ALLOWED_TRANSITIONS: dict[ContentState, list[ContentState]] = {
    state: ([_ORDER[i + 1]] if i + 1 < len(_ORDER) else [])
    for i, state in enumerate(_ORDER)
}


class InvalidTransition(Exception):
    pass


def next_state(current: ContentState) -> ContentState:
    nxt = ALLOWED_TRANSITIONS[current]
    if not nxt:
        raise InvalidTransition(f"{current.value} is a terminal state")
    return nxt[0]


def can_transition(current: ContentState, target: ContentState) -> bool:
    return target in ALLOWED_TRANSITIONS[current]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_states.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/states.py tests/test_states.py
git commit -m "feat: add content state machine"
```

---

## Task 4: Database engine + ContentItem model

**Files:**
- Create: `src/aquen/db.py`
- Create: `src/aquen/models.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the fixtures and a failing model test**

`tests/conftest.py`:

```python
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

import aquen.models  # noqa: F401  (register tables)
from aquen.db import init_db


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as sess:
        yield sess
```

Append to a new `tests/test_models.py`:

```python
from aquen.models import ContentItem
from aquen.states import ContentState


def test_content_item_defaults(session):
    item = ContentItem(title="Beta-glucan 101", pillar="derma_decode")
    session.add(item)
    session.commit()
    session.refresh(item)

    assert item.id is not None
    assert item.state == ContentState.IDEA
    assert item.created_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.db'` (or `aquen.models`).

- [ ] **Step 3: Write `src/aquen/models.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from aquen.states import ContentState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ContentItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    pillar: str
    hook_archetype: str | None = None
    state: ContentState = Field(default=ContentState.IDEA)
    source_inspiration_url: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

- [ ] **Step 4: Write `src/aquen/db.py`**

```python
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.engine import Engine

from aquen.config import get_settings


def make_engine(url: str | None = None) -> Engine:
    if url is None:
        url = f"sqlite:///{get_settings().db_path}"
    return create_engine(url, echo=False)


def init_db(engine: Engine) -> None:
    import aquen.models  # noqa: F401  (ensure tables registered)

    SQLModel.metadata.create_all(engine)


def get_session(engine: Engine) -> Session:
    return Session(engine)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add src/aquen/db.py src/aquen/models.py tests/conftest.py tests/test_models.py
git commit -m "feat: add db engine and ContentItem model"
```

---

## Task 5: Content service layer

**Files:**
- Create: `src/aquen/service.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Write the failing test**

`tests/test_service.py`:

```python
import pytest

from aquen import service
from aquen.states import ContentState, InvalidTransition


def test_add_and_list(session):
    service.add_content(session, title="A", pillar="derma_decode")
    service.add_content(session, title="B", pillar="texture_asmr")

    items = service.list_content(session)
    assert [i.title for i in items] == ["A", "B"]
    assert all(i.state == ContentState.IDEA for i in items)


def test_list_filters_by_state(session):
    item = service.add_content(session, title="A", pillar="derma_decode")
    service.advance_content(session, item.id)  # IDEA -> SCRIPTED

    scripted = service.list_content(session, state=ContentState.SCRIPTED)
    assert [i.title for i in scripted] == ["A"]
    assert service.list_content(session, state=ContentState.IDEA) == []


def test_advance_to_next(session):
    item = service.add_content(session, title="A", pillar="derma_decode")
    advanced = service.advance_content(session, item.id)
    assert advanced.state == ContentState.SCRIPTED


def test_advance_invalid_target_raises(session):
    item = service.add_content(session, title="A", pillar="derma_decode")
    with pytest.raises(InvalidTransition):
        service.advance_content(session, item.id, target=ContentState.READY)


def test_advance_missing_item_raises(session):
    with pytest.raises(ValueError):
        service.advance_content(session, 999)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.service'`.

- [ ] **Step 3: Write `src/aquen/service.py`**

```python
from __future__ import annotations

from sqlmodel import Session, select

from aquen.models import ContentItem
from aquen.states import (
    ContentState,
    InvalidTransition,
    can_transition,
    next_state,
)


def add_content(
    session: Session,
    title: str,
    pillar: str,
    hook_archetype: str | None = None,
    source_inspiration_url: str | None = None,
) -> ContentItem:
    item = ContentItem(
        title=title,
        pillar=pillar,
        hook_archetype=hook_archetype,
        source_inspiration_url=source_inspiration_url,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def list_content(
    session: Session, state: ContentState | None = None
) -> list[ContentItem]:
    stmt = select(ContentItem).order_by(ContentItem.id)
    if state is not None:
        stmt = stmt.where(ContentItem.state == state)
    return list(session.exec(stmt))


def advance_content(
    session: Session, item_id: int, target: ContentState | None = None
) -> ContentItem:
    item = session.get(ContentItem, item_id)
    if item is None:
        raise ValueError(f"content item {item_id} not found")

    tgt = target or next_state(item.state)
    if not can_transition(item.state, tgt):
        raise InvalidTransition(
            f"cannot move content {item_id} from {item.state.value} to {tgt.value}"
        )

    item.state = tgt
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_service.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/service.py tests/test_service.py
git commit -m "feat: add content service layer"
```

---

## Task 6: CLI entrypoint

**Files:**
- Create: `src/aquen/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_init(tmp_path):
    result = runner.invoke(app, ["init"], env=_env(tmp_path))
    assert result.exit_code == 0
    assert "Initialized" in result.stdout
    assert (tmp_path / "test.sqlite").exists()


def test_add_then_list(tmp_path):
    env = _env(tmp_path)
    add = runner.invoke(
        app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env
    )
    assert add.exit_code == 0, add.stdout

    listed = runner.invoke(app, ["content", "list"], env=env)
    assert listed.exit_code == 0
    assert "Beta-glucan 101" in listed.stdout
    assert "[idea]" in listed.stdout


def test_advance(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["content", "add", "A", "derma_decode"], env=env)
    adv = runner.invoke(app, ["content", "advance", "1"], env=env)
    assert adv.exit_code == 0
    assert "scripted" in adv.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.cli'`.

- [ ] **Step 3: Write `src/aquen/cli.py`**

```python
from __future__ import annotations

import typer

from aquen import service
from aquen.config import get_settings
from aquen.db import get_session, init_db, make_engine
from aquen.states import ContentState

app = typer.Typer(help="AQUEN content-ops toolkit", no_args_is_help=True)
content_app = typer.Typer(help="Manage content items", no_args_is_help=True)
app.add_typer(content_app, name="content")


def _ready_engine():
    engine = make_engine()
    init_db(engine)
    return engine


@app.command()
def init() -> None:
    """Initialize the AQUEN database."""
    make_engine()  # validates the configured URL
    engine = _ready_engine()
    typer.echo(f"Initialized DB at {get_settings().db_path}")
    engine.dispose()


@content_app.command("add")
def content_add(
    title: str,
    pillar: str,
    hook: str = typer.Option(None, help="Hook archetype tag"),
    source: str = typer.Option(None, help="Source-of-inspiration URL"),
) -> None:
    engine = _ready_engine()
    with get_session(engine) as sess:
        item = service.add_content(
            sess,
            title=title,
            pillar=pillar,
            hook_archetype=hook,
            source_inspiration_url=source,
        )
        typer.echo(f"#{item.id} [{item.state.value}] {item.title} ({item.pillar})")


@content_app.command("list")
def content_list(
    state: str = typer.Option(None, help="Filter by content state"),
) -> None:
    engine = _ready_engine()
    with get_session(engine) as sess:
        st = ContentState(state) if state else None
        for item in service.list_content(sess, state=st):
            typer.echo(
                f"#{item.id} [{item.state.value}] {item.title} ({item.pillar})"
            )


@content_app.command("advance")
def content_advance(
    item_id: int,
    to: str = typer.Option(None, help="Explicit target state (default: next)"),
) -> None:
    engine = _ready_engine()
    with get_session(engine) as sess:
        tgt = ContentState(to) if to else None
        item = service.advance_content(sess, item_id, target=tgt)
        typer.echo(f"#{item.id} -> {item.state.value}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: PASS (all tests green: smoke + config + states + models + service + cli).

- [ ] **Step 6: Manual smoke check**

Run:
```powershell
.\.venv\Scripts\aquen.exe init
.\.venv\Scripts\aquen.exe content add "Beta-glucan vs HA" derma_decode --hook myth_bust
.\.venv\Scripts\aquen.exe content list
```
Expected: init message, then a `#1 [idea] Beta-glucan vs HA (derma_decode)` line.

- [ ] **Step 7: Commit**

```bash
git add src/aquen/cli.py tests/test_cli.py
git commit -m "feat: add aquen CLI (init, content add/list/advance)"
```

---

## Subsequent plans (outline — written in full when reached)

These build on this foundation; each produces working, testable software on its own.

- **Plan 2 — Research + Ideation:** `Competitor`, `AdInsight`, `Hook`, `ContentIdea` models;
  `MetaAdLibraryClient` adapter (interface + fake for tests); `aquen research` (seeded
  watch-list → hook ideas) and `aquen ideate` (hook → scripted ContentItem). Anti-plagiarism
  originality check + source-of-inspiration logging.
- **Plan 3 — Higgsfield Creative Engine + Virality gate:** `HiggsfieldClient` adapter
  (image/video/audio/character-consistency + virality predictor), asset store, job polling;
  `aquen generate` and `aquen screen` (virality threshold gate). Mira character profile lock.
- **Plan 4 — Compliance gate + Publisher export:** `ComplianceCheck` rules (FTC dual
  disclosure, persistent AI label, prohibited-claim scan), `aquen review`, and
  `aquen publish --export` producing a manual-upload post pack (video + disclosed caption +
  hashtags + overlay notes).
- **Plan 5 — Sample production runbook (creative, not TDD):** generate the consistent Mira
  avatar + reveal set + 3 sample videos (Derma-Decode, hands-only ASMR, myth-bust) through
  the gates via Higgsfield, for quality approval.

Deferred to later cycles (per spec §9): Meta Ads / paid module, web dashboard, AI
skin-analysis quiz, own-SKU launch.

---

## Self-Review

**1. Spec coverage (this plan's slice):** Foundation maps to spec §5.1 (tech stack), §5.3
(data model — `ContentItem` + state machine; remaining tables arrive in Plans 2–4 as their
modules need them), and the CLI-first decision (spec §6). Research, Higgsfield, virality,
compliance, publisher modules are explicitly carried by Plans 2–5. No foundation requirement
left unassigned.

**2. Placeholder scan:** No TBD/TODO; every code step shows complete, runnable code; every
run step has an exact command + expected result.

**3. Type consistency:** `ContentState` values, `add_content` / `list_content` /
`advance_content` signatures, `make_engine` / `init_db` / `get_session`, and the CLI command
names are identical across Tasks 3–6 and the tests that call them.
