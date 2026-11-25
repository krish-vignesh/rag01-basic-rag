from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MigrationSettings(BaseSettings):
    """Configuration dedicated to Alembic migrations."""

    migration_target: Literal["test", "development"] = Field(
        validation_alias="RAG01_MIGRATION_TARGET"
    )

    # Shared PostgreSQL connection settings
    postgres_host: str
    postgres_port: int = Field(ge=1, le=65535)

    # Development database credentials
    postgres_db: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None

    # Test database credentials
    postgres_test_db: str | None = None
    postgres_test_user: str | None = None
    postgres_test_password: str | None = None

    # Development migration safeguard
    allow_development_migrations: bool = Field(
        default=False,
        validation_alias="RAG01_ALLOW_DEVELOPMENT_MIGRATIONS",
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
