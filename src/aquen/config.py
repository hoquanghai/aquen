from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="AQUEN_", extra="ignore"
    )

    db_path: Path = Path("aquen.sqlite")
    higgsfield_api_key: str = ""
    meta_ad_library_token: str = ""


def get_settings() -> Settings:
    """Build settings fresh each call so env overrides apply in tests."""
    return Settings()
