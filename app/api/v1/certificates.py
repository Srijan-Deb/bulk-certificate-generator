"""
Certificate Retrieval Endpoints
Handles secure PDF file download for individual certificates.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.job_service import job_service

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Individual Certificate PDF",
    description="Streams the generated PDF certificate for a specific certificate ID with path-traversal security verification.",
)
def download_certificate(
    certificate_id: str,
    as_attachment: bool = Query(
        False, description="Set True to force download prompt instead of inline browser preview"
    ),
    db: Session = Depends(get_db),
):
    file_path, filename = job_service.get_certificate_file(db=db, certificate_id=certificate_id)

    disposition = "attachment" if as_attachment else "inline"
    headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}

    return FileResponse(path=str(file_path), media_type="application/pdf", headers=headers)
