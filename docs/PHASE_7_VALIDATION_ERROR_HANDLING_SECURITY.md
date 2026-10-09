# Phase 7 — Validation, Error Handling, and Security Specification

## 1. Executive Summary & Security Philosophy

The **Bulk Certificate Generator API** implements defense-in-depth security principles across the entire application stack. It provides robust protection against common web vulnerabilities (OWASP Top 10), data corruption, resource exhaustion, and path traversal attacks while preserving zero financial operating costs ($0.00 / ₹0.00).

To maintain architectural clarity, protections are cleanly divided into:
1. **In-Application Protections**: Enforced directly within Python code, middleware, and database transaction boundaries.
2. **Deployment Responsibilities**: Infrastructure-level protections delegated to production reverse proxies, edge gateways, or container runtimes.

---

## 2. In-Application Security Protections

```
[ Client Request ]
       │
       ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Request Body Size Limit Middleware (Max 10 MB: HTTP 413)            │
├────────────────────────────────────────────────────────────────────────┤
│ 2. OWASP Defensive Security Headers (nosniff, DENY, XSS, Referrer)     │
├────────────────────────────────────────────────────────────────────────┤
│ 3. API Key Authentication Check (X-API-Key header verification: 401)   │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Pydantic v2 Schema Validation (Types, Stripping, Duplicates: 422)   │
├────────────────────────────────────────────────────────────────────────┤
│ 5. ACID DB Transaction (Batch Limits, Foreign Keys, SQLite WAL)        │
├────────────────────────────────────────────────────────────────────────┤
│ 6. Storage Security (Path Traversal Guard, Whitelisted Alphanumeric)   │
├────────────────────────────────────────────────────────────────────────┤
│ 7. Global Exception Shield (Sanitized Error JSON: Zero Traceback Leak) │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Request Schema Validation
- **Pydantic v2 Models**: Enforces strict typing, minimum/maximum lengths (`min_length=2`, `max_length=255`), and automatic leading/trailing whitespace stripping via `@field_validator("strip_strings")`.
- **Email Validation**: Integrated with `email-validator` (`EmailStr | None`) conforming to RFC 5322.
- **In-Batch Duplicate Detection**: Validates that no two recipients share identical `(name, email)` tuples within the same submission batch, immediately rejecting duplicates with HTTP 422 before touching the database.
- **Batch Size Throttling**: Rejects bulk submissions exceeding `MAX_BATCH_SIZE = 1000` via `BatchSizeExceededError` (HTTP 422).

### 2.2 Database Transaction Handling
- **ACID Ingestion**: The `GenerationJob` and all `CertificateRecord` rows are inserted within a single atomic SQLAlchemy transaction (`db.commit()`). If any database write error occurs, the session rolls back entirely, preventing orphan parent jobs.
- **Atomic Concurrency (Compare-and-Swap)**: Workers claim pending jobs using conditional SQL updates:
  ```sql
  UPDATE generation_jobs 
  SET status = 'PROCESSING', started_at = :now, updated_at = :now 
  WHERE id = :candidate_id AND status = 'PENDING';
  ```
  Only the worker that modifies `rowcount == 1` proceeds. Concurrent workers receive `rowcount == 0` and back off, completely eliminating race conditions and double-generation.
- **SQLite Concurrency Hardening**:
  - `PRAGMA journal_mode = WAL;` allows concurrent readers during active writes.
  - `PRAGMA busy_timeout = 5000;` prevents database locked errors under load.
  - `PRAGMA foreign_keys = ON;` enforces relational integrity cascades.

### 2.3 Safe File Paths, Filenames & Path Traversal Prevention
- **Whitelisted Filename Components**: Certificate IDs are sanitized to alphanumeric and hyphen characters `[a-zA-Z0-9_-]` using `"".join(c for c in certificate_id if c.isalnum() or c in ("-", "_"))`.
- **Filesystem Containment Verification**: In [`app/services/job_service.py`](file:///c:/Users/dell/Downloads/Bulk%20Certificate%20Generator/app/services/job_service.py#L124-L132), every requested file path is resolved to its canonical absolute path and verified to reside strictly inside the authorized storage boundary:
  ```python
  file_path = Path(record.file_path).resolve()
  base_storage = settings.STORAGE_DIR.resolve()
  try:
      file_path.relative_to(base_storage)
  except ValueError:
      raise SecurityViolationError("Access denied: File is outside authorized storage path.")
  ```
- **ZIP Packaging Safety**: Filenames inside ZIP archives are sanitized to alphanumeric characters to prevent "Zip Slip" vulnerabilities when extracted on client systems.

### 2.4 File Access Restrictions
- Certificates can **only** be downloaded if their status is explicitly `SUCCESS`. Attempting to download a certificate in `PENDING`, `PROCESSING`, or `FAILED` status returns HTTP 404, preventing unauthorized access to ungenerated or partial file paths.
- Physical file presence is confirmed via `file_path.is_file()` prior to opening.

### 2.5 Request Body Size Limits & DoS Mitigation
- To prevent memory exhaustion attacks from massive HTTP JSON payloads, a custom ASGI middleware inspects incoming `Content-Length` headers:
  ```python
  content_length = request.headers.get("content-length")
  if content_length and int(content_length) > settings.MAX_PAYLOAD_SIZE_BYTES:
      return JSONResponse(
          status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
          content={"detail": "Request payload exceeds allowable limit of 10MB.", "error_code": "PAYLOAD_TOO_LARGE"}
      )
  ```

### 2.6 Defensive OWASP Security Headers
Every HTTP response automatically includes defensive security headers:
- `X-Content-Type-Options: nosniff` — Prevents MIME-sniffing attacks.
- `X-Frame-Options: DENY` — Defends against clickjacking.
- `X-XSS-Protection: 1; mode=block` — Enforces legacy browser XSS filtering.
- `Referrer-Policy: strict-origin-when-cross-origin` — Protects referrer leakage.

### 2.7 API Key Authentication
- Configurable via `API_KEY_ENABLED: bool` and `API_KEY: str` in `app/core/config.py`.
- When enabled in production, the dependency [`verify_api_key`](file:///c:/Users/dell/Downloads/Bulk%20Certificate%20Generator/app/api/deps.py#L14-L26) checks the `X-API-Key` request header. Missing or invalid keys are rejected immediately with HTTP 401 Unauthorized before touching business logic.
- When disabled (default for local development and unit tests), endpoints operate friction-free.

### 2.8 Information Leakage Prevention & Safe Logging
- **Global Error Shield**: All unhandled exceptions are caught by `@app.exception_handler(Exception)` in `app/main.py`:
  - Returns sanitized JSON: `{"detail": "An internal server error occurred...", "error_code": "INTERNAL_SERVER_ERROR"}`.
  - Never leaks Python tracebacks, database table names, SQL syntax, or internal file paths to API clients.
- **Safe Server Logging**: Detailed exceptions and stack traces are logged internally using Python's `logging` module to server logs for debugging by authorized engineers.

### 2.9 Secret Management & Environment Configuration
- Uses `pydantic-settings` to load configurations from `.env` or system environment variables.
- Default secrets are never committed:
  - `.gitignore` explicitly excludes `.env`, `data.db`, and `./storage/`.
  - `.env.example` provides a documented template with dummy placeholder values.

---

## 3. In-App Protections vs. Deployment Responsibilities Matrix

In production systems, security is a shared responsibility between application logic and deployment infrastructure:

| Security Domain | Application Implementation (Included) | Production Deployment Responsibility |
| :--- | :--- | :--- |
| **Authentication & Auth** | `X-API-Key` header dependency; rejects unauthorized requests (HTTP 401) | OAuth2/OIDC Gateway, JWT Provider, or Cloud IAM (e.g. AWS Cognito, Google Cloud Identity) |
| **Transport Security (TLS)** | Enforces strict CORS headers; prevents insecure deserialization | Reverse proxy (NGINX/Caddy/Traefik/Cloudflare) terminates HTTPS on port 443 |
| **Rate Limiting & DDoS** | `MAX_PAYLOAD_SIZE_BYTES` (10 MB limit); batch recipient limit (1,000) | Edge rate limiting (Cloudflare WAF, NGINX `limit_req_zone`, AWS WAF) |
| **Data Storage at Rest** | Isolated `./storage` directory; strictly validated paths | Full disk encryption (LUKS / AWS EBS Encryption / GCP Persistent Disk KMS) |
| **Container Security** | Non-root `appuser` (UID 1001); multi-stage slim container | Read-only container root filesystem (`--read-only`), resource limits (`limits.memory: 1G`) |
| **Secrets Management** | `BaseSettings` reading environment variables; zero hardcoded tokens | Kubernetes Secrets, AWS Secrets Manager, or HashiCorp Vault injection |
| **Log Storage & Audit** | Structured JSON logging; sanitizes client errors | Centralized log ingestion (Grafana Loki, Datadog, AWS CloudWatch) |

---

## 4. Automated Security Verification (28/28 Tests Passing)

All security features are continuously tested in [`tests/test_security.py`](file:///c:/Users/dell/Downloads/Bulk%20Certificate%20Generator/tests/test_security.py):

| Test Case | Vulnerability Tested | Assertion / Expected Outcome | Status |
| :--- | :--- | :--- | :--- |
| `test_security_headers_present` | Missing security headers / Clickjacking | Confirms `nosniff`, `DENY`, and `XSS` headers on responses | **PASSED** |
| `test_payload_limit_enforced` | Memory exhaustion via oversized JSON | Request with `Content-Length > 10MB` returns HTTP 413 | **PASSED** |
| `test_api_key_authentication_enforcement` | Unauthorized job creation | Missing or wrong key rejected with HTTP 401; valid key allowed | **PASSED** |
| `test_path_traversal_prevention_on_download` | Directory traversal (`../../etc/passwd`) | Malicious route parameters rejected with 404/403/422 | **PASSED** |
| `test_unauthorized_download_of_incomplete_certificate` | Incomplete certificate leakage | Attempting download of `PENDING` certificate returns HTTP 404 | **PASSED** |
| `test_error_response_does_not_leak_internals` | Traceback / SQL schema leakage | Internal errors return sanitized JSON without `Traceback` or SQL | **PASSED** |
