"""
Tests for Database Persistence and Transaction Integrity (Phase 10)
Verifies:
- Data persistence across separate, disjoint database sessions
- Transaction rollback on mid-operation exceptions preventing partial state
- Relational foreign key cascade behavior
"""

from datetime import datetime, timezone

from app.models.certificate import CertificateRecord
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from tests.conftest import TestingSessionLocal


def test_database_persistence_across_disjoint_sessions(db_session):
    now = datetime.now(timezone.utc)
    # 1. Insert records in session 1
    session_1 = TestingSessionLocal()
    job = GenerationJob(
        status=JobStatus.PENDING.value,
        event_name="Persistence Workshop",
        issuer_name="Database Council",
        issue_date="2026-10-10",
        total_recipients=1,
        created_at=now,
        updated_at=now,
    )
    session_1.add(job)
    session_1.flush()

    cert = CertificateRecord(
        job_id=job.id,
        recipient_name="Grace Hopper",
        certificate_id="CERT-PERSIST-0001",
        status=CertificateStatus.PENDING.value,
        created_at=now,
    )
    session_1.add(cert)
    session_1.commit()
    job_id = job.id
    session_1.close()

    # 2. Open a completely independent session 2 to verify true disk persistence
    session_2 = TestingSessionLocal()
    persisted_job = session_2.get(GenerationJob, job_id)
    assert persisted_job is not None
    assert persisted_job.event_name == "Persistence Workshop"
    assert len(persisted_job.certificates) == 1
    assert persisted_job.certificates[0].recipient_name == "Grace Hopper"
    session_2.close()


def test_transaction_rollback_prevents_partial_orphans(db_session):
    session = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    job = GenerationJob(
        status=JobStatus.PENDING.value,
        event_name="Rollback Event",
        issuer_name="ACID Lab",
        issue_date="2026-10-10",
        total_recipients=2,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.flush()

    try:
        # Intentionally force a database error (e.g. inserting an invalid or broken state)
        cert1 = CertificateRecord(
            job_id=job.id,
            recipient_name="Valid Recipient",
            status=CertificateStatus.PENDING.value,
            created_at=now,
        )
        session.add(cert1)
        # Simulate unexpected failure mid-transaction
        raise RuntimeError("Simulated mid-transaction failure")
    except RuntimeError:
        session.rollback()

    session.close()

    # Verify that the rolled back transaction left zero orphaned records in the database
    verify_session = TestingSessionLocal()
    remaining_jobs = verify_session.query(GenerationJob).filter_by(event_name="Rollback Event").all()
    assert len(remaining_jobs) == 0
    verify_session.close()


def test_foreign_key_cascade_deletion(db_session):
    session = TestingSessionLocal()
    now = datetime.now(timezone.utc)

    job = GenerationJob(
        status=JobStatus.PENDING.value,
        event_name="Cascade Delete Workshop",
        issuer_name="Test Academy",
        issue_date="2026-10-10",
        total_recipients=1,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.flush()

    cert = CertificateRecord(
        job_id=job.id,
        recipient_name="Cascade Student",
        certificate_id="CERT-CASCADE-0001",
        status=CertificateStatus.PENDING.value,
        created_at=now,
    )
    session.add(cert)
    session.commit()
    job_id = job.id

    # Delete parent job
    session.delete(job)
    session.commit()
    session.close()

    # Verify that child certificate records were cascade-deleted
    verify_session = TestingSessionLocal()
    orphaned_certs = verify_session.query(CertificateRecord).filter_by(job_id=job_id).all()
    assert len(orphaned_certs) == 0
    verify_session.close()
