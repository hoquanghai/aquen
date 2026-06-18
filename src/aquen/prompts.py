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
