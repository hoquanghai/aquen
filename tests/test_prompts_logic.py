import pytest

from aquen.prompts import PromptError, render_template, required_variables


def test_required_variables_extracts_named_fields():
    assert required_variables("a {style} portrait of {subject}") == {"style", "subject"}


def test_required_variables_empty_for_plain_text():
    assert required_variables("a plain prompt") == set()


def test_render_template_fills_named_fields():
    assert render_template("a {style} portrait of {subject}", {"style": "clean", "subject": "Mira"}) == "a clean portrait of Mira"


def test_render_template_missing_variable_raises():
    with pytest.raises(PromptError):
        render_template("a {style} portrait of {subject}", {"style": "clean"})


def test_render_template_ignores_extra_variables():
    assert render_template("hello {name}", {"name": "Mira", "extra": "x"}) == "hello Mira"
