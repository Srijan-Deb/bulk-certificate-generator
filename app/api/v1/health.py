"""
Health Check and Liveness / Readiness Probes
Verifies system health, database connectivity, and file storage access.
"""

from fastapi import APIRouter, Depends, status
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
