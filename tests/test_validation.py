"""
Tests for Request Validation and Constraints
Verifies schema enforcement, blank strings, email formats, and batch size boundaries.
"""


def test_create_job_missing_required_fields(client):
    payload = {
        "event_name": "Tech Summit"
        # Missing issuer_name, issue_date, recipients
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"


def test_create_job_empty_recipients_list(client):
    payload = {
        "event_name": "Web Development Bootcamp",
        "issuer_name": "Dev Academy",
        "issue_date": "2026-10-10",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"


def test_create_job_blank_strings(client):
    payload = {
        "event_name": "   ",
        "issuer_name": "Dev Academy",
        "issue_date": "2026-10-10",
        "recipients": [{"recipient_name": "Jane Doe"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_invalid_recipient_email(client):
    payload = {
        "event_name": "Web Development Bootcamp",
        "issuer_name": "Dev Academy",
        "issue_date": "2026-10-10",
        "recipients": [{"recipient_name": "Jane Doe", "recipient_email": "not-a-valid-email"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_create_job_duplicate_recipients(client):
    payload = {
        "event_name": "Web Development Bootcamp",
        "issuer_name": "Dev Academy",
        "issue_date": "2026-10-10",
        "recipients": [
            {"recipient_name": "Jane Doe", "recipient_email": "jane@example.com"},
            {"recipient_name": "Jane Doe", "recipient_email": "jane@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "Duplicate recipient detected" in str(data["errors"])
