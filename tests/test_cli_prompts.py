from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_add_then_list(tmp_path):
    env = _env(tmp_path)
    out = runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "v1" in out.stdout
    listed = runner.invoke(app, ["prompt", "list"], env=env)
    assert "mira-clean" in listed.stdout
    assert "avatar" in listed.stdout


def test_add_bad_category_errors(tmp_path):
    env = _env(tmp_path)
    out = runner.invoke(app, ["prompt", "add", "x", "nope", "t"], env=env)
    assert out.exit_code == 1
    assert "category" in (out.stdout + (out.stderr or "")).lower()


def test_show_prints_template(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    out = runner.invoke(app, ["prompt", "show", "mira-clean"], env=env)
    assert out.exit_code == 0
    assert "a {style} portrait of {subject}" in out.stdout


def test_render_with_vars(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    out = runner.invoke(
        app, ["prompt", "render", "mira-clean", "--var", "style=clean", "--var", "subject=Mira"], env=env
    )
    assert out.exit_code == 0, out.stdout
    assert "a clean portrait of Mira" in out.stdout


def test_render_missing_var_errors(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "a {style} portrait of {subject}"], env=env)
    out = runner.invoke(app, ["prompt", "render", "mira-clean", "--var", "style=clean"], env=env)
    assert out.exit_code == 1
    assert "missing" in (out.stdout + (out.stderr or "")).lower()


def test_versions_lists_all(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "v1 {subject}"], env=env)
    runner.invoke(app, ["prompt", "add", "mira-clean", "avatar", "v2 {subject}"], env=env)
    out = runner.invoke(app, ["prompt", "versions", "mira-clean"], env=env)
    assert "v1" in out.stdout
    assert "v2" in out.stdout
