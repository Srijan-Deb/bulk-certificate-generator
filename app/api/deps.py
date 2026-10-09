"""
FastAPI Dependencies
Provides dependency-injected database sessions, API key authentication, and utility dependencies.
"""

from fastapi import Header

from app.core.config import settings
from app.core.errors import AuthenticationError
from app.db.session import get_db


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str | None:
    """
    Verifies API key if API_KEY_ENABLED is set to True.
    When API_KEY_ENABLED is False, permits open access for local development and test automation.
    """
    if not settings.API_KEY_ENABLED:
        return None

    if not x_api_key or x_api_key != settings.API_KEY:
        raise AuthenticationError("Invalid or missing X-API-Key header.")

    return x_api_key


__all__ = ["get_db", "verify_api_key"]
