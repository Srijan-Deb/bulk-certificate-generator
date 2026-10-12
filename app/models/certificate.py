"""
CertificateRecord ORM Model
Represents an individual recipient certificate within a bulk generation job.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CertificateStatus

if TYPE_CHECKING:
    from app.models.job import GenerationJob


class CertificateRecord(Base):
    __tablename__ = "certificate_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generation_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Recipient Information
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    custom_remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Generated Certificate Identifiers
    certificate_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=CertificateStatus.PENDING.value, index=True, nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    cloud_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Failure / Error Tracking
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to parent GenerationJob
    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="certificates")

    def __repr__(self) -> str:
        return f"<CertificateRecord id={self.id} cert_id={self.certificate_id} name='{self.recipient_name}' status={self.status}>"
