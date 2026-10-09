"""
Background Worker Engine
Implements a database-backed, zero-cost asynchronous job processor.
Features:
- Atomic job claiming (prevents duplicate processing without distributed locks)
- Fault isolation (recipient failure does not break the batch)
- Real-time progress updates for API polling
- Stale job crash recovery
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.certificate import CertificateRecord
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.services.certificate_service import certificate_generator

logger = logging.getLogger("bulk_certificate_generator.worker")


class JobWorker:
    """Processes pending certificate jobs directly from the database."""

    def __init__(self):
        self.is_running = False

    def recover_stale_jobs(self, db: Session) -> int:
        """
        Detects jobs stuck in PROCESSING due to worker crashes or sudden termination.
        Resets any interrupted recipient records and requeues the job as PENDING.
        """
        timeout_threshold = datetime.now(timezone.utc) - timedelta(seconds=settings.WORKER_JOB_TIMEOUT_SECONDS)
        stale_stmt = select(GenerationJob).where(
            GenerationJob.status == JobStatus.PROCESSING.value, GenerationJob.updated_at < timeout_threshold
        )
        stale_jobs = db.execute(stale_stmt).scalars().all()
        recovered_count = 0

        for job in stale_jobs:
            logger.warning("Recovering stale job '%s' (last updated %s)", job.id, job.updated_at)

            # Reset any records caught mid-processing
            db.execute(
                update(CertificateRecord)
                .where(
                    CertificateRecord.job_id == job.id, CertificateRecord.status == CertificateStatus.PROCESSING.value
                )
                .values(status=CertificateStatus.PENDING.value)
            )

            # Requeue job
            job.status = JobStatus.PENDING.value
            job.updated_at = datetime.now(timezone.utc)
            recovered_count += 1

        if recovered_count > 0:
            db.commit()
            logger.info("Successfully recovered %d stale jobs.", recovered_count)
        return recovered_count

    def claim_next_job(self, db: Session) -> GenerationJob | None:
        """
        Atomically claims the oldest pending job.
        Uses an atomic UPDATE with a rowcount check to eliminate race conditions
        between multiple worker processes without requiring Redis or Celery.
        """
        # Step 1: Find next candidate job ID
        find_candidate_stmt = (
            select(GenerationJob.id)
            .where(GenerationJob.status == JobStatus.PENDING.value)
            .order_by(GenerationJob.created_at.asc())
            .limit(1)
        )
        job_id = db.execute(find_candidate_stmt).scalar_one_or_none()
        if not job_id:
            return None

        # Step 2: Atomically claim candidate job
        now = datetime.now(timezone.utc)
        claim_stmt = (
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == JobStatus.PENDING.value)
            .values(status=JobStatus.PROCESSING.value, started_at=now, updated_at=now)
        )
        result = db.execute(claim_stmt)
        db.commit()

        # If another worker claimed it first, rowcount will be 0
        if result.rowcount == 0:
            logger.debug("Job '%s' was claimed by another worker concurrently.", job_id)
            return None

        claimed_job = db.execute(select(GenerationJob).where(GenerationJob.id == job_id)).scalar_one()
        logger.info(
            "Worker successfully claimed job '%s' (%d recipients)", claimed_job.id, claimed_job.total_recipients
        )
        return claimed_job

    def process_job(self, db: Session, job: GenerationJob) -> None:
        """
        Processes all recipient records for the job with isolated error handling.
        A failure in one recipient never halts processing of subsequent recipients.
        """
        # Fetch pending certificate records for this job
        stmt = (
            select(CertificateRecord)
            .where(
                CertificateRecord.job_id == job.id,
                CertificateRecord.status.in_([CertificateStatus.PENDING.value, CertificateStatus.PROCESSING.value]),
            )
            .order_by(CertificateRecord.created_at.asc())
        )
        records = db.execute(stmt).scalars().all()

        for record in records:
            # Mark individual recipient as PROCESSING
            record.status = CertificateStatus.PROCESSING.value
            db.commit()

            # Recipient Data Validation
            if not record.recipient_name or len(record.recipient_name.strip()) < 2:
                logger.warning("Recipient record '%s' validation failed: Invalid name", record.id)
                record.status = CertificateStatus.FAILED.value
                record.error_code = "INVALID_RECIPIENT_DATA"
                record.error_message = "Recipient name must be at least 2 characters long."
                record.completed_at = datetime.now(timezone.utc)
                job.failed_count += 1
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                continue

            # Render PDF Certificate
            try:
                pdf_path = certificate_generator.render_certificate(
                    job_id=job.id,
                    certificate_id=record.certificate_id,
                    recipient_name=record.recipient_name,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    certificate_title=job.certificate_title,
                    custom_remarks=record.custom_remarks,
                )
                record.file_path = str(pdf_path)
                record.status = CertificateStatus.SUCCESS.value
                record.completed_at = datetime.now(timezone.utc)
                record.error_code = None
                record.error_message = None
                job.successful_count += 1
            except Exception as exc:
                logger.exception("Failed to generate PDF for recipient '%s' (ID: %s)", record.recipient_name, record.id)
                record.status = CertificateStatus.FAILED.value
                record.error_code = "PDF_RENDER_ERROR"
                record.error_message = str(exc)
                record.completed_at = datetime.now(timezone.utc)
                job.failed_count += 1

            # Progressively update job heartbeat
            job.updated_at = datetime.now(timezone.utc)
            db.commit()

        # Step 3: Determine final aggregate job status
        now = datetime.now(timezone.utc)
        job.completed_at = now
        job.updated_at = now

        if job.failed_count == 0:
            job.status = JobStatus.COMPLETED.value
        elif job.successful_count > 0 and job.failed_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS.value if job.total_recipients > 0 else JobStatus.FAILED.value

        db.commit()
        logger.info(
            "Job '%s' finished processing: status=%s, success=%d, failed=%d, total=%d",
            job.id,
            job.status,
            job.successful_count,
            job.failed_count,
            job.total_recipients,
        )

    def process_one_pending_job(self) -> bool:
        """Attempts to claim and process a single pending job. Returns True if a job was processed."""
        db = SessionLocal()
        try:
            # Check for stale jobs periodically
            self.recover_stale_jobs(db)

            job = self.claim_next_job(db)
            if not job:
                return False
            self.process_job(db, job)
            return True
        finally:
            db.close()

    def run_worker_loop(self) -> None:
        """Continuous execution loop for dedicated worker process."""
        self.is_running = True
        logger.info(
            "Worker process started. Polling database for jobs every %.1fs...", settings.WORKER_POLL_INTERVAL_SECONDS
        )
        try:
            while self.is_running:
                job_processed = self.process_one_pending_job()
                if not job_processed:
                    time.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Worker received shutdown signal. Exiting gracefully.")
        finally:
            self.is_running = False


# Global worker instance
worker = JobWorker()
