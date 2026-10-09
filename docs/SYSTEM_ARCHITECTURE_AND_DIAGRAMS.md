# 🏛 Phase 2 — System Architecture & Diagrams Specification

**Project**: Bulk Certificate Generator Backend API  
**Format**: Editable Mermaid.js Text-Based Diagrams  
**Document Version**: 1.0.0 (Implementation-Aligned)

---

## 1. High-Level System Architecture

### 1.1 Mermaid Diagram
```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer"]
        Client["API Client (Web App / Postman / cURL)"]
    end

    subgraph APILayer ["FastAPI Web Application"]
        Router["API Router (/api/v1/jobs, /certificates)"]
        Validator["Pydantic v2 Request Validator"]
        JobService["Job Service"]
    end

    subgraph StorageLayer ["Persistence & Storage Layer"]
        DB[("Relational Database (SQLite WAL / PostgreSQL)<br/>• generation_jobs<br/>• certificate_records")]
        DiskStorage[("Persistent File Storage<br/>./storage/certificates/{job_id}/")]
    end

    subgraph WorkerLayer ["Asynchronous Processing Layer"]
        Worker["Background Worker Process"]
        PDFEngine["ReportLab PDF Generation Engine"]
    end

    %% Client Interactions
    Client -->|"1. Submit Bulk Request (POST /jobs)"| Router
    Router --> Validator
    Validator --> JobService
    JobService -->|"2. Transactional Write (Job + Recipients)"| DB
    JobService -->|"3. HTTP 202 Accepted (Job ID + Status URL)"| Client

    %% Client Polling & Retrieval
    Client -->|"4. Poll Progress (GET /jobs/{id})"| Router
    Router -->|"Query Status"| DB
    Client -->|"5. Download PDF / ZIP"| Router
    Router -->|"Stream File"| DiskStorage

    %% Worker Operations
    Worker -->|"6. Atomic Claim (UPDATE status='PROCESSING')"| DB
    Worker -->|"7. Fetch Pending Recipients"| DB
    Worker -->|"8. Render Vector PDF"| PDFEngine
    PDFEngine -->|"9. Write Safe File"| DiskStorage
    Worker -->|"10. Update Recipient & Job Counters"| DB

    classDef client fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a;
    classDef api fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#0f172a;
    classDef storage fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#0f172a;
    classDef worker fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#0f172a;

    class Client client;
    class Router,Validator,JobService api;
    class DB,DiskStorage storage;
    class Worker,PDFEngine worker;
```

### 1.2 Component Explanation & Data Flow
- **API Client**: Submits bulk certificate generation requests, polls progress endpoints, and retrieves generated PDF certificates or bulk ZIP archives.
- **FastAPI Web Application**: Serves as the high-speed ASGI entry point. It parses JSON payloads, validates schema constraints via Pydantic v2, transactionally persists job records in `PENDING` status, and responds with `HTTP 202 Accepted` in `< 200ms`.
- **Relational Database (`SQLite WAL`)**: Serves as the durable, transactional state store and queue. With Write-Ahead Logging (`WAL`), concurrent read queries from the web API operate without blocking background worker writes.
- **Background Worker**: Polls for pending jobs, claims them atomically to prevent duplicate runs, iterates over recipients with isolated error handling, invokes the PDF engine, and streams updates to the database.
- **Persistent File Storage**: Structured local directory (`./storage/certificates/{job_id}/{certificate_id}.pdf`) preserving generated files with path traversal security protections.

---

## 2. Component Architecture

### 2.1 Mermaid Diagram
```mermaid
flowchart TD
    subgraph Presentation ["Presentation & API Layer"]
        Main["FastAPI App Factory (app/main.py)"]
        JobRouter["Jobs Router (app/api/v1/jobs.py)"]
        CertRouter["Certificates Router (app/api/v1/certificates.py)"]
        HealthRouter["Health Router (app/api/v1/health.py)"]
        Deps["Dependency Injection (app/api/deps.py)"]
    end

    subgraph Schemas ["Contracts & Validation Layer"]
        JobSchemas["Job Schemas (BulkCreateJobRequest, JobStatusResponse)"]
        RecipientSchemas["Recipient Schemas (RecipientInput, CertificateRecordResponse)"]
        CommonSchemas["Common Schemas (HealthResponse, ErrorResponse)"]
    end

    subgraph Service ["Business & Domain Logic Layer"]
        JobService["Job Service (app/services/job_service.py)"]
        WorkerEngine["Worker Engine (app/services/worker.py)"]
        PDFService["Certificate Service (app/services/certificate_service.py)"]
    end

    subgraph DataAccess ["Data Access & Models Layer"]
        DBSession["Engine & SessionLocal (app/db/session.py)"]
        DBBase["Declarative Base (app/db/base.py)"]
        JobModel["GenerationJob ORM Model (app/models/job.py)"]
        CertModel["CertificateRecord ORM Model (app/models/certificate.py)"]
    end

    subgraph CrossCutting ["Cross-Cutting Concerns"]
        Config["Configuration Management (app/core/config.py)"]
        Logging["Structured Logging (app/core/logging.py)"]
        Errors["Domain Exceptions (app/core/errors.py)"]
    end

    %% Dependencies
    Main --> JobRouter & CertRouter & HealthRouter
    JobRouter --> Deps & JobSchemas & RecipientSchemas & JobService
    CertRouter --> Deps & JobService
    HealthRouter --> Deps & CommonSchemas
    JobService --> DBSession & JobModel & CertModel & PDFService & Errors
    WorkerEngine --> DBSession & JobModel & CertModel & PDFService & Logging
    PDFService --> Config & Logging
    DBSession --> Config & DBBase
    JobModel & CertModel --> DBBase
```

### 2.2 Component Explanation
- **API Routers (`app/api/v1/`)**: Expose REST endpoints, map HTTP query/path parameters, and return serialized responses.
- **Schemas (`app/schemas/`)**: Define strict Pydantic v2 data contracts, sanitize strings, and validate email formats.
- **Job Service (`app/services/job_service.py`)**: Coordinates business logic, creates jobs transactionally, resolves canonical file paths, and builds compressed `.zip` archives.
- **Worker Engine (`app/services/worker.py`)**: Runs the background execution loop, claims pending jobs, executes per-recipient generation, and detects stale jobs.
- **Certificate Service (`app/services/certificate_service.py`)**: Implements the ReportLab vector canvas, applying decorative borders, vector seals, typography, and unique ID formatting.
- **Data Access & Models (`app/db/`, `app/models/`)**: Encapsulates SQLAlchemy 2.0 ORM mappings, session lifecycle, and SQLite PRAGMA WAL settings.
- **Cross-Cutting**: Centralizes environment settings via `pydantic-settings`, structured logging, and global exception mapping.

---

## 3. Request-Processing Sequence Diagram

### 3.1 Mermaid Diagram
```mermaid
sequenceDiagram
    autonumber
    actor Client as API Client
    participant Router as FastAPI Router
    participant Validator as Pydantic Validator
    participant Service as Job Service
    participant DB as Relational Database

    Client->>Router: POST /api/v1/jobs (Event Metadata + Recipients Array)
    Router->>Validator: Validate Schema & Batch Size (1 to 1000)
    
    alt Validation Error (Empty array, missing fields, batch > 1000)
        Validator-->>Router: ValidationError
        Router-->>Client: HTTP 422 Unprocessable Content (Error Details)
    else Validation Successful
        Validator-->>Router: Validated BulkCreateJobRequest
        Router->>Service: create_bulk_job(db, request)
        
        Service->>DB: BEGIN Transaction
        Service->>DB: INSERT into generation_jobs (status='PENDING', counters=0)
        loop For each recipient in request
            Service->>DB: INSERT into certificate_records (status='PENDING', unique_cert_id)
        end
        Service->>DB: COMMIT Transaction
        DB-->>Service: Transaction Committed
        
        Service-->>Router: Created GenerationJob (job_id)
        Router-->>Client: HTTP 202 Accepted { job_id, status: "PENDING", status_url }
    end
```

### 3.2 Flow Explanation
1. The client sends a single `POST /api/v1/jobs` request containing event information and up to 1,000 recipients.
2. Pydantic v2 validates types, boundary constraints, and string sanitization. If invalid, the request is rejected immediately with `HTTP 422` before touching the database.
3. If valid, the Job Service creates a parent `GenerationJob` and pre-allocates `CertificateRecord` entries with unique identifiers (`CERT-XXXX-XXXX-XXXX`) inside a single atomic transaction.
4. The API commits the records and immediately responds with `HTTP 202 Accepted`, providing the client with `job_id` and the status URL in `< 200ms`.

---

## 4. Certificate Generation Sequence Diagram

### 4.1 Mermaid Diagram
```mermaid
sequenceDiagram
    autonumber
    participant Worker as Background Worker
    participant DB as Relational Database
    participant Generator as ReportLab Generator
    participant Storage as File Storage (Disk)

    Worker->>DB: Atomic Claim: UPDATE generation_jobs SET status='PROCESSING' WHERE status='PENDING'
    alt No Pending Jobs
        Worker->>Worker: Sleep for poll interval (2.0s)
    else Job Claimed Successfully
        Worker->>DB: SELECT * FROM certificate_records WHERE job_id = :id AND status = 'PENDING'
        
        loop For each CertificateRecord
            Worker->>DB: UPDATE certificate_records SET status = 'PROCESSING'
            
            alt Recipient Data Invalid (e.g., blank name string)
                Worker->>DB: UPDATE certificate_records SET status = 'FAILED', error_code = 'INVALID_RECIPIENT_DATA'
                Worker->>DB: Increment job.failed_count
            else Recipient Data Valid
                Worker->>Generator: render_certificate(job_metadata, recipient_data, cert_id)
                
                alt Rendering Succeeded
                    Generator->>Storage: Write PDF to ./storage/certificates/{job_id}/{cert_id}.pdf
                    Storage-->>Generator: File written (> 1KB)
                    Generator-->>Worker: File Path
                    Worker->>DB: UPDATE certificate_records SET status = 'SUCCESS', file_path = :path
                    Worker->>DB: Increment job.successful_count
                else PDF Generation Exception
                    Generator-->>Worker: Exception (e.g. Render Error)
                    Worker->>DB: UPDATE certificate_records SET status = 'FAILED', error_code = 'PDF_RENDER_ERROR'
                    Worker->>DB: Increment job.failed_count
                end
            end
            
            Worker->>DB: UPDATE generation_jobs SET updated_at = NOW() (Heartbeat)
            Worker->>DB: COMMIT Record Outcome
        end
        
        Worker->>DB: Finalize Job: Set completed_at, status = ('COMPLETED' or 'COMPLETED_WITH_ERRORS')
        Worker->>DB: COMMIT Job Status
    end
```

### 4.2 Flow Explanation
1. The worker discovers and claims a pending job atomically.
2. It fetches all pending certificate records belonging to that job.
3. For each recipient, it updates status to `PROCESSING` and validates recipient data.
4. ReportLab renders the landscape vector PDF canvas and writes it to disk.
5. If rendering succeeds, the record is marked `SUCCESS` and `successful_count` is incremented.
6. If an error occurs, it is caught; the record is marked `FAILED` with an error code, `failed_count` is incremented, and processing continues to the next recipient without halting the batch.
7. Upon finishing the loop, the worker evaluates aggregate counters and sets `COMPLETED` or `COMPLETED_WITH_ERRORS`.

---

## 5. Entity Relationship Diagram (ERD)

### 5.1 Mermaid Diagram
```mermaid
erDiagram
    GENERATION_JOB ||--o{ CERTIFICATE_RECORD : "contains / generates"

    GENERATION_JOB {
        string id PK "UUID v4 (VARCHAR 36)"
        string status "Indexed (PENDING, PROCESSING, COMPLETED, etc.)"
        string event_name "Course / Event Title (VARCHAR 255)"
        string issuer_name "Issuing Organization (VARCHAR 255)"
        string issue_date "Date of award (VARCHAR 50)"
        string certificate_title "Certificate Title Header (VARCHAR 255)"
        int total_recipients "Total batch count"
        int successful_count "Successfully generated count"
        int failed_count "Failed generation count"
        datetime created_at "Creation timestamp"
        datetime started_at "Processing start timestamp"
        datetime completed_at "Processing completion timestamp"
        datetime updated_at "Worker heartbeat timestamp"
    }

    CERTIFICATE_RECORD {
        string id PK "UUID v4 (VARCHAR 36)"
        string job_id FK "References GENERATION_JOB.id (ON DELETE CASCADE)"
        string recipient_name "Recipient full legal name (VARCHAR 255)"
        string recipient_email "Optional email (VARCHAR 320)"
        string custom_remarks "Optional honors / remarks (VARCHAR 500)"
        string certificate_id UK "Unique identifier, e.g. CERT-XXXX-XXXX (VARCHAR 100)"
        string status "Indexed (PENDING, PROCESSING, SUCCESS, FAILED)"
        string file_path "Relative path to PDF file (TEXT)"
        string error_code "Failure category code (VARCHAR 64)"
        string error_message "Human-readable failure details (TEXT)"
        datetime created_at "Creation timestamp"
        datetime completed_at "Generation completion timestamp"
    }
```

### 5.2 Relationship Characteristics
- **Cardinality**: `1:N` (One `GENERATION_JOB` contains zero to many `CERTIFICATE_RECORD` entries).
- **Referential Integrity**: `job_id` references `GENERATION_JOB.id` with `ON DELETE CASCADE`. If a job is removed, its associated certificate records are cleaned up automatically.
- **Uniqueness**: `certificate_id` is globally unique across all jobs to guarantee unambiguous verification and retrieval.

---

## 6. Detailed Database Schema Diagram

### 6.1 Mermaid Diagram
```mermaid
classDiagram
    class generation_jobs {
        +VARCHAR(36) id [PK]
        +VARCHAR(32) status [NOT NULL, INDEXED]
        +VARCHAR(255) event_name [NOT NULL]
        +VARCHAR(255) issuer_name [NOT NULL]
        +VARCHAR(50) issue_date [NOT NULL]
        +VARCHAR(255) certificate_title [NOT NULL, DEFAULT='Certificate of Completion']
        +INTEGER total_recipients [NOT NULL, DEFAULT=0]
        +INTEGER successful_count [NOT NULL, DEFAULT=0]
        +INTEGER failed_count [NOT NULL, DEFAULT=0]
        +DATETIME created_at [NOT NULL]
        +DATETIME started_at [NULLABLE]
        +DATETIME completed_at [NULLABLE]
        +DATETIME updated_at [NOT NULL]
    }

    class certificate_records {
        +VARCHAR(36) id [PK]
        +VARCHAR(36) job_id [FK, NOT NULL, INDEXED]
        +VARCHAR(255) recipient_name [NOT NULL]
        +VARCHAR(320) recipient_email [NULLABLE]
        +VARCHAR(500) custom_remarks [NULLABLE]
        +VARCHAR(100) certificate_id [UNIQUE, INDEXED, NULLABLE]
        +VARCHAR(32) status [NOT NULL, INDEXED, DEFAULT='PENDING']
        +TEXT file_path [NULLABLE]
        +VARCHAR(64) error_code [NULLABLE]
        +TEXT error_message [NULLABLE]
        +DATETIME created_at [NOT NULL]
        +DATETIME completed_at [NULLABLE]
    }

    generation_jobs "1" --> "0..*" certificate_records : foreign_key(job_id)
```

### 6.2 Index Details
1. `ix_generation_jobs_status`: Supports worker polling `WHERE status = 'PENDING'`.
2. `ix_certificate_records_job_id`: Optimizes joins for `WHERE job_id = :job_id`.
3. `ix_certificate_records_certificate_id`: Ensures $O(1)$ lookup for `GET /certificates/{certificate_id}/download`.
4. `ix_certificate_records_status`: Accelerates filtering by status (`SUCCESS`, `FAILED`).

---

## 7. Deployment Architecture

### 7.1 Mermaid Diagram
```mermaid
flowchart TB
    subgraph OptionA ["Option A: Local Development & Demonstration Setup (₹0 Cost)"]
        DevHost["Developer Workstation (Windows / Linux / macOS)"]
        subgraph LocalEnv ["Local Python Environment"]
            Uvicorn["Uvicorn ASGI Server (:8000)"]
            FastAPIApp["FastAPI Application"]
            InAppWorker["In-Process Worker Daemon Thread<br/>(or standalone python worker_runner.py)"]
        end
        LocalDB[("Local SQLite Database<br/>./data.db (WAL Mode)")]
        LocalDisk[("Local Storage Directory<br/>./storage/certificates/")]
        
        DevHost --> LocalEnv
        FastAPIApp --> LocalDB & LocalDisk
        InAppWorker --> LocalDB & LocalDisk
    end

    subgraph OptionB ["Option B: Containerized Multi-Container Setup (₹0 Cost)"]
        DockerEngine["Docker Engine / Docker Compose"]
        subgraph ComposeCluster ["Docker Network"]
            APIContainer["Container 1: cert_generator_api<br/>(Uvicorn + FastAPI :8000)"]
            WorkerContainer["Container 2: cert_generator_worker<br/>(python worker_runner.py)"]
        end
        SharedVolume[("Shared Persistent Volume<br/>cert_data (/app/storage)")]
        
        DockerEngine --> ComposeCluster
        APIContainer -->|"Read / Write"| SharedVolume
        WorkerContainer -->|"Atomic Claim & Render"| SharedVolume
    end

    classDef local fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#0f172a;
    classDef container fill:#eff6ff,stroke:#2563eb,stroke-width:2px,color:#0f172a;
    class OptionA local;
    class OptionB container;
```

### 7.2 Deployment Strategy
- **Option A (Local-First Development)**: Zero external services. Runs on the local developer workstation using SQLite WAL mode and local disk storage. 100% persistent, reproducible, and requires zero paid resources.
- **Option B (Decoupled Multi-Container Docker)**: Employs `docker-compose.yml` to separate the web server (`api`) from the worker process (`worker`). A shared persistent Docker volume mounts both the database file and generated certificate PDFs.

---

## 8. Error-Handling and Retry Flowchart

### 8.1 Mermaid Diagram
```mermaid
flowchart TD
    Start(["Client Submits Request (POST /api/v1/jobs)"]) --> V1{"Schema & Batch Valid?<br/>(1 <= count <= 1000)"}

    V1 -- "No" --> Ret422["Return HTTP 422 Unprocessable Content<br/>(error_code: VALIDATION_ERROR)"]
    V1 -- "Yes" --> CreateJob["Create GenerationJob (PENDING)<br/>Persist Recipient Records (PENDING)"]
    CreateJob --> Ret202["Return HTTP 202 Accepted<br/>(job_id + status_url)"]

    Ret202 --> WorkerClaim["Worker Atomically Claims Job<br/>(status -> PROCESSING)"]
    WorkerClaim --> NextRec{"More Pending Recipients?"}

    NextRec -- "Yes" --> ValRec{"Recipient Fields Valid?<br/>(Name length >= 2)"}
    
    ValRec -- "No" --> RecFailVal["Mark Recipient FAILED<br/>error_code: INVALID_RECIPIENT_DATA<br/>Increment failed_count"]
    ValRec -- "Yes" --> GenPDF["Render PDF via ReportLab"]

    GenPDF --> PDFSuccess{"Generation Succeeded?<br/>(File exists & size > 1KB)"}
    
    PDFSuccess -- "Yes" --> RecSuccess["Mark Recipient SUCCESS<br/>Save file_path<br/>Increment successful_count"]
    PDFSuccess -- "No / Exception" --> RecFailGen["Mark Recipient FAILED<br/>error_code: PDF_RENDER_ERROR<br/>Increment failed_count"]

    RecFailVal --> Heartbeat["Update Job updated_at (Heartbeat)"]
    RecSuccess --> Heartbeat
    RecFailGen --> Heartbeat
    Heartbeat --> NextRec

    NextRec -- "No" --> FinalStatus{"Any Failures Encountered?"}
    FinalStatus -- "0 Failures" --> SetCompleted["Set Job status: COMPLETED"]
    FinalStatus -- "> 0 Failures" --> SetPartial["Set Job status: COMPLETED_WITH_ERRORS"]

    SetCompleted --> Done(["Job Complete & Available for Download"])
    SetPartial --> Done

    classDef failure fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#0f172a;
    classDef success fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#0f172a;
    classDef process fill:#f8fafc,stroke:#64748b,stroke-width:2px,color:#0f172a;

    class Ret422,RecFailVal,RecFailGen failure;
    class Ret202,RecSuccess,SetCompleted success;
    class Start,V1,CreateJob,WorkerClaim,NextRec,ValRec,GenPDF,PDFSuccess,Heartbeat,FinalStatus,SetPartial,Done process;
```

### 8.2 Error Isolation Guarantees
- **HTTP Layer**: Validations fail fast without writing dirty data to the database.
- **Worker Layer**: Each recipient execution is wrapped in an isolated exception handler. An unhandled character or disk error on recipient #10 updates recipient #10 as `FAILED`, increments `failed_count`, and immediately transitions to recipient #11.
- **Job Outcome**: The final job state accurately reflects whether the run was 100% clean (`COMPLETED`) or experienced partial failures (`COMPLETED_WITH_ERRORS`).

---

## 9. Background Worker Architecture & Job Lifecycle Flow

### 9.1 Mermaid Diagram
```mermaid
flowchart TD
    subgraph PollingLoop ["Worker Execution Loop"]
        Start(["Worker Starts Polling Loop"]) --> StaleCheck["Check & Recover Stale Jobs<br/>(status='PROCESSING' and timeout > 600s)"]
        StaleCheck --> FindJob{"Find Pending Job<br/>(status = 'PENDING')"}
        
        FindJob -- "None Found" --> Sleep["Sleep WORKER_POLL_INTERVAL_SECONDS (2.0s)"]
        Sleep --> Start
        
        FindJob -- "Candidate Found" --> AtomicClaim["Execute Atomic UPDATE:<br/>UPDATE generation_jobs<br/>SET status='PROCESSING', started_at=NOW()<br/>WHERE id=:id AND status='PENDING'"]
        
        AtomicClaim --> RaceCheck{"Rows Affected == 1?"}
        RaceCheck -- "No (Claimed by another worker)" --> Sleep
        RaceCheck -- "Yes (Claim Won)" --> FetchBatch["Fetch Recipient Records for Job"]
    end

    subgraph BatchLoop ["Per-Recipient Processing Loop"]
        FetchBatch --> ProcessItem["Process Next Recipient"]
        ProcessItem --> Render["Validate & Render Vector PDF"]
        Render --> PersistResult["Commit Recipient Outcome & Heartbeat"]
        PersistResult --> MoreItems{"More Items Remaining?"}
        MoreItems -- "Yes" --> ProcessItem
        MoreItems -- "No" --> AggregateStatus["Calculate Final Counts & Set Status:<br/>COMPLETED or COMPLETED_WITH_ERRORS"]
    end

    AggregateStatus --> Sleep

    classDef highlight fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px,color:#0f172a;
    class AtomicClaim,RaceCheck,AggregateStatus highlight;
```

### 9.2 Concurrency & Reliability Guarantees
1. **Atomic Claiming**: Avoids distributed lock overhead (Redlock). Only one worker can successfully update the row from `PENDING` to `PROCESSING`.
2. **Heartbeat Leases**: The worker updates `generation_jobs.updated_at` on every recipient outcome.
3. **Crash Recovery**: If a worker process is terminated (e.g., SIGKILL or power outage), the next running worker identifies orphaned jobs where `updated_at < (NOW - 600s)`, resets interrupted recipient records, and requeues the job safely without manual intervention.

---

## 🏁 Phase 2 Architecture Review Summary

All 9 diagrams have been formatted using standard, editable **Mermaid.js** syntax and verified against the actual implemented code in the repository. They are documented in [`docs/SYSTEM_ARCHITECTURE_AND_DIAGRAMS.md`](file:///c:/Users/dell/Downloads/Bulk%20Certificate%20Generator/docs/SYSTEM_ARCHITECTURE_AND_DIAGRAMS.md).
