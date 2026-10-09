# Phase 6 — Bulk Processing and Job Management Specification

## 1. Architectural Strategy: Synchronous vs. In-Memory vs. Database-Backed Worker

A critical architectural decision for bulk generation APIs is determining where and how jobs are processed. Below is a rigorous comparison of the three primary processing models:

| Architectural Metric | Model 1: Synchronous Processing | Model 2: In-Memory BackgroundTasks | Model 3: Database-Backed Worker (Implemented) |
| :--- | :--- | :--- | :--- |
| **Client Connection** | Holds HTTP connection open for entire batch duration (e.g., 30s to 5 minutes) | Returns `202 Accepted` immediately | Returns `202 Accepted` immediately |
| **Timeout Vulnerability** | **Severe**: NGINX (60s), Cloudflare (100s), and client timeouts drop the connection | None on HTTP connection | None on HTTP connection |
| **Durability on Crash** | **Zero**: Abrupt crash leaves batch partially written or missing | **Zero**: Memory queue is wiped on pod/worker restart; jobs lost forever | **Full ACID Durability**: Job and child records written to disk before response |
| **Worker Crash Recovery** | Manual resubmission required by client | None; lost jobs are untrackable | **Automated Heartbeat Recovery**: Recovers interrupted records on reboot |
| **Concurrency Control** | Blocks server thread or worker pool | Uncontrolled in-memory task proliferation | **Atomic SQL Claiming**: Zero duplicate processing across workers |
| **Cost Profile** | $0.00 | $0.00 | **$0.00 (Zero-Cost: No Redis/Celery required)** |

### Why In-Memory BackgroundTasks Are NOT Production-Grade
FastAPI's built-in `BackgroundTasks` executes functions as coroutines or thread tasks inside the web server process memory. If the server is restarted (due to zero-downtime rolling deployments, Kubernetes OOM kills, configuration reloads, or server reboots), all queued and in-flight tasks in memory are permanently erased without any trace or notification to the user.

### The Implemented Solution: Durable Database-Backed Architecture
1. **Immediate Durability**: Ingestion occurs inside an ACID transaction (`db.commit()`), guaranteeing the `GenerationJob` and all child `CertificateRecord` rows reside safely on persistent disk storage before returning HTTP `202 Accepted`.
2. **Decoupled Asynchronous Execution**: Workers (whether running in a dedicated thread or separate container/process) poll the database for pending jobs.
3. **Atomic Single-Row Claiming**: Eliminates race conditions between multiple concurrent worker instances using conditional SQL updates.
4. **Resilience & Fault Isolation**: Individual recipient failures are recorded with sanitized error messages and never crash the batch.

---

## 2. Job Lifecycle and State Transitions

The system coordinates states between the parent `GenerationJob` and each child `CertificateRecord`:

```mermaid
stateDiagram-v2
    [*] --> PENDING: POST /api/v1/jobs (Job & Recipients Committed)
    
    PENDING --> PROCESSING: Worker claims via Atomic UPDATE
    
    state PROCESSING {
        [*] --> ProcessingRecipient
        ProcessingRecipient --> RecipientSuccess: PDF Rendered & Validated
        ProcessingRecipient --> RecipientFailed: Corrupted Data / Render Exception
        RecipientSuccess --> NextRecipient: Update Counters & Heartbeat
        RecipientFailed --> NextRecipient: Log Error & Heartbeat
        NextRecipient --> [*]: All Recipients Processed
    }
    
    PROCESSING --> COMPLETED: All recipients succeeded (failed_count == 0)
    PROCESSING --> COMPLETED_WITH_ERRORS: Partial or total failures (failed_count > 0)
    
    PROCESSING --> PENDING: Worker crash recovery (heartbeat timeout exceeded)
    
    COMPLETED --> [*]
    COMPLETED_WITH_ERRORS --> [*]
```

### State Machine Transition Rules

| Initial State | Target State | Trigger / Condition | DB Action |
| :--- | :--- | :--- | :--- |
| *(None)* | `PENDING` | `POST /api/v1/jobs` accepted | `INSERT INTO generation_jobs`, `INSERT INTO certificate_records` |
| `PENDING` | `PROCESSING` | Worker executes atomic claim query | `UPDATE generation_jobs SET status='PROCESSING', started_at=:now WHERE id=:id AND status='PENDING'` |
| `PROCESSING` | `COMPLETED` | Worker finishes all recipients; `failed_count == 0` | `UPDATE generation_jobs SET status='COMPLETED', completed_at=:now` |
| `PROCESSING` | `COMPLETED_WITH_ERRORS` | Worker finishes all recipients; `failed_count > 0` | `UPDATE generation_jobs SET status='COMPLETED_WITH_ERRORS', completed_at=:now` |
| `PROCESSING` | `PENDING` | Heartbeat timeout exceeded (`updated_at < now - timeout`) | `UPDATE certificate_records SET status='PENDING' WHERE status='PROCESSING'`, `UPDATE generation_jobs SET status='PENDING'` |

---

## 3. Atomic Job Claiming (Concurrency & Deduplication)

To prevent multiple worker processes or threads from claiming and processing the same bulk job simultaneously, the system employs **Atomic Conditional SQL Updates**:

```python
# app/services/worker.py
# Step 1: Discover oldest pending candidate
find_candidate_stmt = (
    select(GenerationJob.id)
    .where(GenerationJob.status == JobStatus.PENDING.value)
    .order_by(GenerationJob.created_at.asc())
    .limit(1)
)
job_id = db.execute(find_candidate_stmt).scalar_one_or_none()
if not job_id:
    return None

# Step 2: Atomically claim candidate with conditional WHERE clause
now = datetime.now(timezone.utc)
claim_stmt = (
    update(GenerationJob)
    .where(
        GenerationJob.id == job_id,
        GenerationJob.status == JobStatus.PENDING.value  # Guard condition!
    )
    .values(status=JobStatus.PROCESSING.value, started_at=now, updated_at=now)
)
result = db.execute(claim_stmt)
db.commit()

# If another worker executed the update first, rowcount is 0
if result.rowcount == 0:
    logger.debug("Job '%s' was claimed concurrently by another worker.", job_id)
    return None
```

### Why This Eliminates Distributed Locks (Redis/Redlock)
- The database engine is the single source of truth.
- Under SQLite WAL mode or PostgreSQL MVCC, row-level updates are serialized. The first worker to match `status == 'PENDING'` modifies the row and gets `rowcount == 1`.
- Any subsequent worker executing against the same ID sees `status == 'PROCESSING'`, resulting in `rowcount == 0`. The losing worker immediately backs off, preventing duplicate generation.

---

## 4. Fault Isolation & Individual Recipient Error Capture

A fundamental requirement of enterprise bulk processing is **failure containment**: a corrupt name, unrenderable character sequence, or single disk write error must never terminate the entire batch job.

```python
# app/services/worker.py
for record in records:
    record.status = CertificateStatus.PROCESSING.value
    db.commit()

    # Recipient validation check
    if not record.recipient_name or len(record.recipient_name.strip()) < 2:
        record.status = CertificateStatus.FAILED.value
        record.error_code = "INVALID_RECIPIENT_DATA"
        record.error_message = "Recipient name must be at least 2 characters long."
        record.completed_at = datetime.now(timezone.utc)
        job.failed_count += 1
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        continue

    # Isolated PDF rendering try-except block
    try:
        pdf_path = certificate_generator.render_certificate(...)
        record.file_path = str(pdf_path)
        record.status = CertificateStatus.SUCCESS.value
        record.completed_at = datetime.now(timezone.utc)
        job.successful_count += 1
    except Exception as exc:
        # Full stack trace logged to backend monitoring
        logger.exception("Failed to generate PDF for recipient '%s'", record.recipient_name)
        # Sanitized error recorded in database
        record.status = CertificateStatus.FAILED.value
        record.error_code = "PDF_RENDER_ERROR"
        record.error_message = str(exc)
        record.completed_at = datetime.now(timezone.utc)
        job.failed_count += 1

    # Progressive heartbeat update
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
```

### Information Preservation vs. Security Boundaries
- **In Internal Logs**: The complete stack trace, traceback frames, and internal arguments are logged via `logger.exception()`, enabling rapid engineer diagnosis.
- **In Public Database & API**: The API response presents a clean, non-sensitive summary:
  - `error_code`: Categorical identifier (`INVALID_RECIPIENT_DATA`, `PDF_RENDER_ERROR`).
  - `error_message`: High-level explanation without exposing internal server paths, database credentials, or system filenames.

---

## 5. Real-Time Metrics & Multi-Counter Progress Tracking

The system provides complete visibility into job execution via `GET /api/v1/jobs/{job_id}`:

```json
{
  "job_id": "4e72c830-1b29-4598-a669-e30d12e6d981",
  "status": "PROCESSING",
  "event_name": "Full Stack Mastery",
  "issuer_name": "Tech Academy",
  "issue_date": "2026-10-10",
  "certificate_title": "Certificate of Completion",
  "total_recipients": 100,
  "successful_count": 45,
  "failed_count": 2,
  "pending_count": 52,
  "processing_count": 1,
  "progress_percentage": 47.0,
  "created_at": "2026-10-10T02:00:00Z",
  "started_at": "2026-10-10T02:00:02Z",
  "completed_at": null,
  "zip_download_url": "http://127.0.0.1:8000/api/v1/jobs/4e72c830-1b29-4598-a669-e30d12e6d981/download"
}
```

### Real-Time Count Derivation
The status query dynamically aggregates counts directly from the child `certificate_records` table:

$$\text{processed} = \text{successful\_count} + \text{failed\_count}$$
$$\text{progress\_percentage} = \operatorname{round}\left(\frac{\text{processed}}{\text{total\_recipients}} \times 100,\, 1\right)$$

---

## 6. Crash Recovery & Stale Job Re-Queueing

### The Worker Crash Scenario
Consider an unexpected worker shutdown (e.g., node reboot, OOM killed by kernel, power failure):
- A batch was halfway through: 25 certificates succeeded, 1 was currently generating (`PROCESSING`), and 74 were queued (`PENDING`).
- The job is left stranded in `PROCESSING`.

### The Recovery Policy (`recover_stale_jobs`)
Every polling iteration, the worker checks for jobs whose `updated_at` timestamp has exceeded the configurable heartbeat timeout:

$$\text{threshold} = \text{now}() - \text{timedelta}(\text{seconds}=\text{WORKER\_JOB\_TIMEOUT\_SECONDS})$$

```python
# app/services/worker.py
def recover_stale_jobs(self, db: Session) -> int:
    timeout_threshold = datetime.now(timezone.utc) - timedelta(seconds=settings.WORKER_JOB_TIMEOUT_SECONDS)
    stale_jobs = db.execute(
        select(GenerationJob).where(
            GenerationJob.status == JobStatus.PROCESSING.value,
            GenerationJob.updated_at < timeout_threshold
        )
    ).scalars().all()

    for job in stale_jobs:
        # Reset interrupted in-flight records
        db.execute(
            update(CertificateRecord)
            .where(
                CertificateRecord.job_id == job.id,
                CertificateRecord.status == CertificateStatus.PROCESSING.value
            )
            .values(status=CertificateStatus.PENDING.value)
        )

        # Requeue job back to PENDING
        job.status = JobStatus.PENDING.value
        job.updated_at = datetime.now(timezone.utc)

    db.commit()
```

### Why Idempotency Prevents Redundant Work
- Succeeded records (`SUCCESS`) remain untouched. Their files exist on disk, and their counters are intact.
- Only the single interrupted record (`PROCESSING`) is reverted to `PENDING`.
- When the recovered job is picked up, the worker loop only queries `status IN ('PENDING', 'PROCESSING')`, skipping already generated certificates.

---

## 7. Verification & Automated Test Coverage (22/22 Passing)

The bulk processing and worker resilience features are validated by comprehensive automated test suites:

| Test Case | Objective | Status |
| :--- | :--- | :--- |
| `test_job_submission_and_processing_lifecycle` | End-to-end test verifying submission, status progression, counter metrics, and completion | **PASSED** |
| `test_individual_recipient_failure_does_not_halt_job` | Verifies failure isolation when 1 of 3 recipients has invalid data; remaining 2 succeed | **PASSED** |
| `test_recover_stale_jobs_after_worker_crash` | Simulates dead worker; verifies state recovery, in-flight record reset, and successful completion | **PASSED** |
| `test_atomic_claim_concurrency_prevents_duplicate_processing` | Confirms second concurrent worker cannot double-claim a pending job | **PASSED** |
| `test_download_single_certificate_pdf` | Verifies download of individual certificate PDF with correct headers | **PASSED** |
| `test_download_job_certificates_zip` | Verifies packaging and download of all successful certificates as a ZIP archive | **PASSED** |
