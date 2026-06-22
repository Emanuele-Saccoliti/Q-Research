from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from .env, key.env, or process environment."""

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, validation_alias="TEMPERATURE")
    max_articles: int = Field(default=12, ge=1, le=50, validation_alias="MAX_ARTICLES")
    output_dir: Path = Field(default=Path("reports"), validation_alias="OUTPUT_DIR")
    request_timeout_seconds: int = Field(
        default=30,
        ge=5,
        validation_alias="REQUEST_TIMEOUT_SECONDS",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "key.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
