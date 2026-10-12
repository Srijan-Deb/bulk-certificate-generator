"""
Health Check and Liveness / Readiness Probes
Verifies system health, database connectivity, and file storage access.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health & Readiness Probe",
    description="Checks the health of the application, database connectivity, and persistent storage availability.",
)
def health_check(db: Session = Depends(get_db)):
    # 1. Database Ping
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    # 2. Storage Directory Check
    storage_ready = settings.STORAGE_DIR.exists() and settings.STORAGE_DIR.is_dir()

    system_status = "ok" if (db_connected and storage_ready) else "degraded"

    return HealthResponse(
        status=system_status,
        db_connected=db_connected,
        storage_accessible=storage_ready,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Kubernetes Liveness Probe",
    description="Fast non-blocking check verifying whether the web server process is running and accepting connections.",
)
def liveness_probe():
    return {"status": "alive", "version": settings.APP_VERSION}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Kubernetes Readiness Probe",
    description="Verifies that all operational dependencies (database connection and storage) are ready to handle traffic.",
)
def readiness_probe(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    storage_ok = settings.STORAGE_DIR.exists() and settings.STORAGE_DIR.is_dir()

    if db_ok and storage_ok:
        return {"status": "ready", "database": "ok", "storage": "ok"}

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "not_ready",
            "database": "ok" if db_ok else "failed",
            "storage": "ok" if storage_ok else "failed",
        },
    )
