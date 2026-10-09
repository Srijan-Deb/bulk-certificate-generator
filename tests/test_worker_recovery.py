"""
Tests for Worker Crash Recovery and Concurrency Control (Phase 6)
Verifies:
- Detection and recovery of stale jobs stuck in PROCESSING after worker crash
- Resetting interrupted in-flight records to PENDING without corrupting completed ones
- Atomic single-row claiming preventing duplicate processing across workers
"""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.models.certificate import CertificateRecord
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.services.worker import worker


def test_recover_stale_jobs_after_worker_crash(client, db_session):
    # 1. Manually insert a job simulating an abrupt worker crash 10 minutes ago
    past_time = datetime.now(timezone.utc) - timedelta(seconds=settings.WORKER_JOB_TIMEOUT_SECONDS + 60)

    job = GenerationJob(
        status=JobStatus.PROCESSING.value,
        event_name="Crash Recovery Workshop",
        issuer_name="Fault Tolerance Lab",
        issue_date="2026-10-10",
        total_recipients=3,
        successful_count=1,
        failed_count=0,
        created_at=past_time,
        started_at=past_time,
        updated_at=past_time,
    )
    db_session.add(job)
    db_session.flush()

    # Recipient 1: Already succeeded before crash
    rec1 = CertificateRecord(
        job_id=job.id,
        recipient_name="Already Succeeded",
        certificate_id="CERT-PAST-0001-SUCC",
        status=CertificateStatus.SUCCESS.value,
        created_at=past_time,
        completed_at=past_time,
    )
    # Recipient 2: Was in-flight (PROCESSING) when worker process died
    rec2 = CertificateRecord(
        job_id=job.id,
        recipient_name="Interrupted Recipient",
        certificate_id="CERT-PAST-0002-INFL",
        status=CertificateStatus.PROCESSING.value,
        created_at=past_time,
    )
    # Recipient 3: Was still queued (PENDING)
    rec3 = CertificateRecord(
        job_id=job.id,
        recipient_name="Queued Recipient",
        certificate_id="CERT-PAST-0003-PEND",
        status=CertificateStatus.PENDING.value,
        created_at=past_time,
    )
    db_session.add_all([rec1, rec2, rec3])
    db_session.commit()

    # 2. Trigger stale job recovery
    recovered_count = worker.recover_stale_jobs(db_session)
    assert recovered_count == 1

    # 3. Verify state transitions after recovery
    db_session.refresh(job)
    db_session.refresh(rec1)
    db_session.refresh(rec2)
    db_session.refresh(rec3)

    assert job.status == JobStatus.PENDING.value
    # Recipient 1 must remain SUCCESS (no duplicate regeneration)
    assert rec1.status == CertificateStatus.SUCCESS.value
    # Recipient 2 must be reset to PENDING so it can be safely re-attempted
    assert rec2.status == CertificateStatus.PENDING.value
    # Recipient 3 must remain PENDING
    assert rec3.status == CertificateStatus.PENDING.value

    # 4. Worker resumes and finishes the job cleanly
    claimed_job = worker.claim_next_job(db_session)
    assert claimed_job is not None
    assert claimed_job.id == job.id

    worker.process_job(db_session, claimed_job)

    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED.value
    assert job.successful_count == 3
    assert job.failed_count == 0


def test_atomic_claim_concurrency_prevents_duplicate_processing(db_session):
    now = datetime.now(timezone.utc)
    job = GenerationJob(
        status=JobStatus.PENDING.value,
        event_name="Concurrency Test",
        issuer_name="Race Condition Lab",
        issue_date="2026-10-10",
        total_recipients=1,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)
    db_session.commit()

    # First worker claims the job -> Succeeds
    worker_1_claimed = worker.claim_next_job(db_session)
    assert worker_1_claimed is not None
    assert worker_1_claimed.id == job.id

    # Second worker attempts to claim concurrently -> Returns None (No duplicates)
    worker_2_claimed = worker.claim_next_job(db_session)
    assert worker_2_claimed is None
