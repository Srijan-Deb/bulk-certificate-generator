"""
Job Management Endpoints
Handles creation, status polling, recipient listings, and bulk ZIP download.
"""

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, verify_api_key
from app.schemas.job import (
    BulkCreateJobRequest,
    JobAcceptedResponse,
    JobStatusResponse,
)
from app.schemas.recipient import CertificateRecordResponse
from app.services.job_service import job_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Bulk Certificate Generation Request",
    description="Accepts event metadata and a list of recipients, validates the payload, queues a persistent generation job, and immediately returns 202 Accepted with a status URL.",
)
def create_bulk_job(
    request: BulkCreateJobRequest,
    req: Request,
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    job = job_service.create_bulk_job(db=db, request=request)
    status_url = str(req.url_for("get_job_status", job_id=job.id))

    return JobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_recipients,
        created_at=job.created_at,
        status_url=status_url,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Status and Progress",
    description="Returns aggregate progress, counts (successful, failed, total), and download URLs.",
)
def get_job_status(job_id: str, req: Request, db: Session = Depends(get_db)):
    job = job_service.get_job(db=db, job_id=job_id)

    # Calculate real-time progress percentage
    progress = 0.0
    if job.total_recipients > 0:
        processed = job.successful_count + job.failed_count
        progress = round((processed / job.total_recipients) * 100.0, 1)

    zip_url = None
    if job.successful_count > 0:
        zip_url = str(req.url_for("download_job_certificates_zip", job_id=job.id))

    status_counts = job_service.get_job_status_counts(db=db, job_id=job.id)

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        event_name=job.event_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        certificate_title=job.certificate_title,
        total_recipients=job.total_recipients,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        pending_count=status_counts.get("PENDING", 0),
        processing_count=status_counts.get("PROCESSING", 0),
        progress_percentage=progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        zip_download_url=zip_url,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=list[CertificateRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="List Certificates in a Job",
    description="Retrieves recipient certificates belonging to a specific job with optional status filtering and pagination.",
)
def list_job_certificates(
    job_id: str,
    req: Request,
    status_filter: str | None = Query(None, description="Filter by status: PENDING, PROCESSING, SUCCESS, FAILED"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    records, _ = job_service.get_job_certificates(
        db=db, job_id=job_id, status_filter=status_filter, limit=limit, offset=offset
    )

    results = []
    for rec in records:
        download_url = None
        if rec.status == "SUCCESS" and rec.certificate_id:
            download_url = str(req.url_for("download_certificate", certificate_id=rec.certificate_id))

        results.append(
            CertificateRecordResponse(
                id=rec.id,
                job_id=rec.job_id,
                recipient_name=rec.recipient_name,
                recipient_email=rec.recipient_email,
                certificate_id=rec.certificate_id,
                status=rec.status,
                error_code=rec.error_code,
                error_message=rec.error_message,
                created_at=rec.created_at,
                completed_at=rec.completed_at,
                download_url=download_url,
            )
        )
    return results


@router.get(
    "/{job_id}/download-zip",
    status_code=status.HTTP_200_OK,
    summary="Download All Job Certificates as a ZIP Archive",
    description="Bundles all successfully generated certificate PDFs in this job into a single compressed ZIP file.",
)
def download_job_certificates_zip(job_id: str, db: Session = Depends(get_db)):
    zip_path = job_service.create_job_zip_archive(db=db, job_id=job_id)
    return FileResponse(path=str(zip_path), media_type="application/zip", filename=f"certificates_job_{job_id}.zip")
