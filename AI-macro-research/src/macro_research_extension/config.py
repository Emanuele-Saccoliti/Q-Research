from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for retrieval, LLM extraction, and NLP/ML analysis."""

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, validation_alias="TEMPERATURE")
    request_timeout_seconds: int = Field(
        default=45,
        ge=5,
        validation_alias="REQUEST_TIMEOUT_SECONDS",
    )

    max_articles: int = Field(default=30, ge=3, le=100, validation_alias="MAX_ARTICLES")
    output_dir: Path = Field(default=Path("reports"), validation_alias="OUTPUT_DIR")

    embedding_provider: Literal["hashing", "sentence-transformer"] = Field(
        default="hashing",
        validation_alias="EMBEDDING_PROVIDER",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(
        default=512,
        ge=64,
        le=4096,
        validation_alias="EMBEDDING_DIMENSIONS",
    )
    cluster_distance_threshold: float = Field(
        default=0.55,
        gt=0.0,
        lt=2.0,
        validation_alias="CLUSTER_DISTANCE_THRESHOLD",
    )
    theme_match_similarity: float = Field(
        default=0.72,
        ge=0.0,
        le=1.0,
        validation_alias="THEME_MATCH_SIMILARITY",
    )

    theme_history_path: Path = Field(
        default=Path("data/theme_history.json"),
        validation_alias="THEME_HISTORY_PATH",
    )
    theme_lookback_days: int = Field(
        default=90,
        ge=7,
        validation_alias="THEME_LOOKBACK_DAYS",
    )
    persistence_target_runs: int = Field(
        default=5,
        ge=2,
        validation_alias="PERSISTENCE_TARGET_RUNS",
    )
    breadth_target_sources: int = Field(
        default=5,
        ge=2,
        validation_alias="BREADTH_TARGET_SOURCES",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "key.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

