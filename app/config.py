"""
Centralised configuration for SnapSearch.

All values can be overridden via environment variables or the .env file.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""

    # Storage
    index_store_dir: Path = Path("index_store")

    # Search defaults
    text_weight_default: float = 0.4
    top_k_default: int = 9

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Module-level singleton — import this everywhere
settings = Settings()
