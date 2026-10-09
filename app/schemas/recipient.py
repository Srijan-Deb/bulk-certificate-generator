"""
Recipient and Certificate Pydantic Schemas
Defines incoming validation rules and outgoing serialization schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RecipientInput(BaseModel):
    recipient_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Full legal name of the certificate recipient",
        examples=["Jane Doe"],
    )
    recipient_email: EmailStr | None = Field(
        default=None, description="Optional contact email for recipient", examples=["jane.doe@example.com"]
    )
    custom_remarks: str | None = Field(
        default=None,
        max_length=500,
        description="Optional honors, grade, or custom note",
        examples=["With Distinction"],
    )

    @field_validator("recipient_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Recipient name cannot be blank or whitespace only.")
        return cleaned


class CertificateRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str | None = None
    certificate_id: str | None = None
    status: str
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = None
