import os
import subprocess
import sys
from pathlib import Path


def _run(args, env):
    return subprocess.run(
        [sys.executable, "-c", "from aquen.cli import app; app()", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_cli_survives_cp932_console(tmp_path: Path):
    """Hook templates contain em-dashes; ensure CLI commands don't crash when the console
    encoding is cp932 (default on Japanese Windows). Cross-platform because the cp932 codec
    ships with Python."""
    env = dict(os.environ)
    env["AQUEN_DB_PATH"] = str(tmp_path / "t.sqlite")
    env["PYTHONIOENCODING"] = "cp932"

    assert _run(["competitor", "add", "rivalskin"], env).returncode == 0
    assert _run(["research"], env).returncode == 0
    res = _run(["hooks", "list"], env)
    assert res.returncode == 0, res.stderr
