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

    # Storage & Asset Settings
    STORAGE_DIR: Path = Path("./storage/certificates")
    TEMPLATES_DIR: Path = Path("./templates")
    SIGNATURES_DIR: Path = Path("./templates/signatures")
    BACKGROUNDS_DIR: Path = Path("./templates/backgrounds")
    SIGNATURE_IMAGE_PATH: Path = Field(
        default=Path("./templates/signature.png"),
        description="Path to authorized signatory signature image",
    )
    BACKGROUND_TEMPLATE_PATH: Path = Field(
        default=Path("./templates/background.png"),
        description="Path to custom certificate background template image",
    )
    MAX_BATCH_SIZE: int = Field(default=1000, ge=1, le=5000, description="Max recipients per bulk request")
    MAX_FILE_RETENTION_HOURS: int = 72

    # Worker Configuration
    WORKER_POLL_INTERVAL_SECONDS: float = 2.0
    WORKER_BATCH_SIZE: int = 50
    WORKER_JOB_TIMEOUT_SECONDS: int = 600
    RUN_WORKER_IN_APP: bool = True  # Allows single-process local dev or separate worker process

    # AI & LLM Vision Settings
    GEMINI_API_KEY: str | None = None
    TEMPLATE_CONFIG_PATH: Path = Field(
        default=Path("./templates/template_config.json"),
        description="Path to active certificate template layout configuration JSON",
    )

    # Security, Limits & Authentication
    API_KEY_ENABLED: bool = False
    API_KEY: str | None = None
    MAX_PAYLOAD_SIZE_BYTES: int = Field(default=10 * 1024 * 1024, description="Max request payload size (10 MB)")
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Google OAuth 2.0 & Session Management
    GOOGLE_CLIENT_ID: str | None = None
    JWT_SECRET_KEY: str = "bulk-certificate-generator-jwt-secret-key-change-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Cloud Storage (S3-compatible: Cloudflare R2 / Supabase / MinIO)
    STORAGE_PROVIDER: str = Field(
        default="local", description="Storage backend: 'local' (default) or 's3'/'r2'/'supabase'"
    )
    S3_BUCKET_NAME: str = "certificates"
    S3_ENDPOINT_URL: str | None = None  # e.g. https://<account_id>.r2.cloudflarestorage.com
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_REGION_NAME: str = "auto"
    S3_PUBLIC_URL_PREFIX: str | None = None

    @field_validator("STORAGE_DIR", "SIGNATURES_DIR", "BACKGROUNDS_DIR", mode="before")
    @classmethod
    def parse_storage_dir(cls, v: str | Path) -> Path:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
