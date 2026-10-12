"""
Unit & Integration Tests for Google Auth and Cloud Storage Integration
"""

from fastapi.testclient import TestClient

from app.core.security import create_access_token, verify_access_token
from app.main import app
from app.services.cloud_storage import cloud_storage

client = TestClient(app)


def test_auth_config():
    """Verify public auth and cloud storage configuration endpoint."""
    resp = client.get("/api/v1/auth/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "storage_provider" in data
    assert "cloud_storage_configured" in data


def test_jwt_token_creation_and_verification():
    """Verify HMAC-SHA256 JWT generation and validation."""
    token = create_access_token(
        subject="user-12345",
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/photo.jpg",
    )
    assert token and len(token.split(".")) == 3

    payload = verify_access_token(token)
    assert payload["sub"] == "user-12345"
    assert payload["email"] == "test@example.com"
    assert payload["name"] == "Test User"


def test_dev_google_login_and_me():
    """Verify Google dev/demo authentication flow and /me endpoint."""
    login_resp = client.post(
        "/api/v1/auth/google",
        json={
            "demo": True,
            "email": "dev.user@example.com",
            "name": "Dev User",
            "avatar_url": "https://example.com/avatar.png",
        },
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    token = login_data["access_token"]
    user = login_data["user"]
    assert user["email"] == "dev.user@example.com"
    assert user["full_name"] == "Dev User"

    # Call /me with Bearer token
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == user["id"]
    assert me_data["email"] == "dev.user@example.com"


def test_unauthenticated_me_rejected():
    """Verify /me fails when unauthenticated."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


def test_list_jobs_endpoint():
    """Verify GET /api/v1/jobs endpoint returns list of jobs."""
    resp = client.get("/api/v1/jobs?limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_cloud_storage_local_mode_health():
    """Verify cloud storage health reporting when in local mode."""
    health = cloud_storage.check_health()
    assert "provider" in health
    assert "status" in health
