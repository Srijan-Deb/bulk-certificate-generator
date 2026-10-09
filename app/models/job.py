"""
GenerationJob ORM Model
Represents the bulk generation request, tracking overall progress and outcome counters.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobStatus

if TYPE_CHECKING:
    from app.models.certificate import CertificateRecord


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(32), index=True, default=JobStatus.PENDING.value, nullable=False)

    # Event / Certificate Metadata
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issue_date: Mapped[str] = mapped_column(String(50), nullable=False)
    certificate_title: Mapped[str] = mapped_column(String(255), default="Certificate of Completion", nullable=False)

    # Counters
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to CertificateRecord
    certificates: Mapped[list["CertificateRecord"]] = relationship(
        "CertificateRecord", back_populates="job", cascade="all, delete-orphan", order_by="CertificateRecord.created_at"
    )

    def __repr__(self) -> str:
        return f"<GenerationJob id={self.id} status={self.status} total={self.total_recipients} success={self.successful_count} fail={self.failed_count}>"
