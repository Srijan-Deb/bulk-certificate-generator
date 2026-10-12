"""
Automated Tests for File Upload Endpoint (POST /api/v1/jobs/upload)
Tests spreadsheet parsing, validation, end-to-end processing lifecycle, and error isolation.
"""

import io
import zipfile

import openpyxl

from app.services.spreadsheet_parser import spreadsheet_parser
from app.services.worker import worker


def _create_test_xlsx(rows: list[list[str]]) -> bytes:
    """Helper to build an in-memory .xlsx file from row lists."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _create_test_csv(content: str) -> bytes:
    """Helper to build CSV bytes."""
    return content.encode("utf-8")


def test_download_upload_template(client):
    """Verifies that GET /api/v1/jobs/upload/template returns a valid Excel template."""
    resp = client.get("/api/v1/jobs/upload/template")
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers["content-type"]
    assert 'attachment; filename="recipients.xlsx"' in resp.headers.get("content-disposition", "")

    # Verify the downloaded workbook can be parsed
    recipients = spreadsheet_parser.parse_recipients_file(resp.content, "recipients.xlsx")
    assert len(recipients) == 5
    assert recipients[0].recipient_name == "Ada Lovelace"
    assert recipients[0].recipient_email == "ada@example.com"


def test_upload_valid_xlsx_and_complete_lifecycle(client, db_session):
    """
    Submits an .xlsx spreadsheet via POST /api/v1/jobs/upload, verifies job creation,
    runs the background worker, and downloads the resulting ZIP archive.
    """
    xlsx_bytes = _create_test_xlsx(
        [
            ["recipient_name", "recipient_email", "custom_remarks"],
            ["Grace Hopper", "grace@example.com", "Compiler Pioneer"],
            ["Alan Turing", "alan@example.com", "Father of Computing"],
            ["Margaret Hamilton", "margaret@example.com", "Apollo Software Lead"],
        ]
    )

    form_data = {
        "event_name": "Distributed Systems Bootcamp 2026",
        "issuer_name": "Computing Foundation",
        "issue_date": "2026-10-11",
        "certificate_title": "Certificate of Distinction",
    }
    files = {
        "file": (
            "recipients.xlsx",
            io.BytesIO(xlsx_bytes),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 202
    data = response.json()
    job_id = data["job_id"]
    assert data["status"] == "PENDING"
    assert data["total_recipients"] == 3
    assert "status_url" in data

    # Worker claims and processes the job
    job = worker.claim_next_job(db_session)
    assert job is not None
    assert job.id == job_id
    worker.process_job(db_session, job)

    # Verify job status reaches COMPLETED
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["successful_count"] == 3
    assert status_data["failed_count"] == 0
    assert status_data["progress_percentage"] == 100.0

    # Download ZIP and verify contents
    zip_resp = client.get(f"/api/v1/jobs/{job_id}/download")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        file_list = zf.namelist()
        assert len(file_list) == 3
        assert any("Grace_Hopper" in name for name in file_list)
        assert any("Alan_Turing" in name for name in file_list)
        assert any("Margaret_Hamilton" in name for name in file_list)


def test_upload_valid_csv(client, db_session):
    """Verifies that CSV files are also cleanly ingested via the upload endpoint."""
    csv_bytes = _create_test_csv(
        "recipient_name,recipient_email,custom_remarks\n"
        "Katherine Johnson,katherine@example.com,NASA Mathematician\n"
        "Dorothy Vaughan,dorothy@example.com,FORTRAN Specialist\n"
    )

    form_data = {
        "event_name": "Space Exploration Seminar",
        "issuer_name": "NASA",
        "issue_date": "2026-10-11",
        "certificate_title": "Certificate of Achievement",
    }
    files = {"file": ("recipients.csv", io.BytesIO(csv_bytes), "text/csv")}

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["total_recipients"] == 2

    # Run worker to process
    job = worker.claim_next_job(db_session)
    assert job is not None
    worker.process_job(db_session, job)

    status_resp = client.get(f"/api/v1/jobs/{data['job_id']}")
    assert status_resp.json()["status"] == "COMPLETED"


def test_upload_missing_required_fields(client):
    """Ensures 422 error when mandatory form fields are omitted."""
    xlsx_bytes = _create_test_xlsx(
        [
            ["name", "email"],
            ["Alice", "alice@example.com"],
        ]
    )
    files = {
        "file": (
            "recipients.xlsx",
            io.BytesIO(xlsx_bytes),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    # Missing event_name and issuer_name
    response = client.post("/api/v1/jobs/upload", data={"issue_date": "2026-10-11"}, files=files)
    assert response.status_code == 422


def test_upload_empty_file(client):
    """Ensures 400 error when an empty 0-byte file is uploaded."""
    form_data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer",
        "issue_date": "2026-10-11",
    }
    files = {
        "file": ("empty.xlsx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_unsupported_file_extension(client):
    """Ensures 400 error when non-spreadsheet file is uploaded."""
    form_data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer",
        "issue_date": "2026-10-11",
    }
    files = {"file": ("document.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 400
    assert "unsupported file format" in response.json()["detail"].lower()


def test_upload_corrupted_xlsx_file(client):
    """Ensures 400 error when invalid bytes are sent as .xlsx."""
    form_data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer",
        "issue_date": "2026-10-11",
    }
    files = {
        "file": (
            "corrupt.xlsx",
            io.BytesIO(b"not an excel zip archive"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"].lower()


def test_upload_missing_name_column(client):
    """Ensures 422 error when spreadsheet has no recognizable name column."""
    xlsx_bytes = _create_test_xlsx(
        [
            ["phone_number", "department", "salary"],
            ["1234567890", "Engineering", "100000"],
        ]
    )
    form_data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer",
        "issue_date": "2026-10-11",
    }
    files = {
        "file": (
            "recipients.xlsx",
            io.BytesIO(xlsx_bytes),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 422
    assert "missing required" in response.json()["detail"].lower()


def test_upload_invalid_email_format(client):
    """Ensures 422 error when a row has an invalid email address."""
    xlsx_bytes = _create_test_xlsx(
        [
            ["recipient_name", "recipient_email"],
            ["John Doe", "not-a-valid-email-address"],
        ]
    )
    form_data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer",
        "issue_date": "2026-10-11",
    }
    files = {
        "file": (
            "recipients.xlsx",
            io.BytesIO(xlsx_bytes),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 422
    assert "validation failed" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


def test_upload_duplicate_recipients(client):
    """Ensures 422 error when spreadsheet contains duplicate recipient entries."""
    xlsx_bytes = _create_test_xlsx(
        [
            ["recipient_name", "recipient_email"],
            ["Alice Cooper", "alice@example.com"],
            ["Alice Cooper", "alice@example.com"],
        ]
    )
    form_data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer",
        "issue_date": "2026-10-11",
    }
    files = {
        "file": (
            "recipients.xlsx",
            io.BytesIO(xlsx_bytes),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 422
    assert "duplicate" in response.json()["detail"].lower()


def test_upload_empty_spreadsheet_no_rows(client):
    """Ensures 422 error when spreadsheet has only headers and no recipient rows."""
    xlsx_bytes = _create_test_xlsx(
        [
            ["recipient_name", "recipient_email", "custom_remarks"],
        ]
    )
    form_data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer",
        "issue_date": "2026-10-11",
    }
    files = {
        "file": (
            "recipients.xlsx",
            io.BytesIO(xlsx_bytes),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/v1/jobs/upload", data=form_data, files=files)
    assert response.status_code == 422
    assert "does not contain any recipient rows" in response.json()["detail"].lower()
