"""
Automated Tests for Observability Suite
Tests distributed request tracing, Prometheus metrics export, structured JSON telemetry,
active component health probes, and worker metric hooks.
"""

from app.core.metrics import metrics
from app.services.worker import worker


def test_request_id_and_process_time_headers(client):
    """Verifies that every HTTP response is decorated with correlation tracing headers."""
    # 1. Without client-supplied X-Request-ID
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"].startswith("req_")
    assert "x-process-time" in response.headers
    assert response.headers["x-process-time"].endswith("ms")

    # 2. With client-supplied X-Request-ID
    custom_trace = "trace-corp-gateway-98765"
    response2 = client.get("/api/v1/health", headers={"X-Request-ID": custom_trace})
    assert response2.status_code == 200
    assert response2.headers["x-request-id"] == custom_trace


def test_prometheus_metrics_endpoints(client):
    """Verifies that both /metrics and /api/v1/metrics expose valid Prometheus 0.0.4 text format."""
    for endpoint in ("/metrics", "/api/v1/metrics"):
        response = client.get(endpoint)
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        text = response.text
        assert "# HELP http_requests_total" in text
        assert "# TYPE http_requests_total counter" in text
        assert "process_uptime_seconds" in text
        assert "http_requests_in_flight" in text
        assert "storage_certificates_total" in text
        assert "storage_used_bytes" in text


def test_observability_stats_json_endpoint(client):
    """Verifies structured JSON telemetry stats endpoint."""
    response = client.get("/api/v1/observability/stats")
    assert response.status_code == 200
    data = response.json()

    assert "application" in data
    assert data["application"]["name"] == "Bulk Certificate Generator"
    assert data["application"]["uptime_seconds"] >= 0.0

    assert "http" in data
    assert data["http"]["total_requests"] >= 1
    assert "in_flight" in data["http"]
    assert "error_rate_percentage" in data["http"]

    assert "jobs" in data
    assert "submitted_total" in data["jobs"]
    assert "completed_total" in data["jobs"]

    assert "certificates" in data
    assert "generated_success" in data["certificates"]
    assert "generated_failed" in data["certificates"]
    assert "avg_render_latency_ms" in data["certificates"]

    assert "storage" in data
    assert "stored_pdf_count" in data["storage"]
    assert "bytes_used" in data["storage"]
    assert "human_readable_size" in data["storage"]


def test_detailed_health_probe(client):
    """Verifies deep active component health checks for database and filesystem."""
    response = client.get("/api/v1/observability/health/detailed")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ("healthy", "degraded")
    assert "components" in data
    assert "database" in data["components"]
    assert data["components"]["database"]["connected"] is True
    assert "latency_ms" in data["components"]["database"]

    assert "storage" in data["components"]
    assert data["components"]["storage"]["writable"] is True
    assert "latency_ms" in data["components"]["storage"]


def test_kubernetes_liveness_and_readiness_probes(client):
    """Verifies standard cloud-native liveness and readiness probe contracts."""
    # Liveness Probe
    live_resp = client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "alive"

    # Readiness Probe
    ready_resp = client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    data = ready_resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "ok"
    assert data["storage"] == "ok"


def test_worker_records_observability_metrics(client, db_session):
    """Ensures worker processing cycles correctly update Prometheus metrics counters and histograms."""
    initial_stats = metrics.get_summary_stats()
    initial_jobs_completed = initial_stats["jobs"]["completed_total"]
    initial_certs_success = initial_stats["certificates"]["generated_success"]

    # Submit a job
    payload = {
        "event_name": "Observability Certification 2026",
        "issuer_name": "SRE Foundation",
        "issue_date": "2026-10-11",
        "certificate_title": "Certificate of Reliability",
        "recipients": [
            {"recipient_name": "Site Reliability Engineer Alice", "recipient_email": "alice.sre@example.com"},
            {"recipient_name": "Observability Specialist Bob", "recipient_email": "bob.obs@example.com"},
        ],
    }
    submit_resp = client.post("/api/v1/jobs", json=payload)
    assert submit_resp.status_code == 202
    job_id = submit_resp.json()["job_id"]

    # Worker executes job
    claimed_job = worker.claim_next_job(db_session)
    assert claimed_job is not None
    assert claimed_job.id == job_id
    worker.process_job(db_session, claimed_job)

    # Verify metrics updated
    updated_stats = metrics.get_summary_stats()
    assert updated_stats["jobs"]["completed_total"] == initial_jobs_completed + 1
    assert updated_stats["certificates"]["generated_success"] == initial_certs_success + 2
    assert updated_stats["certificates"]["avg_render_latency_ms"] > 0.0

    # Verify Prometheus exposition includes recorded certificate latency histogram
    prom_text = metrics.export_prometheus_text()
    assert "certificate_render_duration_seconds_count" in prom_text
    assert "jobs_completed_total{status=\"COMPLETED\"}" in prom_text


def test_path_normalization_protects_cardinality(client):
    """Ensures dynamic IDs are replaced with placeholders in metrics to prevent metric cardinality explosion."""
    # Call an endpoint with a specific job_id
    fake_uuid = "12345678-1234-1234-1234-123456789abc"
    client.get(f"/api/v1/jobs/{fake_uuid}")

    prom_text = metrics.export_prometheus_text()
    # The normalized placeholder should be in the metric, NOT the raw fake_uuid
    assert f'path="/api/v1/jobs/{fake_uuid}"' not in prom_text
    assert 'path="/api/v1/jobs/{job_id}"' in prom_text
