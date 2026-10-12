"""
Observability Metrics Engine
High-performance, zero-overhead metrics collector providing standard Prometheus exposition
format and structured JSON telemetry without external third-party dependencies.
"""

import math
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

try:
    import psutil

    _HAS_PSUTIL = True
    _process = psutil.Process()
    _process.cpu_percent(interval=None)
    psutil.cpu_percent(interval=None)
except Exception:
    _HAS_PSUTIL = False
    _process = None

# Standard latency buckets (in seconds)
HTTP_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
CERT_RENDER_BUCKETS = (0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2, 0.5, 1.0)
JOB_DURATION_BUCKETS = (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)


class MetricsRegistry:
    """Thread-safe in-memory metrics registry for zero-cost observability."""

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()

        # HTTP Metrics
        self._http_requests_total: dict[tuple[str, str, str], int] = defaultdict(int)
        self._http_requests_in_flight: int = 0
        self._http_duration_buckets: dict[tuple[str, str, float], int] = defaultdict(int)
        self._http_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._http_duration_count: dict[tuple[str, str], int] = defaultdict(int)

        # Job Metrics
        self._jobs_submitted_total: dict[str, int] = defaultdict(int)
        self._jobs_completed_total: dict[str, int] = defaultdict(int)
        self._job_duration_buckets: dict[tuple[str, float], int] = defaultdict(int)
        self._job_duration_sum: dict[str, float] = defaultdict(float)
        self._job_duration_count: dict[str, int] = defaultdict(int)

        # Certificate Rendering Metrics
        self._certificates_generated_total: dict[tuple[str, str], int] = defaultdict(int)
        self._cert_render_buckets: dict[float, int] = defaultdict(int)
        self._cert_render_sum: float = 0.0
        self._cert_render_count: int = 0

        # Worker Reliability Metrics
        self._stale_jobs_recovered_total: int = 0

        # Storage Metrics Cache (TTL = 10s to prevent disk thrashing)
        self._storage_cached_at: float = 0.0
        self._storage_file_count: int = 0
        self._storage_bytes_used: int = 0

    # --------------------------------------------------------------------------
    # Recording Hooks
    # --------------------------------------------------------------------------

    def http_request_started(self) -> None:
        """Increments in-flight requests gauge."""
        with self._lock:
            self._http_requests_in_flight += 1

    def record_http_request(self, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        """Records an HTTP request outcome and latency distribution."""
        status_str = str(status_code)
        norm_method = method.upper()

        with self._lock:
            self._http_requests_in_flight = max(0, self._http_requests_in_flight - 1)
            self._http_requests_total[(norm_method, path, status_str)] += 1

            # Histogram observation
            key = (norm_method, path)
            self._http_duration_sum[key] += duration_seconds
            self._http_duration_count[key] += 1
            for b in HTTP_LATENCY_BUCKETS:
                if duration_seconds <= b:
                    self._http_duration_buckets[(norm_method, path, b)] += 1
            self._http_duration_buckets[(norm_method, path, math.inf)] += 1

    def record_job_submitted(self, submission_type: str = "json") -> None:
        """Records a newly queued generation job."""
        with self._lock:
            self._jobs_submitted_total[submission_type] += 1

    def record_job_completed(self, status: str, duration_seconds: float) -> None:
        """Records completed job status and duration."""
        with self._lock:
            self._jobs_completed_total[status] += 1
            self._job_duration_sum[status] += duration_seconds
            self._job_duration_count[status] += 1
            for b in JOB_DURATION_BUCKETS:
                if duration_seconds <= b:
                    self._job_duration_buckets[(status, b)] += 1
            self._job_duration_buckets[(status, math.inf)] += 1

    def record_certificate_render(
        self, duration_seconds: float, status: str = "SUCCESS", error_code: str | None = None
    ) -> None:
        """Records an individual certificate rendering cycle."""
        err_key = error_code or "none"
        with self._lock:
            self._certificates_generated_total[(status, err_key)] += 1
            if status == "SUCCESS":
                self._cert_render_sum += duration_seconds
                self._cert_render_count += 1
                for b in CERT_RENDER_BUCKETS:
                    if duration_seconds <= b:
                        self._cert_render_buckets[b] += 1
                self._cert_render_buckets[math.inf] += 1

    def record_stale_job_recovery(self, count: int = 1) -> None:
        """Records recovery of abandoned or crashed worker jobs."""
        with self._lock:
            self._stale_jobs_recovered_total += count

    # --------------------------------------------------------------------------
    # Telemetry Queries & Storage Computation
    # --------------------------------------------------------------------------

    def get_storage_stats(self) -> tuple[int, int]:
        """Calculates cached storage file count and total size in bytes."""
        now = time.time()
        if now - self._storage_cached_at < 10.0:
            return self._storage_file_count, self._storage_bytes_used

        storage_dir: Path = settings.STORAGE_DIR
        file_count = 0
        total_bytes = 0

        if storage_dir.exists():
            try:
                for file_entry in storage_dir.rglob("*.pdf"):
                    if file_entry.is_file():
                        file_count += 1
                        total_bytes += file_entry.stat().st_size
            except Exception:
                pass

        with self._lock:
            self._storage_file_count = file_count
            self._storage_bytes_used = total_bytes
            self._storage_cached_at = now

        return file_count, total_bytes

    def get_resource_stats(self) -> dict[str, float]:
        """Calculates process and system CPU and memory utilization."""
        if not _HAS_PSUTIL or _process is None:
            return {
                "process_cpu_percent": 0.0,
                "process_memory_mb": 0.0,
                "system_cpu_percent": 0.0,
                "system_memory_percent": 0.0,
            }
        try:
            mem_info = _process.memory_info()
            return {
                "process_cpu_percent": round(_process.cpu_percent(interval=None), 2),
                "process_memory_mb": round(mem_info.rss / (1024 * 1024), 2),
                "system_cpu_percent": round(psutil.cpu_percent(interval=None), 2),
                "system_memory_percent": round(psutil.virtual_memory().percent, 2),
            }
        except Exception:
            return {
                "process_cpu_percent": 0.0,
                "process_memory_mb": 0.0,
                "system_cpu_percent": 0.0,
                "system_memory_percent": 0.0,
            }

    def get_summary_stats(self) -> dict[str, Any]:
        """Returns structured JSON telemetry summary for dashboards and health monitors."""
        uptime_seconds = round(time.time() - self._start_time, 2)
        files_count, storage_bytes = self.get_storage_stats()
        resource_stats = self.get_resource_stats()

        with self._lock:
            total_requests = sum(self._http_requests_total.values())
            http_errors = sum(
                count for (m, p, s), count in self._http_requests_total.items() if s.startswith(("4", "5"))
            )
            total_jobs_submitted = sum(self._jobs_submitted_total.values())
            total_jobs_completed = sum(self._jobs_completed_total.values())
            total_certs_success = sum(
                count for (st, err), count in self._certificates_generated_total.items() if st == "SUCCESS"
            )
            total_certs_failed = sum(
                count for (st, err), count in self._certificates_generated_total.items() if st != "SUCCESS"
            )
            avg_cert_render_ms = (
                round((self._cert_render_sum / self._cert_render_count) * 1000.0, 2)
                if self._cert_render_count > 0
                else 0.0
            )

        # Human-readable storage formatting
        if storage_bytes < 1024:
            human_storage = f"{storage_bytes} B"
        elif storage_bytes < 1024 * 1024:
            human_storage = f"{storage_bytes / 1024:.2f} KB"
        else:
            human_storage = f"{storage_bytes / (1024 * 1024):.2f} MB"

        return {
            "application": {
                "name": settings.PROJECT_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.APP_ENV,
                "uptime_seconds": uptime_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "resources": resource_stats,
            "http": {
                "total_requests": total_requests,
                "in_flight": self._http_requests_in_flight,
                "error_requests": http_errors,
                "error_rate_percentage": (
                    round((http_errors / total_requests) * 100.0, 2) if total_requests > 0 else 0.0
                ),
            },
            "jobs": {
                "submitted_total": total_jobs_submitted,
                "completed_total": total_jobs_completed,
                "by_status": dict(self._jobs_completed_total),
                "stale_recoveries_total": self._stale_jobs_recovered_total,
            },
            "certificates": {
                "generated_success": total_certs_success,
                "generated_failed": total_certs_failed,
                "avg_render_latency_ms": avg_cert_render_ms,
            },
            "storage": {
                "provider": settings.STORAGE_PROVIDER,
                "cloud_configured": (
                    settings.STORAGE_PROVIDER.lower() in ("s3", "r2", "supabase") and bool(settings.S3_ACCESS_KEY_ID)
                ),
                "stored_pdf_count": files_count,
                "bytes_used": storage_bytes,
                "human_readable_size": human_storage,
                "storage_directory": str(settings.STORAGE_DIR),
            },
        }

    # --------------------------------------------------------------------------
    # Prometheus Exposition Format Exporter
    # --------------------------------------------------------------------------

    def export_prometheus_text(self) -> str:
        """
        Serializes all internal metrics into the official Prometheus text-based
        exposition format (0.0.4) for scraping by Prometheus, Grafana, or Datadog agents.
        """
        lines: list[str] = []
        files_count, storage_bytes = self.get_storage_stats()
        uptime_seconds = round(time.time() - self._start_time, 2)
        res = self.get_resource_stats()

        with self._lock:
            # 1. Process Metadata & Uptime
            lines.append("# HELP process_uptime_seconds Process uptime in seconds")
            lines.append("# TYPE process_uptime_seconds gauge")
            lines.append(f"process_uptime_seconds {uptime_seconds}")

            # Resource Utilization (CPU & Memory)
            lines.append("# HELP process_cpu_percent Current process CPU utilization percentage")
            lines.append("# TYPE process_cpu_percent gauge")
            lines.append(f"process_cpu_percent {res['process_cpu_percent']}")

            lines.append("# HELP process_memory_bytes Resident memory bytes used by process")
            lines.append("# TYPE process_memory_bytes gauge")
            lines.append(f"process_memory_bytes {int(res['process_memory_mb'] * 1024 * 1024)}")

            lines.append("# HELP system_cpu_percent Total system CPU utilization percentage")
            lines.append("# TYPE system_cpu_percent gauge")
            lines.append(f"system_cpu_percent {res['system_cpu_percent']}")

            lines.append("# HELP system_memory_percent Total system memory utilization percentage")
            lines.append("# TYPE system_memory_percent gauge")
            lines.append(f"system_memory_percent {res['system_memory_percent']}")

            # 2. HTTP In-Flight Requests
            lines.append("# HELP http_requests_in_flight Current in-flight HTTP requests")
            lines.append("# TYPE http_requests_in_flight gauge")
            lines.append(f"http_requests_in_flight {self._http_requests_in_flight}")

            # 3. HTTP Requests Total Counter
            lines.append("# HELP http_requests_total Total number of HTTP requests processed")
            lines.append("# TYPE http_requests_total counter")
            for (method, path, status), count in sorted(self._http_requests_total.items()):
                lines.append(f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

            # 4. HTTP Request Duration Histogram
            if self._http_duration_count:
                lines.append("# HELP http_request_duration_seconds HTTP request latency histogram in seconds")
                lines.append("# TYPE http_request_duration_seconds histogram")
                paths = sorted(self._http_duration_count.keys())
                for method, path in paths:
                    for b in HTTP_LATENCY_BUCKETS:
                        b_count = self._http_duration_buckets.get((method, path, b), 0)
                        lines.append(
                            f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{b}"}} {b_count}'
                        )
                    inf_count = self._http_duration_buckets.get((method, path, math.inf), 0)
                    lines.append(
                        f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="+Inf"}} {inf_count}'
                    )
                    sum_val = self._http_duration_sum.get((method, path), 0.0)
                    cnt_val = self._http_duration_count.get((method, path), 0)
                    lines.append(f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {sum_val:.6f}')
                    lines.append(f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {cnt_val}')

            # 5. Jobs Submitted Total Counter
            lines.append("# HELP jobs_submitted_total Total generation jobs submitted")
            lines.append("# TYPE jobs_submitted_total counter")
            for sub_type, count in sorted(self._jobs_submitted_total.items()):
                lines.append(f'jobs_submitted_total{{type="{sub_type}"}} {count}')

            # 6. Jobs Completed Total Counter
            lines.append("# HELP jobs_completed_total Total generation jobs completed by status")
            lines.append("# TYPE jobs_completed_total counter")
            for job_status, count in sorted(self._jobs_completed_total.items()):
                lines.append(f'jobs_completed_total{{status="{job_status}"}} {count}')

            # 7. Certificates Generated Total Counter
            lines.append("# HELP certificates_generated_total Total certificates processed")
            lines.append("# TYPE certificates_generated_total counter")
            for (cert_status, err_code), count in sorted(self._certificates_generated_total.items()):
                lines.append(f'certificates_generated_total{{status="{cert_status}",error_code="{err_code}"}} {count}')

            # 8. Certificate Rendering Latency Histogram
            if self._cert_render_count > 0:
                lines.append(
                    "# HELP certificate_render_duration_seconds Per-certificate rendering latency histogram in seconds"
                )
                lines.append("# TYPE certificate_render_duration_seconds histogram")
                for b in CERT_RENDER_BUCKETS:
                    b_count = self._cert_render_buckets.get(b, 0)
                    lines.append(f'certificate_render_duration_seconds_bucket{{le="{b}"}} {b_count}')
                inf_count = self._cert_render_buckets.get(math.inf, 0)
                lines.append(f'certificate_render_duration_seconds_bucket{{le="+Inf"}} {inf_count}')
                lines.append(f"certificate_render_duration_seconds_sum {self._cert_render_sum:.6f}")
                lines.append(f"certificate_render_duration_seconds_count {self._cert_render_count}")

            # 9. Stale Job Recovery Counter
            lines.append("# HELP stale_jobs_recovered_total Total stale jobs recovered after worker crash")
            lines.append("# TYPE stale_jobs_recovered_total counter")
            lines.append(f"stale_jobs_recovered_total {self._stale_jobs_recovered_total}")

            # 10. Storage Metrics
            lines.append("# HELP storage_certificates_total Total PDF certificate files residing in storage")
            lines.append("# TYPE storage_certificates_total gauge")
            lines.append(f"storage_certificates_total {files_count}")

            lines.append("# HELP storage_used_bytes Total bytes utilized by certificate storage")
            lines.append("# TYPE storage_used_bytes gauge")
            lines.append(f"storage_used_bytes {storage_bytes}")

        return "\n".join(lines) + "\n"


# Global singleton metrics registry
metrics = MetricsRegistry()
