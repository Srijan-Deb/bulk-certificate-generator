"""
Unit Tests for ReportLab PDF Generation Engine
"""

from app.services.certificate_service import CertificateGenerator


def test_pdf_generation_output(tmp_path):
    # Instantiate isolated generator instance for unit testing
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
    assert pdf_path.stat().st_size > 1000  # Non-trivial PDF size

    # Verify standard PDF header magic bytes
    with open(pdf_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def test_certificate_id_format():
    generator = CertificateGenerator()
    cert_id = generator.generate_certificate_id()
    assert cert_id.startswith("CERT-")
    parts = cert_id.split("-")
    assert len(parts) == 4
