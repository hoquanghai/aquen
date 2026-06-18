from __future__ import annotations

from contextlib import contextmanager
import sys

# Force UTF-8 console output so non-ASCII copy (em-dashes, Japanese, etc.) never crashes
# on a legacy Windows codepage (e.g. cp932). No-op on streams without reconfigure().
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        _reconfigure(encoding="utf-8", errors="replace")

import typer

from aquen import generation, research, service
from aquen.adapters import SampleMetaAdLibraryClient
from aquen.analysis import OriginalityError
from aquen.config import get_settings
from aquen.db import get_session, init_db, make_engine
from aquen.higgsfield import FakeHiggsfieldClient
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
        item = service.advance_content(sess, item_id, target=tgt)
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
