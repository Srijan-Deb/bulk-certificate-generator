"""
Security and Validation Tests (Phase 7)
Verifies:
- OWASP defensive security headers on all responses
- Request payload size limit enforcement (HTTP 413)
- API key authentication enforcement and rejection (HTTP 401)
- Path traversal prevention on certificate download endpoints
- Prevention of downloading ungenerated or failed certificates
- Sanitized error responses without internal leakages
"""

from app.core.config import settings
from app.models.certificate import CertificateRecord
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob


def test_security_headers_present(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "mode=block" in headers.get("X-XSS-Protection", "")
    assert "strict-origin" in headers.get("Referrer-Policy", "")


def test_payload_limit_enforced(client):
    # Construct a dummy large payload header exceeding MAX_PAYLOAD_SIZE_BYTES
    large_payload = {
        "event_name": "Big Data Workshop",
        "issuer_name": "Data Academy",
        "issue_date": "2026-10-10",
        "recipients": [{"recipient_name": "Test User", "recipient_email": "test@example.com"}],
    }
    # Simulate oversized Content-Length header
    oversized_length = str(settings.MAX_PAYLOAD_SIZE_BYTES + 1024)
    response = client.post("/api/v1/jobs", json=large_payload, headers={"Content-Length": oversized_length})

    assert response.status_code == 413
    data = response.json()
    assert data["error_code"] == "PAYLOAD_TOO_LARGE"
    assert "exceeds allowable limit" in data["detail"]


def test_api_key_authentication_enforcement(client, monkeypatch):
    # Enable API Key authentication in settings for this test
    monkeypatch.setattr(settings, "API_KEY_ENABLED", True)
    monkeypatch.setattr(settings, "API_KEY", "super-secret-prod-token-12345")

    payload = {
        "event_name": "Security Summit",
        "issuer_name": "Cyber Defense Council",
        "issue_date": "2026-10-10",
        "recipients": [{"recipient_name": "Sec Officer", "recipient_email": "sec@example.com"}],
    }

    # 1. Request with no X-API-Key header -> 401 Unauthorized
    resp_no_key = client.post("/api/v1/jobs", json=payload)
    assert resp_no_key.status_code == 401
    assert resp_no_key.json()["error_code"] == "AuthenticationError"

    # 2. Request with invalid key -> 401 Unauthorized
    resp_bad_key = client.post("/api/v1/jobs", json=payload, headers={"X-API-Key": "wrong-token"})
    assert resp_bad_key.status_code == 401
    assert resp_bad_key.json()["error_code"] == "AuthenticationError"

    # 3. Request with valid key -> 202 Accepted
    resp_valid = client.post("/api/v1/jobs", json=payload, headers={"X-API-Key": "super-secret-prod-token-12345"})
    assert resp_valid.status_code == 202
    assert resp_valid.json()["status"] == "PENDING"


def test_path_traversal_prevention_on_download(client):
    # Attempt directory traversal via certificate_id route parameter
    traversal_payloads = [
        "../../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "..\\..\\windows\\system32\\config",
        "....//....//data.db",
    ]

    for payload in traversal_payloads:
        response = client.get(f"/api/v1/certificates/{payload}/download")
        # Should return 404 or 403, and NEVER 200 or 500 leaking filesystem contents
        assert response.status_code in (404, 403, 422)


def test_unauthorized_download_of_incomplete_certificate(client, db_session):
    # Create a certificate record that is still in PENDING or FAILED state
    job = GenerationJob(
        event_name="Draft Workshop",
        issuer_name="Test Org",
        issue_date="2026-10-10",
        status=JobStatus.PROCESSING.value,
        total_recipients=1,
    )
    db_session.add(job)
    db_session.flush()

    cert = CertificateRecord(
        job_id=job.id,
        recipient_name="Pending Student",
        certificate_id="CERT-PENDING-UNFINISHED",
        status=CertificateStatus.PENDING.value,
        file_path=None,
    )
    db_session.add(cert)
    db_session.commit()

    # Attempt download of unfinished certificate
    response = client.get(f"/api/v1/certificates/{cert.certificate_id}/download")
    assert response.status_code == 404
    assert "has not been successfully generated" in response.json()["detail"]


def test_error_response_does_not_leak_internals(client):
    # Request a non-existent job ID
    response = client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()

    # Must contain structured detail and error_code
    assert "detail" in data
    assert data["error_code"] == "JobNotFoundError"

    # Must NOT expose tracebacks or internal DB query syntax
    assert "Traceback" not in data["detail"]
    assert "SELECT" not in data["detail"]
    assert "sqlite" not in data["detail"]
