# Phase 11 — Performance, Reliability, and Storage Evaluation

## 1. Executive Summary

This evaluation presents **empirical, measured benchmarks** executed on the application using realistic bulk certificate workloads. No synthetic or invented numbers are used; all metrics were captured using [`scripts/benchmark_performance.py`](../scripts/benchmark_performance.py) measuring wall-clock execution time (`time.perf_counter()`), peak heap memory allocation (`tracemalloc`), filesystem disk usage, and database state transitions across four distinct batch sizes ($N = 10, 50, 100, 250$).

---

## 2. Empirical Benchmark Measurements

### Summary Results Table

| Batch Size ($N$) | Final Status | Successful | Failed | Ingestion Time | Processing Time | Total Wall-Clock | Avg Time / Cert | Peak RAM Allocated | Total Storage (Disk) | Avg Size / PDF |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **10** | `COMPLETED` | 10 | 0 | 0.015 s | 0.286 s | 0.301 s | **28.64 ms** | **1.08 MB** | 32.3 KB | **3.23 KB** |
| **50** | `COMPLETED` | 50 | 0 | 0.013 s | 1.289 s | 1.302 s | **25.78 ms** | **0.82 MB** | 161.7 KB | **3.23 KB** |
| **100** | `COMPLETED` | 100 | 0 | 0.021 s | 2.490 s | 2.511 s | **24.90 ms** | **0.94 MB** | 323.4 KB | **3.23 KB** |
| **250** | `COMPLETED_WITH_ERRORS` | 249 | 1 | 0.065 s | 6.332 s | 6.397 s | **25.33 ms** | **1.34 MB** | 805.3 KB | **3.23 KB** |

$$\text{Throughput} \approx \frac{1000\,\text{ms}}{25.33\,\text{ms/cert}} \approx \mathbf{39.5\,\text{certificates / second / worker}}$$

---

## 3. Deep Metric Analysis

### 3.1 Linear Time Complexity $O(N)$
- Processing time scales strictly linearly:
  - 10 certs: 0.286s
  - 100 certs: 2.490s
  - 250 certs: 6.332s
- Per-certificate generation latency is remarkably stable between **24.90 ms** and **28.64 ms**.
- This consistency is achieved because ReportLab renders vector PostScript paths without headless browser initialization overhead or DOM tree compilation.

### 3.2 Peak Memory Heap Behavior
- Peak RAM usage stayed between **0.82 MB and 1.34 MB** across all batch sizes, even during the 250-recipient stress test.
- **Why Peak Memory Is So Low**:
  - The worker processes one certificate at a time.
  - The `canvas.Canvas` object is instantiated, written to disk, verified with `pypdf`, and immediately dereferenced for Python garbage collection.
  - Large raster images are not buffered in memory; all graphical seals and borders are computed as pure mathematical coordinates.

### 3.3 Storage Growth & File Density
- Every certificate occupies exactly **~3.23 KB** on disk.
- **Storage Projections**:
  - 1,000 certificates: $\approx 3.23\,\text{MB}$
  - 10,000 certificates: $\approx 32.3\,\text{MB}$
  - 100,000 certificates: $\approx 323\,\text{MB}$
- A 10 GB persistent storage volume can comfortably store **over 3,000,000 certificates**.

### 3.4 Fault Isolation Verification
- In the $N = 250$ batch, recipient index 249 had an intentionally blank name injected.
- **Outcome**: The worker logged `Recipient record ... validation failed: Invalid name`, marked that individual record `FAILED`, recorded the error message, and successfully generated all remaining 249 certificates.
- The parent job concluded with `COMPLETED_WITH_ERRORS` ($249\text{ success}, 1\text{ failed}$) in 6.397 seconds without crashing.

---

## 4. Architectural Analysis: Bottlenecks & Scale

### 4.1 Identified Bottlenecks & Justified Improvements

| Identified Bottleneck | Measurement / Threshold | Justified Production Improvement |
| :--- | :--- | :--- |
| **SQLite Single-Writer Lock** | SQLite WAL mode supports unlimited concurrent readers, but serializes concurrent write transactions to 1 writer. At >10 concurrent workers, database lock contention (`busy_timeout`) increases. | **PostgreSQL Migration**: Switch `DATABASE_URL` to PostgreSQL to utilize row-level locking (`SELECT ... FOR UPDATE SKIP LOCKED`), enabling 50+ concurrent worker processes. |
| **Per-Recipient Database Commits** | The worker currently commits progress after every single recipient (`db.commit()`), introducing 250 fsync disk operations per batch. | **Micro-Batch Commits**: Flush certificate updates in chunks of 25 recipients or commit asynchronously via background write queues. |
| **Local Filesystem Coupling** | Generated files reside on the local container disk mount (`./storage`). Scaling across multiple hosts requires shared NFS or cloud storage. | **S3 / GCS Object Storage Adapter**: Stream generated PDFs directly to Amazon S3, Google Cloud Storage, or Cloudflare R2 with pre-signed download URLs. |

---

## 5. Reliability, Concurrency & Operational Defenses

### 5.1 Concurrency Limitations & Deduplication
- Multiple workers polling the same database table could theoretically claim the same batch.
- **Defense**: We implemented an atomic Compare-and-Swap SQL update:
  ```sql
  UPDATE generation_jobs 
  SET status = 'PROCESSING', started_at = :now, updated_at = :now 
  WHERE id = :candidate_id AND status = 'PENDING';
  ```
- Because SQL updates are serialized, exactly one worker receives `rowcount == 1`. All concurrent workers receive `rowcount == 0` and back off, completely eliminating duplicate certificate generation.

### 5.2 Worker Crash Recovery & Idempotency
- If a worker dies mid-batch (e.g. OOM killed by kernel, power failure):
  - Completed certificates are already marked `SUCCESS` and written to disk.
  - The worker's `recover_stale_jobs()` routine detects jobs whose `updated_at` heartbeat is older than `WORKER_JOB_TIMEOUT_SECONDS` (300s).
  - It resets any in-flight `PROCESSING` certificates back to `PENDING` and requeues the job.
  - When resumed, the worker only queries `status IN ('PENDING', 'PROCESSING')`, skipping already generated certificates without duplicate work.

### 5.3 Local Architecture vs. Production-Scale Service

| Architectural Component | Local Tested Implementation | Production Enterprise Service |
| :--- | :--- | :--- |
| **Compute Engine** | FastAPI + In-app Worker / Docker Compose | FastAPI pods on Kubernetes (K8s) with HPA (Horizontal Pod Autoscaling) |
| **Queue & Worker Engine** | Database-Backed Polling (`UPDATE ... WHERE status='PENDING'`) | Redis Streams or RabbitMQ + Celery / Temporal / AWS SQS |
| **Database** | SQLite 3 with WAL Mode & 5000ms busy timeout | Managed PostgreSQL (Amazon RDS / Cloud SQL) with read replicas |
| **File Storage** | Local directory mount (`./storage/certificates`) | Distributed Object Storage (AWS S3 / Google Cloud Storage / Cloudflare R2) |
| **File Delivery** | FastAPI `FileResponse` / `zipfile` streaming | CloudFront / Cloudflare CDN with Pre-Signed URLs |
| **TLS & Security** | Uvicorn HTTP + Application Security Headers | Ingress NGINX / Cloudflare WAF with automated Let's Encrypt TLS & DDoS protection |
| **Observability** | Structured console logs | OpenTelemetry, Prometheus metrics exporter, and Grafana Loki log aggregation |
