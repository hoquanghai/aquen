from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def _add_item(env: dict[str, str]) -> None:
    runner.invoke(app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env)


def test_schedule_then_list(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    out = runner.invoke(app, ["calendar", "schedule", "1", "2026-07-01T13:00"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "midday" in out.stdout
    listed = runner.invoke(app, ["calendar", "list"], env=env)
    assert "#1" in listed.stdout
    assert "derma_decode" in listed.stdout


def test_schedule_outside_window_errors(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    out = runner.invoke(app, ["calendar", "schedule", "1", "2026-07-01T09:00"], env=env)
    assert out.exit_code == 1
    assert "posting window" in (out.stdout + (out.stderr or "")).lower()


def test_schedule_bad_datetime_errors(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    out = runner.invoke(app, ["calendar", "schedule", "1", "not-a-date"], env=env)
    assert out.exit_code == 1


def test_reschedule_and_unschedule(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    runner.invoke(app, ["calendar", "schedule", "1", "2026-07-01T13:00"], env=env)
    moved = runner.invoke(app, ["calendar", "reschedule", "1", "2026-07-02T20:00"], env=env)
    assert moved.exit_code == 0, moved.stdout
    assert "evening" in moved.stdout
    removed = runner.invoke(app, ["calendar", "unschedule", "1"], env=env)
    assert removed.exit_code == 0
    assert runner.invoke(app, ["calendar", "list"], env=env).stdout.strip() == ""


def test_upcoming_and_audio_check_run(tmp_path):
    env = _env(tmp_path)
    _add_item(env)
    runner.invoke(
        app,
        ["calendar", "schedule", "1", "2026-07-01T20:00", "--audio", "trend-1", "--audio-ttl", "1"],
        env=env,
    )
    up = runner.invoke(app, ["calendar", "upcoming"], env=env)
    assert up.exit_code == 0
    audio = runner.invoke(app, ["calendar", "audio-check"], env=env)
    assert audio.exit_code == 0
