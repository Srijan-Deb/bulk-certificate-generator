"""
FastAPI Dependencies
Provides dependency-injected database sessions, API key authentication, and utility dependencies.
"""

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthenticationError
from app.core.security import verify_access_token
from app.db.session import get_db
from app.models.user import User


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


def get_current_user_optional(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Extracts the authenticated user from the Bearer token if provided.
    Returns None if no token or invalid token, allowing open access where authentication is optional.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[len("Bearer ") :].strip()
    try:
        payload = verify_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()
    except Exception:
        return None


def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """
    Requires an authenticated user from the Bearer token.
    Raises AuthenticationError if missing or invalid.
    """
    user = get_current_user_optional(authorization=authorization, db=db)
    if not user:
        raise AuthenticationError("Authentication required. Please sign in with Google.")
    return user


__all__ = ["get_current_user", "get_current_user_optional", "get_db", "verify_api_key"]
