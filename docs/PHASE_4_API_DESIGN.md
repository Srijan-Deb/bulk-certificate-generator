# 🌐 Phase 4 — API Design Specification

**Project**: Bulk Certificate Generator Backend API  
**Author / Engineering Lead**: Backend Engineering & Architecture Team  
**Contract Standard**: RESTful / OpenAPI 3.1.0 Compatible  
**Document Version**: 1.0.0 (Implementation-Aligned)

---

## 1. API Architecture & Global Conventions

### 1.1 Base URL & Versioning
- **Base Path**: `/api/v1`
- **Root Convenience Paths**: `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`
- **Content Type**: `application/json; charset=utf-8` for standard REST payloads; `application/pdf` and `application/zip` for binary downloads.

### 1.2 Global HTTP Status Code Definitions
- `200 OK`: Request succeeded. Entity returned in response body.
- `202 Accepted`: Asynchronous bulk request accepted and queued for background processing.
- `400 Bad Request`: Client sent malformed request syntax or invalid operation.
- `403 Forbidden`: Access denied (e.g., directory path traversal attack detected).
- `404 Not Found`: Targeted resource (`job_id` or `certificate_id`) does not exist.
- `422 Unprocessable Content`: Schema validation failed (e.g. empty strings, out-of-bounds batch, duplicate recipients).
- `500 Internal Server Error`: Unhandled server exception.

### 1.3 Standard Error Response Format
All application errors follow a unified, predictable structure:

```json
{
  "detail": "Descriptive human-readable error explanation",
  "error_code": "MACHINE_READABLE_ERROR_CODE",
  "details": {}
}
```

For schema validation failures (`HTTP 422`):
```json
{
  "detail": "Input validation error",
  "error_code": "VALIDATION_ERROR",
  "errors": [
    {
      "type": "value_error",
      "loc": ["body", "recipients"],
      "msg": "Duplicate recipient detected at index 1: 'Jane Doe' (jane@example.com).",
      "input": "..."
    }
  ]
}
```

---

## 2. Comprehensive Endpoint Contracts

---

### Endpoint 1: Submit Bulk Certificate Generation Job
- **Purpose**: Ingests event metadata and an array of recipient details, executes schema and duplicate validations, persists job and recipient records transactionally, and queues the job for background execution.
- **HTTP Method & Path**: `POST /api/v1/jobs`
- **Authentication**: None required (Public / Extensible via `X-API-Key`).
- **Headers**:
  - `Content-Type: application/json`
  - *(Optional)* `X-Idempotency-Key: string` (Prevents duplicate processing on client retry).

#### Input Validation Rules:
1. `event_name` (string, required): Length 2–255 characters. Must not be empty or whitespace.
2. `issuer_name` (string, required): Length 2–255 characters. Must not be empty or whitespace.
3. `issue_date` (string, required): Length 4–50 characters (e.g. `"2026-10-10"` or `"October 10, 2026"`).
4. `certificate_title` (string, optional): Length 2–255 characters. Default: `"Certificate of Completion"`.
5. `recipients` (array, required):
   - Min items: `1`.
   - Max items: `MAX_BATCH_SIZE` (`1,000`).
   - Duplicate Rule: Each recipient must be unique within the batch. Duplicate `(recipient_name, recipient_email)` combinations are rejected.
6. `recipients[].recipient_name` (string, required): Length 2–255 characters.
7. `recipients[].recipient_email` (string, optional): Valid RFC 5322 email address format.
8. `recipients[].custom_remarks` (string, optional): Max 500 characters.

#### Request Payload Example:
```json
{
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
}
```

#### Successful Response (`HTTP 202 Accepted`):
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

#### Error Responses:
- **`HTTP 422 Unprocessable Content` (Batch Size Exceeded)**:
  ```json
  {
    "detail": "Batch recipient size of 1200 exceeds configured maximum limit of 1000.",
    "error_code": "BatchSizeExceededError",
    "details": {
      "actual_size": 1200,
      "max_size": 1000
    }
  }
  ```
- **`HTTP 422 Unprocessable Content` (Duplicate Recipient in Batch)**:
  ```json
  {
    "detail": "Input validation error",
    "error_code": "VALIDATION_ERROR",
    "errors": [
      {
        "type": "value_error",
        "loc": ["body", "recipients"],
        "msg": "Value error, Duplicate recipient detected at index 1: 'Jane Doe' (jane.doe@example.com). Each recipient within a batch must be unique."
      }
    ]
  }
  ```
- **`HTTP 422 Unprocessable Content` (Malformed Email)**:
  ```json
  {
    "detail": "Input validation error",
    "error_code": "VALIDATION_ERROR",
    "errors": [
      {
        "type": "value_error",
        "loc": ["body", "recipients", 0, "recipient_email"],
        "msg": "value is not a valid email address: The email address is not valid. It must have exactly one @-sign."
      }
    ]
  }
  ```

---

### Endpoint 2: Retrieve Job Status and Progress
- **Purpose**: Returns real-time aggregate execution state, total/success/failure counters, progress percentage, and ZIP archive download URL.
- **HTTP Method & Path**: `GET /api/v1/jobs/{job_id}`
- **Authentication**: None required.
- **Path Parameters**:
  - `job_id` (string, required): RFC 4122 UUID v4 of the parent job.

#### Successful Response (`HTTP 200 OK` — While Processing):
```json
{
  "job_id": "8f395804-b9b0-466d-a7ca-5c3b9b46e392",
  "status": "PROCESSING",
  "event_name": "Full Stack Backend Engineering Bootcamp",
  "issuer_name": "Global Tech Institute",
  "issue_date": "October 10, 2026",
  "certificate_title": "Certificate of Excellence",
  "total_recipients": 100,
  "successful_count": 45,
  "failed_count": 0,
  "progress_percentage": 45.0,
  "created_at": "2026-10-10T00:30:00.000000Z",
  "started_at": "2026-10-10T00:30:01.000000Z",
  "completed_at": null,
  "zip_download_url": "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392/download-zip"
}
```

#### Successful Response (`HTTP 200 OK` — Fully Completed):
```json
{
  "job_id": "8f395804-b9b0-466d-a7ca-5c3b9b46e392",
  "status": "COMPLETED",
  "event_name": "Full Stack Backend Engineering Bootcamp",
  "issuer_name": "Global Tech Institute",
  "issue_date": "October 10, 2026",
  "certificate_title": "Certificate of Excellence",
  "total_recipients": 100,
  "successful_count": 100,
  "failed_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-10T00:30:00.000000Z",
  "started_at": "2026-10-10T00:30:01.000000Z",
  "completed_at": "2026-10-10T00:30:05.200000Z",
  "zip_download_url": "http://localhost:8000/api/v1/jobs/8f395804-b9b0-466d-a7ca-5c3b9b46e392/download-zip"
}
```

#### Error Response:
- **`HTTP 404 Not Found`**:
  ```json
  {
    "detail": "Generation job 'non-existent-uuid' was not found.",
    "error_code": "JobNotFoundError",
    "details": {}
  }
  ```

---

### Endpoint 3: List Certificates for a Job
- **Purpose**: Lists recipient certificate records for a specific job with optional filtering by status and pagination support.
- **HTTP Method & Path**: `GET /api/v1/jobs/{job_id}/certificates`
- **Authentication**: None required.
- **Path Parameters**:
  - `job_id` (string, required): UUID v4 of the parent job.
- **Query Parameters**:
  - `status_filter` (string, optional): Filter by `SUCCESS`, `FAILED`, `PENDING`, `PROCESSING`.
  - `limit` (integer, optional, default: 100, max: 500): Number of records to return.
  - `offset` (integer, optional, default: 0): Number of records to skip.

#### Successful Response (`HTTP 200 OK`):
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
  },
  {
    "id": "7b81c2d3-9012-4f11-8123-bc9234da1902",
    "job_id": "8f395804-b9b0-466d-a7ca-5c3b9b46e392",
    "recipient_name": "Corrupted Data Participant",
    "recipient_email": "bad@example.com",
    "certificate_id": "CERT-1122-3344-5566",
    "status": "FAILED",
    "error_code": "INVALID_RECIPIENT_DATA",
    "error_message": "Recipient name must be at least 2 characters long.",
    "created_at": "2026-10-10T00:30:00.000000Z",
    "completed_at": "2026-10-10T00:30:01.600000Z",
    "download_url": null
  }
]
```

#### Error Response:
- **`HTTP 404 Not Found`**:
  ```json
  {
    "detail": "Generation job 'unknown-job' was not found.",
    "error_code": "JobNotFoundError",
    "details": {}
  }
  ```

---

### Endpoint 4: Download Individual Certificate PDF
- **Purpose**: Streams the high-resolution vector PDF certificate for a specific certificate ID. Enforces strict directory containment to defend against directory traversal attacks.
- **HTTP Method & Path**: `GET /api/v1/certificates/{certificate_id}/download`
- **Authentication**: None required.
- **Path Parameters**:
  - `certificate_id` (string, required): Stable unique certificate ID (e.g., `CERT-8D4F-912A-B7C1`).
- **Query Parameters**:
  - `as_attachment` (boolean, optional, default: false): If `true`, sets `Content-Disposition: attachment; filename="CERT-XXX.pdf"` to force browser save prompt; if `false`, defaults to `inline` preview.

#### Successful Response (`HTTP 200 OK`):
- **Headers**:
  - `Content-Type: application/pdf`
  - `Content-Disposition: inline; filename="CERT-8D4F-912A-B7C1.pdf"`
- **Binary Stream**: Vector PDF bytes beginning with `%PDF-1.4`.

#### Error Responses:
- **`HTTP 404 Not Found` (Certificate Does Not Exist or Incomplete)**:
  ```json
  {
    "detail": "Certificate 'CERT-UNKNOWN' was not found.",
    "error_code": "CertificateNotFoundError",
    "details": {}
  }
  ```
- **`HTTP 403 Forbidden` (Directory Traversal Attack Attempted)**:
  ```json
  {
    "detail": "Access denied: File is outside authorized storage path.",
    "error_code": "SecurityViolationError",
    "details": {}
  }
  ```

---

### Endpoint 5: Download All Job Certificates as a ZIP Archive
- **Purpose**: Compresses all successfully generated certificate PDFs in this job into a single `.zip` file on disk and streams it to the client.
- **HTTP Method & Path**: `GET /api/v1/jobs/{job_id}/download-zip`
- **Authentication**: None required.
- **Path Parameters**:
  - `job_id` (string, required): UUID v4 of the parent job.

#### Successful Response (`HTTP 200 OK`):
- **Headers**:
  - `Content-Type: application/zip`
  - `Content-Disposition: attachment; filename="certificates_job_8f395804-b9b0-466d-a7ca-5c3b9b46e392.zip"`
- **Binary Stream**: Compressed ZIP file containing files named `{Recipient_Name}_{Certificate_ID}.pdf`.

#### Error Response:
- **`HTTP 500 Internal Server Error` (No Successful Certificates Yet)**:
  ```json
  {
    "detail": "No successfully generated certificates found for job '8f395804-b9b0-466d-a7ca-5c3b9b46e392'.",
    "error_code": "StorageAccessError",
    "details": {}
  }
  ```

---

### Endpoint 6: System Health & Readiness Probe
- **Purpose**: Verifies that the FastAPI process is alive, the relational database is reachable (`SELECT 1`), and the persistent storage directory is accessible.
- **HTTP Method & Path**: `GET /api/v1/health` and `GET /health`
- **Authentication**: None required.

#### Successful Response (`HTTP 200 OK`):
```json
{
  "status": "ok",
  "db_connected": true,
  "storage_accessible": true,
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2026-10-10T02:45:00.000000Z"
}
```

---

## 3. Security, Rate Limiting & Concurrency Architecture

1. **Configurable Batch Boundaries**: Protected via `MAX_BATCH_SIZE=1000` in `.env` to prevent denial-of-service memory exhaustion.
2. **Path Traversal Defense**: All download endpoints verify canonical file containment:
   ```python
   file_path = Path(record.file_path).resolve()
   base_storage = settings.STORAGE_DIR.resolve()
   file_path.relative_to(base_storage)  # Raises ValueError -> HTTP 403 Forbidden
   ```
3. **Database Concurrency Protection**: SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL`) allows simultaneous readers without database lock contention.
4. **CORS Headers**: Fully configurable allowed origins (`settings.ALLOWED_ORIGINS`).

---

## 🏁 Phase 4 Sign-Off

The RESTful API contracts are fully documented, implemented in FastAPI, backed by Pydantic v2 schemas, and verified by 15 automated Pytest tests.
