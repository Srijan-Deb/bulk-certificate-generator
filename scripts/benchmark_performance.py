"""
Performance, Reliability, and Storage Benchmark Suite
Measures actual wall-clock processing time, memory allocation, storage growth,
and failure containment across realistic sample batches (N=10, N=50, N=100, N=250).
Usage:
    python scripts/benchmark_performance.py
"""

import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.certificate import CertificateRecord
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.services.certificate_service import certificate_generator
from app.services.worker import worker

SAMPLE_NAMES = [
    "Ada Lovelace",
    "Alan Turing",
    "Grace Hopper",
    "Margaret Hamilton",
    "Edsger W. Dijkstra",
    "Donald Knuth",
    "Barbara Liskov",
    "Ken Thompson",
    "Dennis Ritchie",
    "Linus Torvalds",
    "Dr. Alexander Montgomery Bartholomew-Fitzgerald III",
    "Katherine Johnson",
    "John von Neumann",
    "Claude Shannon",
    "Tim Berners-Lee",
    "Guido van Rossum",
    "Bjarne Stroustrup",
    "James Gosling",
    "Vint Cerf",
    "Radia Perlman",
]


def run_benchmark_batch(batch_size: int, inject_failure: bool = False) -> dict:
    db = SessionLocal()
    tracemalloc.start()
    tracemalloc.reset_peak()

    now = datetime.now(timezone.utc)
    job = GenerationJob(
        status=JobStatus.PENDING.value,
        event_name="Benchmark Performance Evaluation",
        issuer_name="Software Quality & Reliability Institute",
        issue_date="2026-10-10",
        certificate_title="Certificate of Excellence",
        total_recipients=batch_size,
        successful_count=0,
        failed_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.flush()

    # Create recipient records
    for i in range(batch_size):
        name = SAMPLE_NAMES[i % len(SAMPLE_NAMES)]
        # If inject_failure is True, make the last recipient invalid
        if inject_failure and i == batch_size - 1:
            name = " "  # Blank name triggers worker validation failure

        cert_record = CertificateRecord(
            job_id=job.id,
            recipient_name=name,
            recipient_email=f"recipient_{i:04d}@example.com",
            custom_remarks="Benchmark Evaluation Run" if i % 2 == 0 else None,
            certificate_id=certificate_generator.generate_certificate_id(),
            status=CertificateStatus.PENDING.value,
            created_at=now,
        )
        db.add(cert_record)

    # 1. Measure Ingestion / DB Commit Time
    t0_commit = time.perf_counter()
    db.commit()
    t_ingest = time.perf_counter() - t0_commit

    # 2. Measure Worker Processing Time
    t0_process = time.perf_counter()
    claimed_job = worker.claim_next_job(db)
    if not claimed_job:
        raise RuntimeError("Worker failed to claim benchmark job")

    worker.process_job(db, claimed_job)
    t_process = time.perf_counter() - t0_process

    # 3. Measure Memory Usage
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 4. Measure Storage Growth
    job_dir = certificate_generator.output_dir / job.id
    total_bytes = 0
    file_count = 0
    if job_dir.exists():
        for f in job_dir.glob("*.pdf"):
            total_bytes += f.stat().st_size
            file_count += 1

    db.refresh(job)
    metrics = {
        "batch_size": batch_size,
        "job_id": job.id,
        "status": job.status,
        "successful_count": job.successful_count,
        "failed_count": job.failed_count,
        "ingest_time_sec": round(t_ingest, 4),
        "process_time_sec": round(t_process, 4),
        "total_time_sec": round(t_ingest + t_process, 4),
        "avg_ms_per_cert": round((t_process / batch_size) * 1000.0, 2),
        "peak_ram_mb": round(peak_mem / (1024 * 1024), 2),
        "total_storage_bytes": total_bytes,
        "total_storage_kb": round(total_bytes / 1024, 2),
        "avg_kb_per_cert": round((total_bytes / 1024) / max(1, file_count), 2),
        "file_count": file_count,
    }
    db.close()
    return metrics


def main():
    print("=" * 80)
    print("  Bulk Certificate Generator — Real-World Performance & Reliability Benchmark")
    print("=" * 80)
    print("Evaluating real wall-clock execution, peak RAM, disk storage, and DB behavior...\n")

    test_batches = [
        (10, False),    # Small batch
        (50, False),    # Medium batch
        (100, False),   # Large batch
        (250, True),    # High stress batch with 1 injected failure
    ]

    results = []
    for size, inject_fail in test_batches:
        print(f">> Running Benchmark Batch: N = {size:<3} (Inject Failure: {inject_fail})...", end="", flush=True)
        res = run_benchmark_batch(size, inject_failure=inject_fail)
        results.append(res)
        print(f" DONE in {res['total_time_sec']}s (Avg: {res['avg_ms_per_cert']}ms/cert, Peak RAM: {res['peak_ram_mb']}MB)")

    print("\n" + "=" * 80)
    print("                         BENCHMARK RESULTS TABLE")
    print("=" * 80)
    print(f"{'Batch Size':<10} | {'Status':<15} | {'Success':<8} | {'Failed':<8} | {'Process Time':<13} | {'Avg ms/Cert':<12} | {'Peak RAM':<10} | {'Storage (KB)':<12}")
    print("-" * 80)
    for r in results:
        print(
            f"{r['batch_size']:<10} | {r['status']:<15} | {r['successful_count']:<8} | {r['failed_count']:<8} | "
            f"{r['process_time_sec']:>10.3f}s | {r['avg_ms_per_cert']:>9.2f} ms | {r['peak_ram_mb']:>7.2f} MB | {r['total_storage_kb']:>9.1f} KB"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()
