# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**AQUEN** is a single-developer, Windows-friendly Python toolkit for running an AI-native
skincare content brand. This repo currently holds the **foundation slice** (GĐ1/start of
GĐ2): the `aquen` CLI that creates, lists, and advances *content items* through their
lifecycle on SQLite. External integrations (Higgsfield generation, Meta Ad Library research,
compliance gate, publisher export) are **not implemented yet** — they arrive in later plans
behind swappable adapter interfaces and deliberately have no network calls today.

The full brand/product strategy lives in `docs/superpowers/specs/2026-06-18-aquen-content-brand-design.md`
and the implementation roadmap in `docs/superpowers/plans/2026-06-18-aquen-toolkit-foundation.md`.
Read those before adding modules — they define the data model, the module boundaries, and
hard compliance constraints (FTC dual disclosure, no AI testimonials/before-afters) that the
toolkit is meant to enforce.

## Commands

The project uses a local virtualenv at `.venv`. On Windows/PowerShell:

```powershell
# One-time setup
python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run the full test suite
.\.venv\Scripts\python.exe -m pytest -v

# Run one test file / one test
.\.venv\Scripts\python.exe -m pytest tests/test_service.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_service.py::test_advance_to_next -v

# Run the CLI
.\.venv\Scripts\aquen.exe init
.\.venv\Scripts\aquen.exe content add "Beta-glucan 101" derma_decode --hook myth_bust
.\.venv\Scripts\aquen.exe content list --state idea
.\.venv\Scripts\aquen.exe content advance 1            # advance to next state
.\.venv\Scripts\aquen.exe content advance 1 --to rendered
```

There is no separate lint step configured. `pytest` config lives in `pyproject.toml`
(`pythonpath = ["src"]`, `testpaths = ["tests"]`), so tests resolve the `src/`-layout package
without an editable install — but the `aquen` console script does need the install.

## Architecture

Layered `src/`-layout package (`src/aquen/`), built so pure domain logic is unit-testable
offline and the CLI is a thin shell:

- **`states.py`** — pure domain logic, no DB. `ContentState` enum + the linear lifecycle
  `idea → scripted → generating → rendered → screened → review → ready → published → measured`.
  `ALLOWED_TRANSITIONS` is derived from `_ORDER` and permits **only the immediate next step**;
  `next_state` / `can_transition` enforce it and raise `InvalidTransition`. Change the lifecycle
  by editing `_ORDER`, not the transition map.
- **`models.py`** — `ContentItem` SQLModel table (the only table so far). Adds non-DB imports
  nothing; depends on `states`.
- **`db.py`** — engine/session plumbing. `make_engine(url=None)` builds a SQLite URL from
  settings; `init_db` imports `aquen.models` for its table-registration side effect before
  `create_all`. Don't drop that import.
- **`service.py`** — the seam everything goes through: `add_content`, `list_content`,
  `advance_content`. Functions take an explicit `Session` (never open their own), so they're
  trivially testable. `advance_content` defaults to `next_state` but accepts an explicit
  `target`, validates via `can_transition`, and refreshes `updated_at`.
- **`config.py`** — `Settings` (pydantic-settings), env prefix `AQUEN_`, reads `.env`.
  `get_settings()` builds a **fresh** `Settings` each call on purpose so env overrides take
  effect in tests; keep it that way rather than caching a singleton.
- **`cli.py`** — Typer app. `_session_scope()` is the only place the CLI touches DB lifecycle:
  it builds an engine, `init_db`s, yields a session, and **disposes the engine in `finally`**.
  CLI commands stay thin — they parse args, call a `service` function, and echo; put logic in
  `service`/`states`, not here.

Dependency direction: `cli → service → {models, states}` and `db`/`config` underneath. New
modules (research, generate, compliance, publish) should follow the same shape — a pure-logic
or service module first, a thin Typer sub-app added via `app.add_typer(...)` second.

## Conventions specific to this codebase

- **Datetimes are tz-naive UTC.** Always use `aquen.models.utcnow()` (it strips tzinfo).
  SQLite has no tz support; mixing aware/naive datetimes breaks comparisons. `advance_content`
  sets `updated_at = utcnow()` — note `service` imports `utcnow` so tests `monkeypatch`
  `service.utcnow`.
- **`ContentState` persists by member NAME** (e.g. `"SCRIPTED"`), not its lowercase `.value`.
  It round-trips through the ORM correctly, but when querying raw SQL use the name. At every
  edge (CLI args, display) convert with `ContentState(...)` / `.value`.
- **Tests** use an in-memory SQLite engine via `StaticPool` (`tests/conftest.py` `engine`/
  `session` fixtures) for service/model tests, and Typer's `CliRunner` with a `tmp_path`
  `AQUEN_DB_PATH` env override for CLI tests. New service logic should be tested against the
  `session` fixture; new CLI commands against `CliRunner` + an env-isolated DB.
- Development follows **TDD** (red → green → commit) per the plan docs, and commits use
  Conventional-Commit prefixes (`feat:`, `fix:`).

## Compliance is a product requirement, not a nicety

When you reach the compliance/publisher work, the spec's hard guardrails are design
constraints the toolkit must *enforce* in code (a post cannot reach `ready` without dual FTC
disclosure + persistent AI label + claim substantiation; no AI-generated testimonials or
before/afters ever). Don't treat these as optional copy — re-read spec §4.5 before building
that gate.
