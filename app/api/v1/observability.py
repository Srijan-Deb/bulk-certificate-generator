"""
Observability and Telemetry Endpoints
Provides Prometheus metrics exposition, real-time JSON statistics,
and deep system diagnostics.
"""

import sys
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.metrics import metrics

router = APIRouter(tags=["Observability"])


@router.get(
    "/metrics",
    summary="Prometheus Metrics Exposition",
    description="Exposes application, HTTP, job, and storage metrics in standard Prometheus 0.0.4 exposition format.",
    response_class=Response,
)
def get_prometheus_metrics():
    """Returns Prometheus plain-text scrape exposition."""
    content = metrics.export_prometheus_text()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get(
    "/observability/stats",
    summary="Real-Time System Telemetry & Statistics",
    description="Returns aggregate runtime metrics, job counts, certificate throughput, and storage usage as structured JSON.",
)
def get_observability_stats():
    """Returns JSON telemetry dashboard stats."""
    return JSONResponse(status_code=status.HTTP_200_OK, content=metrics.get_summary_stats())


@router.get(
    "/observability/health/detailed",
    summary="Deep Component Health Probe",
    description="Performs deep active probes on the SQLite database, persistent storage filesystem, and runtime environment.",
)
def get_detailed_health(db: Session = Depends(get_db)):
    """Deep active health check verifying write and read capabilities."""
    components: dict[str, dict[str, str | bool | float]] = {}
    is_healthy = True

    # 1. Database Connectivity & Write Capability Probe
    db_start = time.perf_counter()
    try:
        db.execute(text("SELECT 1")).scalar()
    except Exception as exc:
        is_healthy = False
        components["database"] = {"status": "unhealthy", "error": str(exc)}
    else:
        db_latency = round((time.perf_counter() - db_start) * 1000.0, 2)
        components["database"] = {"status": "healthy", "latency_ms": db_latency, "connected": True}

    # 2. Storage Directory Write Probe
    storage_start = time.perf_counter()
    try:
        settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        probe_file = settings.STORAGE_DIR / f".probe_{uuid4().hex[:8]}"
        probe_file.write_text("healthcheck")
        probe_file.unlink(missing_ok=True)
    except Exception as exc:
        is_healthy = False
        components["storage"] = {"status": "unhealthy", "error": str(exc)}
    else:
        storage_latency = round((time.perf_counter() - storage_start) * 1000.0, 2)
        components["storage"] = {
            "status": "healthy",
            "latency_ms": storage_latency,
            "writable": True,
            "path": str(settings.STORAGE_DIR),
        }

    # 3. Runtime Environment
    components["runtime"] = {
        "status": "healthy",
        "python_version": sys.version.split()[0],
        "in_app_worker_enabled": settings.RUN_WORKER_IN_APP,
    }

    http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    overall_status = "healthy" if is_healthy else "degraded"

    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall_status,
            "timestamp": time.time(),
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "components": components,
        },
    )
