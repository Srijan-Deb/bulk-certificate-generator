"""
FastAPI Application Entry Point
Configures application lifespan, CORS, middleware, global error handling,
and OpenAPI route registration.
"""

import threading
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine, get_db
from app.services.worker import worker

# Initialize structured logging
logger = setup_logging()

# Background thread handle for in-app worker
_worker_thread = None
_worker_stop_event = threading.Event()


def _in_app_worker_runner():
    """Runs the worker polling loop in a daemon thread for single-command development."""
    logger.info("In-app background worker thread started.")
    while not _worker_stop_event.is_set():
        try:
            job_processed = worker.process_one_pending_job()
            if not job_processed:
                # Sleep in short slices so stop event can terminate promptly
                for _ in range(int(settings.WORKER_POLL_INTERVAL_SECONDS * 10)):
                    if _worker_stop_event.is_set():
                        break
                    time.sleep(0.1)
        except Exception:
            logger.exception("Error in background worker thread")
            time.sleep(1.0)
    logger.info("In-app background worker thread terminated.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown hooks."""
    # 1. Startup: Auto-create database tables
    logger.info("Initializing database schema on %s...", settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Startup: Optional in-app worker
    global _worker_thread
    if settings.RUN_WORKER_IN_APP:
        _worker_stop_event.clear()
        _worker_thread = threading.Thread(target=_in_app_worker_runner, daemon=True, name="WorkerDaemon")
        _worker_thread.start()

    logger.info("%s ready to accept requests.", settings.PROJECT_NAME)
    yield

    # 3. Shutdown
    if settings.RUN_WORKER_IN_APP and _worker_thread:
        logger.info("Stopping background worker thread...")
        _worker_stop_event.set()
        _worker_thread.join(timeout=3.0)
    logger.info("Application shutdown complete.")


# FastAPI Application Definition
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade, zero-cost Bulk Certificate Generator Backend API. "
        "Accepts bulk recipients, renders verified vector PDF certificates, "
        "tracks asynchronous progress with isolated fault-tolerance, and provides bulk downloads."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security Headers & Request Body Size Limit Middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_PAYLOAD_SIZE_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "detail": f"Request payload exceeds allowable limit of {settings.MAX_PAYLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
                "error_code": "PAYLOAD_TOO_LARGE",
            },
        )

    response = await call_next(request)

    # Standard OWASP Defensive Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Global Exception Handlers
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_code": exc.__class__.__name__, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Input validation error",
            "error_code": "VALIDATION_ERROR",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(Exception)
async def handle_unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled server exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing your request.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


# Register Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }


@app.get("/health", include_in_schema=False)
def health_alias(db=Depends(get_db)):
    from app.api.v1.health import health_check

    return health_check(db=db)
