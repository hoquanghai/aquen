from pathlib import Path

from typer.testing import CliRunner

from aquen.cli import app

runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {"AQUEN_DB_PATH": str(tmp_path / "test.sqlite")}


def _seed_review_item(env: dict[str, str]) -> None:
    runner.invoke(app, ["content", "add", "Beta-glucan 101", "derma_decode"], env=env)
    for _ in range(5):  # idea -> scripted -> generating -> rendered -> screened -> review
        runner.invoke(app, ["content", "advance", "1"], env=env)


def test_content_set_updates_fields(tmp_path):
    env = _env(tmp_path)
    runner.invoke(app, ["content", "add", "t", "derma_decode"], env=env)
    out = runner.invoke(
        app,
        ["content", "set", "1", "--caption", "Created with AI. #ad", "--sponsored", "--ai-label"],
        env=env,
    )
    assert out.exit_code == 0, out.stdout
    assert "sponsored=True" in out.stdout
    assert "ai_label=True" in out.stdout


def test_compliance_check_reports_failures(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    out = runner.invoke(app, ["compliance", "check", "1"], env=env)
    assert out.exit_code == 0, out.stdout
    assert "FAIL" in out.stdout
    assert "ai_disclosure" in out.stdout


def test_compliance_check_all_pass_then_advance(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    runner.invoke(
        app,
        ["content", "set", "1", "--caption", "Created with AI. Honest beta-glucan science. #ad",
         "--sponsored", "--ai-label"],
        env=env,
    )
    checked = runner.invoke(app, ["compliance", "check", "1"], env=env)
    assert "ALL CHECKS PASS" in checked.stdout
    advanced = runner.invoke(app, ["content", "advance", "1", "--to", "ready"], env=env)
    assert advanced.exit_code == 0, advanced.stdout
    assert "ready" in advanced.stdout


def test_advance_blocked_shows_message(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    out = runner.invoke(app, ["content", "advance", "1", "--to", "ready"], env=env)
    assert out.exit_code == 1
    assert "not ready" in out.stdout.lower() or "not ready" in (out.stderr or "").lower()


def test_compliance_log_lists_rows(tmp_path):
    env = _env(tmp_path)
    _seed_review_item(env)
    runner.invoke(app, ["compliance", "check", "1"], env=env)
    out = runner.invoke(app, ["compliance", "log", "1"], env=env)
    assert "ai_disclosure" in out.stdout
