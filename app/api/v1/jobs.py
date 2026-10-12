"""
Job Management Endpoints
Handles creation, status polling, recipient listings, and bulk ZIP download.
"""

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, get_db, verify_api_key
from app.core.metrics import metrics
from app.models.user import User
from app.schemas.job import (
    BulkCreateJobRequest,
    JobAcceptedResponse,
    JobStatusResponse,
)
from app.schemas.recipient import CertificateRecordResponse
from app.services.job_service import job_service
from app.services.spreadsheet_parser import spreadsheet_parser

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "",
    response_model=list[JobStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="List Recent Generation Jobs",
    description="Returns recent jobs, optionally filtered to the authenticated user.",
)
def list_jobs(
    req: Request,
    limit: int = Query(50, ge=1, le=100),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user_id = current_user.id if current_user else None
    jobs = job_service.list_jobs(db=db, user_id=user_id, limit=limit)
    results = []
    for job in jobs:
        progress = 0.0
        if job.total_recipients > 0:
            processed = job.successful_count + job.failed_count
            progress = round((processed / job.total_recipients) * 100.0, 1)

        zip_url = None
        if job.successful_count > 0:
            zip_url = str(req.url_for("download_job_certificates_zip", job_id=job.id))

        status_counts = job_service.get_job_status_counts(db=db, job_id=job.id)
        results.append(
            JobStatusResponse(
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
        )
    return results


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
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    user_id = current_user.id if current_user else None
    job = job_service.create_bulk_job(db=db, request=request, user_id=user_id)
    metrics.record_job_submitted("json")
    status_url = str(req.url_for("get_job_status", job_id=job.id))

    return JobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_recipients,
        created_at=job.created_at,
        status_url=status_url,
    )


@router.post(
    "/upload",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Spreadsheet to Generate Bulk Certificates",
    description=(
        "Accepts event metadata as form fields and a spreadsheet file (.xlsx or .csv) containing recipient rows. "
        "Parses and validates all recipients, queues a background certificate generation job, "
        "and returns a 202 Accepted response with a polling status URL and ZIP download link once processed."
    ),
)
async def upload_recipients_job(
    req: Request,
    file: UploadFile = File(
        ...,
        description="Spreadsheet containing recipient records (Excel .xlsx or CSV .csv)",
    ),
    event_name: str = Form(
        ...,
        min_length=2,
        max_length=255,
        description="Event Name (e.g., Course, conference, or workshop title)",
        examples=["Advanced Python Backend Engineering"],
    ),
    issuer_name: str = Form(
        ...,
        min_length=2,
        max_length=255,
        description="Issuer Name (Issuing organization or authority)",
        examples=["Global Tech Institute"],
    ),
    issue_date: str = Form(
        ...,
        min_length=4,
        max_length=50,
        description="Issue Date (Date of award or completion)",
        examples=["2026-10-10"],
    ),
    certificate_title: str = Form(
        "Certificate of Completion",
        max_length=255,
        description="Certificate Title (Heading printed on certificate)",
        examples=["Certificate of Completion"],
    ),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    _api_key: str | None = Depends(verify_api_key),
):
    # Read file bytes
    contents = await file.read()

    # Parse and validate recipients from spreadsheet
    recipients = spreadsheet_parser.parse_recipients_file(
        file_bytes=contents,
        filename=file.filename or "recipients.xlsx",
    )

    # Build job request schema with parsed recipients
    job_request = BulkCreateJobRequest(
        event_name=event_name,
        issuer_name=issuer_name,
        issue_date=issue_date,
        certificate_title=certificate_title,
        recipients=recipients,
    )

    # Persist and queue the job
    user_id = current_user.id if current_user else None
    job = job_service.create_bulk_job(db=db, request=job_request, user_id=user_id)
    metrics.record_job_submitted("upload")
    status_url = str(req.url_for("get_job_status", job_id=job.id))

    return JobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_recipients,
        created_at=job.created_at,
        status_url=status_url,
        message=f"Spreadsheet '{file.filename}' processed successfully ({job.total_recipients} recipients queued).",
    )


@router.get(
    "/upload/template",
    status_code=status.HTTP_200_OK,
    summary="Download Sample Recipients Spreadsheet Template",
    description="Downloads a pre-formatted Excel template (.xlsx) with expected column headers and sample recipient rows.",
)
def download_recipients_template():
    content = spreadsheet_parser.generate_sample_recipients_excel()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="recipients.xlsx"'},
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
@router.get(
    "/{job_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download All Job Certificates as a ZIP Archive (Alias)",
    description="Alias for download-zip: bundles all successfully generated certificate PDFs in this job into a single compressed ZIP file.",
)
def download_job_certificates_zip(job_id: str, db: Session = Depends(get_db)):
    zip_path = job_service.create_job_zip_archive(db=db, job_id=job_id)
    filename = f"certificates_{job_id}.zip"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=filename,
        content_disposition_type="attachment",
        headers=headers,
    )
