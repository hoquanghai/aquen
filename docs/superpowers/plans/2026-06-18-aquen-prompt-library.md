# AQUEN Prompt Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned, categorized library of Higgsfield prompt templates (avatar, hands-only, texture, GRWM, explainer, voiceover) so on-brand prompts are stored once, versioned, and rendered with variables for repeatable generation.

**Architecture:** Builds on Plans 1–5. Mirrors the `analysis.py`/`scheduling.py` split: pure template logic (placeholder extraction + render) lives in `prompts.py` with no DB, a thin service layer persists templates to a new `Prompt` table with per-name version bumping, and a Typer `prompt` sub-app wraps it. `prompt render` prints the filled prompt text, which the user passes to `gen`. No new dependencies, fully offline-testable.

**Tech Stack:** Python 3.11+, Typer, SQLModel/SQLite, pytest, `string.Formatter` (stdlib). No new dependencies.

**Spec coverage:** §5.2 module 2 ("Ideation + Prompt library — ... a versioned library of Higgsfield prompts (avatar, hands-only, texture, GRWM, explainer, voiceover) for repeatable, on-brand generation") and the §5.3 `prompts` table. Templates use **named** `{placeholder}` fields only.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/aquen/models.py` | (modify) add `Prompt` table |
| `src/aquen/prompts.py` | (create) `PROMPT_CATEGORIES`, `PromptError`, `required_variables`/`render_template` (pure) + service (`add_prompt`, `get_prompt`, `list_prompts`, `prompt_versions`, `render_prompt`) |
| `src/aquen/cli.py` | (modify) add `prompt` sub-app (`add`/`list`/`versions`/`show`/`render`) |
| `tests/test_prompt_foundation.py` | (create) model tests |
| `tests/test_prompts_logic.py` | (create) pure-logic tests |
| `tests/test_prompts_service.py` | (create) service tests |
| `tests/test_cli_prompts.py` | (create) CLI tests |

**Baseline:** the suite is at **128 passing** before this plan.

---

## Task 1: Prompt model

**Files:**
- Modify: `src/aquen/models.py`
- Test: `tests/test_prompt_foundation.py`

- [ ] **Step 1: Write the failing test** — `tests/test_prompt_foundation.py`:

```python
from aquen.models import Prompt


def test_prompt_defaults(session):
    p = Prompt(name="mira-clean-portrait", category="avatar", template="a clean portrait of {subject}")
    session.add(p)
    session.commit()
    session.refresh(p)
    assert p.id is not None
    assert p.kind == "image"
    assert p.version == 1
    assert p.notes is None
    assert p.created_at is not None


def test_prompt_explicit_fields_roundtrip(session):
    p = Prompt(
        name="mira-grwm",
        category="grwm",
        kind="video",
        template="{subject} does a GRWM with {product}",
        version=3,
        notes="house GRWM v3",
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    assert p.category == "grwm"
    assert p.kind == "video"
    assert p.version == 3
    assert p.notes == "house GRWM v3"
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prompt_foundation.py -v` — Expected: FAIL (`cannot import name 'Prompt'`).

- [ ] **Step 3: Append the `Prompt` class to the END of `src/aquen/models.py`**:

```python


class Prompt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category: str  # avatar | hands_only | texture | grwm | explainer | voiceover
    kind: str = "image"  # image | video | audio
    template: str
    version: int = 1
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prompt_foundation.py -v` — Expected: PASS (2 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (130 passed: 128 + 2).

- [ ] **Step 6: Commit** — `git add src/aquen/models.py tests/test_prompt_foundation.py && git commit -m "feat: add Prompt model"`

---

## Task 2: Prompt template pure logic

**Files:**
- Create: `src/aquen/prompts.py`
- Test: `tests/test_prompts_logic.py`

- [ ] **Step 1: Write the failing test** — `tests/test_prompts_logic.py`:

```python
import pytest

from aquen.prompts import PromptError, render_template, required_variables


def test_required_variables_extracts_named_fields():
    assert required_variables("a {style} portrait of {subject}") == {"style", "subject"}


def test_required_variables_empty_for_plain_text():
    assert required_variables("a plain prompt") == set()


def test_render_template_fills_named_fields():
    assert render_template("a {style} portrait of {subject}", {"style": "clean", "subject": "Mira"}) == "a clean portrait of Mira"


def test_render_template_missing_variable_raises():
    with pytest.raises(PromptError):
        render_template("a {style} portrait of {subject}", {"style": "clean"})


def test_render_template_ignores_extra_variables():
    assert render_template("hello {name}", {"name": "Mira", "extra": "x"}) == "hello Mira"
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prompts_logic.py -v` — Expected: FAIL (`No module named 'aquen.prompts'`).

- [ ] **Step 3: Write `src/aquen/prompts.py`** (pure logic; the service is added in Task 3):

```python
from __future__ import annotations

import string

# Higgsfield prompt categories (spec §5.2 module 2).
PROMPT_CATEGORIES = [
    "avatar",
    "hands_only",
    "texture",
    "grwm",
    "explainer",
    "voiceover",
]


class PromptError(Exception):
    pass


def required_variables(template: str) -> set[str]:
    """Return the set of named {placeholder} fields a template needs."""
    return {
        field_name
        for _, field_name, _, _ in string.Formatter().parse(template)
        if field_name
    }


def render_template(template: str, variables: dict[str, str]) -> str:
    """Fill a template's named placeholders. Raises PromptError if any are missing;
    extra variables are ignored."""
    missing = required_variables(template) - set(variables)
    if missing:
        raise PromptError(f"missing variables: {', '.join(sorted(missing))}")
    return template.format(**variables)
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prompts_logic.py -v` — Expected: PASS (5 passed).

- [ ] **Step 5: Commit** — `git add src/aquen/prompts.py tests/test_prompts_logic.py && git commit -m "feat: add prompt template render logic"`

---

## Task 3: Prompt library service

**Files:**
- Modify: `src/aquen/prompts.py`
- Test: `tests/test_prompts_service.py`

- [ ] **Step 1: Write the failing test** — `tests/test_prompts_service.py`:

```python
import pytest

from aquen import prompts
from aquen.prompts import PromptError


def test_add_prompt_stores_version_1(session):
    p = prompts.add_prompt(session, "mira-clean", "avatar", "a {style} portrait of {subject}")
    assert p.id is not None
    assert p.version == 1
    assert p.kind == "image"


def test_add_prompt_unknown_category_raises(session):
    with pytest.raises(PromptError):
        prompts.add_prompt(session, "x", "not-a-category", "t")


def test_add_prompt_same_name_increments_version(session):
    prompts.add_prompt(session, "mira-clean", "avatar", "v1 {subject}")
    second = prompts.add_prompt(session, "mira-clean", "avatar", "v2 {subject}")
    assert second.version == 2


def test_get_prompt_returns_latest_by_default(session):
    prompts.add_prompt(session, "mira-clean", "avatar", "v1 {subject}")
    prompts.add_prompt(session, "mira-clean", "avatar", "v2 {subject}")
    assert prompts.get_prompt(session, "mira-clean").version == 2


def test_get_prompt_specific_version(session):
    prompts.add_prompt(session, "mira-clean", "avatar", "v1 {subject}")
    prompts.add_prompt(session, "mira-clean", "avatar", "v2 {subject}")
    assert prompts.get_prompt(session, "mira-clean", version=1).template == "v1 {subject}"


def test_get_prompt_missing_raises(session):
    with pytest.raises(ValueError):
        prompts.get_prompt(session, "nope")


def test_list_prompts_returns_latest_per_name_and_filters_category(session):
    prompts.add_prompt(session, "mira-clean", "avatar", "v1 {subject}")
    prompts.add_prompt(session, "mira-clean", "avatar", "v2 {subject}")
    prompts.add_prompt(session, "hands-serum", "hands_only", "hands with {product}")
    listed = prompts.list_prompts(session)
    assert {p.name: p.version for p in listed} == {"mira-clean": 2, "hands-serum": 1}
    avatars = prompts.list_prompts(session, category="avatar")
    assert [p.name for p in avatars] == ["mira-clean"]


def test_prompt_versions_lists_all_ascending(session):
    prompts.add_prompt(session, "mira-clean", "avatar", "v1 {subject}")
    prompts.add_prompt(session, "mira-clean", "avatar", "v2 {subject}")
    assert [p.version for p in prompts.prompt_versions(session, "mira-clean")] == [1, 2]


def test_render_prompt_renders_latest(session):
    prompts.add_prompt(session, "mira-clean", "avatar", "a {style} portrait of {subject}")
    out = prompts.render_prompt(session, "mira-clean", {"style": "clean", "subject": "Mira"})
    assert out == "a clean portrait of Mira"


def test_render_prompt_missing_var_raises(session):
    prompts.add_prompt(session, "mira-clean", "avatar", "a {style} portrait of {subject}")
    with pytest.raises(PromptError):
        prompts.render_prompt(session, "mira-clean", {"style": "clean"})
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prompts_service.py -v` — Expected: FAIL (`module 'aquen.prompts' has no attribute 'add_prompt'`).

- [ ] **Step 3: Append the service layer to `src/aquen/prompts.py`** — first add these imports right after `import string`:

```python
from sqlmodel import Session, select

from aquen.models import Prompt
```

Then append to the END of the file:

```python
def add_prompt(
    session: Session,
    name: str,
    category: str,
    template: str,
    *,
    kind: str = "image",
    notes: str | None = None,
) -> Prompt:
    """Store a prompt template. Re-using a name creates the next version of it."""
    if category not in PROMPT_CATEGORIES:
        raise PromptError(
            f"unknown category '{category}' (allowed: {', '.join(PROMPT_CATEGORIES)})"
        )
    latest = session.exec(
        select(Prompt).where(Prompt.name == name).order_by(Prompt.version.desc())
    ).first()
    version = latest.version + 1 if latest is not None else 1
    prompt = Prompt(
        name=name,
        category=category,
        kind=kind,
        template=template,
        version=version,
        notes=notes,
    )
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt


def get_prompt(session: Session, name: str, version: int | None = None) -> Prompt:
    stmt = select(Prompt).where(Prompt.name == name)
    stmt = stmt.where(Prompt.version == version) if version is not None else stmt.order_by(
        Prompt.version.desc()
    )
    prompt = session.exec(stmt).first()
    if prompt is None:
        label = f"'{name}'" + (f" v{version}" if version is not None else "")
        raise ValueError(f"prompt {label} not found")
    return prompt


def list_prompts(session: Session, category: str | None = None) -> list[Prompt]:
    """Return the latest version of each prompt name, optionally filtered by category."""
    stmt = select(Prompt).order_by(Prompt.name, Prompt.version)
    if category is not None:
        stmt = stmt.where(Prompt.category == category)
    latest: dict[str, Prompt] = {}
    for prompt in session.exec(stmt):
        latest[prompt.name] = prompt  # version-ascending order means the last seen wins
    return list(latest.values())


def prompt_versions(session: Session, name: str) -> list[Prompt]:
    return list(
        session.exec(
            select(Prompt).where(Prompt.name == name).order_by(Prompt.version)
        )
    )


def render_prompt(
    session: Session, name: str, variables: dict[str, str], *, version: int | None = None
) -> str:
    prompt = get_prompt(session, name, version=version)
    return render_template(prompt.template, variables)
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prompts_service.py -v` — Expected: PASS (10 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (145 passed: 130 + 5 + 10).

- [ ] **Step 6: Commit** — `git add src/aquen/prompts.py tests/test_prompts_service.py && git commit -m "feat: add prompt library service (add/get/list/versions/render)"`

---

## Task 4: CLI `prompt` sub-app

**Files:**
- Modify: `src/aquen/cli.py`
- Test: `tests/test_cli_prompts.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cli_prompts.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_add_then_list(tmp_path):
    env = _env(tmp_path)
    out = runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "v1" in out.stdout
    listed = runner.invoke(app, ["prompt", "list"], env=env)
    assert "mira-clean" in listed.stdout
    assert "avatar" in listed.stdout


def test_add_bad_category_errors(tmp_path):
    env = _env(tmp_path)
    out = runner.invoke(app, ["prompt", "add", "x", "nope", "t"], env=env)
    assert out.exit_code == 1
    assert "category" in (out.stdout + (out.stderr or "")).lower()


def test_show_prints_template(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    out = runner.invoke(app, ["prompt", "show", "mira-clean"], env=env)
    assert out.exit_code == 0
    assert "a {style} portrait of {subject}" in out.stdout


def test_render_with_vars(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    out = runner.invoke(
        app, ["prompt", "render", "mira-clean", "--var", "style=clean", "--var", "subject=Mira"], env=env
    )
    assert out.exit_code == 0, out.stdout
    assert "a clean portrait of Mira" in out.stdout


def test_render_missing_var_errors(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    out = runner.invoke(app, ["prompt", "render", "mira-clean", "--var", "style=clean"], env=env)
    assert out.exit_code == 1
    assert "missing" in (out.stdout + (out.stderr or "")).lower()


def test_versions_lists_all(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "v1 {subject}"], env=env)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "v2 {subject}"], env=env)
    out = runner.invoke(app, ["prompt", "versions", "mira-clean"], env=env)
    assert "v1" in out.stdout
    assert "v2" in out.stdout
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_prompts.py -v` — Expected: FAIL (no `prompt` command).

- [ ] **Step 3: Modify `src/aquen/cli.py`** — three edits:

(a) Add `prompts` to the `aquen` imports block (change `from aquen import compliance, generation, publish, research, scheduling, service`):

```python
from aquen import compliance, generation, prompts, publish, research, scheduling, service
```

(b) Register the `prompt` sub-app — add after the `app.add_typer(calendar_app, name="calendar")` line:

```python
prompt_app = typer.Typer(help="Versioned Higgsfield prompt library", no_args_is_help=True)
app.add_typer(prompt_app, name="prompt")
```

(c) Append the commands to the END of the file:

```python
@prompt_app.command("add")
def prompt_add(
    name: str,
    category: str,
    template: str,
    kind: str = typer.Option("image", help="image | video | audio"),
    notes: str = typer.Option(None, help="Optional note"),
) -> None:
    with _session_scope() as sess:
        try:
            p = prompts.add_prompt(sess, name, category, template, kind=kind, notes=notes)
        except prompts.PromptError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(f"{p.name} v{p.version} [{p.category}/{p.kind}]")


@prompt_app.command("list")
def prompt_list(
    category: str = typer.Option(None, help="Filter by category"),
) -> None:
    with _session_scope() as sess:
        for p in prompts.list_prompts(sess, category=category):
            typer.echo(f"{p.name} v{p.version} [{p.category}/{p.kind}]")


@prompt_app.command("versions")
def prompt_versions_cmd(name: str) -> None:
    with _session_scope() as sess:
        for p in prompts.prompt_versions(sess, name):
            typer.echo(f"{p.name} v{p.version} [{p.category}/{p.kind}]")


@prompt_app.command("show")
def prompt_show(
    name: str,
    version: int = typer.Option(None, help="Specific version (default: latest)"),
) -> None:
    with _session_scope() as sess:
        try:
            p = prompts.get_prompt(sess, name, version=version)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(f"{p.name} v{p.version} [{p.category}/{p.kind}]")
        if p.notes:
            typer.echo(f"# {p.notes}")
        typer.echo(p.template)


@prompt_app.command("render")
def prompt_render(
    name: str,
    var: list[str] = typer.Option(None, "--var", help="Template variable as k=v (repeatable)"),
    version: int = typer.Option(None, help="Specific version (default: latest)"),
) -> None:
    variables: dict[str, str] = {}
    for item in var or []:
        if "=" not in item:
            typer.echo(f"invalid --var '{item}' (use k=v)", err=True)
            raise typer.Exit(1)
        key, value = item.split("=", 1)
        variables[key] = value
    with _session_scope() as sess:
        try:
            text = prompts.render_prompt(sess, name, variables, version=version)
        except (ValueError, prompts.PromptError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(text)
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_prompts.py -v` — Expected: PASS (6 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (151 passed: 145 + 6).

- [ ] **Step 6: Manual smoke check** (PowerShell):

```powershell
if (Test-Path aquen.sqlite) { Remove-Item aquen.sqlite }
.\.venv\Scripts\aquen.exe prompt add mira-clean avatar "a {style} portrait of {subject}"
.\.venv\Scripts\aquen.exe prompt list
.\.venv\Scripts\aquen.exe prompt render mira-clean --var style=clean --var subject=Mira
if (Test-Path aquen.sqlite) { Remove-Item aquen.sqlite }
```

Expected: `mira-clean v1 [avatar/image]`, then the list line, then `a clean portrait of Mira`.

- [ ] **Step 7: Commit** — `git add src/aquen/cli.py tests/test_cli_prompts.py && git commit -m "feat: add prompt CLI sub-app"`

---

## Subsequent plans

- **Wire `prompt render` into `gen`** (`gen image --from <name> --var k=v`) so generation pulls straight from the library.
- **Live `HttpHiggsfieldClient`** + live `MetaAdLibraryClient` — deferred until credentials/endpoints are wired and verified.
- **Thin local dashboard** (FastAPI + Jinja/HTMX) and the **Meta Ads module**.

---

## Self-Review

**1. Spec coverage:** §5.2 module 2 prompt library — categories (`PROMPT_CATEGORIES` avatar/hands_only/texture/grwm/explainer/voiceover, Task 2), versioned templates (`Prompt.version` + per-name bump in `add_prompt`, Tasks 1/3), repeatable rendering (`render_template`/`render_prompt`, Tasks 2/3). §5.3 `prompts` table → `Prompt` (Task 1). Gen integration is listed as the immediate follow-up.

**2. Placeholder scan:** No TBD/TODO. Every code step is complete and runnable; every run step has an exact command and expected count. Template `{placeholder}` syntax is product behaviour, not a plan placeholder.

**3. Type consistency:** `required_variables(template)` / `render_template(template, variables)` signatures match across Tasks 2–3. `Prompt` columns (`name`, `category`, `kind`, `template`, `version`, `notes`) match across Task 1 (model), Task 3 (service writes), Task 4 (CLI display). `prompts.add_prompt/get_prompt/list_prompts/prompt_versions/render_prompt` signatures match their callers in the CLI. `PromptError` is raised by the service/logic and caught by the CLI; `get_prompt` raises `ValueError` for a missing name, also caught.
