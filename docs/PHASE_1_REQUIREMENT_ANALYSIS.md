# 📋 Phase 1 — Requirement Analysis and Planning Specification
**Project**: Bulk Certificate Generator Backend API  
**Author / Engineering Lead**: Backend Engineering & Architecture Team  
**Cost Target**: Strict ₹0 / $0 Zero-Cost Footprint  
**Document Version**: 1.0.0 (Approved Baseline)

---

## 1. Project Overview

### 1.1 Executive Summary
The **Bulk Certificate Generator Backend API** is an asynchronous, high-throughput, fault-tolerant web service engineered for educational institutions, corporate training academies, and conference organizers. The platform automates the end-to-end lifecycle of certificate generation: validating bulk recipient data, queuing asynchronous generation jobs, rendering high-resolution vector PDF certificates from an elegant predefined template, tracking granular job and recipient statuses, and exposing secure retrieval endpoints for individual PDFs and consolidated ZIP archives.

### 1.2 Problem Statement
Organizations frequently host workshops, training cohorts, and conferences involving dozens to thousands of attendees. Existing manual approaches or naive synchronous APIs present significant engineering bottlenecks:
1. **Network Timeouts on Bulk Loads**: Generating 500+ PDFs synchronously blocks HTTP worker threads, leading to gateway timeouts (`HTTP 504`) and dropped connections.
2. **Cascading Batch Failures**: In naive implementations, a single invalid recipient (e.g., malformed email or corrupted name string) terminates the entire batch, forcing organizers to restart the process.
3. **Heavy Infrastructure Costs**: Typical enterprise solutions rely on complex paid infrastructure (AWS Lambda, Celery, Redis clusters, paid document generation APIs), which violates accessibility for student, open-source, or zero-budget projects.
4. **Lack of Concurrency Control**: Multiple background workers querying jobs can easily introduce race conditions, duplicate certificate generation, or database lock contentions.

### 1.3 Business & System Objectives
- **Bulk Processing via Single Request**: Ingest up to 1,000 recipients in a single `POST` request without blocking client HTTP threads.
- **Asynchronous Execution & Immediate Acceptance**: Return `HTTP 202 Accepted` within `< 200ms` with a deterministic polling URL.
- **Per-Recipient Fault Isolation**: Ensure failures are isolated to the specific recipient record while allowing all valid certificates to generate successfully.
- **Auditability & Traceability**: Maintain persistent records of every job and certificate, capturing timestamps, error codes, and unique cryptographic IDs.
- **Zero-Cost Operation**: Run entirely on free, open-source software with ₹0 in software licensing, database, cloud, or third-party API fees.

---

## 2. Scope and Exclusions

To ensure high engineering quality, clean architecture, and timely delivery, boundaries are strictly defined.

### 2.1 In-Scope (Mandatory Requirements)
- **API Endpoints**:
  - `POST /api/v1/jobs`: Bulk job creation and validation.
  - `GET /api/v1/jobs/{job_id}`: Real-time progress, counters, and status.
  - `GET /api/v1/jobs/{job_id}/certificates`: Paginated recipient certificate listing with status filtering.
  - `GET /api/v1/certificates/{certificate_id}/download`: Direct PDF download with security checks.
  - `GET /api/v1/jobs/{job_id}/download-zip`: Bulk ZIP archive generation and download.
  - `GET /api/v1/health`: Liveness and readiness health probe.
- **Input Validation**: Strict schema enforcement, boundary checks, email format validation, and whitespace sanitization.
- **PDF Generation Engine**: Vector-based PDF generation via ReportLab using an elegant, predefined landscape template (decorative borders, institutional seal, dynamic metadata, unique certificate ID).
- **Asynchronous Processing**: Decoupled database-backed job queue with atomic job claiming (`UPDATE ... WHERE status = 'PENDING'`) and heartbeat updates.
- **Fault Tolerance**: Isolated per-recipient execution with explicit error code logging (`INVALID_RECIPIENT_DATA`, `PDF_RENDER_ERROR`).
- **Data Persistence**: Relational schema managed via SQLAlchemy 2.0 with versioned Alembic database migrations.
- **Concurrency Support**: SQLite configured with Write-Ahead Logging (`WAL`) mode and busy timeouts to guarantee concurrent read/write operations without locking.
- **Automated QA**: Comprehensive Pytest suite covering positive paths, boundary conditions, partial failures, and security attacks.
- **Documentation & Packaging**: Production `Dockerfile`, `docker-compose.yml`, environment configuration (`.env.example`), and interview-ready documentation.

### 2.2 Out-of-Scope (Exclusions / Deliberate Non-Requirements)
- **WYSIWYG Template Editor**: The system utilizes a single, polished, predefined template. Supporting custom dynamic template builders or HTML-to-PDF drag-and-drop canvases is excluded.
- **Email / SMTP Delivery Engine**: Direct automated email dispatch (e.g., SendGrid, Mailgun, SMTP) is out of scope to avoid paid third-party dependencies, API quota exhaustion, and spam reputation management.
- **Paid Cloud Message Brokers**: No Redis, RabbitMQ, or AWS SQS dependencies. All job queuing is backed natively by the ACID relational database.
- **User Authentication / RBAC**: The assignment scope focuses on backend architecture, data integrity, and job processing. Multi-tenant auth (OAuth2/JWT) is excluded from the core MVP to keep the API lightweight and testable.

### 2.3 Optional Improvements (Post-MVP Enhancements)
- Verification QR code embedded on the PDF canvas directing to a public verification endpoint.
- Webhook callbacks notifying client URLs upon job finalization (`COMPLETED` or `COMPLETED_WITH_ERRORS`).
- Plug-and-play S3-compatible cloud storage adapter (e.g., Cloudflare R2 free tier).

---

## 3. Functional Requirements (FR)

| Requirement ID | Module | Description |
| :--- | :--- | :--- |
| **FR-01** | Job Ingestion | The system MUST accept a JSON payload containing event details (`event_name`, `issuer_name`, `issue_date`, `certificate_title`) and an array of recipients. |
| **FR-02** | Payload Validation | The system MUST validate that recipient arrays contain between 1 and 1,000 items. Strings must be stripped of leading/trailing whitespace. Missing required fields or invalid email formats must return `HTTP 422 Unprocessable Content`. |
| **FR-03** | Asynchronous Handshake | The system MUST persist the job as `PENDING`, initialize counters (`total_recipients`, `successful_count = 0`, `failed_count = 0`), and immediately return `HTTP 202 Accepted` with `job_id` and `status_url` within `< 200ms`. |
| **FR-04** | Atomic Job Claiming | The worker process MUST atomically claim pending jobs using a single transactional update (`status='PROCESSING'`) to prevent race conditions across concurrent workers. |
| **FR-05** | Per-Recipient Processing | The worker MUST process each recipient sequentially or in controlled batches, generating a unique certificate identifier (`CERT-XXXX-XXXX-XXXX`) for each. |
| **FR-06** | Vector PDF Rendering | The system MUST render an A4 landscape vector PDF containing the recipient name, event name, issuer, issue date, custom remarks (if any), decorative seal, and certificate ID. |
| **FR-07** | Fault Isolation | If an individual recipient fails validation or PDF rendering, the system MUST record the failure (`status = 'FAILED'`), log the error code and message, increment `failed_count`, and proceed to the next recipient without interrupting the job. |
| **FR-08** | Status Finalization | Upon processing all recipients, the job MUST transition to `COMPLETED` (if 0 failures) or `COMPLETED_WITH_ERRORS` (if `failed_count > 0`). If all recipients fail, it transitions to `COMPLETED_WITH_ERRORS` (or `FAILED` if a job-level system fault occurs). |
| **FR-09** | Progress Tracking | The system MUST provide `GET /api/v1/jobs/{job_id}` returning current status, counts, real-time progress percentage, and timestamps (`created_at`, `started_at`, `completed_at`). |
| **FR-10** | Recipient Querying | The system MUST provide `GET /api/v1/jobs/{job_id}/certificates` with pagination (`limit`, `offset`) and status filtering (`SUCCESS`, `FAILED`, `PENDING`). |
| **FR-11** | PDF Download | The system MUST provide `GET /api/v1/certificates/{certificate_id}/download` streaming the file with `Content-Type: application/pdf` and `Content-Disposition`. |
| **FR-12** | Batch ZIP Download | The system MUST provide `GET /api/v1/jobs/{job_id}/download-zip` compiling all successfully generated certificates into a compressed `.zip` archive. |
| **FR-13** | Stale Job Recovery | The worker MUST detect jobs stuck in `PROCESSING` beyond `WORKER_JOB_TIMEOUT_SECONDS` (default 600s), reset unfinished records to `PENDING`, and requeue the job. |

---

## 4. Non-Functional Requirements (NFR)

### 4.1 Performance & Scalability (NFR-01)
- **API Ingestion Latency**: The submission endpoint (`POST /api/v1/jobs`) must respond within **< 200ms** for a batch of 1,000 recipients by offloading rendering to the background.
- **Rendering Throughput**: On a standard 2-core developer workstation, the ReportLab engine must achieve a throughput of **15 to 30 certificates per second**.
- **Memory Footprint**: The application and worker combined must operate within **< 100MB of RAM**, making it safe for free cloud containers (which typically provide 512MB limits).

### 4.2 Reliability & Fault Tolerance (NFR-02)
- **Crash Resilience**: Because state is persisted to disk in the relational database at each step, a worker crash or server restart will not lose submitted jobs.
- **Stale Lease Recovery**: The system must automatically recover orphaned jobs using timestamp-based heartbeat checks.
- **Zero Cascading Failures**: A corrupt recipient string or character encoding issue must never abort the remaining items in the batch.

### 4.3 Security & Path Traversal Prevention (NFR-03)
- **Directory Traversal Protection**: All file download endpoints must resolve canonical paths using `Path.resolve()` and verify that the target path strictly resides within `settings.STORAGE_DIR`. Requests attempting path traversal (`../../`) must be rejected with `HTTP 403 Forbidden`.
- **Input Sanitization**: Recipient names, event names, and remarks must be validated and sanitized to prevent injection attacks.
- **Non-Root Execution**: Docker containers must execute under an unprivileged user (`appuser`, UID 1001).
- **CORS Protection**: Configurable allowed origins to prevent unauthorized cross-origin browser requests.

### 4.4 Data Concurrency & Storage Management (NFR-04)
- **Concurrency via SQLite WAL Mode**: SQLite connections must automatically execute `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`. This allows the API to serve read requests (e.g. status polling) concurrently while the background worker performs write updates.
- **Deterministic Storage Hierarchy**: Certificates are stored on disk in structured subdirectories: `storage/certificates/{job_id}/{certificate_id}.pdf`.

### 4.5 Observability & Maintainability (NFR-05)
- **Structured Logging**: Standardized logs outputting timestamp, log level, module, line number, and contextual message.
- **Liveness & Readiness**: `GET /api/v1/health` verifying database connectivity (`SELECT 1`) and storage read/write accessibility.
- **PEP 8 & Clean Code**: 100% compliant with modern Ruff linting and formatting rules.

---

## 5. User Stories and Acceptance Criteria (Gherkin Syntax)

### User Story 1: Submitting a Valid Bulk Certificate Generation Request
> **As an** event organizer,  
> **I want to** submit a single JSON request containing event details and a list of participants,  
> **So that** I do not have to make hundreds of individual API calls.

- **Scenario 1.1: Successful Bulk Submission**
  - **Given** the client sends a `POST /api/v1/jobs` request,
  - **And** the payload contains valid `event_name`, `issuer_name`, `issue_date`, and 25 valid recipients,
  - **When** the FastAPI validation pipeline executes,
  - **Then** the system returns `HTTP 202 Accepted`,
  - **And** the response body contains a UUID `job_id`, `status: "PENDING"`, `total_recipients: 25`, and a valid `status_url`.

---

### User Story 2: Handling Invalid or Out-of-Bounds Payloads
> **As an** API consumer,  
> **I want to** receive immediate, descriptive validation errors when sending malformed data,  
> **So that** I can correct my request payload before processing begins.

- **Scenario 2.1: Empty Recipient Array**
  - **Given** the client sends a `POST /api/v1/jobs` request with `"recipients": []`,
  - **When** the Pydantic schema evaluates the payload,
  - **Then** the system returns `HTTP 422 Unprocessable Content`,
  - **And** the response body contains `"error_code": "VALIDATION_ERROR"` and details stating recipients cannot be empty.

- **Scenario 2.2: Batch Exceeds Maximum Configured Limit**
  - **Given** the client sends a `POST /api/v1/jobs` request with 1,200 recipients (limit is 1,000),
  - **When** the service boundary validator executes,
  - **Then** the system returns `HTTP 422 Unprocessable Content`,
  - **And** the response body indicates the batch size of 1,200 exceeds the maximum limit of 1,000.

---

### User Story 3: Monitoring Progress and Completion
> **As an** API consumer,  
> **I want to** poll the status endpoint of my generation job,  
> **So that** I can track progress and know when the certificates are ready for download.

- **Scenario 3.1: Polling a Running Job**
  - **Given** a valid job is currently processing recipients,
  - **When** the client sends a `GET /api/v1/jobs/{job_id}` request,
  - **Then** the response returns `HTTP 200 OK`,
  - **And** includes `status: "PROCESSING"`, accurate `successful_count`, `failed_count`, and `progress_percentage`.

- **Scenario 3.2: Polling a Completed Job**
  - **Given** all recipients in the job have been processed,
  - **When** the client sends a `GET /api/v1/jobs/{job_id}` request,
  - **Then** the response returns `status: "COMPLETED"`, `progress_percentage: 100.0`, a populated `completed_at` timestamp, and a `zip_download_url`.

---

### User Story 4: Isolated Handling of Recipient Failures
> **As an** event organizer,  
> **I want to** ensure that a corrupted recipient entry does not stop the entire generation job,  
> **So that** all valid attendees receive their certificates without delay.

- **Scenario 4.1: Batch with 1 Invalid and 9 Valid Recipients**
  - **Given** a job contains 1 recipient with an invalid name string (e.g. whitespace only) and 9 valid recipients,
  - **When** the background worker executes,
  - **Then** the invalid recipient is marked `FAILED` with `error_code: "INVALID_RECIPIENT_DATA"`,
  - **And** the remaining 9 valid recipients are rendered and marked `SUCCESS`,
  - **And** the parent job finalizes with `status: "COMPLETED_WITH_ERRORS"`, `successful_count: 9`, and `failed_count: 1`.

---

### User Story 5: Downloading an Individual Certificate PDF
> **As an** attendee or organizer,  
> **I want to** download a single certificate PDF by its unique identifier,  
> **So that** I can view or print the verified certificate.

- **Scenario 5.1: Successful PDF Retrieval**
  - **Given** a certificate record has `status: "SUCCESS"` and an existing file on disk,
  - **When** the client requests `GET /api/v1/certificates/{certificate_id}/download`,
  - **Then** the system returns `HTTP 200 OK` with `Content-Type: application/pdf`,
  - **And** the binary body begins with the PDF magic bytes `%PDF`.

- **Scenario 5.2: Attempted Path Traversal Attack**
  - **Given** a malicious request attempts path traversal using relative parent path segments,
  - **When** the service validates canonical storage boundaries,
  - **Then** the system rejects the request with `HTTP 403 Forbidden` or `HTTP 404 Not Found`.

---

### User Story 6: Bulk Downloading Certificates as a ZIP Archive
> **As an** event administrator,  
> **I want to** download all generated certificates in a single compressed ZIP file,  
> **So that** I can archive or distribute them in bulk without making hundreds of download calls.

- **Scenario 6.1: Successful ZIP Generation and Stream**
  - **Given** a job has at least one successfully generated certificate,
  - **When** the client requests `GET /api/v1/jobs/{job_id}/download-zip`,
  - **Then** the system returns `HTTP 200 OK` with `Content-Type: application/zip`,
  - **And** the stream unzips into individual valid PDF files formatted as `{Recipient_Name}_{Certificate_ID}.pdf`.

---

## 6. Technology Selection & Architectural Justifications

### Comparison Matrix
| Layer | Selected Technology | Evaluated Alternative | Architectural Verdict |
| :--- | :--- | :--- | :--- |
| **Language** | **Python 3.11 - 3.13** | Node.js / Go | Python offers native mature ReportLab bindings and strong typing. |
| **Web Framework** | **FastAPI** | Django / Flask | Async ASGI performance, automated OpenAPI docs, native Pydantic v2. |
| **Database & ORM** | **SQLite (WAL) + SQLAlchemy 2.0** | Postgres / Raw SQL | Zero-cost local setup, WAL enables concurrent reads without locks. |
| **Migrations** | **Alembic** | Manual DDL scripts | Production-grade versioned schema migrations. |
| **Job Processing** | **DB-Backed Worker Model** | Celery + Redis | Eliminates paid Redis, avoids dual-writes, fits in <100MB RAM. |
| **PDF Rendering** | **ReportLab (Open Source)** | WeasyPrint/Puppeteer | Pure Python, high speed, vector output, no headless Chromium. |
| **Testing** | **Pytest + TestClient** | Unittest | Rich fixtures, fast execution, isolated DB. |
| **Containers** | **Docker + Docker Compose** | Bare VM / Bare Metal | 100% reproducible, decoupled worker container. |

### Deep-Dive: Database-Backed Worker vs. Celery + Redis
1. **Elimination of the Dual-Write Problem**:
   With Celery + Redis, saving a job requires writing to the relational database AND publishing a message to Redis. If the database transaction commits but Redis is unreachable (or vice versa), the system enters an inconsistent state. With our database-backed worker, job creation and recipient persistence occur within a **single atomic ACID database transaction**.
2. **Infrastructure Simplicity & Zero-Cost Compliance**:
   Redis is an in-memory datastore. Free cloud containers provide 512MB RAM. Running FastAPI + Redis server + Celery worker easily causes Out-Of-Memory (OOM) crashes. Our database-backed worker runs inside the existing Python environment and consumes under **30MB of RAM**.
3. **Optimistic Concurrency & Safe Job Claiming**:
   By using `UPDATE generation_jobs SET status='PROCESSING' WHERE id=:id AND status='PENDING'`, we leverage the database's native row-level atomicity. Multiple workers can poll without distributed locking services like Redlock.

---

## 7. Project Milestones & Estimated Development Timeline

| Milestone | Deliverables | Target Duration | Status |
| :--- | :--- | :---: | :---: |
| **M1: Requirements & Planning** | Scope document, user stories, Gherkin acceptance criteria, cost ledger. | 1 Day | **Completed** |
| **M2: Architecture & Schemas** | ERD, DFD, Sequence diagrams, SQLAlchemy 2.0 models, Alembic migrations. | 1 Day | **Completed** |
| **M3: Environment & Core Scaffolding** | Python virtualenv, pydantic-settings, structured logging, SQLite WAL. | 0.5 Day | **Completed** |
| **M4: PDF Rendering Engine** | ReportLab landscape canvas, decorative borders, vector seal, font hierarchy. | 1 Day | **Completed** |
| **M5: Background Worker Engine** | Atomic claiming (`UPDATE ... WHERE`), fault isolation, crash recovery loop. | 1.5 Days | **Completed** |
| **M6: API & Retrieval Endpoints** | `POST /jobs`, `GET /jobs/{id}`, `/certificates`, `/download`, `/download-zip`. | 1 Day | **Completed** |
| **M7: Automated Testing & QA** | 13 Pytest tests (validation, lifecycle, partial failures, security). | 1 Day | **Completed** |
| **M8: Containerization & DevOps** | Production `Dockerfile`, `docker-compose.yml`, non-root security. | 0.5 Day | **Completed** |
| **M9: Documentation & Interview Prep**| Comprehensive README, cURL examples, technical interview defense. | 0.5 Day | **Completed** |
| **Total Development Estimate** | Full Production-Grade Implementation | **8 Days** | **Ready** |

---

## 8. Zero-Cost Feasibility Assessment & Risk Management

| Risk ID | Identified Technical Risk | Potential Impact | Zero-Cost Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **R-01** | **SQLite Concurrency Contention**<br>Simultaneous write operations causing `database is locked` errors. | High (Jobs fail to claim or status queries hang). | **Configured WAL Mode & Busy Timeout**: Enabling `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` allows unlimited concurrent readers alongside active writes, eliminating lock contention. |
| **R-02** | **Ephemeral Cloud Storage**<br>Free cloud hosting providers (Render, Fly.io) wipe local disk upon container restart. | High (Generated PDFs lost upon app restart). | **Local-First Architecture**: 100% persistent on local developer workstation. For zero-cost cloud deployment, architecture uses a modular storage interface that can map to Cloudflare R2 (10GB free tier, ₹0). |
| **R-03** | **Worker Crash Mid-Batch**<br>Server reboot or worker termination leaves jobs stuck in `PROCESSING`. | Medium (Jobs never finish and client receives stale status). | **Heartbeat Lease & Stale Job Recovery**: The worker executes `recover_stale_jobs()` on startup and polling ticks, identifying jobs whose heartbeat is older than 600s, resetting interrupted records, and requeuing them safely. |
| **R-04** | **Free Container Memory Quota (512MB RAM)**<br>High-memory PDF tools (e.g. headless Chrome) causing Out-Of-Memory (OOM) kills. | High (Container crashes under load). | **ReportLab Vector Generation**: ReportLab compiles PDFs directly in C/Python byte streams without browser binaries, maintaining memory usage under **80MB** even under peak load. |
| **R-05** | **Path Traversal Attack on Downloads**<br>Malicious queries downloading sensitive system files (`/etc/passwd`). | Critical (Data leak / security vulnerability). | **Strict Path Containment Verification**: Download handlers canonicalize file paths using `.resolve()` and enforce `file_path.relative_to(storage_dir)`, returning `HTTP 403` on any boundary breach. |

---

## 9. Phase 1 Sign-Off & Verification

This **Phase 1 Requirement Analysis and Planning Specification** establishes an unambiguous, production-grade foundation for the project:
1. Every mandatory requirement from the assignment is mapped to a concrete functional specification.
2. The zero-cost requirement (₹0) has been verified with zero paid dependencies.
3. Edge cases—such as partial batch failures, concurrency races, and crash recovery—are addressed through formal design patterns.
4. The technology stack choices are defended against standard enterprise alternatives.
