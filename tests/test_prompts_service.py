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
