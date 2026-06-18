# AQUEN Content Calendar + Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the AQUEN content calendar — schedule content items into posting-window slots across lanes, attach trending-audio with a shelf-life timer, and query the upcoming queue and expiring audio.

**Architecture:** Builds on Plans 1–4. Mirrors the existing `analysis.py`/`compliance.py` split: pure scheduling rules (posting windows, audio freshness) live in `scheduling.py` with no DB, a thin service layer persists slots to a new `CalendarSlot` table, and a Typer `calendar` sub-app wraps it. No new dependencies, fully offline-testable. Datetimes follow the project convention (tz-naive; the user schedules in their own planning timezone and the clock hour drives the posting-window check).

**Tech Stack:** Python 3.11+, Typer, SQLModel/SQLite, pytest. No new dependencies.

**Spec coverage:** §5.2 module 5 (Content DB + Calendar — 3-lane calendar, posting windows 12–2pm / 7–9pm, trending-audio shelf-life timers, asset links) and the §5.3 `calendar_slots` table. Scheduling is a planning step and is intentionally **not** gated on content state — the publisher already gates `ready`.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/aquen/models.py` | (modify) add `CalendarSlot` table |
| `src/aquen/scheduling.py` | (create) `POSTING_WINDOWS`, `window_for`/`in_posting_window`/`audio_is_fresh`, `SchedulingError`, + service (`schedule_content`, `reschedule_content`, `unschedule`, `list_calendar`, `upcoming`, `expiring_audio`) |
| `src/aquen/cli.py` | (modify) add `calendar` sub-app (`schedule`/`list`/`reschedule`/`unschedule`/`upcoming`/`audio-check`) |
| `tests/test_calendar_foundation.py` | (create) model tests |
| `tests/test_scheduling_logic.py` | (create) pure-logic tests |
| `tests/test_scheduling_service.py` | (create) service tests |
| `tests/test_cli_calendar.py` | (create) CLI tests |

**Baseline:** the suite is at **101 passing** before this plan.

---

## Task 1: CalendarSlot model

**Files:**
- Modify: `src/aquen/models.py`
- Test: `tests/test_calendar_foundation.py`

- [ ] **Step 1: Write the failing test** — `tests/test_calendar_foundation.py`:

```python
from datetime import datetime

from aquen.models import CalendarSlot


def test_calendar_slot_defaults(session):
    slot = CalendarSlot(
        content_item_id=1,
        scheduled_for=datetime(2026, 7, 1, 13, 0),
        lane="derma_decode",
        window="midday",
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    assert slot.id is not None
    assert slot.trending_audio is None
    assert slot.audio_expires_at is None
    assert slot.note is None
    assert slot.created_at is not None


def test_calendar_slot_with_audio_roundtrip(session):
    slot = CalendarSlot(
        content_item_id=2,
        scheduled_for=datetime(2026, 7, 1, 20, 0),
        lane="myth_bust",
        window="evening",
        trending_audio="trend-123",
        audio_expires_at=datetime(2026, 7, 3, 20, 0),
        note="pair with hook #4",
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    assert slot.trending_audio == "trend-123"
    assert slot.audio_expires_at == datetime(2026, 7, 3, 20, 0)
    assert slot.note == "pair with hook #4"
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_calendar_foundation.py -v` — Expected: FAIL (`cannot import name 'CalendarSlot'`).

- [ ] **Step 3: Append the `CalendarSlot` class to the END of `src/aquen/models.py`**:

```python


class CalendarSlot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content_item_id: int = Field(index=True)
    scheduled_for: datetime = Field(index=True)
    lane: str
    window: str  # midday | evening
    trending_audio: str | None = None
    audio_expires_at: datetime | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_calendar_foundation.py -v` — Expected: PASS (2 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (103 passed: 101 + 2).

- [ ] **Step 6: Commit** — `git add src/aquen/models.py tests/test_calendar_foundation.py && git commit -m "feat: add CalendarSlot model"`

---

## Task 2: Scheduling pure logic

**Files:**
- Create: `src/aquen/scheduling.py`
- Test: `tests/test_scheduling_logic.py`

- [ ] **Step 1: Write the failing test** — `tests/test_scheduling_logic.py`:

```python
from datetime import datetime

from aquen.models import CalendarSlot
from aquen.scheduling import audio_is_fresh, in_posting_window, window_for


def test_window_for_midday():
    assert window_for(datetime(2026, 7, 1, 13, 0)) == "midday"


def test_window_for_evening():
    assert window_for(datetime(2026, 7, 1, 20, 30)) == "evening"


def test_window_for_outside_returns_none():
    assert window_for(datetime(2026, 7, 1, 9, 0)) is None


def test_in_posting_window():
    assert in_posting_window(datetime(2026, 7, 1, 12, 0)) is True
    assert in_posting_window(datetime(2026, 7, 1, 15, 0)) is False


def test_audio_is_fresh_when_no_expiry():
    slot = CalendarSlot(content_item_id=1, scheduled_for=datetime(2026, 7, 1, 13, 0), lane="x", window="midday")
    assert audio_is_fresh(slot, datetime(2026, 7, 1, 13, 0)) is True


def test_audio_freshness_respects_expiry():
    slot = CalendarSlot(
        content_item_id=1,
        scheduled_for=datetime(2026, 7, 1, 13, 0),
        lane="x",
        window="midday",
        audio_expires_at=datetime(2026, 7, 2, 13, 0),
    )
    assert audio_is_fresh(slot, datetime(2026, 7, 1, 18, 0)) is True
    assert audio_is_fresh(slot, datetime(2026, 7, 3, 0, 0)) is False
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scheduling_logic.py -v` — Expected: FAIL (`No module named 'aquen.scheduling'`).

- [ ] **Step 3: Write `src/aquen/scheduling.py`** (pure logic; the service is added in Task 3):

```python
from __future__ import annotations

from datetime import datetime

from aquen.models import CalendarSlot

# Posting windows by clock hour (half-open [start, end)): midday 12:00–14:00, evening 19:00–21:00.
POSTING_WINDOWS: dict[str, tuple[int, int]] = {
    "midday": (12, 14),
    "evening": (19, 21),
}


class SchedulingError(Exception):
    pass


def window_for(dt: datetime) -> str | None:
    """Return the posting-window name a datetime falls in, or None if outside every window."""
    for name, (start, end) in POSTING_WINDOWS.items():
        if start <= dt.hour < end:
            return name
    return None


def in_posting_window(dt: datetime) -> bool:
    return window_for(dt) is not None


def audio_is_fresh(slot: CalendarSlot, now: datetime) -> bool:
    """A slot's trending audio is fresh until its shelf-life timer (audio_expires_at) elapses."""
    if slot.audio_expires_at is None:
        return True
    return now < slot.audio_expires_at
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scheduling_logic.py -v` — Expected: PASS (6 passed).

- [ ] **Step 5: Commit** — `git add src/aquen/scheduling.py tests/test_scheduling_logic.py && git commit -m "feat: add scheduling pure logic (posting windows, audio freshness)"`

---

## Task 3: Scheduling service

**Files:**
- Modify: `src/aquen/scheduling.py`
- Test: `tests/test_scheduling_service.py`

- [ ] **Step 1: Write the failing test** — `tests/test_scheduling_service.py`:

```python
from datetime import datetime

import pytest

from aquen import scheduling
from aquen.models import ContentItem
from aquen.scheduling import SchedulingError


def _item(session, pillar="derma_decode") -> ContentItem:
    item = ContentItem(title="Beta-glucan 101", pillar=pillar)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_schedule_derives_window_and_defaults_lane_to_pillar(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    assert slot.id is not None
    assert slot.window == "midday"
    assert slot.lane == "derma_decode"


def test_schedule_lane_override(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 20, 0), lane="myth_bust")
    assert slot.lane == "myth_bust"
    assert slot.window == "evening"


def test_schedule_outside_window_raises(session):
    item = _item(session)
    with pytest.raises(SchedulingError):
        scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 9, 0))


def test_schedule_missing_item_raises(session):
    with pytest.raises(ValueError):
        scheduling.schedule_content(session, 999, datetime(2026, 7, 1, 13, 0))


def test_schedule_double_booking_raises(session):
    item = _item(session)
    scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    with pytest.raises(SchedulingError):
        scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 20, 0))


def test_schedule_sets_audio_expiry_from_ttl(session):
    item = _item(session)
    slot = scheduling.schedule_content(
        session, item.id, datetime(2026, 7, 1, 13, 0), trending_audio="trend-1", audio_ttl_hours=48
    )
    assert slot.trending_audio == "trend-1"
    assert slot.audio_expires_at == datetime(2026, 7, 3, 13, 0)


def test_reschedule_moves_and_revalidates_window(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    moved = scheduling.reschedule_content(session, slot.id, datetime(2026, 7, 2, 20, 0))
    assert moved.window == "evening"
    assert moved.scheduled_for == datetime(2026, 7, 2, 20, 0)


def test_reschedule_outside_window_raises(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    with pytest.raises(SchedulingError):
        scheduling.reschedule_content(session, slot.id, datetime(2026, 7, 2, 9, 0))


def test_reschedule_missing_raises(session):
    with pytest.raises(ValueError):
        scheduling.reschedule_content(session, 999, datetime(2026, 7, 2, 13, 0))


def test_unschedule_removes_slot(session):
    item = _item(session)
    slot = scheduling.schedule_content(session, item.id, datetime(2026, 7, 1, 13, 0))
    scheduling.unschedule(session, slot.id)
    assert scheduling.list_calendar(session) == []


def test_unschedule_missing_raises(session):
    with pytest.raises(ValueError):
        scheduling.unschedule(session, 999)


def test_list_calendar_orders_and_filters_by_lane(session):
    a = _item(session, pillar="derma_decode")
    b = _item(session, pillar="myth_bust")
    scheduling.schedule_content(session, b.id, datetime(2026, 7, 2, 20, 0), lane="myth_bust")
    scheduling.schedule_content(session, a.id, datetime(2026, 7, 1, 13, 0), lane="derma_decode")
    ordered = scheduling.list_calendar(session)
    assert [s.scheduled_for for s in ordered] == [datetime(2026, 7, 1, 13, 0), datetime(2026, 7, 2, 20, 0)]
    only = scheduling.list_calendar(session, lane="myth_bust")
    assert [s.lane for s in only] == ["myth_bust"]


def test_upcoming_returns_future_only_within_window(session):
    a = _item(session)
    b = _item(session)
    scheduling.schedule_content(session, a.id, datetime(2026, 7, 1, 13, 0))
    scheduling.schedule_content(session, b.id, datetime(2026, 7, 5, 20, 0))
    now = datetime(2026, 7, 2, 0, 0)
    assert [s.scheduled_for for s in scheduling.upcoming(session, now)] == [datetime(2026, 7, 5, 20, 0)]
    assert scheduling.upcoming(session, now, within_hours=24) == []


def test_expiring_audio_lists_expired_only(session):
    a = _item(session)
    b = _item(session)
    scheduling.schedule_content(session, a.id, datetime(2026, 7, 1, 13, 0), trending_audio="fresh", audio_ttl_hours=48)
    scheduling.schedule_content(session, b.id, datetime(2026, 7, 1, 20, 0), trending_audio="stale", audio_ttl_hours=1)
    now = datetime(2026, 7, 1, 23, 0)
    expired = scheduling.expiring_audio(session, now)
    assert [s.trending_audio for s in expired] == ["stale"]
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scheduling_service.py -v` — Expected: FAIL (`module 'aquen.scheduling' has no attribute 'schedule_content'`).

- [ ] **Step 3: Append the service layer to `src/aquen/scheduling.py`** — first extend the imports at the TOP of the file:

```python
from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, select

from aquen.models import CalendarSlot, ContentItem, utcnow
```

Then append to the END of the file:

```python
def schedule_content(
    session: Session,
    content_item_id: int,
    scheduled_for: datetime,
    *,
    lane: str | None = None,
    trending_audio: str | None = None,
    audio_ttl_hours: int | None = None,
    note: str | None = None,
) -> CalendarSlot:
    """Book a content item into a posting-window slot. The window is derived from the time;
    the lane defaults to the item's pillar. An item can hold only one slot (reschedule to move)."""
    item = session.get(ContentItem, content_item_id)
    if item is None:
        raise ValueError(f"content item {content_item_id} not found")
    window = window_for(scheduled_for)
    if window is None:
        raise SchedulingError(
            f"{scheduled_for:%H:%M} is outside the posting windows (midday 12–14, evening 19–21)"
        )
    existing = session.exec(
        select(CalendarSlot).where(CalendarSlot.content_item_id == content_item_id)
    ).first()
    if existing is not None:
        raise SchedulingError(
            f"content {content_item_id} is already scheduled (slot #{existing.id}); reschedule instead"
        )
    audio_expires_at = None
    if trending_audio and audio_ttl_hours:
        audio_expires_at = scheduled_for + timedelta(hours=audio_ttl_hours)
    slot = CalendarSlot(
        content_item_id=content_item_id,
        scheduled_for=scheduled_for,
        lane=lane or item.pillar,
        window=window,
        trending_audio=trending_audio,
        audio_expires_at=audio_expires_at,
        note=note,
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def reschedule_content(
    session: Session, slot_id: int, new_scheduled_for: datetime
) -> CalendarSlot:
    slot = session.get(CalendarSlot, slot_id)
    if slot is None:
        raise ValueError(f"calendar slot {slot_id} not found")
    window = window_for(new_scheduled_for)
    if window is None:
        raise SchedulingError(
            f"{new_scheduled_for:%H:%M} is outside the posting windows (midday 12–14, evening 19–21)"
        )
    slot.scheduled_for = new_scheduled_for
    slot.window = window
    slot.updated_at = utcnow()
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot


def unschedule(session: Session, slot_id: int) -> None:
    slot = session.get(CalendarSlot, slot_id)
    if slot is None:
        raise ValueError(f"calendar slot {slot_id} not found")
    session.delete(slot)
    session.commit()


def list_calendar(session: Session, lane: str | None = None) -> list[CalendarSlot]:
    stmt = select(CalendarSlot).order_by(CalendarSlot.scheduled_for)
    if lane is not None:
        stmt = stmt.where(CalendarSlot.lane == lane)
    return list(session.exec(stmt))


def upcoming(
    session: Session, now: datetime, within_hours: int | None = None
) -> list[CalendarSlot]:
    """Slots scheduled at/after `now`, ordered; optionally only those within `within_hours`."""
    slots = list(
        session.exec(
            select(CalendarSlot)
            .where(CalendarSlot.scheduled_for >= now)
            .order_by(CalendarSlot.scheduled_for)
        )
    )
    if within_hours is not None:
        cutoff = now + timedelta(hours=within_hours)
        slots = [s for s in slots if s.scheduled_for <= cutoff]
    return slots


def expiring_audio(session: Session, now: datetime) -> list[CalendarSlot]:
    """Slots whose trending-audio shelf-life timer has elapsed at `now`."""
    slots = session.exec(select(CalendarSlot).order_by(CalendarSlot.scheduled_for))
    return [
        s for s in slots if s.audio_expires_at is not None and s.audio_expires_at <= now
    ]
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_scheduling_service.py -v` — Expected: PASS (14 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (123 passed: 103 + 6 + 14).

- [ ] **Step 6: Commit** — `git add src/aquen/scheduling.py tests/test_scheduling_service.py && git commit -m "feat: add scheduling service (schedule/reschedule/list/upcoming/audio)"`

---

## Task 4: CLI `calendar` sub-app

**Files:**
- Modify: `src/aquen/cli.py`
- Test: `tests/test_cli_calendar.py`

- [ ] **Step 1: Write the failing test** — `tests/test_cli_calendar.py`:

```python
from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def _add_item(env: dict[str, str]) -> None:
    runner.invoke(app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env)


def test_schedule_then_list(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    out = runner.invoke(app, ["calendar", "schedule", "1", "2026-07-01T13:00"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "midday" in out.stdout
    listed = runner.invoke(app, ["calendar", "list"], env=env)
    assert "#1" in listed.stdout
    assert "derma_decode" in listed.stdout


def test_schedule_outside_window_errors(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    out = runner.invoke(app, ["calendar", "schedule", "1", "2026-07-01T09:00"], env=env)
    assert out.exit_code == 1
    assert "posting window" in (out.stdout + (out.stderr or "")).lower()


def test_schedule_bad_datetime_errors(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    out = runner.invoke(app, ["calendar", "schedule", "1", "not-a-date"], env=env)
    assert out.exit_code == 1


def test_reschedule_and_unschedule(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    runner.invoke(app, ["calendar", "schedule", "1", "2026-07-01T13:00"], env=env)
    moved = runner.invoke(app, ["calendar", "reschedule", "1", "2026-07-02T20:00"], env=env)
    assert moved.exit_code == 0, moved.stdout
    assert "evening" in moved.stdout
    removed = runner.invoke(app, ["calendar", "unschedule", "1"], env=env)
    assert removed.exit_code == 0
    assert runner.invoke(app, ["calendar", "list"], env=env).stdout.strip() == ""


def test_upcoming_and_audio_check_run(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    runner.invoke(
        app,
        ["calendar", "schedule", "1", "2026-07-01T20:00", "--audio", "trend-1", "--audio-ttl", "1"],
        env=env,
    )
    up = runner.invoke(app, ["calendar", "upcoming"], env=env)
    assert up.exit_code == 0
    audio = runner.invoke(app, ["calendar", "audio-check"], env=env)
    assert audio.exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_calendar.py -v` — Expected: FAIL (no `calendar` command).

- [ ] **Step 3: Modify `src/aquen/cli.py`** — four edits:

(a) Add `datetime` import near the top (after `import sys`):

```python
from datetime import datetime
```

(b) Add to the `aquen` imports block (alongside `from aquen import compliance, generation, publish, research, service`): change it to add `scheduling`, and add the `utcnow` import:

```python
from aquen import compliance, generation, publish, research, scheduling, service
from aquen.models import utcnow
```

(c) Register the `calendar` sub-app — add after the `app.add_typer(publish_app, name="publish")` line:

```python
calendar_app = typer.Typer(help="Schedule content across the posting calendar", no_args_is_help=True)
app.add_typer(calendar_app, name="calendar")
```

(d) Append the commands to the END of the file:

```python
def _parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        typer.echo(f"invalid datetime '{value}' (use ISO, e.g. 2026-07-01T13:00)", err=True)
        raise typer.Exit(1)


def _slot_line(s) -> str:
    audio = f" audio={s.trending_audio}" if s.trending_audio else ""
    return (
        f"#{s.id} {s.scheduled_for:%Y-%m-%d %H:%M} [{s.window}] {s.lane} "
        f"content=#{s.content_item_id}{audio}"
    )


@calendar_app.command("schedule")
def calendar_schedule(
    content_id: int,
    when: str,
    lane: str = typer.Option(None, help="Lane (defaults to the content item's pillar)"),
    audio: str = typer.Option(None, help="Trending audio id/name"),
    audio_ttl: int = typer.Option(None, help="Audio shelf-life in hours"),
    note: str = typer.Option(None, help="Optional note"),
) -> None:
    dt = _parse_dt(when)
    with _session_scope() as sess:
        try:
            slot = scheduling.schedule_content(
                sess, content_id, dt, lane=lane, trending_audio=audio,
                audio_ttl_hours=audio_ttl, note=note,
            )
        except (ValueError, scheduling.SchedulingError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(_slot_line(slot))


@calendar_app.command("list")
def calendar_list(
    lane: str = typer.Option(None, help="Filter by lane"),
) -> None:
    with _session_scope() as sess:
        for s in scheduling.list_calendar(sess, lane=lane):
            typer.echo(_slot_line(s))


@calendar_app.command("reschedule")
def calendar_reschedule(slot_id: int, when: str) -> None:
    dt = _parse_dt(when)
    with _session_scope() as sess:
        try:
            slot = scheduling.reschedule_content(sess, slot_id, dt)
        except (ValueError, scheduling.SchedulingError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(_slot_line(slot))


@calendar_app.command("unschedule")
def calendar_unschedule(slot_id: int) -> None:
    with _session_scope() as sess:
        try:
            scheduling.unschedule(sess, slot_id)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(f"unscheduled slot #{slot_id}")


@calendar_app.command("upcoming")
def calendar_upcoming(
    hours: int = typer.Option(None, help="Only slots within the next N hours"),
) -> None:
    with _session_scope() as sess:
        slots = scheduling.upcoming(sess, utcnow(), within_hours=hours)
        if not slots:
            typer.echo("no upcoming slots")
        for s in slots:
            typer.echo(_slot_line(s))


@calendar_app.command("audio-check")
def calendar_audio_check() -> None:
    with _session_scope() as sess:
        slots = scheduling.expiring_audio(sess, utcnow())
        if not slots:
            typer.echo("no expired trending audio")
        for s in slots:
            typer.echo(f"#{s.id} audio '{s.trending_audio}' expired (slot {s.scheduled_for:%Y-%m-%d %H:%M})")
```

- [ ] **Step 4: Run test to verify it passes** — Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli_calendar.py -v` — Expected: PASS (5 passed).

- [ ] **Step 5: Run full suite** — Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: PASS (128 passed: 123 + 5).

- [ ] **Step 6: Manual smoke check** (PowerShell):

```powershell
if (Test-Path aquen.sqlite) { Remove-Item aquen.sqlite }
.\.venv\Scripts\aquen.exe content add "Beta-glucan 101" derma_decode
.\.venv\Scripts\aquen.exe calendar schedule 1 2026-07-01T13:00 --audio trend-1 --audio-ttl 48
.\.venv\Scripts\aquen.exe calendar list
.\.venv\Scripts\aquen.exe calendar upcoming
```

Expected: a `#1 2026-07-01 13:00 [midday] derma_decode content=#1 audio=trend-1` line.

- [ ] **Step 7: Commit** — `git add src/aquen/cli.py tests/test_cli_calendar.py && git commit -m "feat: add calendar CLI sub-app"`

---

## Subsequent plans

- **Live `HttpHiggsfieldClient`** + live `MetaAdLibraryClient` — deferred until credentials/endpoints are wired and verified.
- **Thin local dashboard** (FastAPI + Jinja/HTMX) over the services: board, calendar, review/compliance UI.
- **Meta Ads module** (Custom Audience seeds, interest topic-stacks, Spark Ads).

---

## Self-Review

**1. Spec coverage:** §5.2 module 5 — posting windows (`POSTING_WINDOWS` 12–14 / 19–21, Task 2), 3-lane calendar (`lane` per slot, defaults to pillar; `list_calendar(lane=...)`, Task 3), trending-audio shelf-life timers (`audio_expires_at` + `audio_is_fresh`/`expiring_audio`, Tasks 2–3). §5.3 `calendar_slots` → `CalendarSlot` table (Task 1). Asset links remain on `Generation.content_item_id` (Plan 3) and the exported pack (Plan 4); the calendar references the content item by id. Scheduling is intentionally not state-gated.

**2. Placeholder scan:** No TBD/TODO. Every code step is complete and runnable; every run step has an exact command and expected count. The `–` in window messages is literal output.

**3. Type consistency:** `window_for`/`in_posting_window`/`audio_is_fresh` signatures match across Tasks 2–3. `CalendarSlot` columns (`scheduled_for`, `lane`, `window`, `trending_audio`, `audio_expires_at`, `note`) match across Task 1 (model), Task 3 (service writes), Task 4 (CLI `_slot_line`). `scheduling.schedule_content/reschedule_content/unschedule/list_calendar/upcoming/expiring_audio` signatures match their callers in the CLI. `SchedulingError` is raised by the service and caught by the CLI.
