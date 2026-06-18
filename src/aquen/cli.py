from __future__ import annotations

from contextlib import contextmanager

import typer

from aquen import service
from aquen.config import get_settings
from aquen.db import get_session, init_db, make_engine
from aquen.states import ContentState

app = typer.Typer(help="AQUEN content-ops toolkit", no_args_is_help=True)
content_app = typer.Typer(help="Manage content items", no_args_is_help=True)
app.add_typer(content_app, name="content")


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
