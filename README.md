# AQUEN

**A single-developer, Windows-friendly Python toolkit for running an AI-native skincare content brand.**

AQUEN is a content-ops CLI that takes a skincare content idea through its full lifecycle —
competitor research → original hook → script → AI generation → virality screen →
**compliance gate** → manual-upload post pack — on a local SQLite database, with every external
integration behind a swappable adapter so the whole pipeline runs offline and testable.

> The creative core is [Higgsfield](https://higgsfield.ai) (image/video/audio + a virality
> predictor) wrapped in a lightweight content-ops layer. There is **no SaaS lock-in and no
> auto-posting** — a human-in-the-loop publisher exports a ready-to-post pack for manual upload.

---

## Status

The toolkit MVP is complete and green (**128 tests passing**). Built in five plans:

| Plan | Module | Ships |
|---|---|---|
| 1 — Foundation | content lifecycle | `content add/list/advance`, state machine, SQLite |
| 2 — Research + Ideation | hook swipe-file | `competitor`, `research`, `hooks`, `ideate` + anti-plagiarism gate |
| 3 — Higgsfield + Virality | creative engine | `gen image/video/refresh/list/screen` + virality pre-screen |
| 4 — Compliance + Publisher | the gate + export | `content set`, `compliance check/log`, `publish pack` |
| 5 — Content Calendar | scheduling | `calendar schedule/list/reschedule/unschedule/upcoming/audio-check` |

**Deferred** (Fakes/Samples ship now): the live `HttpHiggsfieldClient` and live
`MetaAdLibraryClient` (token-backed); the FastAPI/HTMX dashboard; and the Meta Ads module. See
each plan's "Subsequent plans" section in [`docs/superpowers/plans/`](docs/superpowers/plans/).

---

## Install

The project uses a local virtualenv at `.venv`. On Windows / PowerShell:

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Initialize the database (defaults to .\aquen.sqlite)
.\.venv\Scripts\aquen.exe init
```

Requires **Python 3.11+**. Dependencies: Typer, SQLModel, pydantic-settings, httpx (pytest for dev).

---

## Quickstart — idea to post pack

```powershell
# 1. Seed a competitor watch-list, then pull public ads and derive ORIGINAL house hooks
.\.venv\Scripts\aquen.exe competitor add somebrand --platform meta
.\.venv\Scripts\aquen.exe research --limit 10
.\.venv\Scripts\aquen.exe hooks list

# 2. Turn a hook into a scripted content item (blocked if the script copies the source ad)
.\.venv\Scripts\aquen.exe ideate 1 --pillar derma_decode --script "Your original script in Mira's voice"

# 3. Generate creative with Higgsfield, then virality pre-screen it
.\.venv\Scripts\aquen.exe gen video "Mira explains beta-glucan" --content 1
.\.venv\Scripts\aquen.exe gen refresh 1
.\.venv\Scripts\aquen.exe gen screen 1

# 4. Walk the item to the review stage
1..4 | ForEach-Object { .\.venv\Scripts\aquen.exe content advance 1 }   # scripted -> review

# 5. Attach the compliance inputs, check, then clear the gate to `ready`
.\.venv\Scripts\aquen.exe content set 1 `
    --caption "Created with AI. The honest science on beta-glucan. #ad" `
    --sponsored --ai-label
.\.venv\Scripts\aquen.exe compliance check 1          # five PASS lines + ALL CHECKS PASS
.\.venv\Scripts\aquen.exe content advance 1 --to ready

# 6. Export the manual-upload post pack
.\.venv\Scripts\aquen.exe publish pack 1 --out exports
# -> exports\aquen-post-1\{caption.txt, post_pack.md}

# 7. Book it into a posting-window slot (window derived from the time; 12–14h / 19–21h)
.\.venv\Scripts\aquen.exe calendar schedule 1 2026-07-01T13:00 --audio trend-1 --audio-ttl 48
.\.venv\Scripts\aquen.exe calendar list
```

---

## Content lifecycle

```
idea → scripted → generating → rendered → screened → review → ready → published → measured
                                                              ▲
                                              compliance gate blocks here
```

Transitions advance **one step at a time** (`content advance <id>`), or jump explicitly with
`--to <state>`. The **compliance gate** is enforced on the `review → ready` step: the item
cannot reach `ready` until every compliance check passes (see below).

---

## CLI reference

| Command | Purpose |
|---|---|
| `aquen init` | Create the SQLite database |
| `aquen research [--limit N]` | Pull competitor ads (Sample data until a Meta token is wired) and derive original house hooks |
| `aquen ideate <hook_id> --pillar P --script S` | Turn a hook into a `scripted` content item (anti-plagiarism gated) |
| `aquen content add <title> <pillar> [--hook H] [--source URL]` | Create a content item |
| `aquen content list [--state S]` | List items, optionally filtered by state |
| `aquen content advance <id> [--to STATE]` | Advance lifecycle (default: next step) |
| `aquen content set <id> [--caption ...] [--sponsored] [--ai-label] [--substantiation URL]` | Set the compliance inputs |
| `aquen competitor add <handle> [--platform P] [--note N]` | Add to the watch-list |
| `aquen competitor list` | List competitors |
| `aquen hooks list` | Browse derived hooks |
| `aquen gen image <prompt> [--content ID] [--element EL] [--aspect AR]` | Submit an image generation |
| `aquen gen video <prompt> [--content ID] [--start-url URL] [--aspect AR] [--duration N]` | Submit a video generation |
| `aquen gen refresh <generation_id>` | Poll a job → completed + result URL |
| `aquen gen list [--content ID]` | List generations |
| `aquen gen screen <generation_id> [--threshold T]` | Run the virality pre-screen (PASS/FAIL vs threshold) |
| `aquen compliance check <id>` | Run + record the compliance checks (does not advance) |
| `aquen compliance log <id>` | Show the recorded compliance-check audit trail |
| `aquen publish pack <id> [--out DIR]` | Export a manual-upload post pack for a `ready` item |
| `aquen calendar schedule <content_id> <when> [--lane L] [--audio NAME] [--audio-ttl HOURS] [--note N]` | Book an item into a posting-window slot (window derived from `when`) |
| `aquen calendar list [--lane L]` | List scheduled slots, ordered by time |
| `aquen calendar reschedule <slot_id> <when>` | Move a slot to a new time |
| `aquen calendar unschedule <slot_id>` | Remove a slot |
| `aquen calendar upcoming [--hours H]` | Slots scheduled from now (optionally within N hours) |
| `aquen calendar audio-check` | Slots whose trending-audio shelf-life has expired |

---

## Compliance gate — a product requirement, not a nicety

A post **cannot reach `ready`** until all of these pass (spec §4.5). The checks live in
[`compliance.py`](src/aquen/compliance.py) and are recorded to the `ComplianceCheck` audit table:

- **AI disclosure** — the caption must carry a separate "AI-generated / created with AI" disclosure.
  Mira is a synthetic performer, so this is required on **every** post.
- **Persistent AI label** — confirm the on-content overlay label (`--ai-label`).
- **Commercial disclosure** — sponsored posts need a commercial-relationship disclosure
  (`#ad` *alone* is insufficient — it does not satisfy the AI-disclosure check).
- **No prohibited claims** — AI testimonials, before/after, fabricated efficacy
  ("cleared my skin"), and "anti-aging" are **flatly prohibited regardless of disclosure**.
- **Claim substantiation** — skincare claim language requires a `--substantiation` source URL.

The publisher bakes the disclosures into the exported caption and emits an on-content AI-label
overlay instruction in the post pack.

---

## Architecture

Layered `src/`-layout package (`src/aquen/`) — pure domain logic is unit-testable offline and the
CLI is a thin shell. Dependency direction: `cli → {service, research, generation, compliance,
publish} → {models, states, analysis, adapters, higgsfield}` with `db`/`config` underneath.

| Module | Responsibility |
|---|---|
| [`states.py`](src/aquen/states.py) | `ContentState` enum + linear lifecycle; only the immediate next transition is allowed |
| [`models.py`](src/aquen/models.py) | SQLModel tables: `ContentItem`, `Competitor`, `AdInsight`, `Hook`, `Generation`, `ComplianceCheck` |
| [`db.py`](src/aquen/db.py) | engine/session plumbing; `init_db` registers tables before `create_all` |
| [`config.py`](src/aquen/config.py) | `Settings` (pydantic-settings, env prefix `AQUEN_`, reads `.env`) |
| [`service.py`](src/aquen/service.py) | content CRUD + `advance_content` (enforces the compliance gate on `→ ready`) |
| [`adapters.py`](src/aquen/adapters.py) | `MetaAdLibraryClient` Protocol + Sample/Fake (live HTTP client deferred) |
| [`analysis.py`](src/aquen/analysis.py) | hook derivation + anti-plagiarism originality check (pure) |
| [`research.py`](src/aquen/research.py) | research + ideation services |
| [`higgsfield.py`](src/aquen/higgsfield.py) | `HiggsfieldClient` Protocol + `FakeHiggsfieldClient` (live HTTP client deferred) |
| [`generation.py`](src/aquen/generation.py) | submit/refresh/list/screen generations + virality gate |
| [`compliance.py`](src/aquen/compliance.py) | pure compliance checks + gate service + `ComplianceError` |
| [`publish.py`](src/aquen/publish.py) | `export_pack` — write the manual-upload post-pack folder |
| [`scheduling.py`](src/aquen/scheduling.py) | posting-window rules + calendar service (`schedule`/`reschedule`/`upcoming`/`expiring_audio`) |
| [`cli.py`](src/aquen/cli.py) | Typer app; the only place that opens/disposes a DB engine |

New modules follow the same shape: a pure-logic or service module first, then a thin Typer
sub-app added via `app.add_typer(...)`.

### Conventions

- **Datetimes are tz-naive UTC** — always via `aquen.models.utcnow()` (SQLite has no tz support).
- **`ContentState` persists by member NAME** (e.g. `"SCRIPTED"`) — convert with
  `ContentState(...)` / `.value` at the edges (CLI args, display).
- **TDD** (red → green → commit); Conventional-Commit prefixes (`feat:`, `fix:`, `docs:`).

---

## Configuration

Settings are read from the environment (prefix `AQUEN_`) or a local `.env` file (never commit secrets):

| Variable | Default | Meaning |
|---|---|---|
| `AQUEN_DB_PATH` | `aquen.sqlite` | SQLite database path |
| `AQUEN_HIGGSFIELD_API_KEY` | _(empty)_ | Higgsfield credentials (for the deferred live client) |
| `AQUEN_META_AD_LIBRARY_TOKEN` | _(empty)_ | Meta Ad Library token (for the deferred live client) |
| `AQUEN_MIRA_SOUL_ID` | _(locked default)_ | Mira's trained Higgsfield Soul id |
| `AQUEN_MIRA_ELEMENT_ID` | _(locked default)_ | Mira's reusable Element id (clean stills) |
| `AQUEN_VIRALITY_THRESHOLD` | `0.6` | Virality pre-screen pass cutoff |
| `AQUEN_EXPORT_DIR` | `exports` | Default output directory for post packs |

---

## Testing

```powershell
# Full suite
.\.venv\Scripts\python.exe -m pytest -v

# One file / one test
.\.venv\Scripts\python.exe -m pytest tests/test_compliance_gate.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_service.py::test_advance_to_next -v
```

`pytest` is configured in `pyproject.toml` (`pythonpath = ["src"]`, `testpaths = ["tests"]`), so
tests resolve the `src/`-layout package without the editable install — but the `aquen` console
script does need `pip install -e ".[dev]"`. Service/model tests use an in-memory SQLite engine
(`StaticPool`); CLI tests use Typer's `CliRunner` with a `tmp_path` `AQUEN_DB_PATH` override.

---

## Documentation

- **Brand & product strategy:** [`docs/superpowers/specs/2026-06-18-aquen-content-brand-design.md`](docs/superpowers/specs/2026-06-18-aquen-content-brand-design.md)
- **Implementation plans:** [`docs/superpowers/plans/`](docs/superpowers/plans/)
- **Contributor guide for AI agents:** [`CLAUDE.md`](CLAUDE.md)
