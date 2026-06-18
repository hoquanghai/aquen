from __future__ import annotations

import string

from sqlmodel import Session, select

from aquen.models import Prompt

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
    stmt = (
        stmt.where(Prompt.version == version)
        if version is not None
        else stmt.order_by(Prompt.version.desc())
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
