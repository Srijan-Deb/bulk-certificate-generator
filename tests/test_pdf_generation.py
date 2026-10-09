"""
Unit Tests for ReportLab PDF Generation Engine (Phase 5)
Verifies:
- Standard generation & layout integrity
- Format & uniqueness of Certificate IDs
- Format & determinism of Cryptographic Verification Codes
- Dynamic auto-scaling for long recipient names and event titles
- Safe Unicode text sanitization and normalization
- Prevention of accidental file overwrites
- Structural validation using pypdf (opening and metadata verification)
"""

import pypdf
import pytest

from app.services.certificate_service import CertificateGenerator


def test_pdf_generation_output(tmp_path):
    generator = CertificateGenerator(output_dir=tmp_path)
    job_id = "test-job-unit"
    cert_id = generator.generate_certificate_id()

    pdf_path = generator.render_certificate(
        job_id=job_id,
        certificate_id=cert_id,
        recipient_name="Grace Hopper",
        event_name="Compiler Construction Masterclass",
        issuer_name="Computer Science Foundation",
        issue_date="2026-10-10",
        certificate_title="Distinguished Achievement Award",
        custom_remarks="Pioneer in Computing",
    )

    assert pdf_path.exists()
    assert pdf_path.is_file()
    assert pdf_path.stat().st_size > 1000

    # Verify standard PDF header magic bytes
    with open(pdf_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def test_certificate_id_format():
    generator = CertificateGenerator()
    cert_id_1 = generator.generate_certificate_id()
    cert_id_2 = generator.generate_certificate_id()

    assert cert_id_1.startswith("CERT-")
    assert cert_id_2.startswith("CERT-")
    assert cert_id_1 != cert_id_2

    parts = cert_id_1.split("-")
    assert len(parts) == 4
    for part in parts[1:]:
        assert len(part) == 4
        assert part.isalnum()


def test_verification_code_generation():
    generator = CertificateGenerator()
    job_id = "job-uuid-1234"
    cert_id = "CERT-ABCD-EF01-2345"
    recipient_1 = "Alice Walker"
    recipient_2 = "Bob Stone"

    code_1a = generator.generate_verification_code(job_id, cert_id, recipient_1)
    code_1b = generator.generate_verification_code(job_id, cert_id, recipient_1)
    code_2 = generator.generate_verification_code(job_id, cert_id, recipient_2)

    # Deterministic for same inputs
    assert code_1a == code_1b
    # Distinct for different recipients
    assert code_1a != code_2

    # Verification Code format: V-XXXX-XXXX-XXXX
    assert code_1a.startswith("V-")
    parts = code_1a.split("-")
    assert len(parts) == 4
    for part in parts[1:]:
        assert len(part) == 4
        assert part.isalnum()


def test_long_recipient_name_and_event_handling(tmp_path):
    generator = CertificateGenerator(output_dir=tmp_path)
    job_id = "test-job-long-text"
    cert_id = generator.generate_certificate_id()

    very_long_name = "Dr. Alexander Montgomery Bartholomew-Fitzgerald III, Baron of Wellington"
    very_long_event = "Advanced Distributed Systems, Fault Tolerance, and High-Performance Cloud Architecture Certification"

    pdf_path = generator.render_certificate(
        job_id=job_id,
        certificate_id=cert_id,
        recipient_name=very_long_name,
        event_name=very_long_event,
        issuer_name="International Institute of Advanced Software Engineering",
        issue_date="2026-10-10",
    )

    assert pdf_path.exists()
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 1


def test_unicode_text_sanitization(tmp_path):
    generator = CertificateGenerator(output_dir=tmp_path)
    raw_text = "  José María François Müller  "
    sanitized = generator.sanitize_text(raw_text)
    assert sanitized == "José María François Müller"

    # Verify rendering unicode characters without failure
    job_id = "test-unicode-job"
    cert_id = generator.generate_certificate_id()
    pdf_path = generator.render_certificate(
        job_id=job_id,
        certificate_id=cert_id,
        recipient_name="José María François",
        event_name="Machine Learning & Intelligence Artificielle",
        issuer_name="Académie Européenne",
        issue_date="2026-10-10",
    )
    assert pdf_path.exists()


def test_overwrite_prevention(tmp_path):
    generator = CertificateGenerator(output_dir=tmp_path)
    job_id = "test-overwrite-job"
    cert_id = "CERT-STATIC-0001-TEST"

    # First generation succeeds
    path_1 = generator.render_certificate(
        job_id=job_id,
        certificate_id=cert_id,
        recipient_name="John Doe",
        event_name="Web Security Workshop",
        issuer_name="Open Security Org",
        issue_date="2026-10-10",
        allow_overwrite=True,
    )
    assert path_1.exists()

    # Second generation with allow_overwrite=False should raise FileExistsError
    with pytest.raises(FileExistsError, match="already exists"):
        generator.render_certificate(
            job_id=job_id,
            certificate_id=cert_id,
            recipient_name="John Doe",
            event_name="Web Security Workshop",
            issuer_name="Open Security Org",
            issue_date="2026-10-10",
            allow_overwrite=False,
        )


def test_pdf_can_be_opened_and_parsed_with_pypdf(tmp_path):
    generator = CertificateGenerator(output_dir=tmp_path)
    job_id = "test-open-job"
    cert_id = generator.generate_certificate_id()

    pdf_path = generator.render_certificate(
        job_id=job_id,
        certificate_id=cert_id,
        recipient_name="Ada Lovelace",
        event_name="Analytical Engine Programming",
        issuer_name="Royal Society of Computing",
        issue_date="2026-10-10",
        certificate_title="Certificate of Excellence",
    )

    # Open and inspect with pypdf
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 1
    page = reader.pages[0]
    # Verify A4 landscape dimensions: ~841.89 pt width x ~595.27 pt height
    assert float(page.mediabox.width) > 800
    assert float(page.mediabox.height) > 590

    # Verify metadata fields embedded in PDF document info
    metadata = reader.metadata
    assert metadata is not None
    assert "Ada Lovelace" in metadata.title
    assert "Royal Society of Computing" in metadata.author
