from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_competitor_add_and_list(tmp_path):
    env = _env(tmp_path)
    add = runner.invoke(app, ["competitor", "add", "rivalskin"], env=env)
    assert add.exit_code == 0, add.stdout
    listed = runner.invoke(app, ["competitor", "list"], env=env)
    assert "rivalskin" in listed.stdout


def test_research_then_hooks(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["competitor", "add", "rivalskin"], env=env)
    res = runner.invoke(app, ["research"], env=env)
    assert res.exit_code == 0, res.stdout
    assert "hooks" in res.stdout.lower()

    hooks = runner.invoke(app, ["hooks", "list"], env=env)
    assert hooks.exit_code == 0
    assert "#" in hooks.stdout


def test_ideate_command(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["competitor", "add", "rivalskin"], env=env)
    runner.invoke(app, ["research"], env=env)
    item = runner.invoke(
        app,
        [
            "ideate",
            "1",
            "--pillar",
            "derma_decode",
            "--script",
            "A calm, simple barrier-first routine beats chasing every new trend.",
        ],
        env=env,
    )
    assert item.exit_code == 0, item.stdout
    assert "scripted" in item.stdout.lower()
