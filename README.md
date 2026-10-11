# 🎓 Bulk Certificate Generator Backend API

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org[![Pytest](https://img.shields.io/badge/pytest-passed%2050%2F50-brightgreen.svg)](https://pytest.org/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://pytest-cov.readthedocs.io/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![Prometheus](https://img.shields.io/badge/prometheus-monitored-E6522C.svg)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/grafana-dashboard-F46800.svg)](https://grafana.com/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-black.svg)](https://github.com/astral-sh/ruff)
[![Cost](https://img.shields.io/badge/infrastructure%20cost-%E2%82%B90%20(Zero--Cost)-green.svg)](#-zero-cost-financial-ledger)

A production-grade, fault-tolerant, interview-ready Bulk Certificate Generator Backend API built with **Python, FastAPI, SQLAlchemy 2.0, ReportLab, and Alembic**. Designed around an asynchronous database-backed job model that handles bulk recipient generation with isolated error handling, full Prometheus/Grafana observability, and zero cloud or licensing costs ($0.00 / ₹0.00).

---

## 📑 Table of Contents
1. [Project Overview & Key Features](#-project-overview--key-features)
2. [Zero-Cost Financial Ledger (₹0 Cost Model)](#-zero-cost-financial-ledger)
3. [System Architecture & Visual Diagrams](#-system-architecture--visual-diagrams)
4. [Technology Stack](#-technology-stack)
5. [Project Directory Structure](#-project-directory-structure)
6. [Prerequisites & Quickstart Installation](#-prerequisites--quickstart-installation)
7. [Running the Application and Worker](#-running-the-application-and-worker)
8. [API Specification & Endpoints](#-api-specification--endpoints)
9. [Sample Workflows & Example JSON Payloads](#-sample-workflows--example-json-payloads)
10. [Automated Testing & QA](#-automated-testing--qa)
11. [Performance Benchmarks & Storage Density](#-performance-benchmarks--storage-density)
12. [Observability, Prometheus & Grafana](#-observability-prometheus--grafana)
13. [Deployment Guide (Docker Compose & Cloud)](#-deployment-guide)
14. [Backups & Storage Retention Policy](#-backups--storage-retention-policy)
15. [Troubleshooting Guide](#-troubleshooting-guide)
16. [Design Decisions & Trade-Offs](#-design-decisions--trade-offs)
17. [Security Considerations](#-security-considerations)
18. [Known Limitations & Future Improvements](#-known-limitations--future-improvements)

---

## 🌟 Project Overview & Key Features

Bulk certificate generation is a frequent requirement for universities, bootcamps, and virtual conferences. Traditional solutions rely on paid SaaS APIs or unstable headless browser converters (Puppeteer/Chrome) that suffer from massive memory overhead, network timeouts, and unpredictable costs.

This project delivers a **100% free, purely programmatic vector rendering engine** coupled with a **durable, database-backed background worker** that ensures zero dropped jobs and per-recipient fault containment.

### Core Features
- **High-Throughput Vector PDF Engine**: Renders high-resolution landscape certificates in ~28ms per certificate (~35 certs/second) using ReportLab vector drawing primitives.
- **Spreadsheet Upload API**: Upload Excel (`.xlsx`) or `.csv` files directly via `POST /api/v1/jobs/upload` with auto-header detection, and download verified templates via `GET /api/v1/jobs/upload/template`.
- **Authorized Signature Embedding**: Automatically integrates authorized signature images (`templates/signature.png`) with alpha-transparency masking and seamless vector fallback.
- **Dynamic Font Auto-Scaling**: Iteratively computes text width with `canvas.stringWidth()` to dynamically downscale long recipient names (e.g. 70+ characters) without border collision or clipping.
- **Cryptographic Verification Codes**: Generates deterministic SHA-256 verification codes (`V-XXXX-XXXX-XXXX`) binding job ID, certificate ID, and recipient name together for authenticity checks.
- **Post-Generation Structural Integrity**: Every output PDF is opened and parsed with `pypdf.PdfReader` before saving; corrupted outputs are unlinked and marked `FAILED` without failing the batch.
- **Fault-Isolated Bulk Processing**: An individual recipient failure (e.g. corrupted name, empty string) does not halt the batch. Valid recipients generate successfully, and the batch concludes as `COMPLETED_WITH_ERRORS`.
- **Atomic Compare-and-Swap Claiming**: Worker concurrency uses `UPDATE generation_jobs SET status='PROCESSING' WHERE id=:id AND status='PENDING'`, preventing duplicate execution across multiple workers without requiring Redis or distributed locks.
- **Worker Crash Recovery**: Automatically identifies jobs stranded in `PROCESSING` after a worker death or server reboot (`recover_stale_jobs`), resetting in-flight records to `PENDING` while preserving already generated `SUCCESS` records.
- **Full Observability Stack**: Embedded Prometheus exporter (`/metrics`), real-time JSON telemetry (`/api/v1/observability/stats`), CPU/RAM tracking, and a pre-configured 17-panel Grafana dashboard.
- **Comprehensive API & Retrieval**: Immediate `202 Accepted` response with status polling, individual PDF download, and streaming batch ZIP compression.
- **Defense-in-Depth Security**: Non-root container execution (`appuser:1001`), OWASP security headers, 10 MB payload limits, path traversal shields, and optional `X-API-Key` authentication.

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
| **Spreadsheet Parser**| OpenPyXL + python-multipart | MIT / Apache 2.0 | **₹0** |
| **Observability** | Prometheus 2.53 + Grafana 10.4 | Apache 2.0 / AGPLv3 | **₹0** |
| **Testing & Quality**| Pytest + pytest-cov + Ruff | MIT License | **₹0** |
| **Containers** | Docker Community Edition | Free | **₹0** |
| **Total Project Cost**| — | — | **₹0 / $0** |

---

## 🏛 System Architecture & Visual Diagrams

The application implements a **Layered Modular Monolith with an Asynchronous Database-Backed Job Worker**. Below are the visual architecture and engineering design diagrams:

### 1. High-Level System Architecture
<p align="center">
  <img src="System%20Architecture%20and%20Design/01_High_Level_System_Architecture.png" alt="High-Level System Architecture" width="100%" />
</p>

*Complete architectural overview depicting client interactions with the FastAPI web service, SQLite WAL database, background worker, persistent PDF storage, Prometheus metrics scraper, and Grafana telemetry.*

---

### 2. Component & Layer Architecture
<p align="center">
  <img src="System%20Architecture%20and%20Design/02_Component_Architecture.png" alt="Component & Layer Architecture" width="100%" />
</p>

*Seven decoupled architectural tiers: Transport & API, Validation & Contract (Pydantic v2), Business Domain & Orchestration, Asynchronous Worker, Pure Vector PDF Engine (ReportLab), Relational ORM (SQLAlchemy 2.0), and Persistent Storage.*

---

### 3. Request Processing Sequence
<p align="center">
  <img src="System%20Architecture%20and%20Design/03_Request_Processing_Sequence.png" alt="Request Processing Sequence" width="100%" />
</p>

*End-to-end sequence showing non-blocking HTTP 202 Accepted job intake, database transaction commit, worker polling, and status retrieval.*

---

### 4. Certificate Generation Flow
<p align="center">
  <img src="System%20Architecture%20and%20Design/04_Certificate_Generation_Sequence.png" alt="Certificate Generation Flow" width="100%" />
</p>

*Detailed ReportLab vector canvas execution: golden guilloche borders, dynamic recipient font downscaling, authorized signature image compositing, HMAC verification tokens, and disk persistence.*

---

### 5. Database Entity Relationship Diagram (ERD)
<p align="center">
  <img src="System%20Architecture%20and%20Design/05_Database_ERD.png" alt="Database Entity Relationship Diagram" width="85%" />
</p>

*Relational database schema: 1:N relationship between `generation_jobs` and `certificate_records` with cascading foreign key integrity and WAL concurrency.*

---

### 6. Production Deployment Topology
<p align="center">
  <img src="System%20Architecture%20and%20Design/07_Deployment_Architecture.png" alt="Production Deployment Topology" width="85%" />
</p>

*Multi-container Docker Compose deployment featuring isolated non-root containers (`appuser:1001`), shared named storage volumes, Prometheus scraping, and Grafana visualization.*

---

### 7. Fault Isolation & Error Recovery Flow
<p align="center">
  <img src="System%20Architecture%20and%20Design/08_Error_Handling_Retry_Flow.png" alt="Error Handling & Failure Containment Flow" width="100%" />
</p>

*Per-recipient failure containment: isolated try-catch boundaries prevent batch crashes and allow valid certificates to complete even when individual rows fail.*

---

### 8. Background Worker Operational Lifecycle
<p align="center">
  <img src="System%20Architecture%20and%20Design/09_Background_Worker_Flow.png" alt="Background Worker Operational Lifecycle" width="100%" />
</p>

*Worker operational loop: atomic compare-and-swap job claiming, batch iteration, heartbeat timestamps, and automatic recovery of stale/crashed jobs.*

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
| `POST` | `/api/v1/jobs` | Submit a bulk generation job (JSON payload) | `202 Accepted` |
| `POST` | `/api/v1/jobs/upload` | Upload spreadsheet (`recipients.xlsx` or `.csv`) with event metadata | `202 Accepted` |
| `GET` | `/api/v1/jobs/upload/template` | Download sample Excel template (`recipients.xlsx`) | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}` | Retrieve real-time job progress and multi-counter metrics | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/certificates` | List recipient certificates with status filtering | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/download` | Download all successful certificates as a ZIP archive | `200 OK` |
| `GET` | `/api/v1/certificates/{certificate_id}/download` | Download an individual certificate PDF | `200 OK` |
| `GET` | `/metrics` / `/api/v1/metrics` | Prometheus 0.0.4 plain-text metrics scrape exposition | `200 OK` |
| `GET` | `/api/v1/observability/stats` | Real-time structured JSON telemetry & dashboard metrics | `200 OK` |
| `GET` | `/api/v1/observability/health/detailed` | Deep active probes for SQLite DB, storage disk, and worker | `200 OK` |
| `GET` | `/api/v1/health` | Service liveness probe and database connectivity check | `200 OK` |
| `GET` | `/api/v1/health/live` | Cloud-native Kubernetes liveness probe | `200 OK` |
| `GET` | `/api/v1/health/ready` | Cloud-native Kubernetes readiness probe | `200 OK` |

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

### 2. Upload Spreadsheet (`POST /api/v1/jobs/upload`)
You can upload an Excel spreadsheet (`recipients.xlsx`) or CSV file directly:

**Via Swagger UI ([http://localhost:8000/docs](http://localhost:8000/docs)):**
1. Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.
2. Expand `POST /api/v1/jobs/upload` under the **Jobs** section and click **Try it out**.
3. Fill in the event metadata:
   - **Event Name**: e.g., `Executive Cloud & Backend Engineering Summit 2026`
   - **Issuer Name**: e.g., `Global Tech Institute`
   - **Issue Date**: e.g., `2026-10-11`
   - **Certificate Title**: e.g., `Certificate of Completion`
4. Click **Choose File** and select `recipients.xlsx` (a sample `recipients.xlsx` is provided in the repository root).
5. Click **Execute**. The API returns `202 Accepted` with the `job_id` and `status_url`.
6. Follow the status until 100%, then download the ZIP archive from `GET /api/v1/jobs/{job_id}/download`.

**Via cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/jobs/upload" \
  -F "file=@recipients.xlsx" \
  -F "event_name=Executive Cloud & Backend Engineering Summit 2026" \
  -F "issuer_name=Global Tech Institute" \
  -F "issue_date=2026-10-11" \
  -F "certificate_title=Certificate of Completion"
```

**Via Demo Script:**
```bash
python scripts/demo_upload_job.py
```

### 3. Poll Status (`GET /api/v1/jobs/{job_id}`)
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

### 4. Automated Demo Scripts
To see end-to-end workflows executed automatically:
```bash
# Option 1: JSON payload submission demo
python scripts/create_demo_job.py

# Option 2: Excel spreadsheet upload demo
python scripts/demo_upload_job.py
```

---

## 🔭 Observability & Telemetry Architecture

The project implements a complete, zero-cost observability architecture satisfying all **Three Pillars of Observability**:

### 1. Prometheus Metrics (`/metrics` & `/api/v1/metrics`)
- Exposes standard Prometheus text exposition format (0.0.4) for scraping by Prometheus, Grafana, Datadog, or cloud monitoring agents.
- **Included Metrics**:
  - `http_requests_total`: Counters partitioned by `method`, `path`, and `status`.
  - `http_request_duration_seconds`: Histogram measuring API latency across standard buckets (`5ms` to `10s`).
  - `http_requests_in_flight`: Real-time gauge of currently active incoming HTTP connections.
  - `jobs_submitted_total`: Counters partitioned by submission type (`json`, `upload`).
  - `jobs_completed_total`: Counters partitioned by completion status (`COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`).
  - `certificates_generated_total`: Counters partitioned by outcome (`SUCCESS`, `FAILED`) and error codes.
  - `certificate_render_duration_seconds`: Histogram measuring per-certificate PDF rendering duration.
  - `stale_jobs_recovered_total`: Counter tracking automated recovery cycles after worker crashes.
  - `storage_certificates_total` & `storage_used_bytes`: Gauges of disk files and storage consumption.
  - `process_uptime_seconds`: Gauge measuring process longevity.
- **Scrape Configuration**: Provided out of the box in [`prometheus.yml`](prometheus.yml).

### 2. Distributed Tracing & Correlation Headers
- Every incoming HTTP request is tagged with a unique correlation identifier (`X-Request-ID`).
- Clients can supply their own trace header (e.g. from an API gateway or load balancer), or the ASGI middleware generates a clean UUID.
- The response returns `X-Request-ID` and `X-Process-Time` (in milliseconds) for client-side latency audit.
- **Context-Aware Logging**: Log records automatically bind `[req:<id>]` for HTTP requests and `[job:<id>]` for worker processing threads, enabling seamless log searching in Datadog or Loki.

### 3. Real-Time Telemetry & Health Diagnostics
- **Structured Stats Endpoint (`GET /api/v1/observability/stats`)**:
  Returns comprehensive JSON metrics covering uptime, error rate percentages, active jobs, average PDF render latency, and human-readable storage sizes.
- **Deep Active Health Probe (`GET /api/v1/observability/health/detailed`)**:
  Performs live read/write capability tests on the SQLite database and filesystem storage volume.
- **Cloud-Native Probes**:
  - `GET /api/v1/health/live`: Fast Kubernetes liveness probe.
  - `GET /api/v1/health/ready`: Kubernetes readiness probe validating dependencies before traffic routing.

---

## 🧪 Automated Testing & QA

Run the full automated test suite with statement coverage:
```bash
pytest -v --cov=app --cov-report=term-missing
```

### Actual Test Coverage
```text
======================= 50 passed, 8 warnings in 9.91s ========================
TOTAL STATEMENTS: 1335 | OVERALL COVERAGE: 88%
- app/api/deps.py:              100%
- app/api/v1/jobs.py:           100%
- app/api/v1/certificates.py:   100%
- app/core/config.py:           100%
- app/core/logging.py:          100%
- app/core/metrics.py:          98%
- app/schemas/job.py:           100%
- app/services/spreadsheet_parser.py: 92%
- app/services/job_service.py:  90%
- app/api/v1/observability.py:  87%
- app/api/v1/health.py:         85%
- app/main.py:                  80%
- app/services/worker.py:       75%
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
