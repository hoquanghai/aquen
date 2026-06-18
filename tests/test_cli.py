from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_init(tmp_path):
    result = runner.invoke(app, ["init"], env=_env(tmp_path))
    assert result.exit_code == 0
    assert "Initialized" in result.stdout
    assert (tmp_path / "test.sqlite").exists()


def test_add_then_list(tmp_path):
    env = _env(tmp_path)
    add = runner.invoke(
        app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env
    )
    assert add.exit_code == 0, add.stdout

    listed = runner.invoke(app, ["content", "list"], env=env)
    assert listed.exit_code == 0
    assert "Beta-glucan 101" in listed.stdout
    assert "[idea]" in listed.stdout


def test_advance(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["content", "add", "A", "derma_decode"], env=env)
    adv = runner.invoke(app, ["content", "advance", "1"], env=env)
    assert adv.exit_code == 0
    assert "scripted" in adv.stdout
