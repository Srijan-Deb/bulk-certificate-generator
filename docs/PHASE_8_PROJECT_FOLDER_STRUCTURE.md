# Phase 8 — Project Folder Structure Specification

## 1. Architectural Layout Rationale

The **Bulk Certificate Generator** follows a **Layered Modular Monolith** architecture. This structure balances clean separation of concerns, enterprise maintainability, and pragmatic simplicity. 

In strict accordance with the project guidelines:
> *"Modify the structure when technically appropriate. Do not create empty modules or unnecessary layers just to make the project look complex."*

We avoid creating artificial single-line pass-through abstractions (e.g. redundant "Repository" classes that merely wrap `db.query()`), while organizing controllers, data access, business services, background processing, and tests into dedicated, cohesive directories.

---

## 2. Directory Tree & Component Responsibilities

```
bulk-certificate-generator/
├── app/
│   ├── main.py                     # FastAPI application factory, lifespan hooks, middleware, & global error handlers
│   ├── api/
│   │   ├── deps.py                 # Dependency injection providers (db sessions, X-API-Key auth guard)
│   │   └── v1/
│   │       ├── router.py           # V1 API router aggregation
│   │       ├── jobs.py             # Bulk job submission, status polling, recipient listing, ZIP downloads
│   │       ├── certificates.py     # Individual PDF download endpoint & path validation
│   │       └── health.py           # Liveness & readiness probes (/api/v1/health)
│   ├── core/
│   │   ├── config.py               # Strongly typed settings via Pydantic BaseSettings (.env loading)
│   │   ├── errors.py               # Domain-specific exception hierarchy (RFC 7807 compatible)
│   │   └── logging.py              # Structured logging configuration
│   ├── db/
│   │   ├── base.py                 # DeclarativeBase foundation for SQLAlchemy 2.0 ORM models
│   │   └── session.py              # Engine factory, SQLite WAL mode pragmas, & sessionmaker
│   ├── models/
│   │   ├── enums.py                # JobStatus and CertificateStatus enumerations
│   │   ├── job.py                  # GenerationJob ORM model (metadata, counters, timestamps)
│   │   └── certificate.py          # CertificateRecord ORM model (recipient, cert_id, status, error info)
│   ├── schemas/
│   │   ├── common.py               # Standard API response wrappers & error models
│   │   ├── recipient.py            # RecipientInput and CertificateRecordResponse Pydantic schemas
│   │   └── job.py                  # BulkCreateJobRequest, JobStatusResponse, JobAcceptedResponse
│   └── services/
│       ├── certificate_service.py  # Zero-cost ReportLab PDF vector rendering engine with pypdf validation
│       ├── job_service.py          # Job orchestration, counter aggregation, security checks, ZIP packaging
│       └── worker.py               # Database-backed background worker with atomic claims & crash recovery
├── alembic/                        # Version-controlled database schema migrations
│   ├── env.py                      # Alembic runtime configuration & model metadata binding
│   ├── script.py.mako              # Migration file template
│   └── versions/                   # Migration revision scripts (e.g. initial_schema.py)
├── templates/                      # Predefined certificate template specifications & documentation
│   └── README.md                   # ReportLab vector layout documentation, coordinates, and typography
├── generated_certificates/          # Storage documentation & authorized storage reference
│   └── README.md                   # Path structure, retention policy, and directory permissions
├── storage/                        # Persistent volume mount for production deployment
│   └── certificates/               # Partitioned certificate output: storage/certificates/{job_id}/
├── tests/                          # Automated Pytest suite (28/28 tests passing)
│   ├── conftest.py                 # Fixtures (in-memory SQLite session, TestClient, monkeypatching)
│   ├── test_health.py              # Health check endpoints & root redirects
│   ├── test_validation.py          # Pydantic v2 input validations & in-batch duplicate checks
│   ├── test_pdf_generation.py      # ReportLab canvas output, auto-scaling, verification codes, pypdf
│   ├── test_job_lifecycle.py       # End-to-end bulk job lifecycle from PENDING to COMPLETED
│   ├── test_failure_isolation.py   # Partial recipient failure isolation tests
│   ├── test_worker_recovery.py     # Worker crash recovery & atomic claiming deduplication tests
│   ├── test_retrieval.py           # Single PDF download & batch ZIP archive packaging tests
│   └── test_security.py            # OWASP headers, payload size limit, API key auth, path traversal
├── migrations/                     # Migration reference documentation
│   └── README.md                   # Guide to applying Alembic migrations and CLI commands
├── scripts/                        # Automation & pre-flight verification scripts
│   ├── verify_system.py            # Pre-flight environment check (Python, DB, ReportLab, pypdf)
│   └── create_demo_job.py          # Client demonstration script (submits batch, polls, downloads ZIP)
├── .env.example                    # Template environment variables for development & production
├── .gitignore                      # Git exclusion rules (virtualenv, data.db, .env, storage/)
├── requirements.txt                # Pinned production and test dependencies
├── pyproject.toml                  # Project metadata, Ruff linter settings, and Pytest configuration
├── Dockerfile                      # Multi-stage lightweight, non-root, secure Docker container
├── docker-compose.yml              # Multi-container orchestration (API + Worker + Shared Storage)
├── compose.yaml                    # Modern Docker Compose v2 canonical specification
├── worker_runner.py                # Standalone entrypoint for dedicated background worker container
└── README.md                       # Comprehensive project documentation & quickstart guide
```

---

## 3. Detailed File Responsibility Matrix

| Path | Primary Responsibility | Key Classes / Functions |
| :--- | :--- | :--- |
| `app/main.py` | Application entry point; registers routers, CORS, request size limit middleware, OWASP headers, and starts optional in-app worker thread. | `app`, `lifespan()`, `security_middleware()` |
| `app/api/deps.py` | FastAPI dependency injection provider. Yields scoped DB sessions and validates optional `X-API-Key` headers. | `get_db()`, `verify_api_key()` |
| `app/api/v1/jobs.py` | Handles `POST /jobs` (accepts batch), `GET /jobs/{id}` (real-time status), `GET /jobs/{id}/certificates`, and `GET /jobs/{id}/download` (ZIP). | `create_bulk_job()`, `get_job_status()` |
| `app/api/v1/certificates.py` | Handles `GET /certificates/{cert_id}/download` for individual PDF downloads with path traversal defenses. | `download_certificate()` |
| `app/api/v1/health.py` | Liveness & readiness probes verifying DB connectivity. | `health_check()` |
| `app/core/config.py` | Parses and validates environment variables into strongly typed settings via `pydantic-settings`. | `Settings`, `settings` |
| `app/core/errors.py` | Defines domain exceptions mapped to standard HTTP status codes. | `AppError`, `JobNotFoundError`, `SecurityViolationError` |
| `app/core/logging.py` | Configures structured logging with ISO timestamps and component loggers. | `setup_logging()` |
| `app/db/session.py` | Configures SQLite engine with WAL mode (`PRAGMA journal_mode=WAL`), busy timeouts (5000ms), and scoped sessions. | `engine`, `SessionLocal`, `set_sqlite_pragma()` |
| `app/models/job.py` | SQLAlchemy ORM model for generation jobs with counters and timestamps. | `GenerationJob` |
| `app/models/certificate.py` | SQLAlchemy ORM model for individual recipient certificates. | `CertificateRecord` |
| `app/schemas/job.py` | Pydantic v2 validation models for batch submission and status responses. | `BulkCreateJobRequest`, `JobStatusResponse` |
| `app/services/certificate_service.py` | Predefined ReportLab vector PDF rendering engine, dynamic font scaling, SHA-256 verification codes, and pypdf validation. | `CertificateGenerator`, `certificate_generator` |
| `app/services/job_service.py` | Job domain logic: ACID batch persistence, multi-counter aggregation, path containment checks, and ZIP packaging. | `JobService`, `job_service` |
| `app/services/worker.py` | Database-backed worker: atomic conditional claims (`UPDATE ... WHERE status='PENDING'`), error isolation, and crash recovery. | `JobWorker`, `worker` |
| `worker_runner.py` | Standalone CLI entrypoint for running the background worker in a dedicated container or process. | `if __name__ == '__main__': worker.run_worker_loop()` |
| `scripts/verify_system.py` | Pre-flight probe verifying Python version, dependencies, SQLite WAL mode, and canvas compilation. | `verify_system()` |
| `scripts/create_demo_job.py` | Interactive client script submitting demo batch, polling status, and downloading output ZIP. | `main()` |
| `Dockerfile` | Multi-stage Docker image running as non-root `appuser` (UID 1001) with curl healthchecks. | `FROM python:3.13-slim` |
| `compose.yaml` | Multi-container Compose service running API and Worker containers with shared persistent volume mount. | `services: api, worker` |
