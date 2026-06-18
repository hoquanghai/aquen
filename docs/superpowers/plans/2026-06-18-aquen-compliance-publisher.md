# AQUEN Compliance Gate + Publisher Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the AQUEN compliance gate that blocks a content item from reaching `ready` until FTC dual disclosure + persistent AI label + claim-substantiation + no-prohibited-claim all pass, plus a human-in-the-loop publisher that exports a manual-upload post pack (disclosed caption + hashtags + overlay notes + asset links).

**Architecture:** Builds on Plans 1–3. Mirrors the existing `analysis.py`/`research.py` split: pure check logic lives in `compliance.py` (no DB, unit-testable like `analysis.check_originality`), a thin service layer persists results to a new `ComplianceCheck` audit table and enforces the gate inside the single `service.advance_content` transition seam. The publisher (`publish.py`) reads a `ready` item plus its linked `Generation` rows and writes a post-pack folder to disk — no network, manual upload only, per spec §5.2 module 8. New compliance fields live on `ContentItem` and are set via a `content set` CLI command.

**Tech Stack:** Python 3.11+, Typer, SQLModel/SQLite, pytest. No new dependencies.

**Spec constraints (re-read §4.5 before building):** FTC dual disclosure = a commercial-relationship disclosure **and** a separate "AI-generated" disclosure (`#ad` alone is insufficient); persistent on-content AI label; substantiate skincare claims; **flatly prohibited regardless of disclosure**: AI testimonials, before/after, fabricated efficacy ("cleared my skin"), and "anti-aging". Mira is a synthetic performer, so the AI disclosure + AI label are required on **every** post; the commercial-relationship disclosure is required only when the post is sponsored.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/aquen/config.py` | (modify) add `export_dir` |
| `src/aquen/models.py` | (modify) add compliance fields to `ContentItem`; add `ComplianceCheck` table |
| `src/aquen/compliance.py` | (create) pure check logic (markers, prohibited patterns, `CheckResult`, `evaluate`) + `ComplianceError` + service (`record_checks`, `assert_compliant`, `list_checks`) |
| `src/aquen/service.py` | (modify) `set_content_fields`; wire the compliance gate into `advance_content` on `→ ready` |
| `src/aquen/publish.py` | (create) `export_pack` — write the post-pack folder for a `ready` item |
| `src/aquen/cli.py` | (modify) `content set`; `compliance` sub-app (`check`/`log`); `publish` sub-app (`pack`); catch `ComplianceError` in `content advance` |
| `tests/test_compliance_foundation.py` | (create) config + model tests |
| `tests/test_compliance_logic.py` | (create) pure check-function tests |
| `tests/test_compliance_gate.py` | (create) service + gate tests |
| `tests/test_cli_compliance.py` | (create) CLI tests for `content set` + `compliance` |
| `tests/test_publish_service.py` | (create) publisher service tests |
| `tests/test_cli_publish.py` | (create) CLI tests for `publish` |

**Baseline:** the suite is at **65 passing** before this plan.

---

## Task 1: Config + model fields + ComplianceCheck table

**Files:**
- Modify: `src/aquen/config.py`
- Modify: `src/aquen/models.py`
- Test: `tests/test_compliance_foundation.py`

- [ ] **Step 1: Write the failing test** — `tests/test_compliance_foundation.py`:

```python
from pathlib import Path

from aquen.config import get_settings
from aquen.models import ComplianceCheck, ContentItem


def test_export_dir_default():
    assert get_settings().export_dir == Path("exports")


def test_export_dir_env_override(monkeypatch):
    monkeypatch.setenv("AQUEN_EXPORT_DIR", "out/packs")
    assert get_settings().export_dir == Path("out/packs")


def test_content_item_compliance_field_defaults(session):
    item = ContentItem(title="Beta-glucan 101", pillar="derma_decode")
    session.add(item)
    session.commit()
    session.refresh(item)
    assert item.caption is None
    assert item.is_sponsored is False
    assert item.ai_label_on_content is False
    assert item.substantiation_url is None


def test_compliance_check_roundtrip(session):
    row = ComplianceCheck(
        content_item_id=1, check="ai_disclosure", passed=False, detail="missing"
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    assert row.id is not None
    assert row.passed is False
    assert row.created_at is not None
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_compliance_foundation.py -v` — Expected: FAIL (`export_dir` not on Settings / `cannot import name 'ComplianceCheck'`).

- [ ] **Step 3: Add `export_dir` to `src/aquen/config.py`** — insert this line in the `Settings` class right after `virality_threshold: float = 0.6`:

```python
    export_dir: Path = Path("exports")
```

- [ ] **Step 4: Add compliance fields to `ContentItem` in `src/aquen/models.py`** — replace this exact block:

```python
    source_inspiration_url: str | None = None
    script: str | None = None
    originality_note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

with:

```python
    source_inspiration_url: str | None = None
    script: str | None = None
    originality_note: str | None = None
    # Compliance inputs (validated by the compliance gate before reaching `ready`).
    caption: str | None = None
    is_sponsored: bool = False
    ai_label_on_content: bool = False
    substantiation_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 5: Append the `ComplianceCheck` class to the END of `src/aquen/models.py`** (do not change existing classes):

```python


class ComplianceCheck(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content_item_id: int = Field(index=True)
    check: str  # ai_disclosure | ai_label | commercial_disclosure | no_prohibited_claims | substantiation
    passed: bool
    detail: str
    created_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 6: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_compliance_foundation.py -v` — Expected: PASS (4 passed).

- [ ] **Step 7: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (69 passed: 65 prior + 4).

- [ ] **Step 8: Commit**

```bash
git add src/aquen/config.py src/aquen/models.py tests/test_compliance_foundation.py
git commit -m "feat: add compliance fields, ComplianceCheck table, export_dir config"
```

---

## Task 2: Compliance check logic (pure)

**Files:**
- Create: `src/aquen/compliance.py`
- Test: `tests/test_compliance_logic.py`

- [ ] **Step 1: Write the failing test** — `tests/test_compliance_logic.py`:

```python
from aquen.compliance import (
    CheckResult,
    check_ai_disclosure,
    check_ai_label,
    check_commercial_disclosure,
    check_no_prohibited_claims,
    check_substantiation,
    evaluate,
)
from aquen.models import ContentItem


def test_ai_disclosure_pass():
    r = check_ai_disclosure("Created with AI — the science on beta-glucan.")
    assert isinstance(r, CheckResult)
    assert r.name == "ai_disclosure"
    assert r.passed is True


def test_ai_disclosure_fail_when_absent():
    assert check_ai_disclosure("Here's the science on beta-glucan.").passed is False


def test_ai_disclosure_fail_when_none():
    assert check_ai_disclosure(None).passed is False


def test_ai_label_reflects_flag():
    assert check_ai_label(True).passed is True
    assert check_ai_label(False).passed is False


def test_commercial_disclosure_required_only_when_sponsored():
    assert check_commercial_disclosure("no markers here", is_sponsored=False).passed is True
    assert check_commercial_disclosure("no markers here", is_sponsored=True).passed is False
    assert check_commercial_disclosure("paid partnership with X", is_sponsored=True).passed is True


def test_prohibited_testimonial_blocked():
    r = check_no_prohibited_claims("This serum cleared my skin in 2 weeks.", None)
    assert r.passed is False


def test_prohibited_before_after_blocked():
    assert check_no_prohibited_claims("Before and after using Mira's routine.", None).passed is False


def test_prohibited_anti_aging_blocked():
    assert check_no_prohibited_claims(None, "Great anti-aging benefits for everyone.").passed is False


def test_prohibited_clean_caption_passes():
    assert check_no_prohibited_claims("Created with AI. The science on beta-glucan. #ad", "").passed is True


def test_substantiation_required_when_claim_present():
    assert check_substantiation("Clinically supported hydration.", None, None).passed is False
    assert check_substantiation("Clinically supported hydration.", None, "https://study").passed is True


def test_substantiation_not_required_without_claims():
    assert check_substantiation("A calm look at beta-glucan.", None, None).passed is True


def test_evaluate_returns_all_five_checks_in_order():
    item = ContentItem(
        title="t",
        pillar="derma_decode",
        caption="Created with AI. The science on beta-glucan. #ad",
        is_sponsored=True,
        ai_label_on_content=True,
    )
    results = evaluate(item)
    assert [r.name for r in results] == [
        "ai_disclosure",
        "ai_label",
        "commercial_disclosure",
        "no_prohibited_claims",
        "substantiation",
    ]
    assert all(r.passed for r in results)
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_compliance_logic.py -v` — Expected: FAIL (`ModuleNotFoundError: No module named 'aquen.compliance'`).

- [ ] **Step 3: Write `src/aquen/compliance.py`** (pure logic only; the service functions are added in Task 3):

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from aquen.models import ContentItem

# Mira is a synthetic performer, so an AI disclosure is required on every post.
AI_DISCLOSURE_MARKERS = [
    "ai-generated",
    "ai generated",
    "created with ai",
    "made with ai",
    "generated with ai",
    "ai avatar",
    "synthetic",
    "virtual creator",
]

# A commercial-relationship disclosure is required only on sponsored/branded posts.
COMMERCIAL_MARKERS = [
    "#ad",
    "paid partnership",
    "paid promotion",
    "sponsored",
    "advertisement",
]

# Skincare claim language that must be backed by a substantiation source.
CLAIM_MARKERS = [
    "clinically",
    "clinical",
    "proven",
    "reduces",
    "boosts",
    "increases",
    "strengthens",
    "repairs",
    "dermatologist-tested",
    "%",
]

# Flatly prohibited regardless of disclosure (spec §4.5): AI testimonials, before/after,
# fabricated efficacy, "anti-aging". First match wins.
PROHIBITED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"before\s*(?:and|/|&|-)\s*after", re.IGNORECASE),
        "before/after results are prohibited",
    ),
    (
        re.compile(
            r"\b(?:cleared|healed|fixed|cured|transformed|improved)\b[^.?!]{0,25}\b(?:skin|acne|breakouts?)\b",
            re.IGNORECASE,
        ),
        "AI testimonial / efficacy claim is prohibited",
    ),
    (
        re.compile(r"got rid of[^.?!]{0,25}\b(?:acne|breakouts?|pimples?)\b", re.IGNORECASE),
        "efficacy claim is prohibited",
    ),
    (
        re.compile(r"anti[\s-]?aging", re.IGNORECASE),
        "'anti-aging' claim is prohibited",
    ),
]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _find_marker(text: str | None, markers: list[str]) -> str | None:
    t = (text or "").lower()
    return next((m for m in markers if m in t), None)


def check_ai_disclosure(caption: str | None) -> CheckResult:
    marker = _find_marker(caption, AI_DISCLOSURE_MARKERS)
    if marker:
        return CheckResult("ai_disclosure", True, f"AI disclosure present ('{marker}')")
    return CheckResult(
        "ai_disclosure", False, "caption is missing an 'AI-generated' disclosure"
    )


def check_ai_label(ai_label_on_content: bool) -> CheckResult:
    if ai_label_on_content:
        return CheckResult("ai_label", True, "persistent on-content AI label confirmed")
    return CheckResult(
        "ai_label", False, "persistent on-content AI label not confirmed"
    )


def check_commercial_disclosure(caption: str | None, is_sponsored: bool) -> CheckResult:
    if not is_sponsored:
        return CheckResult(
            "commercial_disclosure", True, "not a sponsored post — disclosure not required"
        )
    marker = _find_marker(caption, COMMERCIAL_MARKERS)
    if marker:
        return CheckResult(
            "commercial_disclosure", True, f"commercial disclosure present ('{marker}')"
        )
    return CheckResult(
        "commercial_disclosure",
        False,
        "sponsored post is missing a commercial-relationship disclosure (#ad alone is not enough)",
    )


def check_no_prohibited_claims(caption: str | None, script: str | None) -> CheckResult:
    blob = f"{caption or ''} {script or ''}"
    for pattern, reason in PROHIBITED_PATTERNS:
        if pattern.search(blob):
            return CheckResult("no_prohibited_claims", False, reason)
    return CheckResult("no_prohibited_claims", True, "no prohibited claims found")


def check_substantiation(
    caption: str | None, script: str | None, substantiation_url: str | None
) -> CheckResult:
    marker = _find_marker(f"{caption or ''} {script or ''}", CLAIM_MARKERS)
    if marker and not substantiation_url:
        return CheckResult(
            "substantiation",
            False,
            f"claim language ('{marker}') needs a substantiation source",
        )
    return CheckResult("substantiation", True, "claims substantiated or none made")


def evaluate(item: ContentItem) -> list[CheckResult]:
    """Run all five compliance checks against a content item (pure, no DB)."""
    return [
        check_ai_disclosure(item.caption),
        check_ai_label(item.ai_label_on_content),
        check_commercial_disclosure(item.caption, item.is_sponsored),
        check_no_prohibited_claims(item.caption, item.script),
        check_substantiation(item.caption, item.script, item.substantiation_url),
    ]
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_compliance_logic.py -v` — Expected: PASS (12 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/compliance.py tests/test_compliance_logic.py
git commit -m "feat: add compliance check logic (FTC disclosure, AI label, claims gate)"
```

---

## Task 3: Compliance service + gate enforcement

**Files:**
- Modify: `src/aquen/compliance.py`
- Modify: `src/aquen/service.py`
- Test: `tests/test_compliance_gate.py`

- [ ] **Step 1: Write the failing test** — `tests/test_compliance_gate.py`:

```python
import pytest

from aquen import compliance, service
from aquen.compliance import ComplianceError
from aquen.models import ContentItem
from aquen.states import ContentState, InvalidTransition


def _compliant_item(session) -> ContentItem:
    item = ContentItem(
        title="Beta-glucan 101",
        pillar="derma_decode",
        state=ContentState.REVIEW,
        caption="Created with AI. The honest science on beta-glucan. #ad",
        is_sponsored=True,
        ai_label_on_content=True,
        script="A calm explainer in Mira's voice.",
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def _noncompliant_item(session) -> ContentItem:
    item = ContentItem(
        title="Quick promo",
        pillar="derma_decode",
        state=ContentState.REVIEW,
        caption="Check out this serum #ad",  # no AI disclosure
        is_sponsored=True,
        ai_label_on_content=False,  # no AI label
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_record_checks_persists_five_rows(session):
    item = _compliant_item(session)
    rows = compliance.record_checks(session, item.id)
    assert len(rows) == 5
    assert all(r.id is not None for r in rows)
    assert compliance.list_checks(session, item.id) == rows


def test_assert_compliant_passes_for_compliant_item(session):
    item = _compliant_item(session)
    rows = compliance.assert_compliant(session, item.id)
    assert all(r.passed for r in rows)


def test_assert_compliant_raises_and_still_logs(session):
    item = _noncompliant_item(session)
    with pytest.raises(ComplianceError):
        compliance.assert_compliant(session, item.id)
    # The audit trail is recorded even on failure.
    assert len(compliance.list_checks(session, item.id)) == 5


def test_record_checks_missing_item_raises(session):
    with pytest.raises(ValueError):
        compliance.record_checks(session, 999)


def test_advance_to_ready_blocked_when_noncompliant(session):
    item = _noncompliant_item(session)
    with pytest.raises(ComplianceError):
        service.advance_content(session, item.id, target=ContentState.READY)
    session.refresh(item)
    assert item.state == ContentState.REVIEW  # not advanced


def test_advance_to_ready_succeeds_when_compliant(session):
    item = _compliant_item(session)
    advanced = service.advance_content(session, item.id, target=ContentState.READY)
    assert advanced.state == ContentState.READY


def test_non_ready_transitions_skip_the_gate(session):
    # An empty IDEA item would fail compliance, but moving idea -> scripted must not run it.
    item = ContentItem(title="t", pillar="derma_decode", state=ContentState.IDEA)
    session.add(item)
    session.commit()
    session.refresh(item)
    advanced = service.advance_content(session, item.id)  # -> scripted
    assert advanced.state == ContentState.SCRIPTED
    assert compliance.list_checks(session, item.id) == []
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_compliance_gate.py -v` — Expected: FAIL (`cannot import name 'ComplianceError'` / `module 'aquen.compliance' has no attribute 'record_checks'`).

- [ ] **Step 3: Append the service layer to `src/aquen/compliance.py`** — first add these imports at the TOP of the file, right after `import re`:

```python
from sqlmodel import Session, select
```

and right after `from aquen.models import ContentItem`:

```python
from aquen.models import ComplianceCheck
```

Then append to the END of the file:

```python
class ComplianceError(Exception):
    pass


def record_checks(session: Session, item_id: int) -> list[ComplianceCheck]:
    """Run the gate on a content item and persist one ComplianceCheck row per check."""
    item = session.get(ContentItem, item_id)
    if item is None:
        raise ValueError(f"content item {item_id} not found")
    rows = [
        ComplianceCheck(
            content_item_id=item_id, check=r.name, passed=r.passed, detail=r.detail
        )
        for r in evaluate(item)
    ]
    for row in rows:
        session.add(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def assert_compliant(session: Session, item_id: int) -> list[ComplianceCheck]:
    """Record the checks; raise ComplianceError listing every failure if any check fails."""
    rows = record_checks(session, item_id)
    failed = [r for r in rows if not r.passed]
    if failed:
        summary = "; ".join(f"{r.check}: {r.detail}" for r in failed)
        raise ComplianceError(f"content {item_id} is not ready — {summary}")
    return rows


def list_checks(session: Session, item_id: int) -> list[ComplianceCheck]:
    stmt = (
        select(ComplianceCheck)
        .where(ComplianceCheck.content_item_id == item_id)
        .order_by(ComplianceCheck.id)
    )
    return list(session.exec(stmt))
```

- [ ] **Step 4: Wire the gate into `src/aquen/service.py`** — add this import after the existing `from aquen.models import ...` line:

```python
from aquen import compliance
```

Then in `advance_content`, insert the gate check between the `can_transition` guard and the `item.state = tgt` line. Replace this block:

```python
    if not can_transition(item.state, tgt):
        raise InvalidTransition(
            f"cannot move content {item_id} from {item.state.value} to {tgt.value}"
        )

    item.state = tgt
```

with:

```python
    if not can_transition(item.state, tgt):
        raise InvalidTransition(
            f"cannot move content {item_id} from {item.state.value} to {tgt.value}"
        )

    # Compliance gate: a content item cannot reach `ready` until every check passes.
    if tgt == ContentState.READY:
        compliance.assert_compliant(session, item_id)

    item.state = tgt
```

- [ ] **Step 5: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_compliance_gate.py -v` — Expected: PASS (7 passed).

- [ ] **Step 6: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (88 passed: 69 + 12 + 7).

- [ ] **Step 7: Commit**

```bash
git add src/aquen/compliance.py src/aquen/service.py tests/test_compliance_gate.py
git commit -m "feat: enforce compliance gate on review->ready transition"
```

---

## Task 4: CLI — `content set` + `compliance` sub-app

**Files:**
- Modify: `src/aquen/service.py`
- Modify: `src/aquen/cli.py`
- Test: `tests/test_cli_compliance.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cli_compliance.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def _seed_review_item(env: dict[str, str]) -> None:
    runner.invoke(app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env)
    for _ in range(5):  # idea -> scripted -> generating -> rendered -> screened -> review
        runner.invoke(app, ["content", "advance", "1"], env=env)


def test_content_set_updates_fields(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["content", "add", "t", "derma_decode"], env=env)
    out = runner.invoke(
        app,
        ["content", "set", "1", "--caption", "Created with AI. #ad", "--sponsored", "--ai-label"],
        env=env,
    )
    assert out.exit_code == 0, out.stdout
    assert "sponsored=True" in out.stdout
    assert "ai_label=True" in out.stdout


def test_compliance_check_reports_failures(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    out = runner.invoke(app, ["compliance", "check", "1"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "FAIL" in out.stdout
    assert "ai_disclosure" in out.stdout


def test_compliance_check_all_pass_then_advance(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    runner.invoke(
        app,
        ["content", "set", "1", "--caption", "Created with AI. Honest beta-glucan science. #ad",
         "--sponsored", "--ai-label"],
        env=env,
    )
    checked = runner.invoke(app, ["compliance", "check", "1"], env=env)
    assert "ALL CHECKS PASS" in checked.stdout
    advanced = runner.invoke(app, ["content", "advance", "1", "--to", "ready"], env=env)
    assert advanced.exit_code == 0, advanced.stdout
    assert "ready" in advanced.stdout


def test_advance_blocked_shows_message(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    out = runner.invoke(app, ["content", "advance", "1", "--to", "ready"], env=env)
    assert out.exit_code == 1
    assert "not ready" in out.stdout.lower() or "not ready" in (out.stderr or "").lower()


def test_compliance_log_lists_rows(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    runner.invoke(app, ["compliance", "check", "1"], env=env)
    out = runner.invoke(app, ["compliance", "log", "1"], env=env)
    assert "ai_disclosure" in out.stdout
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_compliance.py -v` — Expected: FAIL (no `content set` / no `compliance` command).

- [ ] **Step 3: Add `set_content_fields` to `src/aquen/service.py`** — append to the end of the file:

```python
def set_content_fields(
    session: Session,
    item_id: int,
    *,
    caption: str | None = None,
    is_sponsored: bool | None = None,
    ai_label_on_content: bool | None = None,
    substantiation_url: str | None = None,
) -> ContentItem:
    """Update the compliance-relevant fields on a content item. Only non-None args change."""
    item = session.get(ContentItem, item_id)
    if item is None:
        raise ValueError(f"content item {item_id} not found")
    if caption is not None:
        item.caption = caption
    if is_sponsored is not None:
        item.is_sponsored = is_sponsored
    if ai_label_on_content is not None:
        item.ai_label_on_content = ai_label_on_content
    if substantiation_url is not None:
        item.substantiation_url = substantiation_url
    item.updated_at = utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
```

- [ ] **Step 4: Modify `src/aquen/cli.py`** — four edits, do NOT touch existing commands except `content_advance`:

(a) Add to the imports block near the top (alongside `from aquen import generation, research, service`):

```python
from aquen import compliance
```

(b) Register a `compliance` sub-app — add after the existing `app.add_typer(gen_app, name="gen")` line:

```python
compliance_app = typer.Typer(help="Run and inspect the compliance gate", no_args_is_help=True)
app.add_typer(compliance_app, name="compliance")
```

(c) Add the `content set` command — append to the END of the file:

```python
@content_app.command("set")
def content_set(
    item_id: int,
    caption: str = typer.Option(None, help="Post caption (disclosures baked in)"),
    sponsored: bool = typer.Option(None, "--sponsored/--not-sponsored", help="Mark as a sponsored post"),
    ai_label: bool = typer.Option(None, "--ai-label/--no-ai-label", help="Confirm the persistent on-content AI label"),
    substantiation: str = typer.Option(None, help="Substantiation source URL for skincare claims"),
) -> None:
    with _session_scope() as sess:
        item = service.set_content_fields(
            sess,
            item_id,
            caption=caption,
            is_sponsored=sponsored,
            ai_label_on_content=ai_label,
            substantiation_url=substantiation,
        )
        typer.echo(
            f"#{item.id} caption={'set' if item.caption else 'none'} "
            f"sponsored={item.is_sponsored} ai_label={item.ai_label_on_content}"
        )
```

(d) Add the `compliance` commands — append to the END of the file:

```python
@compliance_app.command("check")
def compliance_check(item_id: int) -> None:
    with _session_scope() as sess:
        try:
            rows = compliance.record_checks(sess, item_id)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        for r in rows:
            typer.echo(f"[{'PASS' if r.passed else 'FAIL'}] {r.check}: {r.detail}")
        if all(r.passed for r in rows):
            typer.echo("ALL CHECKS PASS")


@compliance_app.command("log")
def compliance_log(item_id: int) -> None:
    with _session_scope() as sess:
        for r in compliance.list_checks(sess, item_id):
            typer.echo(f"#{r.id} [{'PASS' if r.passed else 'FAIL'}] {r.check}")
```

(e) Make `content advance` surface a blocked gate cleanly — replace the existing `content_advance` body:

```python
@content_app.command("advance")
def content_advance(
    item_id: int,
    to: str = typer.Option(None, help="Explicit target state (default: next)"),
) -> None:
    with _session_scope() as sess:
        tgt = ContentState(to) if to else None
        item = service.advance_content(sess, item_id, target=tgt)
        typer.echo(f"#{item.id} -> {item.state.value}")
```

with:

```python
@content_app.command("advance")
def content_advance(
    item_id: int,
    to: str = typer.Option(None, help="Explicit target state (default: next)"),
) -> None:
    with _session_scope() as sess:
        tgt = ContentState(to) if to else None
        try:
            item = service.advance_content(sess, item_id, target=tgt)
        except compliance.ComplianceError as exc:
            typer.echo(f"Blocked: {exc}", err=True)
            raise typer.Exit(1)
        typer.echo(f"#{item.id} -> {item.state.value}")
```

- [ ] **Step 4b: Note on CliRunner output** — `CliRunner()` (default `mix_stderr=True`) folds stderr into `.stdout`, so the `test_advance_blocked_shows_message` assertion finds "not ready" in `out.stdout`. No extra config needed.

- [ ] **Step 5: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_compliance.py -v` — Expected: PASS (5 passed).

- [ ] **Step 6: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (93 passed: 88 + 5).

- [ ] **Step 7: Commit**

```bash
git add src/aquen/service.py src/aquen/cli.py tests/test_cli_compliance.py
git commit -m "feat: add content set + compliance check/log CLI commands"
```

---

## Task 5: Publisher export service

**Files:**
- Create: `src/aquen/publish.py`
- Test: `tests/test_publish_service.py`

- [ ] **Step 1: Write the failing test** — `tests/test_publish_service.py`:

```python
import pytest

from aquen import publish
from aquen.models import ContentItem, Generation
from aquen.states import ContentState


def _ready_item(session, **kw) -> ContentItem:
    item = ContentItem(
        title="Beta-glucan 101",
        pillar="derma_decode",
        state=ContentState.READY,
        caption="Created with AI. The honest science on beta-glucan. #ad",
        is_sponsored=True,
        ai_label_on_content=True,
        **kw,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_export_requires_ready_state(session, tmp_path):
    item = ContentItem(title="t", pillar="derma_decode", state=ContentState.REVIEW)
    session.add(item)
    session.commit()
    session.refresh(item)
    with pytest.raises(ValueError):
        publish.export_pack(session, item.id, out_dir=tmp_path)


def test_export_missing_item_raises(session, tmp_path):
    with pytest.raises(ValueError):
        publish.export_pack(session, 999, out_dir=tmp_path)


def test_export_writes_pack_files(session, tmp_path):
    item = _ready_item(session)
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    assert pack.is_dir()
    assert (pack / "caption.txt").exists()
    assert (pack / "post_pack.md").exists()


def test_caption_file_carries_caption_and_hashtags(session, tmp_path):
    item = _ready_item(session)
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    caption = (pack / "caption.txt").read_text(encoding="utf-8")
    assert "Created with AI" in caption
    assert "#AQUEN" in caption


def test_pack_includes_asset_urls(session, tmp_path):
    item = _ready_item(session)
    session.add(
        Generation(
            content_item_id=item.id,
            kind="video",
            prompt="p",
            model="minimax_hailuo",
            external_job_id="job-1",
            status="completed",
            result_url="https://fake.local/job-1.png",
        )
    )
    session.commit()
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    body = (pack / "post_pack.md").read_text(encoding="utf-8")
    assert "https://fake.local/job-1.png" in body


def test_pack_has_ai_label_overlay_note(session, tmp_path):
    item = _ready_item(session)
    pack = publish.export_pack(session, item.id, out_dir=tmp_path)
    body = (pack / "post_pack.md").read_text(encoding="utf-8")
    assert "AI-generated" in body
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_publish_service.py -v` — Expected: FAIL (`ModuleNotFoundError: No module named 'aquen.publish'`).

- [ ] **Step 3: Write `src/aquen/publish.py`**:

```python
from __future__ import annotations

from pathlib import Path

from sqlmodel import Session

from aquen.config import get_settings
from aquen.generation import list_generations
from aquen.models import ContentItem
from aquen.states import ContentState

BRAND_HASHTAGS = ["#AQUEN", "#skincare", "#skintok"]

AI_LABEL_NOTE = (
    "Burn a persistent on-screen 'AI-generated' label into the video for its full duration "
    "(plain language, legible). Keep the AI + commercial disclosures in the first line of the "
    "caption — do not bury them below the fold."
)


def _hashtags(item: ContentItem) -> list[str]:
    tags = list(BRAND_HASHTAGS)
    if item.pillar:
        tags.append("#" + item.pillar.replace("_", ""))
    return tags


def export_pack(
    session: Session, item_id: int, out_dir: str | Path | None = None
) -> Path:
    """Export a manual-upload post pack for a `ready` content item: a folder holding the
    disclosed caption (caption.txt) and a human-readable manifest (post_pack.md) with
    hashtags, AI-label overlay notes, and links to the item's rendered assets."""
    item = session.get(ContentItem, item_id)
    if item is None:
        raise ValueError(f"content item {item_id} not found")
    if item.state != ContentState.READY:
        raise ValueError(
            f"content {item_id} is {item.state.value}; only a 'ready' item can be exported"
        )

    base = Path(out_dir) if out_dir is not None else get_settings().export_dir
    pack_dir = base / f"aquen-post-{item.id}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    hashtags = _hashtags(item)
    caption = item.caption or ""
    assets = [
        g.result_url
        for g in list_generations(session, content_item_id=item.id)
        if g.result_url
    ]

    (pack_dir / "caption.txt").write_text(
        f"{caption}\n\n{' '.join(hashtags)}\n", encoding="utf-8"
    )

    lines = [
        f"# AQUEN post pack — #{item.id}",
        "",
        f"- **Title:** {item.title}",
        f"- **Pillar:** {item.pillar}",
        f"- **Hook:** {item.hook_archetype or '—'}",
        f"- **Sponsored:** {'yes' if item.is_sponsored else 'no'}",
        "",
        "## Caption (disclosures baked in)",
        "",
        caption or "_(no caption)_",
        "",
        "## Hashtags",
        "",
        " ".join(hashtags),
        "",
        "## Overlay / AI-label notes",
        "",
        AI_LABEL_NOTE,
        "",
        "## Assets",
        "",
    ]
    lines += [f"- {url}" for url in assets] if assets else ["_(no rendered assets linked)_"]
    lines.append("")
    (pack_dir / "post_pack.md").write_text("\n".join(lines), encoding="utf-8")

    return pack_dir
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_publish_service.py -v` — Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/publish.py tests/test_publish_service.py
git commit -m "feat: add publisher post-pack export service"
```

---

## Task 6: CLI `publish` command

**Files:**
- Modify: `src/aquen/cli.py`
- Test: `tests/test_cli_publish.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cli_publish.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def _seed_ready_item(env: dict[str, str]) -> None:
    runner.invoke(app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env)
    for _ in range(5):  # -> review
        runner.invoke(app, ["content", "advance", "1"], env=env)
    runner.invoke(
        app,
        ["content", "set", "1", "--caption", "Created with AI. Honest beta-glucan science. #ad",
         "--sponsored", "--ai-label"],
        env=env,
    )
    runner.invoke(app, ["content", "advance", "1", "--to", "ready"], env=env)


def test_publish_pack_happy_path(tmp_path):
    env = _env(tmp_path)
    _seed_ready_item(env)
    out_dir = tmp_path / "packs"
    result = runner.invoke(app, ["publish", "pack", "1", "--out", str(out_dir)], env=env)
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "aquen-post-1" / "post_pack.md").exists()
    assert "aquen-post-1" in result.stdout


def test_publish_pack_non_ready_errors(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["content", "add", "t", "derma_decode"], env=env)  # stays idea
    result = runner.invoke(app, ["publish", "pack", "1", "--out", str(tmp_path)], env=env)
    assert result.exit_code == 1
    assert "ready" in (result.stdout + (result.stderr or "")).lower()
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_publish.py -v` — Expected: FAIL (no `publish` command).

- [ ] **Step 3: Modify `src/aquen/cli.py`** — three edits:

(a) Add to the imports block (alongside `from aquen import compliance`):

```python
from aquen import publish
```

(b) Register the `publish` sub-app — add after the `app.add_typer(compliance_app, name="compliance")` line:

```python
publish_app = typer.Typer(help="Export manual-upload post packs", no_args_is_help=True)
app.add_typer(publish_app, name="publish")
```

(c) Add the `publish pack` command — append to the END of the file:

```python
@publish_app.command("pack")
def publish_pack(
    item_id: int,
    out: str = typer.Option(None, help="Output directory (defaults to AQUEN_EXPORT_DIR)"),
) -> None:
    with _session_scope() as sess:
        try:
            pack_dir = publish.export_pack(sess, item_id, out_dir=out)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(f"Exported post pack to {pack_dir}")
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_publish.py -v` — Expected: PASS (2 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (101 passed: 93 + 6 + 2).

- [ ] **Step 6: Manual smoke check** (PowerShell) — delete any stale dev DB first:

```powershell
if (Test-Path aquen.sqlite) { Remove-Item aquen.sqlite }
.\.venv\Scripts\aquen.exe content add "Beta-glucan 101" derma_decode
1..5 | ForEach-Object { .\.venv\Scripts\aquen.exe content advance 1 }
.\.venv\Scripts\aquen.exe content set 1 --caption "Created with AI. Honest beta-glucan science. #ad" --sponsored --ai-label
.\.venv\Scripts\aquen.exe compliance check 1
.\.venv\Scripts\aquen.exe content advance 1 --to ready
.\.venv\Scripts\aquen.exe publish pack 1 --out exports
```

Expected: `compliance check` prints five `[PASS]` lines + `ALL CHECKS PASS`; advance prints `#1 -> ready`; publish prints `Exported post pack to exports\aquen-post-1`. (`aquen.sqlite` and `exports/` are dev artifacts — confirm they are gitignored before committing; if `exports/` is not ignored, add it to `.gitignore` in this step.)

- [ ] **Step 7: Commit**

```bash
git add src/aquen/cli.py tests/test_cli_publish.py
git commit -m "feat: add publish pack CLI command"
```

---

## Subsequent plans

- **Live `HttpHiggsfieldClient`** (token-backed image/video/audio + real virality predictor) and the
  live `MetaAdLibraryClient` — both deferred until credentials/endpoints are wired and verified.
- **Thin local dashboard** (FastAPI + Jinja/HTMX) over the same services: board, calendar,
  review/compliance UI.
- **Meta Ads module** (Custom Audience seeds, interest topic-stacks, Spark Ads) and the
  **Content DB + Calendar** scheduling layer (posting windows, trending-audio timers).

---

## Self-Review

**1. Spec coverage:**
- Spec §4.5 FTC dual disclosure → `check_ai_disclosure` + `check_commercial_disclosure` (Task 2), enforced on `→ ready` (Task 3). `#ad`-alone insufficiency is encoded: the AI disclosure is a separate required check.
- §4.5 persistent AI label → `check_ai_label` + the `ai_label_on_content` field; the export bakes the overlay instruction (`AI_LABEL_NOTE`) into the pack (Tasks 2/5).
- §4.5 no AI testimonials / before-after / fabricated efficacy / "anti-aging" → `check_no_prohibited_claims` + `PROHIBITED_PATTERNS` (Task 2).
- §4.5 substantiate claims → `check_substantiation` (Task 2).
- §5.2 module 6 Compliance Gate (blocks `ready`, bakes disclosures into export) → Task 3 gate + Task 5 export.
- §5.2 module 8 Human-in-the-Loop Publisher (export pack: video + disclosed caption + hashtags + overlay notes, manual upload) → Tasks 5/6.
- §5.3 data model `compliance_checks` → `ComplianceCheck` table (Task 1).
- Deferred (live clients, dashboard, Meta Ads, calendar) explicitly listed under "Subsequent plans", consistent with the §9 deferral pattern.

**2. Placeholder scan:** No TBD/TODO in shipped behaviour. Every code step shows complete, runnable code; every run step has an exact command and expected count. The `—` characters in echo/markdown are literal output, not placeholders.

**3. Type consistency:** `CheckResult(name, passed, detail)` is used identically in Tasks 2–4. `evaluate(item)` returns the five checks in the order asserted by `test_evaluate_returns_all_five_checks_in_order` and surfaced by `record_checks`. `ComplianceCheck` columns (`content_item_id`, `check`, `passed`, `detail`, `created_at`) match across Task 1 (model), Task 3 (service writes), and Task 4 (CLI reads). `ContentItem` compliance fields (`caption`, `is_sponsored`, `ai_label_on_content`, `substantiation_url`) match across Task 1 (model), Task 2 (`evaluate`), Task 4 (`set_content_fields`), Task 5 (`export_pack`). `compliance.assert_compliant(session, item_id)` / `record_checks(session, item_id)` / `list_checks(session, item_id)` signatures match their callers in `service.advance_content` and the CLI. `publish.export_pack(session, item_id, out_dir=None)` matches the CLI call and tests.
