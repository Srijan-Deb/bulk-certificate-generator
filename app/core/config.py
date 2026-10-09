"""
Core Application Configuration
Uses pydantic-settings to manage environment variables with strong typing,
sensible defaults, and production-ready validation.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # Application Metadata
    PROJECT_NAME: str = "Bulk Certificate Generator"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration (Default: Zero-Cost Local SQLite with WAL mode)
    DATABASE_URL: str = "sqlite:///./data.db"
    DB_ECHO: bool = False

    # Storage Settings
    STORAGE_DIR: Path = Path("./storage/certificates")
    MAX_BATCH_SIZE: int = Field(default=1000, ge=1, le=5000, description="Max recipients per bulk request")
    MAX_FILE_RETENTION_HOURS: int = 72

    # Worker Configuration
    WORKER_POLL_INTERVAL_SECONDS: float = 2.0
    WORKER_BATCH_SIZE: int = 50
    WORKER_JOB_TIMEOUT_SECONDS: int = 600
    RUN_WORKER_IN_APP: bool = True  # Allows single-process local dev or separate worker process

    # Security & CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    @field_validator("STORAGE_DIR", mode="before")
    @classmethod
    def parse_storage_dir(cls, v: str | Path) -> Path:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
