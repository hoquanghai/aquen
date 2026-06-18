from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import sys

# Force UTF-8 console output so non-ASCII copy (em-dashes, Japanese, etc.) never crashes
# on a legacy Windows codepage (e.g. cp932). No-op on streams without reconfigure().
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

import typer

from aquen import compliance, generation, publish, research, scheduling, service
from aquen.adapters import SampleMetaAdLibraryClient
from aquen.analysis import OriginalityError
from aquen.config import get_settings
from aquen.db import get_session, init_db, make_engine
from aquen.higgsfield import FakeHiggsfieldClient
from aquen.models import utcnow
from aquen.states import ContentState

app = typer.Typer(help="AQUEN content-ops toolkit", no_args_is_help=True)
content_app = typer.Typer(help="Manage content items", no_args_is_help=True)
app.add_typer(content_app, name="content")

competitor_app = typer.Typer(help="Manage the competitor watch-list", no_args_is_help=True)
app.add_typer(competitor_app, name="competitor")
hooks_app = typer.Typer(help="Browse derived hooks", no_args_is_help=True)
app.add_typer(hooks_app, name="hooks")

gen_app = typer.Typer(help="Generate and screen Higgsfield creative", no_args_is_help=True)
app.add_typer(gen_app, name="gen")

compliance_app = typer.Typer(help="Run and inspect the compliance gate", no_args_is_help=True)
app.add_typer(compliance_app, name="compliance")

publish_app = typer.Typer(help="Export manual-upload post packs", no_args_is_help=True)
app.add_typer(publish_app, name="publish")

calendar_app = typer.Typer(help="Schedule content across the posting calendar", no_args_is_help=True)
app.add_typer(calendar_app, name="calendar")


@contextmanager
def _session_scope():
    """Open a ready DB session and dispose the engine when done."""
    engine = make_engine()
    init_db(engine)
    try:
        with get_session(engine) as sess:
            yield sess
    finally:
        engine.dispose()


@app.command()
def init() -> None:
    """Initialize the AQUEN database."""
    engine = make_engine()
    init_db(engine)
    typer.echo(f"Initialized DB at {get_settings().db_path}")
    engine.dispose()


@content_app.command("add")
def content_add(
    title: str,
    pillar: str,
    hook: str = typer.Option(None, help="Hook archetype tag"),
    source: str = typer.Option(None, help="Source-of-inspiration URL"),
) -> None:
    with _session_scope() as sess:
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
    with _session_scope() as sess:
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
    with _session_scope() as sess:
        tgt = ContentState(to) if to else None
        try:
            item = service.advance_content(sess, item_id, target=tgt)
        except compliance.ComplianceError as exc:
            typer.echo(f"Blocked: {exc}", err=True)
            raise typer.Exit(1)
        typer.echo(f"#{item.id} -> {item.state.value}")


@competitor_app.command("add")
def competitor_add(
    handle: str,
    platform: str = typer.Option("meta", help="meta / tiktok / instagram"),
    note: str = typer.Option(None, help="Optional note"),
) -> None:
    with _session_scope() as sess:
        try:
            c = research.add_competitor(sess, handle, platform=platform, note=note)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        typer.echo(f"#{c.id} {c.handle} ({c.platform})")


@competitor_app.command("list")
def competitor_list() -> None:
    with _session_scope() as sess:
        for c in research.list_competitors(sess):
            typer.echo(f"#{c.id} {c.handle} ({c.platform})")


@app.command("research")
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
        try:
            g = generation.refresh_generation(sess, client, generation_id)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
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
        try:
            g = generation.screen_generation(sess, client, generation_id, threshold=threshold)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1)
        verdict = "PASS" if g.passed else "FAIL"
        typer.echo(f"#{g.id} score={g.virality_score} -> {verdict}")


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


if __name__ == "__main__":
    app()
