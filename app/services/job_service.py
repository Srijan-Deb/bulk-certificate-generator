"""
Job Service
Orchestrates bulk certificate jobs, persistence, queries, and file packaging.
"""

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    BatchSizeExceededError,
    CertificateNotFoundError,
    JobNotFoundError,
    SecurityViolationError,
    StorageAccessError,
)
from app.models.certificate import CertificateRecord
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.schemas.job import BulkCreateJobRequest
from app.services.certificate_service import certificate_generator
from app.services.cloud_storage import cloud_storage


class JobService:
    """Business logic for generation jobs and certificate retrieval."""

    def create_bulk_job(self, db: Session, request: BulkCreateJobRequest, user_id: str | None = None) -> GenerationJob:
        """
        Validates request batch limits and transactionally creates
        the GenerationJob and all initial CertificateRecord entries.
        """
        recipient_count = len(request.recipients)
        if recipient_count > settings.MAX_BATCH_SIZE:
            raise BatchSizeExceededError(actual_size=recipient_count, max_size=settings.MAX_BATCH_SIZE)

        # Create GenerationJob parent record
        now = datetime.now(timezone.utc)
        job = GenerationJob(
            status=JobStatus.PENDING.value,
            user_id=user_id,
            event_name=request.event_name,
            issuer_name=request.issuer_name,
            issue_date=request.issue_date,
            certificate_title=request.certificate_title,
            total_recipients=recipient_count,
            successful_count=0,
            failed_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        db.flush()  # Populates job.id for foreign keys

        # Create child recipient records
        for item in request.recipients:
            cert_record = CertificateRecord(
                job_id=job.id,
                recipient_name=item.recipient_name,
                recipient_email=str(item.recipient_email) if item.recipient_email else None,
                custom_remarks=item.custom_remarks,
                certificate_id=certificate_generator.generate_certificate_id(),
                status=CertificateStatus.PENDING.value,
                created_at=now,
            )
            db.add(cert_record)

        db.commit()
        db.refresh(job)
        return job

    def get_job(self, db: Session, job_id: str) -> GenerationJob:
        """Retrieves GenerationJob by ID, raising JobNotFoundError if not present."""
        stmt = select(GenerationJob).where(GenerationJob.id == job_id)
        job = db.execute(stmt).scalar_one_or_none()
        if not job:
            raise JobNotFoundError(job_id)
        return job

    def get_job_status_counts(self, db: Session, job_id: str) -> dict[str, int]:
        """
        Aggregates individual certificate status counts (PENDING, PROCESSING, SUCCESS, FAILED)
        for a job directly from the database.
        """
        stmt = (
            select(CertificateRecord.status, func.count(CertificateRecord.id))
            .where(CertificateRecord.job_id == job_id)
            .group_by(CertificateRecord.status)
        )
        rows = db.execute(stmt).all()
        return {status: count for status, count in rows}

    def get_job_certificates(
        self, db: Session, job_id: str, status_filter: str | None = None, limit: int = 100, offset: int = 0
    ) -> tuple[list[CertificateRecord], int]:
        """
        Lists certificates for a specific job with optional status filtering
        and pagination. Returns (records, total_matching).
        """
        # Ensure job exists
        self.get_job(db, job_id)

        # Base filter query
        base_query = select(CertificateRecord).where(CertificateRecord.job_id == job_id)
        count_query = select(func.count(CertificateRecord.id)).where(CertificateRecord.job_id == job_id)

        if status_filter:
            norm_status = status_filter.upper().strip()
            base_query = base_query.where(CertificateRecord.status == norm_status)
            count_query = count_query.where(CertificateRecord.status == norm_status)

        total = db.execute(count_query).scalar_one()
        records = (
            db.execute(base_query.order_by(CertificateRecord.created_at.asc()).offset(offset).limit(limit))
            .scalars()
            .all()
        )

        return list(records), total

    def get_certificate_file(self, db: Session, certificate_id: str) -> tuple[Path, str]:
        """
        Locates the physical PDF file for a certificate ID.
        Includes security checks to prevent path traversal attacks.
        Returns (Path, filename).
        """
        stmt = select(CertificateRecord).where(CertificateRecord.certificate_id == certificate_id)
        record = db.execute(stmt).scalar_one_or_none()
        if not record:
            raise CertificateNotFoundError(certificate_id)

        if not record.file_path or record.status != CertificateStatus.SUCCESS.value:
            raise CertificateNotFoundError(f"{certificate_id} (certificate has not been successfully generated)")

        file_path = Path(record.file_path).resolve()
        base_storage = settings.STORAGE_DIR.resolve()

        # Security check: Ensure file resides strictly inside storage directory
        try:
            file_path.relative_to(base_storage)
        except ValueError:
            raise SecurityViolationError("Access denied: File is outside authorized storage path.")

        if not file_path.exists() or not file_path.is_file():
            # If missing locally, attempt to restore from S3 cloud storage
            if record.cloud_key and cloud_storage.is_configured():
                cloud_storage.download_file(record.cloud_key, file_path)

        if not file_path.exists() or not file_path.is_file():
            raise StorageAccessError(f"Certificate file for '{certificate_id}' is missing from storage.")

        filename = f"{certificate_id}.pdf"
        return file_path, filename

    def create_job_zip_archive(self, db: Session, job_id: str) -> Path:
        """
        Packages all successfully generated certificates for a job into a ZIP archive.
        Returns the path to the generated ZIP file.
        """
        self.get_job(db, job_id)  # Validate job exists
        stmt = select(CertificateRecord).where(
            CertificateRecord.job_id == job_id, CertificateRecord.status == CertificateStatus.SUCCESS.value
        )
        successful_records = db.execute(stmt).scalars().all()

        if not successful_records:
            raise StorageAccessError(f"No successfully generated certificates found for job '{job_id}'.")

        job_dir = settings.STORAGE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        zip_path = job_dir / f"job_{job_id}_certificates.zip"

        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for record in successful_records:
                if record.file_path:
                    p = Path(record.file_path)
                    if not p.exists() and record.cloud_key and cloud_storage.is_configured():
                        cloud_storage.download_file(record.cloud_key, p)
                    if p.exists():
                        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in record.recipient_name)
                        arcname = f"{safe_name}_{record.certificate_id}.pdf"
                        zip_file.write(p, arcname=arcname)

        return zip_path

    def list_jobs(self, db: Session, user_id: str | None = None, limit: int = 50) -> list[GenerationJob]:
        """Lists recent jobs, optionally filtered by user_id."""
        query = select(GenerationJob)
        if user_id:
            query = query.where(GenerationJob.user_id == user_id)
        query = query.order_by(GenerationJob.created_at.desc()).limit(limit)
        return list(db.execute(query).scalars().all())


job_service = JobService()
