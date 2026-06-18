# AQUEN Research + Ideation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the competitor-research → hook → ideation pipeline to the AQUEN toolkit: a compliant competitor ad-research module (behind a swappable adapter), deterministic hook derivation from competitor ad archetypes, an anti-plagiarism originality gate, and CLI commands to manage a competitor watch-list, run research, list hooks, and turn a hook into a scripted content item.

**Architecture:** Builds on the Plan 1 foundation (config/states/db/models/service/cli). New persistence models (`Competitor`, `AdInsight`, `Hook`) plus a `script` field on `ContentItem`. A `MetaAdLibraryClient` Protocol with an offline `FakeMetaAdLibraryClient` and a bundled `SampleMetaAdLibraryClient` keeps everything testable with zero network. Pure-logic `analysis.py` does archetype classification, house-hook templating (never copies competitor words), and an n-gram/Jaccard originality check. A `research.py` service orchestrates competitors → ads → hooks → ideation. CLI extends the existing Typer app.

**Tech Stack:** Python 3.11+, Typer, SQLModel/SQLite, pytest. No new dependencies.

**Compliance note (baked in):** This module only ever consumes *public* ad data through an adapter and derives *original* house hooks (it never stores or emits competitor copy as our content). The originality gate blocks any script that is too close to a source ad. There is NO scraping of follower lists, NO bots — out of scope by design.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/aquen/models.py` | (modify) add `script` to `ContentItem`; add `Competitor`, `AdInsight`, `Hook` |
| `src/aquen/adapters.py` | (create) `AdRecord`, `MetaAdLibraryClient` Protocol, `FakeMetaAdLibraryClient`, `SAMPLE_ADS`, `SampleMetaAdLibraryClient` |
| `src/aquen/analysis.py` | (create) archetype classify, topic extract, `derive_hook`, `check_originality`, `OriginalityError` |
| `src/aquen/research.py` | (create) competitor + research + hook-listing + `ideate` services |
| `src/aquen/cli.py` | (modify) add `competitor`, `research`, `hooks`, `ideate` commands |
| `tests/test_research_models.py` | (create) new model tests |
| `tests/test_adapters.py` | (create) adapter tests |
| `tests/test_analysis.py` | (create) analysis/originality tests |
| `tests/test_research_service.py` | (create) research + ideation service tests |
| `tests/test_cli_research.py` | (create) CLI tests for the new commands |

---

## Task 1: Research models + ContentItem.script

**Files:**
- Modify: `src/aquen/models.py`
- Test: `tests/test_research_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_research_models.py`:

```python
from aquen.models import AdInsight, Competitor, ContentItem, Hook
from aquen.states import ContentState


def test_competitor_roundtrip(session):
    c = Competitor(handle="rivalskin", platform="meta", note="watch")
    session.add(c)
    session.commit()
    session.refresh(c)
    assert c.id is not None
    assert c.platform == "meta"
    assert c.created_at is not None


def test_ad_insight_roundtrip(session):
    a = AdInsight(
        competitor_handle="rivalskin",
        ad_archive_id="AD123",
        ad_text="Stop believing this hydration myth.",
        page_name="RivalSkin",
        source_url="https://example.com/ad/123",
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    assert a.id is not None


def test_hook_roundtrip(session):
    h = Hook(
        text="The one hydration step almost everyone skips.",
        archetype="curiosity",
        topic="hydration",
        source_ad_archive_id="AD123",
        source_ad_text="Stop believing this hydration myth.",
    )
    session.add(h)
    session.commit()
    session.refresh(h)
    assert h.id is not None


def test_content_item_has_optional_script(session):
    item = ContentItem(title="x", pillar="derma_decode", script="Hello barrier.")
    session.add(item)
    session.commit()
    session.refresh(item)
    assert item.script == "Hello barrier."
    assert item.state == ContentState.IDEA
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_research_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'Competitor'` (and `script` not yet a field).

- [ ] **Step 3: Replace the ENTIRE contents of `src/aquen/models.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel

from aquen.states import ContentState


def utcnow() -> datetime:
    """Return the current UTC time as a tz-naive datetime.

    Convention: every datetime stored by AQUEN is UTC and tz-naive. SQLite has no
    timezone support and would silently drop an offset, so we standardize on naive
    UTC to keep writes and reads loss-free and to avoid mixing aware/naive datetimes
    in comparisons.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ContentItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    pillar: str
    hook_archetype: str | None = None
    # Note: SQLAlchemy persists this str-enum by member NAME (e.g. "SCRIPTED"); it
    # round-trips correctly through the ORM. Use ContentState(...) / .value at the
    # edges rather than matching the lowercase value in raw SQL.
    state: ContentState = Field(default=ContentState.IDEA)
    source_inspiration_url: str | None = None
    script: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Competitor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    handle: str = Field(index=True, unique=True)
    platform: str = "meta"
    note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class AdInsight(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    competitor_handle: str = Field(index=True)
    ad_archive_id: str = Field(index=True)
    ad_text: str
    page_name: str | None = None
    source_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Hook(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    text: str
    archetype: str
    topic: str = "skincare"
    source_inspiration_url: str | None = None
    source_ad_archive_id: str | None = None
    source_ad_text: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_research_models.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: PASS (all previous tests still green + the 4 new = 20 passed).

> Note: `create_all` only creates missing tables/columns on a fresh DB; it does NOT
> ALTER an existing `aquen.sqlite`. Delete a stale dev `aquen.sqlite` (it is gitignored)
> if the new `script` column is missing. A real migration tool (Alembic) is a later plan.

- [ ] **Step 6: Commit**

```bash
git add src/aquen/models.py tests/test_research_models.py
git commit -m "feat: add research models and ContentItem.script"
```

---

## Task 2: Meta Ad Library adapter

**Files:**
- Create: `src/aquen/adapters.py`
- Test: `tests/test_adapters.py`

- [ ] **Step 1: Write the failing test**

`tests/test_adapters.py`:

```python
from aquen.adapters import (
    AdRecord,
    FakeMetaAdLibraryClient,
    SampleMetaAdLibraryClient,
    SAMPLE_ADS,
)


def test_fake_client_returns_seeded_records():
    rec = AdRecord(ad_archive_id="A1", page_name="Riv", ad_text="hi", url=None)
    client = FakeMetaAdLibraryClient({"riv": [rec]})
    assert client.search("riv") == [rec]
    assert client.search("unknown") == []


def test_fake_client_respects_limit():
    recs = [AdRecord(ad_archive_id=f"A{i}", page_name="p", ad_text="t") for i in range(5)]
    client = FakeMetaAdLibraryClient({"riv": recs})
    assert len(client.search("riv", limit=2)) == 2


def test_sample_client_returns_samples_for_any_handle():
    client = SampleMetaAdLibraryClient()
    out = client.search("anything", limit=3)
    assert len(out) == 3
    assert all(isinstance(r, AdRecord) for r in out)
    assert len(SAMPLE_ADS) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_adapters.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.adapters'`.

- [ ] **Step 3: Write `src/aquen/adapters.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AdRecord:
    ad_archive_id: str
    page_name: str
    ad_text: str
    url: str | None = None


class MetaAdLibraryClient(Protocol):
    """Compliant, public-only competitor ad source. Implementations must use official
    APIs / public data only — never scraped follower or customer lists."""

    def search(self, handle: str, limit: int = 10) -> list[AdRecord]: ...


class FakeMetaAdLibraryClient:
    """Deterministic dict-backed client for tests and offline development."""

    def __init__(self, data: dict[str, list[AdRecord]] | None = None) -> None:
        self._data = data or {}

    def search(self, handle: str, limit: int = 10) -> list[AdRecord]:
        return list(self._data.get(handle, []))[:limit]


# Bundled sample ad copy (original, generic) so `aquen research` is demonstrable offline
# without a Meta token. Replace with a live MetaAdLibraryClient when a token is configured.
SAMPLE_ADS: list[AdRecord] = [
    AdRecord("SAMPLE1", "GlowRival", "Stop believing this hydration myth — your barrier needs more than water."),
    AdRecord("SAMPLE2", "DermLab", "Dermatologist-tested: clinically proven to strengthen the skin barrier in 4 weeks."),
    AdRecord("SAMPLE3", "SkinSimple", "5 skincare swaps that finally cleared my dull, tired skin."),
    AdRecord("SAMPLE4", "BarrierCo", "I tracked my skin for 4 weeks — the before and after shocked me."),
    AdRecord("SAMPLE5", "AquaTrend", "The one niacinamide step almost everyone skips."),
]


class SampleMetaAdLibraryClient:
    """Returns the bundled SAMPLE_ADS for any handle. Used as the CLI default until a
    live MetaAdLibraryClient (token-backed) is wired in."""

    def search(self, handle: str, limit: int = 10) -> list[AdRecord]:
        return list(SAMPLE_ADS)[:limit]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_adapters.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/adapters.py tests/test_adapters.py
git commit -m "feat: add Meta Ad Library adapter (interface + fake + sample)"
```

---

## Task 3: Analysis — hook derivation + originality gate

**Files:**
- Create: `src/aquen/analysis.py`
- Test: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing test**

`tests/test_analysis.py`:

```python
import pytest

from aquen.analysis import (
    OriginalityError,
    check_originality,
    classify_archetype,
    derive_hook,
    extract_topic,
)


def test_classify_archetype():
    assert classify_archetype("Stop believing this myth") == "myth_bust"
    assert classify_archetype("5 swaps that changed my skin") == "listicle"
    assert classify_archetype("My before and after after 4 weeks") == "transformation"
    assert classify_archetype("Dermatologist-tested and clinically proven") == "authority"
    assert classify_archetype("A calm everyday glow") == "curiosity"


def test_extract_topic_prefers_known_ingredient():
    assert extract_topic("more niacinamide for your barrier") == "niacinamide"
    assert extract_topic("just a nice glow") == "skincare"


def test_derive_hook_uses_house_template_not_source_words():
    text, archetype, topic = derive_hook("Stop believing this niacinamide myth!!!")
    assert archetype == "myth_bust"
    assert topic == "niacinamide"
    # House template, original phrasing — does NOT copy the source verbatim
    assert "Stop believing this niacinamide myth" not in text
    assert "niacinamide" in text


def test_check_originality_passes_for_distinct_text():
    ok, reason = check_originality(
        "Stop believing this hydration myth your barrier needs oil",
        "Here is a totally different script about ceramides and calm routines",
    )
    assert ok is True


def test_check_originality_fails_on_verbatim_phrase():
    src = "your skin barrier needs more than water to stay healthy and strong"
    ok, reason = check_originality(src, "honestly your skin barrier needs more than water friends")
    assert ok is False
    assert "verbatim" in reason


def test_check_originality_fails_on_high_overlap():
    src = "barrier repair hydration glow serum routine niacinamide ceramide dewy skin"
    cand = "barrier repair hydration glow serum routine niacinamide ceramide dewy skin today"
    ok, reason = check_originality(src, cand)
    assert ok is False


def test_originality_error_is_exception():
    assert issubclass(OriginalityError, Exception)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.analysis'`.

- [ ] **Step 3: Write `src/aquen/analysis.py`**

```python
from __future__ import annotations

import re

KNOWN_TOPICS = [
    "beta-glucan",
    "niacinamide",
    "retinol",
    "vitamin c",
    "hyaluronic acid",
    "ceramide",
    "peptide",
    "spf",
    "postbiotic",
    "exosome",
    "hydration",
    "barrier",
]

HOOK_TEMPLATES = {
    "myth_bust": "Stop and rethink: the {topic} 'rule' you were sold is wrong — here's what actually helps.",
    "listicle": "{n} small {topic} swaps that quietly upgraded my skin barrier.",
    "transformation": "I logged my skin for {weeks} weeks with {topic} — here's the honest timeline.",
    "authority": "Here's what the research actually says about {topic} (no hype).",
    "curiosity": "The one {topic} step almost everyone skips.",
}


class OriginalityError(Exception):
    pass


def classify_archetype(ad_text: str) -> str:
    t = ad_text.lower()
    if any(k in t for k in ["myth", "lie", "stop believing", "don't", "do not"]):
        return "myth_bust"
    if re.search(r"\b\d+\s+(ways|steps|things|tips|swaps|reasons)\b", t):
        return "listicle"
    if any(k in t for k in ["before and after", "before/after", "weeks", "results", "transformation"]):
        return "transformation"
    if any(k in t for k in ["dermatologist", "clinically", "science", "study", "proven", "tested"]):
        return "authority"
    return "curiosity"


def extract_topic(ad_text: str) -> str:
    t = ad_text.lower()
    for topic in KNOWN_TOPICS:
        if topic in t:
            return topic
    return "skincare"


def derive_hook(ad_text: str) -> tuple[str, str, str]:
    """Return (house_hook_text, archetype, topic). The hook is an ORIGINAL AQUEN house
    template filled with the inferred topic — it never reuses the source ad's wording."""
    archetype = classify_archetype(ad_text)
    topic = extract_topic(ad_text)
    template = HOOK_TEMPLATES[archetype]
    text = template.format(topic=topic, n=5, weeks=4)
    return text, archetype, topic


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def check_originality(
    source_text: str,
    candidate_text: str,
    n: int = 5,
    jaccard_threshold: float = 0.6,
) -> tuple[bool, str]:
    """Guard against plagiarism: reject a candidate script that shares a long verbatim
    phrase with the source ad, or whose word-set overlaps too heavily."""
    src = _words(source_text)
    cand = _words(candidate_text)
    if _ngrams(src, n) & _ngrams(cand, n):
        return False, f"shares a {n}-word verbatim phrase with the source"
    src_set, cand_set = set(src), set(cand)
    if src_set and cand_set:
        jaccard = len(src_set & cand_set) / len(src_set | cand_set)
        if jaccard >= jaccard_threshold:
            return False, f"word overlap {jaccard:.0%} exceeds the {jaccard_threshold:.0%} limit"
    return True, "original"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/analysis.py tests/test_analysis.py
git commit -m "feat: add hook derivation and anti-plagiarism originality gate"
```

---

## Task 4: Research service (competitors → ads → hooks) + ideation

**Files:**
- Create: `src/aquen/research.py`
- Test: `tests/test_research_service.py`

- [ ] **Step 1: Write the failing test**

`tests/test_research_service.py`:

```python
import pytest

from aquen import research
from aquen.adapters import AdRecord, FakeMetaAdLibraryClient
from aquen.analysis import OriginalityError
from aquen.states import ContentState


def test_add_and_list_competitors(session):
    research.add_competitor(session, "rivalskin", note="main rival")
    research.add_competitor(session, "glowco")
    handles = [c.handle for c in research.list_competitors(session)]
    assert handles == ["rivalskin", "glowco"]


def test_run_research_stores_ads_and_hooks(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "Stop believing this niacinamide myth.")]}
    )
    counts = research.run_research(session, client, limit=10)
    assert counts == {"ads": 1, "hooks": 1}

    hooks = research.list_hooks(session)
    assert len(hooks) == 1
    assert hooks[0].archetype == "myth_bust"
    assert hooks[0].topic == "niacinamide"
    assert hooks[0].source_ad_archive_id == "AD1"


def test_run_research_dedupes_ads(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "Dermatologist tested formula.")]}
    )
    research.run_research(session, client)
    counts = research.run_research(session, client)  # same ad again
    assert counts["ads"] == 0  # already stored


def test_ideate_creates_scripted_item(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "The one niacinamide step everyone skips.")]}
    )
    research.run_research(session, client)
    hook = research.list_hooks(session)[0]

    item = research.ideate(
        session,
        hook.id,
        pillar="derma_decode",
        script="Today let's talk about why a calm, simple barrier routine beats chasing trends.",
    )
    assert item.state == ContentState.SCRIPTED
    assert item.pillar == "derma_decode"
    assert item.hook_archetype == hook.archetype
    assert item.script is not None


def test_ideate_blocks_plagiarised_script(session):
    research.add_competitor(session, "rivalskin")
    client = FakeMetaAdLibraryClient(
        {"rivalskin": [AdRecord("AD1", "Rival", "The one niacinamide step almost everyone skips today friends")]}
    )
    research.run_research(session, client)
    hook = research.list_hooks(session)[0]

    with pytest.raises(OriginalityError):
        research.ideate(
            session,
            hook.id,
            pillar="derma_decode",
            script="The one niacinamide step almost everyone skips today friends",
        )


def test_ideate_missing_hook_raises(session):
    with pytest.raises(ValueError):
        research.ideate(session, 999, pillar="derma_decode", script="hi")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_research_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'aquen.research'`.

- [ ] **Step 3: Write `src/aquen/research.py`**

```python
from __future__ import annotations

from sqlmodel import Session, select

from aquen.adapters import MetaAdLibraryClient
from aquen.analysis import OriginalityError, check_originality, derive_hook
from aquen.models import AdInsight, Competitor, ContentItem, Hook
from aquen.states import ContentState


def add_competitor(
    session: Session, handle: str, platform: str = "meta", note: str | None = None
) -> Competitor:
    competitor = Competitor(handle=handle, platform=platform, note=note)
    session.add(competitor)
    session.commit()
    session.refresh(competitor)
    return competitor


def list_competitors(session: Session) -> list[Competitor]:
    return list(session.exec(select(Competitor).order_by(Competitor.id)))


def list_hooks(session: Session) -> list[Hook]:
    return list(session.exec(select(Hook).order_by(Hook.id)))


def _ad_exists(session: Session, ad_archive_id: str) -> bool:
    stmt = select(AdInsight).where(AdInsight.ad_archive_id == ad_archive_id)
    return session.exec(stmt).first() is not None


def run_research(
    session: Session, client: MetaAdLibraryClient, limit: int = 10
) -> dict[str, int]:
    """For every competitor in the watch-list, pull public ads via the client, store new
    AdInsights, and derive one ORIGINAL house Hook per new ad. Returns counts."""
    ads_added = 0
    hooks_added = 0
    for competitor in list_competitors(session):
        for record in client.search(competitor.handle, limit=limit):
            if _ad_exists(session, record.ad_archive_id):
                continue
            session.add(
                AdInsight(
                    competitor_handle=competitor.handle,
                    ad_archive_id=record.ad_archive_id,
                    ad_text=record.ad_text,
                    page_name=record.page_name,
                    source_url=record.url,
                )
            )
            text, archetype, topic = derive_hook(record.ad_text)
            session.add(
                Hook(
                    text=text,
                    archetype=archetype,
                    topic=topic,
                    source_inspiration_url=record.url,
                    source_ad_archive_id=record.ad_archive_id,
                    source_ad_text=record.ad_text,
                )
            )
            ads_added += 1
            hooks_added += 1
    session.commit()
    return {"ads": ads_added, "hooks": hooks_added}


def ideate(
    session: Session, hook_id: int, pillar: str, script: str
) -> ContentItem:
    """Turn a hook into a SCRIPTED ContentItem, enforcing the anti-plagiarism gate against
    the source ad text."""
    hook = session.get(Hook, hook_id)
    if hook is None:
        raise ValueError(f"hook {hook_id} not found")

    if hook.source_ad_text:
        ok, reason = check_originality(hook.source_ad_text, script)
        if not ok:
            raise OriginalityError(f"script rejected: {reason}")

    item = ContentItem(
        title=hook.text[:80],
        pillar=pillar,
        hook_archetype=hook.archetype,
        state=ContentState.SCRIPTED,
        source_inspiration_url=hook.source_inspiration_url,
        script=script,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_research_service.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/aquen/research.py tests/test_research_service.py
git commit -m "feat: add research + ideation services with originality gate"
```

---

## Task 5: CLI commands for research + ideation

**Files:**
- Modify: `src/aquen/cli.py`
- Test: `tests/test_cli_research.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli_research.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_competitor_add_and_list(tmp_path):
    env = _env(tmp_path)
    add = runner.invoke(app, ["competitor", "add", "rivalskin"], env=env)
    assert add.exit_code == 0, add.stdout
    listed = runner.invoke(app, ["competitor", "list"], env=env)
    assert "rivalskin" in listed.stdout


def test_research_then_hooks(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["competitor", "add", "rivalskin"], env=env)
    res = runner.invoke(app, ["research"], env=env)
    assert res.exit_code == 0, res.stdout
    assert "hooks" in res.stdout.lower()

    hooks = runner.invoke(app, ["hooks", "list"], env=env)
    assert hooks.exit_code == 0
    # at least one of the sample-derived archetypes shows up
    assert "#" in hooks.stdout


def test_ideate_command(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["competitor", "add", "rivalskin"], env=env)
    runner.invoke(app, ["research"], env=env)
    item = runner.invoke(
        app,
        [
            "ideate",
            "1",
            "--pillar",
            "derma_decode",
            "--script",
            "A calm, simple barrier-first routine beats chasing every new trend.",
        ],
        env=env,
    )
    assert item.exit_code == 0, item.stdout
    assert "scripted" in item.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_research.py -v`
Expected: FAIL — the `competitor` / `research` / `hooks` / `ideate` commands do not exist yet (exit_code != 0 / NoSuchCommand).

- [ ] **Step 3: Append to `src/aquen/cli.py`**

Add this import near the top (after the existing imports):

```python
from aquen import research
from aquen.adapters import SampleMetaAdLibraryClient
from aquen.analysis import OriginalityError
```

Add a new sub-app registration after the existing `app.add_typer(content_app, name="content")` line:

```python
competitor_app = typer.Typer(help="Manage the competitor watch-list", no_args_is_help=True)
app.add_typer(competitor_app, name="competitor")
hooks_app = typer.Typer(help="Browse derived hooks", no_args_is_help=True)
app.add_typer(hooks_app, name="hooks")
```

Append these commands to the end of the file:

```python
@competitor_app.command("add")
def competitor_add(
    handle: str,
    platform: str = typer.Option("meta", help="meta / tiktok / instagram"),
    note: str = typer.Option(None, help="Optional note"),
) -> None:
    with _session_scope() as sess:
        c = research.add_competitor(sess, handle, platform=platform, note=note)
        typer.echo(f"#{c.id} {c.handle} ({c.platform})")


@competitor_app.command("list")
def competitor_list() -> None:
    with _session_scope() as sess:
        for c in research.list_competitors(sess):
            typer.echo(f"#{c.id} {c.handle} ({c.platform})")


@app.command()
def research_cmd(
    limit: int = typer.Option(10, help="Max ads per competitor"),
) -> None:
    """Pull public competitor ads (sample data until a Meta token is configured) and
    derive original house hooks."""
    client = SampleMetaAdLibraryClient()
    with _session_scope() as sess:
        counts = research.run_research(sess, client, limit=limit)
        typer.echo(f"ads: {counts['ads']}, hooks: {counts['hooks']}")


@hooks_app.command("list")
def hooks_list() -> None:
    with _session_scope() as sess:
        for h in research.list_hooks(sess):
            typer.echo(f"#{h.id} [{h.archetype}/{h.topic}] {h.text}")


@app.command()
def ideate(
    hook_id: int,
    pillar: str = typer.Option(..., help="Content pillar"),
    script: str = typer.Option(..., help="Your original script in Mira's voice"),
) -> None:
    """Turn a hook into a scripted content item (blocked if the script copies the source)."""
    with _session_scope() as sess:
        try:
            item = research.ideate(sess, hook_id, pillar=pillar, script=script)
        except OriginalityError as exc:
            typer.echo(f"Rejected: {exc}", err=True)
            raise typer.Exit(1)
        typer.echo(f"#{item.id} [{item.state.value}] {item.title} ({item.pillar})")
```

> Note: the `research` command function is named `research_cmd` to avoid shadowing the
> imported `research` module, but Typer registers it under the CLI name `research`
> (Typer converts the function name; to be explicit the decorator name is set below).

Change the `research_cmd` decorator line from `@app.command()` to:

```python
@app.command("research")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_research.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: PASS (all green — Plan 1 + Plan 2 tests).

- [ ] **Step 6: Manual smoke check**

Run (PowerShell):
```powershell
.\.venv\Scripts\aquen.exe competitor add rivalskin
.\.venv\Scripts\aquen.exe research
.\.venv\Scripts\aquen.exe hooks list
.\.venv\Scripts\aquen.exe ideate 1 --pillar derma_decode --script "A calm barrier-first routine beats chasing trends."
```
Expected: a competitor line, an `ads: N, hooks: N` line, a list of `#id [archetype/topic] ...` hooks, then a `#1 [scripted] ...` content item. (If `aquen.sqlite` has a stale schema, delete it first — it is gitignored.)

- [ ] **Step 7: Commit**

```bash
git add src/aquen/cli.py tests/test_cli_research.py
git commit -m "feat: add competitor/research/hooks/ideate CLI commands"
```

---

## Subsequent plans (unchanged)

- **Plan 3 — Higgsfield Creative Engine + Virality gate** (adapters for image/video/audio +
  the trained Mira Soul `83c0591d` / Element `Mira-1` `1972c3b9`, virality pre-screen).
- **Plan 4 — Compliance gate + Publisher export.**
- **Plan 5 — Sample production runbook** (largely done ad-hoc: Mira Soul trained, clean
  still pipeline, first sample reel — to be folded into the toolkit).

Deferred (per spec §9): Meta Ads / paid module (incl. the live token-backed
`MetaAdLibraryClient`), web dashboard, AI skin-analysis quiz, own-SKU launch.

---

## Self-Review

**1. Spec coverage:** Implements spec §5.2 module 1 (Research — compliant, public-only, no
scraping) and module 2 (Ideation + the anti-plagiarism remix SOP from §4.3) plus the
`Competitor`/`AdInsight`/`Hook` slice of the §5.3 data model and the `script` content field.
The live Meta token client is explicitly deferred (sample client ships now), consistent with
the §9 "paid module deferred" decision.

**2. Placeholder scan:** No TBD/TODO; every code step is complete and runnable; every run step
has an exact command + expected result. `SampleMetaAdLibraryClient` is a deliberate, working
stand-in (documented), not a placeholder.

**3. Type consistency:** `AdRecord` fields, `MetaAdLibraryClient.search` signature,
`derive_hook` returning `(text, archetype, topic)`, `check_originality` returning
`(bool, str)`, and `research.add_competitor/list_competitors/list_hooks/run_research/ideate`
signatures match across Tasks 2–5 and their tests. `ContentState.SCRIPTED` and the
`ContentItem(... state=..., script=...)` constructor match the Task 1 model.
