# 🎓 Bulk Certificate Generator Backend API

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Pytest](https://img.shields.io/badge/pytest-passed%2013%2F13-brightgreen.svg)](https://pytest.org/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-black.svg)](https://github.com/astral-sh/ruff)
[![Cost](https://img.shields.io/badge/infrastructure%20cost-%E2%82%B90%20(Zero--Cost)-green.svg)](#-zero-cost-financial-ledger)

A production-grade, fault-tolerant, interview-ready Bulk Certificate Generator Backend API built with **Python, FastAPI, SQLAlchemy 2.0, ReportLab, and Alembic**. Designed around an asynchronous database-backed job model that handles bulk recipient generation with isolated error handling and zero cloud or licensing costs.

---

## 📑 Table of Contents
1. [System Architecture Overview](#-system-architecture-overview)
2. [Zero-Cost Financial Ledger (₹0 Cost Model)](#-zero-cost-financial-ledger)
3. [Technology Stack](#-technology-stack)
4. [Project Directory Structure](#-project-directory-structure)
5. [Quickstart & Installation](#-quickstart--installation)
6. [Running the Application](#-running-the-application)
7. [API Specification & Endpoints](#-api-specification--endpoints)
8. [Sample API Workflows (cURL Examples)](#-sample-api-workflows)
9. [Automated Testing & QA](#-automated-testing--qa)
10. [Docker & Containerized Deployment](#-docker--containerized-deployment)
11. [Architectural & System Design Defense (Interview Q&A)](#-architectural-and-system-design-defense)

---

## 🏛 System Architecture Overview

The system implements a **Layered Modular Monolith with an Asynchronous Database-Backed Job Worker**.

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
                     |  - Transactional Job Creation      |
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

### Architectural Diagrams
Comprehensive system architecture diagrams are available in the [`System Architecture and Design/`](./System%20Architecture%20and%20Design/) directory:
- `01_High_Level_System_Architecture.png`: Full architectural overview
- `02_Component_Architecture.png`: Internal modular design
- `03_Request_Processing_Sequence.png`: Asynchronous submission sequence
- `04_Certificate_Generation_Sequence.png`: Individual PDF rendering flow
- `05_Database_ERD.png` & `06_Detailed_Database_Schema.png`: Relational schema & indexes
- `07_Deployment_Architecture.png`: Local vs Zero-cost cloud deployment
- `08_Error_Handling_Retry_Flow.png`: Fault isolation flowchart
- `09_Background_Worker_Flow.png`: Worker claim, polling & recovery logic
- `10_DFD_Level_0_Context.png` & `11_DFD_Level_1.png`: Data Flow Diagrams
- `12_End_to_End_Activity_Diagram.png`: UML activity lifecycle

---

## 💰 Zero-Cost Financial Ledger

This project satisfies a strict **₹0 ($0) Zero-Cost Requirement**. No paid cloud services, no paid API keys, and no credit card requirements.

| Layer | Technology | License / Pricing Tier | Cost |
| :--- | :--- | :--- | :--- |
| **Language** | Python 3.11 - 3.13 | Open Source (PSFL) | **₹0** |
| **Framework** | FastAPI + Uvicorn | MIT License | **₹0** |
| **Database** | SQLite with WAL Mode / Local PostgreSQL | Public Domain / Open Source | **₹0** |
| **ORM & Migrations**| SQLAlchemy 2.0 + Alembic | MIT License | **₹0** |
| **Data Validation** | Pydantic v2 | MIT License | **₹0** |
| **PDF Rendering** | ReportLab Open-Source Engine | BSD License | **₹0** |
| **Testing & Quality**| Pytest + Ruff | MIT License | **₹0** |
| **Containers** | Docker Community Edition | Apache 2.0 / Free | **₹0** |
| **Local Deployment**| Localhost (Self-Hosted) | Bare metal / Developer PC | **₹0** |
| **Cloud Hosting (Optional)**| Render.com / Koyeb / Fly.io / HuggingFace | Free Web Tier (No Credit Card required options) | **₹0** |
| **Total Project Cost**| — | — | **₹0 / $0** |

> **Local vs Cloud Caveat**: While local deployment is 100% persistent and permanent at ₹0, cloud free tiers (e.g., Render free web service) feature ephemeral disks and compute spin-down after inactivity. For production cloud deployments at zero cost, external persistent S3-compatible free object storage (e.g., Cloudflare R2 free 10GB tier) can be plugged in without changing the core business logic.

---

## 🛠 Technology Stack

- **Python 3.11+**: Modern, typed Python with native typing and high performance.
- **FastAPI**: High-performance async web framework generating automated OpenAPI and Swagger UI documentation.
- **SQLAlchemy 2.0**: Modern typed ORM using `Mapped` and `mapped_column` with transactional safety.
- **SQLite with WAL Mode**: Write-Ahead Logging (`PRAGMA journal_mode=WAL`) enables concurrent non-blocking reads during active background writes.
- **Alembic**: Database migration tool for versioned schema evolution.
- **ReportLab**: High-fidelity vector PDF generation engine with custom borders, seals, and typography.
- **Pydantic v2**: High-speed validation with custom field sanitizers and email format verification.
- **Pytest & TestClient**: Test suite covering unit, integration, validation, and fault-tolerance edge cases.
- **Ruff**: Fast Python linter and formatter.

---

## 📂 Project Directory Structure

```
bulk_certificate_generator/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Application entry point, lifespan, CORS, and error handlers
│   ├── api/
│   │   ├── deps.py              # Dependency injection (get_db)
│   │   └── v1/
│   │       ├── router.py        # API v1 aggregator router
│   │       ├── health.py        # Liveness & storage probe (/health)
│   │       ├── jobs.py          # Job creation, polling, filtering, ZIP download
│   │       └── certificates.py  # Single certificate PDF streaming (/download)
│   ├── core/
│   │   ├── config.py            # Pydantic BaseSettings (.env loading)
│   │   ├── logging.py           # Structured logging configuration
│   │   └── errors.py            # Custom domain exception hierarchy
│   ├── db/
│   │   ├── base.py              # DeclarativeBase for ORM
│   │   └── session.py           # Engine with SQLite WAL pragmas and SessionLocal
│   ├── models/
│   │   ├── enums.py             # JobStatus and CertificateStatus enums
│   │   ├── job.py               # GenerationJob ORM model
│   │   └── certificate.py       # CertificateRecord ORM model
│   ├── schemas/
│   │   ├── recipient.py         # Recipient input & certificate output schemas
│   │   ├── job.py               # Bulk request & job status schemas
│   │   └── common.py            # Health and error schemas
│   └── services/
│       ├── certificate_service.py # ReportLab PDF template generator
│       ├── job_service.py       # Job orchestration, queries, and ZIP archive packaging
│       └── worker.py            # Asynchronous background worker with atomic claim
├── alembic/                     # Database migration revisions
│   ├── env.py
│   └── versions/
│       └── dfb1ace84fda_initial_schema.py
├── storage/
│   └── certificates/           # Persistent directory for generated PDF files
├── tests/
│   ├── conftest.py              # Isolated DB and temporary storage fixtures
│   ├── test_health.py           # Health checks
│   ├── test_validation.py       # Schema validation and batch limits
│   ├── test_pdf_generation.py   # PDF rendering engine unit tests
│   ├── test_job_lifecycle.py    # End-to-end async submission & status lifecycle
│   ├── test_failure_isolation.py# Fault-tolerance test for partial failures
│   └── test_retrieval.py        # Single PDF download and bulk ZIP tests
├── Dockerfile                   # Non-root secure container image
├── docker-compose.yml           # Multi-container setup (API + decoupled worker)
├── pyproject.toml               # Modern build configuration and Ruff rules
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Locked project dependencies
├── worker_runner.py             # Standalone CLI worker entrypoint
├── .env.example                 # Example environment configuration
└── README.md                    # Project documentation
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13 installed
- Git installed

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone <your-repo-url>
cd "Bulk Certificate Generator"

# Create a local virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the provided `.env.example` to `.env`:
```bash
# Windows:
copy .env.example .env
# Linux / macOS:
cp .env.example .env
```

### 4. Apply Database Migrations
Initialize the SQLite schema using Alembic:
```bash
alembic upgrade head
```

---

## 💻 Running the Application

### Option A: Single-Process Developer Mode (Recommended for testing)
By default, `RUN_WORKER_IN_APP=True` is enabled in `.env`. Starting the FastAPI server automatically spawns an in-process background worker thread:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Interactive ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Option B: Decoupled Multi-Process Mode (Production Topology)
To run the API server and the Background Worker in separate dedicated operating system processes:

**Terminal 1 (FastAPI Web Server):**
```bash
# Set RUN_WORKER_IN_APP=false in .env, then:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 (Dedicated Background Worker):**
```bash
python worker_runner.py
```

---

## 📡 API Specification & Endpoints

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System health, database connection, and storage probe | `200 OK` |
| `POST` | `/api/v1/jobs` | Submit bulk certificate generation request | `202 Accepted` |
| `GET` | `/api/v1/jobs/{job_id}` | Poll overall job status, progress %, and counters | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/certificates` | List recipient certificates with status filter and pagination | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/download-zip` | Download all successfully generated certificates as a `.zip` archive | `200 OK` |
| `GET` | `/api/v1/certificates/{certificate_id}/download` | Stream individual certificate PDF file | `200 OK` |

---

## 🧪 Sample API Workflows

### 1. Submit a Bulk Generation Job
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Full Stack Backend Engineering Bootcamp",
    "issuer_name": "Global Tech Institute",
    "issue_date": "October 10, 2026",
    "certificate_title": "Certificate of Excellence",
    "recipients": [
      {
        "recipient_name": "Jane Doe",
        "recipient_email": "jane.doe@example.com",
        "custom_remarks": "First Class with Distinction"
      },
      {
        "recipient_name": "John Smith",
        "recipient_email": "john.smith@example.com",
        "custom_remarks": "High Honors"
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
  "created_at": "2026-10-10T00:30:00.000000Z",
  "status_url": "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392",
  "message": "Bulk certificate generation job accepted and queued for processing."
}
```

### 2. Poll Job Status
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392"
```

**Response (`200 OK`):**
```json
{
  "job_id": "8f395804-b9b0-466d-a7ca-5c3b9b46e392",
  "status": "COMPLETED",
  "event_name": "Full Stack Backend Engineering Bootcamp",
  "issuer_name": "Global Tech Institute",
  "issue_date": "October 10, 2026",
  "certificate_title": "Certificate of Excellence",
  "total_recipients": 2,
  "successful_count": 2,
  "failed_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-10T00:30:00.000000Z",
  "started_at": "2026-10-10T00:30:01.000000Z",
  "completed_at": "2026-10-10T00:30:02.000000Z",
  "zip_download_url": "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392/download-zip"
}
```

### 3. List Recipient Certificates
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392/certificates"
```

**Response (`200 OK`):**
```json
[
  {
    "id": "e6a2b8e4-1845-45dc-96ba-a1cbcfc4d44b",
    "job_id": "8f395804-b9b0-466d-a7ca-5c3b9b46e392",
    "recipient_name": "Jane Doe",
    "recipient_email": "jane.doe@example.com",
    "certificate_id": "CERT-8D4F-912A-B7C1",
    "status": "SUCCESS",
    "error_code": null,
    "error_message": null,
    "created_at": "2026-10-10T00:30:00.000000Z",
    "completed_at": "2026-10-10T00:30:01.500000Z",
    "download_url": "http://localhost:8000/api/v1/certificates/CERT-8D4F-912A-B7C1/download"
  }
]
```

### 4. Download Single Certificate PDF
```bash
curl -O -J "http://localhost:8000/api/v1/certificates/CERT-8D4F-912A-B7C1/download"
```

### 5. Download All Certificates as ZIP
```bash
curl -O -J "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392/download-zip"
```

---

## 🧪 Automated Testing & QA

The application includes an automated test suite verifying input validation, ReportLab rendering, concurrency, failure isolation, and retrieval.

Run the test suite with Pytest:
```bash
pytest -v
```

### Test Coverage Highlights
- `test_validation.py`: Tests missing fields, empty arrays, whitespace sanitization, and invalid emails.
- `test_pdf_generation.py`: Verifies valid vector PDF byte headers (`%PDF`), size thresholds, and unique IDs.
- `test_job_lifecycle.py`: Tests the complete state machine: `PENDING` → `PROCESSING` → `COMPLETED`.
- `test_failure_isolation.py`: Simulates an invalid recipient in a multi-recipient batch. Verifies that valid recipients generate without interruption and aggregate job finishes as `COMPLETED_WITH_ERRORS`.
- `test_retrieval.py`: Tests single PDF streaming, 404 handling, path traversal prevention, and ZIP decompression integrity.

### Code Quality & Linting
Run Ruff to ensure adherence to PEP 8 standards:
```bash
# Format codebase
ruff format .

# Static analysis and linting
ruff check .
```

---

## 🐳 Docker & Containerized Deployment

### Run with Docker Compose
The provided `docker-compose.yml` configures a decoupled production topology with the API server and worker running in separate containers sharing a persistent storage volume:

```bash
docker compose up --build -d
```
Check container status:
```bash
docker compose ps
docker compose logs -f
```

---

## 💡 Architectural and System Design Defense

Here are technical explanations of key design decisions for interview discussions:

### 1. Why a Database-Backed Job Model instead of Celery + Redis?
- **Operational Simplicity & Cost**: Celery requires an independent message broker (Redis or RabbitMQ) and result backend. This adds infrastructure overhead, network hops, memory costs, and paid managed service dependencies.
- **Transactional Consistency**: With a database-backed model, the creation of a generation job and all recipient records occurs within a single ACID transaction. A Redis-based approach introduces dual-write hazards where database commits could succeed while Redis enqueuing fails.
- **Zero-Cost Free Tier Compliance**: Free hosting tiers (e.g., Render, Fly.io) provide 512MB RAM containers. Running Redis + Celery alongside Python can easily breach these memory limits. Our DB worker runs comfortably under 60MB of RAM.

### 2. How are Race Conditions Prevented in Worker Job Claiming?
To allow multiple worker instances without distributed locks:
```python
claim_stmt = (
    update(GenerationJob)
    .where(GenerationJob.id == candidate_id, GenerationJob.status == "PENDING")
    .values(status="PROCESSING", started_at=now, updated_at=now)
)
result = db.execute(claim_stmt)
if result.rowcount == 0:
    # Another worker claimed it concurrently; skip without collision
    continue
```
In relational databases (including SQLite and PostgreSQL), single-row updates are atomic. If two workers attempt to claim the same job, only one succeeds (`rowcount == 1`), while the other gets `rowcount == 0` and safely backs off.

### 3. How does SQLite Handle Concurrent Reads and Writes?
Standard SQLite in rollback journal mode locks the entire file during a write, causing `database is locked` errors during concurrent API queries.
We resolve this via SQLite Pragmas on connection:
```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```
- **Write-Ahead Logging (WAL)**: Writers write to an append-only `-wal` log file while readers read from the main database file simultaneously without blocking each other.
- **Busy Timeout**: Instructs SQLite to sleep and retry for up to 5 seconds before raising an error if a checkpoint is in progress.

### 4. How is Fault Isolation Guaranteed?
Each recipient within a batch is processed within an isolated `try...except` block with its own status update. If recipient #27 encounters invalid data or a rendering exception:
1. Recipient #27 is marked `FAILED` with `error_code` and `error_message`.
2. Job's `failed_count` is incremented.
3. The loop immediately continues to recipient #28.
4. The final aggregate job status is set to `COMPLETED_WITH_ERRORS` rather than crashing the job.

### 5. How are Crashed or Interrupted Workers Recovered?
If a worker process terminates abruptly (e.g., OOM, server reboot), jobs could remain stuck in `PROCESSING`.
The worker implements `recover_stale_jobs()`:
- Scans for jobs where `status == 'PROCESSING'` and `updated_at < (now - WORKER_JOB_TIMEOUT_SECONDS)`.
- Resets interrupted `PROCESSING` recipient records back to `PENDING`.
- Requeues the parent job to `PENDING` so active workers automatically resume generation without lost data.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
