"""
API v1 Router Aggregator
Combines health, jobs, and certificate endpoints.
"""

from fastapi import APIRouter

from app.api.v1.certificates import router as certificates_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.observability import router as observability_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(jobs_router)
api_router.include_router(certificates_router)
api_router.include_router(observability_router)
