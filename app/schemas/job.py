"""
Job Request and Response Schemas
Validation and serialization schemas for bulk certificate generation jobs.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.recipient import CertificateRecordResponse, RecipientInput


class BulkCreateJobRequest(BaseModel):
    event_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Course, conference, or workshop title",
        examples=["Advanced Python Backend Engineering"],
    )
    issuer_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Issuing organization or authority",
        examples=["Global Tech Institute"],
    )
    issue_date: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="Date of award or completion (e.g., 2026-10-10 or October 10, 2026)",
        examples=["2026-10-10"],
    )
    certificate_title: str = Field(
        default="Certificate of Completion",
        max_length=255,
        description="Heading title printed on the certificate",
        examples=["Certificate of Achievement"],
    )
    recipients: list[RecipientInput] = Field(
        ..., min_length=1, description="List of recipients to generate certificates for"
    )

    @field_validator("event_name", "issuer_name", "issue_date", "certificate_title")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace.")
        return cleaned


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str
    total_recipients: int
    created_at: datetime
    status_url: str
    message: str = "Bulk certificate generation job accepted and queued for processing."


class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: str
    event_name: str
    issuer_name: str
    issue_date: str
    certificate_title: str
    total_recipients: int
    successful_count: int
    failed_count: int
    progress_percentage: float
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    zip_download_url: str | None = None


class JobDetailResponse(JobStatusResponse):
    certificates: list[CertificateRecordResponse] = Field(default_factory=list)
