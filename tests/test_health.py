"""
Tests for Health and Root Endpoints
"""


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "Bulk Certificate Generator"
    assert "docs" in data


def test_health_check_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db_connected"] is True
    assert data["storage_accessible"] is True


def test_root_health_alias_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db_connected"] is True
