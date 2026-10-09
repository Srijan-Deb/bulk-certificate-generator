# 🎓 Bulk Certificate Generator Backend API

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Pytest](https://img.shields.io/badge/pytest-passed%2031%2F31-brightgreen.svg)](https://pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://pytest-cov.readthedocs.io/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-black.svg)](https://github.com/astral-sh/ruff)
[![Cost](https://img.shields.io/badge/infrastructure%20cost-%E2%82%B90%20(Zero--Cost)-green.svg)](#-zero-cost-financial-ledger)

A production-grade, fault-tolerant, interview-ready Bulk Certificate Generator Backend API built with **Python, FastAPI, SQLAlchemy 2.0, ReportLab, and Alembic**. Designed around an asynchronous database-backed job model that handles bulk recipient generation with isolated error handling and zero cloud or licensing costs ($0.00 / ₹0.00).

---

## 📑 Table of Contents
1. [Project Overview & Key Features](#-project-overview--key-features)
2. [Zero-Cost Financial Ledger (₹0 Cost Model)](#-zero-cost-financial-ledger)
3. [System Architecture](#-system-architecture)
4. [Technology Stack](#-technology-stack)
5. [Project Directory Structure](#-project-directory-structure)
6. [Prerequisites & Quickstart Installation](#-prerequisites--quickstart-installation)
7. [Running the Application and Worker](#-running-the-application-and-worker)
8. [API Specification & Endpoints](#-api-specification--endpoints)
9. [Sample Workflows & Example JSON Payloads](#-sample-workflows--example-json-payloads)
10. [Automated Testing & QA](#-automated-testing--qa)
11. [Performance Benchmarks & Storage Density](#-performance-benchmarks--storage-density)
12. [Deployment Guide (Local & Verified Free Cloud)](#-deployment-guide)
13. [Backups & Storage Retention Policy](#-backups--storage-retention-policy)
14. [Troubleshooting Guide](#-troubleshooting-guide)
15. [Design Decisions & Trade-Offs](#-design-decisions--trade-offs)
16. [Security Considerations](#-security-considerations)
17. [Known Limitations & Future Improvements](#-known-limitations--future-improvements)

---

## 🌟 Project Overview & Key Features

Bulk certificate generation is a frequent requirement for universities, bootcamps, and virtual conferences. Traditional solutions rely on paid SaaS APIs or unstable headless browser converters (Puppeteer/Chrome) that suffer from massive memory overhead, network timeouts, and unpredictable costs.

This project delivers a **100% free, purely programmatic vector rendering engine** coupled with a **durable, database-backed background worker** that ensures zero dropped jobs and per-recipient fault containment.

### Core Features
- **High-Throughput Vector PDF Engine**: Renders high-resolution A4 landscape certificates in ~25ms per certificate (~40 certs/second) using ReportLab vector drawing primitives.
- **Dynamic Font Auto-Scaling**: Iteratively computes text width with `canvas.stringWidth()` to dynamically downscale long recipient names (e.g. 70+ characters) without border collision or clipping.
- **Cryptographic Verification Codes**: Generates deterministic SHA-256 verification codes (`V-XXXX-XXXX-XXXX`) binding job ID, certificate ID, and recipient name together for authenticity checks.
- **Post-Generation Structural Integrity**: Every output PDF is opened and parsed with `pypdf.PdfReader` before saving; corrupted outputs are unlinked and marked `FAILED` without failing the batch.
- **Fault-Isolated Bulk Processing**: An individual recipient failure (e.g. corrupted name, empty string) does not halt the batch. Valid recipients generate successfully, and the batch concludes as `COMPLETED_WITH_ERRORS`.
- **Atomic Compare-and-Swap Claiming**: Worker concurrency uses `UPDATE generation_jobs SET status='PROCESSING' WHERE id=:id AND status='PENDING'`, preventing duplicate execution across multiple workers without requiring Redis or distributed locks.
- **Worker Crash Recovery**: Automatically identifies jobs stranded in `PROCESSING` after a worker death or server reboot (`recover_stale_jobs`), resetting in-flight records to `PENDING` while preserving already generated `SUCCESS` records.
- **Comprehensive API & Retrieval**: Immediate `202 Accepted` response with status polling, individual PDF download, and streaming batch ZIP compression.
- **Defense-in-Depth Security**: OWASP security headers, 10 MB payload limits, path traversal shields, and optional `X-API-Key` authentication.

---

## 💰 Zero-Cost Financial Ledger

This application strictly satisfies a **₹0 ($0.00) Zero-Cost Model**. No paid cloud services, no proprietary APIs, and no credit card requirements.

| Layer | Technology | License / Pricing Tier | Cost |
| :--- | :--- | :--- | :--- |
| **Language** | Python 3.11 - 3.13 | Open Source (PSFL) | **₹0** |
| **Framework** | FastAPI + Uvicorn | MIT License | **₹0** |
| **Database** | SQLite WAL Mode / Local PostgreSQL | Public Domain / Open Source | **₹0** |
| **ORM & Migrations**| SQLAlchemy 2.0 + Alembic | MIT License | **₹0** |
| **Data Validation** | Pydantic v2 + email-validator | MIT License | **₹0** |
| **PDF Rendering** | ReportLab Open-Source Engine | BSD License | **₹0** |
| **PDF Validation** | pypdf | BSD 3-Clause | **₹0** |
| **Testing & Quality**| Pytest + pytest-cov + Ruff | MIT License | **₹0** |
| **Containers** | Docker Community Edition | Free | **₹0** |
| **Local Deployment**| Localhost / Bare-Metal / Docker | Developer Host | **₹0** |
| **Cloud Hosting** | Oracle Cloud Infrastructure (OCI Always Free) | Permanent Free Tier | **₹0** |
| **Total Project Cost**| — | — | **₹0 / $0** |

---

## 🏛 System Architecture

The application implements a **Layered Modular Monolith with an Asynchronous Database-Backed Job Worker**:

```
                           +------------------------+
                           |       API Client       |
                           | (cURL / Swagger / App) |
                           +-----------+------------+
                                       |
                       1. POST /jobs   | 4. Polling & Retrieval
                      (Bulk Recipient) | (GET /jobs/{id}, GET /download)
                                       v
                     +------------------------------------+
                     |        FastAPI Web Service         |
                     |  - Pydantic v2 Input Validation    |
                     |  - Transactional Job Ingestion     |
                     |  - Non-blocking HTTP 202 Accepted  |
                     +-----------------+------------------+
                                       |
                        2. Write State | 5. Read Status
                                       v
                     +------------------------------------+
                     |       Relational Database          |
                     |    (SQLite WAL / PostgreSQL)       |
                     |  - generation_jobs                 |
                     |  - certificate_records             |
                     +-----------------+------------------+
                                       |
                     3. Atomic Claim   | Update Progress
                     & Fetch Batch     | (Heartbeat & Counters)
                                       v
                     +------------------------------------+
                     |      Background Job Worker         |
                     |  - Atomic Claim (UPDATE ... WHERE) |
                     |  - Per-Recipient Fault Isolation   |
                     |  - ReportLab PDF Vector Engine     |
                     |  - Stale Crash Recovery Policy     |
                     +-----------------+------------------+
                                       |
                                       | Saves PDF
                                       v
                     +------------------------------------+
                     |    Persistent Storage Directory    |
                     |   `./storage/certificates/{job}/`  |
                     +------------------------------------+
```

---

## 🛠 Technology Stack

- **FastAPI**: Async ASGI web framework with OpenAPI / Swagger UI interactive documentation.
- **SQLAlchemy 2.0**: Typed ORM leveraging `Mapped` and `mapped_column` with strict transactional control.
- **SQLite (WAL Mode)**: Write-Ahead Logging (`PRAGMA journal_mode=WAL`) enabling concurrent non-blocking reads during active writes with 5000ms busy timeout.
- **Alembic**: Database schema migration framework.
- **ReportLab**: High-speed, zero-cost vector PDF drawing engine.
- **pypdf**: Structural PDF inspection and page-tree validation.
- **Pydantic v2**: Type enforcement, string trimming, email verification, and duplicate recipient detection.
- **Pytest & pytest-cov**: Automated testing framework with statement coverage reporting.
- **Ruff**: Modern Python linter and code formatter.
- **Docker & Docker Compose**: Multi-stage, non-root (`appuser`, UID 1001) containerization.

---

## 📂 Project Directory Structure

```
bulk-certificate-generator/
├── app/
│   ├── main.py                     # FastAPI application factory, lifespan hooks, middleware
│   ├── api/
│   │   ├── deps.py                 # Dependency injection (DB session, API key verification)
│   │   └── v1/
│   │       ├── router.py           # API v1 router aggregation
│   │       ├── jobs.py             # Job submission, status polling, recipient lists, ZIP downloads
│   │       ├── certificates.py     # Single certificate PDF download endpoint
│   │       └── health.py           # Liveness & readiness probes
│   ├── core/
│   │   ├── config.py               # Strongly typed settings via Pydantic BaseSettings
│   │   ├── errors.py               # Standardized domain exceptions
│   │   └── logging.py              # Structured logging configuration
│   ├── db/
│   │   ├── base.py                 # DeclarativeBase foundation for ORM models
│   │   └── session.py              # SQLite WAL mode pragmas & SessionLocal factory
│   ├── models/
│   │   ├── enums.py                # JobStatus and CertificateStatus enumerations
│   │   ├── job.py                  # GenerationJob ORM model
│   │   └── certificate.py          # CertificateRecord ORM model
│   ├── schemas/
│   │   ├── common.py               # Standard API response schemas
│   │   ├── recipient.py            # RecipientInput and CertificateRecordResponse schemas
│   │   └── job.py                  # BulkCreateJobRequest, JobStatusResponse schemas
│   └── services/
│       ├── certificate_service.py  # ReportLab PDF rendering engine with pypdf validation
│       ├── job_service.py          # Job orchestration, counter aggregation, ZIP packaging
│       └── worker.py               # Database-backed background worker with crash recovery
├── alembic/                        # Version-controlled database migrations
├── templates/                      # Certificate layout specifications and assets
├── generated_certificates/          # Storage documentation and retention rules
├── storage/certificates/           # Output directory for generated PDF certificates
├── tests/                          # 31 unit, integration, and security tests (90% coverage)
├── scripts/
│   ├── verify_system.py            # Pre-flight environment check
│   ├── create_demo_job.py          # End-to-end client demo script
│   ├── benchmark_performance.py    # Performance & storage density benchmark suite
│   ├── backup_restore.py           # Online SQLite WAL backup and restoration utility
│   └── cleanup_retention.py        # 72-hour storage retention cleanup script
├── .env.example                    # Environment configuration template
├── .gitignore                      # Git exclusion rules
├── requirements.txt                # Pinned production dependencies
├── pyproject.toml                  # Project metadata, Ruff, and Pytest configuration
├── Dockerfile                      # Non-root, multi-stage production container
├── compose.yaml                    # Canonical Docker Compose v2 specification
├── docker-compose.yml              # Legacy Docker Compose specification
├── worker_runner.py                # Standalone entrypoint for dedicated background worker
└── README.md                       # Master project documentation
```

---

## ⚡ Prerequisites & Quickstart Installation

### Prerequisites
- Python 3.11, 3.12, or 3.13 installed.
- Git installed.

### Installation Steps
```bash
# 1. Clone repository
git clone <repo-url>
cd "Bulk Certificate Generator"

# 2. Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Configure environment
# Windows:
copy .env.example .env
# Linux / macOS:
cp .env.example .env

# 5. Initialize database schema
alembic upgrade head
```

---

## 💻 Running the Application and Worker

### Mode A: Single-Process Developer Mode
By default, `RUN_WORKER_IN_APP=true` in `.env`. Starting FastAPI automatically spawns an in-process background worker thread:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Interactive ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Mode B: Decoupled Multi-Process Production Mode
Set `RUN_WORKER_IN_APP=false` in `.env`, then launch:

**Terminal 1 (Web API Server):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

**Terminal 2 (Dedicated Background Worker):**
```bash
python worker_runner.py
```

### Mode C: Docker Compose Multi-Container
```bash
docker compose up --build -d
```
Spawns `cert_generator_api`, `cert_generator_worker`, and mounts the shared persistent storage volume.

---

## 📡 API Specification & Endpoints

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/jobs` | Submit a bulk generation job (validates and enqueues) | `202 Accepted` |
| `GET` | `/api/v1/jobs/{job_id}` | Retrieve real-time job progress and multi-counter metrics | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/certificates` | List recipient certificates with status filtering | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/download` | Download all successful certificates as a ZIP archive | `200 OK` |
| `GET` | `/api/v1/certificates/{certificate_id}/download` | Download an individual certificate PDF | `200 OK` |
| `GET` | `/api/v1/health` | Service liveness probe and database connectivity check | `200 OK` |

---

## 📝 Sample Workflows & Example JSON Payloads

### 1. Submit Bulk Job (`POST /api/v1/jobs`)
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Distributed Systems Masterclass",
    "issuer_name": "Software Architecture Guild",
    "issue_date": "2026-10-10",
    "certificate_title": "Certificate of Excellence",
    "recipients": [
      {
        "recipient_name": "Ada Lovelace",
        "recipient_email": "ada@example.com",
        "custom_remarks": "First Programmer"
      },
      {
        "recipient_name": "Alan Turing",
        "recipient_email": "alan@example.com",
        "custom_remarks": "Father of Computing"
      }
    ]
  }'
```

**Response (`202 Accepted`):**
```json
{
  "job_id": "8f395804-b9b0-466d-a7ca-5c3b9b46e392",
  "status": "PENDING",
  "total_recipients": 2,
  "created_at": "2026-10-10T02:00:00Z",
  "status_url": "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392",
  "message": "Bulk certificate generation job accepted and queued for processing."
}
```

### 2. Poll Status (`GET /api/v1/jobs/{job_id}`)
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392"
```

**Response (`200 OK`):**
```json
{
  "job_id": "8f395804-b9b0-466d-a7ca-5c3b9b46e392",
  "status": "COMPLETED",
  "event_name": "Distributed Systems Masterclass",
  "issuer_name": "Software Architecture Guild",
  "issue_date": "2026-10-10",
  "certificate_title": "Certificate of Excellence",
  "total_recipients": 2,
  "successful_count": 2,
  "failed_count": 0,
  "pending_count": 0,
  "processing_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-10T02:00:00Z",
  "started_at": "2026-10-10T02:00:01Z",
  "completed_at": "2026-10-10T02:00:02Z",
  "zip_download_url": "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392/download"
}
```

### 3. Automated Demo Script
To see the full end-to-end workflow executed automatically:
```bash
python scripts/create_demo_job.py
```

---

## 🧪 Automated Testing & QA

Run the full automated test suite with statement coverage:
```bash
pytest -v --cov=app --cov-report=term-missing
```

### Actual Test Coverage
```text
======================= 31 passed, 7 warnings in 5.07s ========================
TOTAL STATEMENTS: 785 | COVERAGE: 90%
- app/api/deps.py:           100%
- app/api/v1/jobs.py:        100%
- app/core/config.py:        100%
- app/schemas/job.py:        100%
- app/services/certificate_service.py: 95%
- app/services/job_service.py:         90%
- app/services/worker.py:              74%
```

---

## 📊 Performance Benchmarks & Storage Density

Empirical benchmarks captured via [`scripts/benchmark_performance.py`](scripts/benchmark_performance.py):

| Batch Size ($N$) | Final Status | Processing Time | Avg Time / Cert | Peak RAM Allocated | Storage Used | Avg Size / PDF |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **10** | `COMPLETED` | 0.286 s | **28.64 ms** | **1.08 MB** | 32.3 KB | **3.23 KB** |
| **50** | `COMPLETED` | 1.289 s | **25.78 ms** | **0.82 MB** | 161.7 KB | **3.23 KB** |
| **100** | `COMPLETED` | 2.490 s | **24.90 ms** | **0.94 MB** | 323.4 KB | **3.23 KB** |
| **250** | `COMPLETED_WITH_ERRORS` | 6.332 s | **25.33 ms** | **1.34 MB** | 805.3 KB | **3.23 KB** |

- **Throughput**: ~39.5 certificates/second per single worker process.
- **Storage Density**: Each vector certificate requires only ~3.23 KB of storage. Over 300,000 certificates fit in 1 GB.

---

## 🚀 Deployment Guide

### Path A: Zero-Cost Local Production Deployment
Use Docker Compose:
```bash
docker compose up --build -d
```
The persistent volume `cert_data` preserves database state and certificates across container rebuilds.

### Path B: Verified Zero-Cost Cloud Deployment (Oracle Cloud Always Free)
> [!CAUTION]
> **The Ephemeral Filesystem Trap**: PaaS providers (Render, Koyeb, Railway) use ephemeral filesystems. Files written to disk are destroyed whenever containers sleep or redeploy. Furthermore, Render puts free web services to sleep after 15 minutes of inactivity, freezing background workers.

**Recommended Cloud Solution: Oracle Cloud (OCI Always Free)**
- Provides 2 x AMD Compute VMs OR 4 ARM cores (up to 24 GB RAM free) with **200 GB persistent block storage included at $0 forever**.
- Compute runs 24/7 without sleep timeouts.

**OCI Deployment Blueprint:**
```bash
# 1. On Ubuntu 22.04 LTS VM:
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git nginx certbot python3-certbot-nginx

# 2. Clone repository & launch:
git clone <repo-url> bulk-certificate-generator
cd bulk-certificate-generator
cp .env.example .env
docker compose up --build -d

# 3. Setup NGINX with SSL:
sudo certbot --nginx -d certs.yourdomain.com
```

---

## 💾 Backups & Storage Retention Policy

### Online Safe Database Backup
SQLite WAL mode allows non-blocking online backups while writers are active:
```bash
# Create system backup (database + certificates):
python scripts/backup_restore.py backup ./backups

# Restore system state:
python scripts/backup_restore.py restore ./backups/cert_backup_YYYYMMDD_HHMMSS.tar.gz
```

### Storage Retention Pruning
Prune job directories older than `MAX_FILE_RETENTION_HOURS = 72`:
```bash
# Dry run:
python scripts/cleanup_retention.py --dry-run

# Active cleanup:
python scripts/cleanup_retention.py
```

---

## 🔧 Troubleshooting Guide

| Issue / Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| `sqlite3.OperationalError: database is locked` | Concurrent write lock contention on SQLite. | Ensure SQLite connection pragmas include `PRAGMA busy_timeout=5000;` and `PRAGMA journal_mode=WAL;`. |
| `ModuleNotFoundError: No module named 'pypdf'` | Missing dependency in virtual environment. | Run `pip install -r requirements.txt`. |
| `HTTP 413 PAYLOAD_TOO_LARGE` | Bulk submission payload exceeded 10 MB limit. | Reduce batch size or adjust `MAX_PAYLOAD_SIZE_BYTES` in `.env`. |
| `Job status stuck in PROCESSING` | Worker crashed mid-batch due to unexpected reboot. | Trigger worker loop; `recover_stale_jobs()` will automatically reset in-flight records and requeue the job. |
| `HTTP 401 AuthenticationError` | `API_KEY_ENABLED=True` but `X-API-Key` header missing or incorrect. | Provide `-H "X-API-Key: <key>"` or set `API_KEY_ENABLED=False` in `.env`. |

---

## ⚖️ Design Decisions & Trade-Offs

1. **Database-Backed Worker vs. Celery + Redis**:
   - *Decision*: Database-backed worker with atomic compare-and-swap SQL claims.
   - *Rationale*: Eliminates operational complexity and hosting costs ($0 Redis). Provides single-transaction ACID guarantees for batch ingestion.
2. **ReportLab vs. Headless Chrome (Puppeteer)**:
   - *Decision*: Pure programmatic ReportLab vector drawing.
   - *Rationale*: ReportLab uses 1 MB RAM and takes 25ms per certificate. Puppeteer consumes 300+ MB RAM and takes 1,500ms per certificate.
3. **SQLite WAL vs. PostgreSQL**:
   - *Decision*: SQLite WAL mode with busy timeout for default deployment.
   - *Rationale*: Zero-cost, zero-configuration local persistence that handles 40 certs/sec. Full migration path to PostgreSQL is supported via SQLAlchemy connection strings.

---

## 🔒 Security Considerations

- **OWASP Security Headers**: Enforces `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `X-XSS-Protection`.
- **Path Traversal Shield**: Canonical path resolution verifies files reside strictly within `STORAGE_DIR`.
- **Incomplete Download Shield**: Restricts downloads strictly to records with `status == 'SUCCESS'`.
- **Information Leakage Shield**: Global exception handlers sanitize server errors; stack traces and SQL queries are never leaked to clients.
- **Non-Root Container**: Runs as UID 1001 (`appuser`) in Docker.

---

## 🔮 Known Limitations & Future Improvements

- **Known Limitation**: SQLite supports a single writer at any given instant. At $>10$ concurrent workers, write lock contention increases.
- **Future Improvement 1**: PostgreSQL migration (`SELECT ... FOR UPDATE SKIP LOCKED`) for horizontal scaling across dozens of worker nodes.
- **Future Improvement 2**: Direct cloud object storage streaming (Cloudflare R2 / AWS S3) via pre-signed URLs.
- **Future Improvement 3**: Webhook notifications (`POST /webhook`) on job completion.


---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
