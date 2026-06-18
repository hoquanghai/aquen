from pathlib import Path

from aquen.config import get_settings


def test_defaults():
    settings = get_settings()
    assert settings.db_path == Path("aquen.sqlite")
    assert settings.higgsfield_api_key == ""


def test_env_override(monkeypatch):
    monkeypatch.setenv("AQUEN_DB_PATH", "custom.sqlite")
    monkeypatch.setenv("AQUEN_HIGGSFIELD_API_KEY", "secret")
    settings = get_settings()
    assert settings.db_path == Path("custom.sqlite")
    assert settings.higgsfield_api_key == "secret"
