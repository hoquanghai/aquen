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
