"""
Security & Authentication Module
Handles JWT generation/verification and Google OAuth 2.0 token validation.
Uses standard HMAC-SHA256 tokens and Google's official tokeninfo endpoint.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import AuthenticationError

logger = logging.getLogger("bulk_certificate_generator.security")


def _base64url_encode(data: bytes) -> str:
    """Encodes bytes to base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    """Decodes base64url string with optional padding."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("ascii"))


def create_access_token(subject: str, email: str, name: str, avatar_url: str | None = None) -> str:
    """
    Creates a signed HMAC-SHA256 JWT access token.
    Contains sub (user_id), email, name, avatar_url, iat, and exp.
    """
    now = int(time.time())
    expires = now + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "email": email,
        "name": name,
        "avatar_url": avatar_url,
        "iat": now,
        "exp": expires,
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    message = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_access_token(token: str) -> dict[str, Any]:
    """
    Validates the token signature and expiration, returning the decoded payload dict.
    Raises AuthenticationError if invalid or expired.
    """
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise AuthenticationError("Invalid token format.")

    header_b64, payload_b64, signature_b64 = parts
    message = f"{header_b64}.{payload_b64}".encode("ascii")

    expected_sig = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    actual_sig = _base64url_decode(signature_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise AuthenticationError("Invalid token signature.")

    try:
        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise AuthenticationError("Malformed token payload.")

    exp = payload.get("exp")
    if not exp or int(time.time()) > int(exp):
        raise AuthenticationError("Token has expired. Please sign in again.")

    return payload


async def verify_google_credential(credential: str) -> dict[str, Any]:
    """
    Validates a Google OAuth 2.0 ID Token / Credential using Google's public tokeninfo endpoint.
    Returns normalized user info: google_id, email, name, avatar_url.
    """
    token_url = "https://oauth2.googleapis.com/tokeninfo"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(token_url, params={"id_token": credential})
        except Exception as exc:
            logger.error("Failed to connect to Google OAuth service: %s", exc)
            raise AuthenticationError("Cannot verify Google credential. Please try again.")

    if resp.status_code != 200:
        logger.warning("Google tokeninfo returned status %d: %s", resp.status_code, resp.text)
        raise AuthenticationError("Invalid or expired Google authentication credential.")

    data = resp.json()

    # Optional audience check if client ID is set
    if settings.GOOGLE_CLIENT_ID and data.get("aud") != settings.GOOGLE_CLIENT_ID:
        logger.error("Google token audience mismatch: expected %s, got %s", settings.GOOGLE_CLIENT_ID, data.get("aud"))
        raise AuthenticationError("Google token audience does not match configured Client ID.")

    email = data.get("email")
    if not email:
        raise AuthenticationError("Google account does not have an associated email address.")

    if data.get("email_verified") not in (True, "true"):
        raise AuthenticationError("Google account email is not verified.")

    return {
        "google_id": data.get("sub"),
        "email": email.lower().strip(),
        "name": data.get("name") or email.split("@")[0],
        "avatar_url": data.get("picture"),
    }
