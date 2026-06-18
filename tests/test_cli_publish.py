from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def _seed_ready_item(env: dict[str, str]) -> None:
    runner.invoke(app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env)
    for _ in range(5):  # -> review
        runner.invoke(app, ["content", "advance", "1"], env=env)
    runner.invoke(
        app,
        ["content", "set", "1", "--caption", "Created with AI. Honest beta-glucan science. #ad",
         "--sponsored", "--ai-label"],
        env=env,
    )
    runner.invoke(app, ["content", "advance", "1", "--to", "ready"], env=env)


def test_publish_pack_happy_path(tmp_path):
    env = _env(tmp_path)
    _seed_ready_item(env)
    out_dir = tmp_path / "packs"
    result = runner.invoke(app, ["publish", "pack", "1", "--out", str(out_dir)], env=env)
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "aquen-post-1" / "post_pack.md").exists()
    assert "aquen-post-1" in result.stdout


def test_publish_pack_non_ready_errors(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["content", "add", "t", "derma_decode"], env=env)  # stays idea
    result = runner.invoke(app, ["publish", "pack", "1", "--out", str(tmp_path)], env=env)
    assert result.exit_code == 1
    assert "ready" in (result.stdout + (result.stderr or "")).lower()
