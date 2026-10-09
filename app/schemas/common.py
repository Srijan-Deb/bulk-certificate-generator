"""
Common API Schemas
Health check, error formats, and paginated responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    db_connected: bool = True
    storage_accessible: bool = True
    version: str = "1.0.0"
    environment: str = "development"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    details: dict[str, Any] | None = None
