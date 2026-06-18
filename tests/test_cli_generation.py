from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def test_gen_image_then_list(tmp_path):
    env = _env(tmp_path)
    out = runner.invoke(app, ["gen", "image", "a clean Mira portrait"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "image" in out.stdout
    listed = runner.invoke(app, ["gen", "list"], env=env)
    assert "#1" in listed.stdout


def test_gen_video_refresh_screen(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["gen", "video", "she explains beta-glucan"], env=env)
    refreshed = runner.invoke(app, ["gen", "refresh", "1"], env=env)
    assert refreshed.exit_code == 0
    assert "completed" in refreshed.stdout
    screened = runner.invoke(app, ["gen", "screen", "1"], env=env)
    assert screened.exit_code == 0
    assert "score" in screened.stdout.lower()


def test_gen_refresh_unknown_id_errors(tmp_path):
    env = _env(tmp_path)
    res = runner.invoke(app, ["gen", "refresh", "999"], env=env)
    assert res.exit_code == 1
    assert "not found" in res.output.lower()


def test_gen_screen_pending_errors(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["gen", "video", "clip"], env=env)  # pending, never refreshed
    res = runner.invoke(app, ["gen", "screen", "1"], env=env)
    assert res.exit_code == 1
    assert "completed" in res.output.lower()
