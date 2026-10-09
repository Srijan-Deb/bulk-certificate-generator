"""
End-to-End Tests for Job Lifecycle and Worker Processing
"""

from app.services.worker import worker


def test_job_submission_and_processing_lifecycle(client, db_session):
    # 1. Submit bulk job
    payload = {
        "event_name": "Full Stack Mastery",
        "issuer_name": "Tech Academy",
        "issue_date": "2026-10-10",
        "certificate_title": "Certificate of Completion",
        "recipients": [
            {"recipient_name": "Alice Johnson", "recipient_email": "alice@example.com"},
            {"recipient_name": "Bob Smith", "recipient_email": "bob@example.com", "custom_remarks": "Top Performer"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    job_id = data["job_id"]
    assert data["status"] == "PENDING"
    assert data["total_recipients"] == 2
    assert "status_url" in data

    # 2. Check initial status via GET
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "PENDING"
    assert status_data["successful_count"] == 0
    assert status_data["failed_count"] == 0
    assert status_data["progress_percentage"] == 0.0

    # 3. Trigger worker tick using the test DB session
    job = worker.claim_next_job(db_session)
    assert job is not None
    assert job.id == job_id
    assert job.status == "PROCESSING"

    worker.process_job(db_session, job)

    # 4. Check completed status via GET
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    final_data = status_resp.json()
    assert final_data["status"] == "COMPLETED"
    assert final_data["successful_count"] == 2
    assert final_data["failed_count"] == 0
    assert final_data["progress_percentage"] == 100.0
    assert final_data["completed_at"] is not None
    assert final_data["zip_download_url"] is not None

    # 5. List certificates for this job
    certs_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert certs_resp.status_code == 200
    certs_list = certs_resp.json()
    assert len(certs_list) == 2
    for cert in certs_list:
        assert cert["status"] == "SUCCESS"
        assert cert["certificate_id"].startswith("CERT-")
        assert cert["download_url"] is not None
