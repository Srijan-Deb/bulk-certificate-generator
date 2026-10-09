# Phase 10 — Automated Testing & Quality Assurance Specification

## 1. Testing Strategy & Isolation Philosophy

The test suite is built on **Pytest**, **pytest-asyncio**, **pytest-cov**, and FastAPI's **TestClient** (backed by HTTPX). It guarantees complete test isolation, zero contamination of development data, zero flaky dependencies, and zero reliance on paid external cloud services ($0.00 / ₹0.00).

### Core Test Design Patterns
1. **Isolated Ephemeral Database**: Tests run against a dedicated SQLite database (`sqlite:///./test_data.db`). Each test function executes within an isolated fixture lifecycle that tears down and rebuilds the schema (`Base.metadata.drop_all()` and `create_all()`).
2. **Temporary Sandboxed Storage**: Fixtures utilize `tmp_path_factory.mktemp("cert_storage")`, preventing test artifacts from polluting production or local `./storage/certificates/` directories.
3. **Deterministic Worker Control**: `settings.RUN_WORKER_IN_APP` is automatically disabled during test runs. Asynchronous worker polling is replaced with deterministic, explicit worker tick invocations (`worker.claim_next_job()` and `worker.process_job()`), preventing race conditions in test assertions.

---

## 2. Test Execution Commands & Run Options

### A. Run Full Test Suite
```bash
# Windows (PowerShell):
.\.venv\Scripts\python.exe -m pytest -v

# Linux / macOS:
pytest -v
```

### B. Run a Single Test File
```bash
# Run only validation tests:
pytest tests/test_validation.py -v

# Run only worker crash recovery tests:
pytest tests/test_worker_recovery.py -v

# Run only PDF rendering tests:
pytest tests/test_pdf_generation.py -v
```

### C. Run with Code Coverage Reporting
```bash
pytest -v --cov=app --cov-report=term-missing
```

### D. Generate HTML Coverage Report
```bash
pytest --cov=app --cov-report=html
# View in browser: start htmlcov/index.html (Windows) or open htmlcov/index.html (macOS)
```

---

## 3. Actual Automated Test Results

The test suite executed with **31 passed tests and 90% total application statement coverage**:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.1.1, pluggy-1.6.0
plugins: anyio-4.15.1, asyncio-1.4.0, cov-7.1.0
collecting ... collected 31 items

tests/test_database_persistence.py::test_database_persistence_across_disjoint_sessions PASSED [  3%]
tests/test_database_persistence.py::test_transaction_rollback_prevents_partial_orphans PASSED [  6%]
tests/test_database_persistence.py::test_foreign_key_cascade_deletion PASSED [  9%]
tests/test_failure_isolation.py::test_individual_recipient_failure_does_not_halt_job PASSED [ 12%]
tests/test_health.py::test_root_endpoint PASSED                          [ 16%]
tests/test_health.py::test_health_check_endpoint PASSED                  [ 19%]
tests/test_health.py::test_root_health_alias_endpoint PASSED             [ 22%]
tests/test_job_lifecycle.py::test_job_submission_and_processing_lifecycle PASSED [ 25%]
tests/test_pdf_generation.py::test_pdf_generation_output PASSED          [ 29%]
tests/test_pdf_generation.py::test_certificate_id_format PASSED          [ 32%]
tests/test_pdf_generation.py::test_verification_code_generation PASSED   [ 35%]
tests/test_pdf_generation.py::test_long_recipient_name_and_event_handling PASSED [ 38%]
tests/test_pdf_generation.py::test_unicode_text_sanitization PASSED      [ 41%]
tests/test_pdf_generation.py::test_overwrite_prevention PASSED           [ 45%]
tests/test_pdf_generation.py::test_pdf_can_be_opened_and_parsed_with_pypdf PASSED [ 48%]
tests/test_retrieval.py::test_download_single_certificate_pdf PASSED     [ 51%]
tests/test_retrieval.py::test_download_nonexistent_certificate_returns_404 PASSED [ 54%]
tests/test_retrieval.py::test_download_job_certificates_zip PASSED       [ 58%]
tests/test_security.py::test_security_headers_present PASSED             [ 61%]
tests/test_security.py::test_payload_limit_enforced PASSED               [ 64%]
tests/test_security.py::test_api_key_authentication_enforcement PASSED   [ 67%]
tests/test_security.py::test_path_traversal_prevention_on_download PASSED [ 70%]
tests/test_security.py::test_unauthorized_download_of_incomplete_certificate PASSED [ 74%]
tests/test_security.py::test_error_response_does_not_leak_internals PASSED [ 77%]
tests/test_validation.py::test_create_job_missing_required_fields PASSED [ 80%]
tests/test_validation.py::test_create_job_empty_recipients_list PASSED   [ 83%]
tests/test_validation.py::test_create_job_blank_strings PASSED           [ 87%]
tests/test_validation.py::test_create_job_invalid_recipient_email PASSED [ 90%]
tests/test_validation.py::test_create_job_duplicate_recipients PASSED    [ 93%]
tests/test_worker_recovery.py::test_recover_stale_jobs_after_worker_crash PASSED [ 96%]
tests/test_worker_recovery.py::test_atomic_claim_concurrency_prevents_duplicate_processing PASSED [100%]

=============================== tests coverage ================================
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
app\api\deps.py                          11      0   100%
app\api\v1\certificates.py               12      0   100%
app\api\v1\health.py                     18      2    89%   30-31
app\api\v1\jobs.py                       39      0   100%
app\api\v1\router.py                      8      0   100%
app\core\config.py                       30      0   100%
app\core\errors.py                       25      3    88%   31, 40, 45
app\core\logging.py                      13      0   100%
app\db\base.py                            3      0   100%
app\db\session.py                        23      4    83%   41-45
app\main.py                              79     21    73%   35-48, 62-64, 71-73, 148-149
app\models\__init__.py                    4      0   100%
app\models\certificate.py                24      1    96%   52
app\models\enums.py                      12      0   100%
app\models\job.py                        25      1    96%   56
app\schemas\__init__.py                   4      0   100%
app\schemas\common.py                    14      0   100%
app\schemas\job.py                       54      0   100%
app\schemas\recipient.py                 26      1    96%   34
app\services\certificate_service.py     168      8    95%   47, 74, 295, 301-305
app\services\job_service.py              83      8    90%   38, 110-112, 143-144, 147, 164
app\services\worker.py                  110     29    74%   97-98, 157-163, 179, 193-204, 208-220
-------------------------------------------------------------------
TOTAL                                   785     78    90%
======================= 31 passed, 7 warnings in 5.07s ========================
```

---

## 4. Requirements Traceability Matrix

| Requirement from Specification | Test File | Test Method | Outcome |
| :--- | :--- | :--- | :--- |
| **Creating a generation job** | `test_job_lifecycle.py` | `test_job_submission_and_processing_lifecycle` | **PASS** |
| **Invalid and missing input data** | `test_validation.py` | `test_create_job_missing_required_fields`, `test_create_job_blank_strings` | **PASS** |
| **Invalid recipient records** | `test_validation.py` | `test_create_job_empty_recipients_list`, `test_create_job_invalid_recipient_email` | **PASS** |
| **In-batch duplicate recipients** | `test_validation.py` | `test_create_job_duplicate_recipients` | **PASS** |
| **Certificate PDF generation** | `test_pdf_generation.py` | `test_pdf_generation_output`, `test_certificate_id_format` | **PASS** |
| **Dynamic font scaling** | `test_pdf_generation.py` | `test_long_recipient_name_and_event_handling` | **PASS** |
| **Verification code integrity** | `test_pdf_generation.py` | `test_verification_code_generation` | **PASS** |
| **PDF opening & parsing verification** | `test_pdf_generation.py` | `test_pdf_can_be_opened_and_parsed_with_pypdf` | **PASS** |
| **Job status & progress tracking** | `test_job_lifecycle.py` | `test_job_submission_and_processing_lifecycle` | **PASS** |
| **Individual certificate failure handling** | `test_failure_isolation.py` | `test_individual_recipient_failure_does_not_halt_job` | **PASS** |
| **Retrieval of generated certificates** | `test_retrieval.py` | `test_download_single_certificate_pdf`, `test_download_job_certificates_zip` | **PASS** |
| **Non-existent IDs handling** | `test_retrieval.py`, `test_security.py` | `test_download_nonexistent_certificate_returns_404`, `test_error_response_does_not_leak_internals` | **PASS** |
| **Duplicate processing prevention** | `test_worker_recovery.py` | `test_atomic_claim_concurrency_prevents_duplicate_processing` | **PASS** |
| **File access and authorization** | `test_security.py` | `test_unauthorized_download_of_incomplete_certificate` | **PASS** |
| **Path traversal prevention** | `test_security.py` | `test_path_traversal_prevention_on_download` | **PASS** |
| **Database persistence across sessions** | `test_database_persistence.py` | `test_database_persistence_across_disjoint_sessions` | **PASS** |
| **ACID rollback on mid-operation error** | `test_database_persistence.py` | `test_transaction_rollback_prevents_partial_orphans` | **PASS** |
| **Foreign key cascade integrity** | `test_database_persistence.py` | `test_foreign_key_cascade_deletion` | **PASS** |
| **Worker crash recovery behavior** | `test_worker_recovery.py` | `test_recover_stale_jobs_after_worker_crash` | **PASS** |
| **OWASP security headers** | `test_security.py` | `test_security_headers_present` | **PASS** |
| **Payload size limit (10MB)** | `test_security.py` | `test_payload_limit_enforced` | **PASS** |
| **API key authentication** | `test_security.py` | `test_api_key_authentication_enforcement` | **PASS** |
