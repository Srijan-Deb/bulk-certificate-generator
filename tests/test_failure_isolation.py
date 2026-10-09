"""
Tests for Fault Isolation and Partial Failures
Verifies that individual recipient failures do not crash the job,
and remaining valid recipients continue generating successfully.
"""

from app.models.certificate import CertificateRecord
from app.services.worker import worker


def test_individual_recipient_failure_does_not_halt_job(client, db_session):
    # 1. Submit job with 3 recipients: 2 valid, 1 invalid (invalid name injected)
    payload = {
        "event_name": "Cloud Native Architecture",
        "issuer_name": "DevOps Institute",
        "issue_date": "2026-10-10",
        "recipients": [
            {"recipient_name": "Carol Danvers", "recipient_email": "carol@example.com"},
            {"recipient_name": "Valid Participant", "recipient_email": "valid@example.com"},
            {"recipient_name": "Dave Bowman", "recipient_email": "dave@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Invalidate recipient 2 at the DB level to simulate a downstream processing/data fault
    # (e.g., corrupted record or empty name bypass)
    rec2 = db_session.query(CertificateRecord).filter_by(job_id=job_id, recipient_name="Valid Participant").first()
    rec2.recipient_name = " "  # Blank name triggers worker validation failure
    db_session.commit()

    # 2. Worker claims and processes job
    job = worker.claim_next_job(db_session)
    assert job is not None
    worker.process_job(db_session, job)

    # 3. Assert aggregate job status is COMPLETED_WITH_ERRORS
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert data["total_recipients"] == 3
    assert data["successful_count"] == 2
    assert data["failed_count"] == 1

    # 4. Assert individual certificate outcomes
    certs_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert certs_resp.status_code == 200
    certs = certs_resp.json()

    successes = [c for c in certs if c["status"] == "SUCCESS"]
    failures = [c for c in certs if c["status"] == "FAILED"]

    assert len(successes) == 2
    assert len(failures) == 1
    assert failures[0]["error_code"] == "INVALID_RECIPIENT_DATA"
    assert "at least 2 characters" in failures[0]["error_message"]
