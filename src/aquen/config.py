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
    # Locked Mira identity references (see docs/brand/mira-kol.md)
    mira_soul_id: str = "83c0591d-223f-461d-b4f2-0040fa029b8b"
    mira_element_id: str = "1972c3b9-1f3f-49fb-bcf0-104c7b171a23"
    virality_threshold: float = 0.6


def get_settings() -> Settings:
    """Build settings fresh each call so env overrides apply in tests."""
    return Settings()
