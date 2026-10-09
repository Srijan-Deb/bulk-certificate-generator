"""
Tests for Certificate and Batch ZIP Retrieval
Verifies file streaming, MIME types, headers, and error scenarios.
"""

import io
import zipfile

from app.services.worker import worker


def test_download_single_certificate_pdf(client, db_session):
    # 1. Create and process job
    payload = {
        "event_name": "API Security Masterclass",
        "issuer_name": "SecOps Labs",
        "issue_date": "2026-10-10",
        "recipients": [{"recipient_name": "Eve Polastri", "recipient_email": "eve@example.com"}],
    }
    create_resp = client.post("/api/v1/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    job = worker.claim_next_job(db_session)
    worker.process_job(db_session, job)

    certs_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    cert_id = certs_resp.json()[0]["certificate_id"]

    # 2. Download certificate
    download_resp = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert "inline" in download_resp.headers.get("content-disposition", "")
    assert download_resp.content.startswith(b"%PDF")


def test_download_nonexistent_certificate_returns_404(client):
    response = client.get("/api/v1/certificates/CERT-NON-EXISTENT/download")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "CertificateNotFoundError"


def test_download_job_certificates_zip(client, db_session):
    # 1. Create and process job with multiple recipients
    payload = {
        "event_name": "Distributed Systems",
        "issuer_name": "Cloud University",
        "issue_date": "2026-10-10",
        "recipients": [{"recipient_name": "Ada Lovelace"}, {"recipient_name": "Alan Turing"}],
    }
    create_resp = client.post("/api/v1/jobs", json=payload)
    job_id = create_resp.json()["job_id"]

    job = worker.claim_next_job(db_session)
    worker.process_job(db_session, job)

    # 2. Download ZIP
    zip_resp = client.get(f"/api/v1/jobs/{job_id}/download-zip")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    # 3. Verify ZIP contents
    zip_bytes = io.BytesIO(zip_resp.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        file_list = zf.namelist()
        assert len(file_list) == 2
        for fname in file_list:
            assert fname.endswith(".pdf")
