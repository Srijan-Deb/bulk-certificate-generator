"""
Certificate Generation Engine
Renders high-resolution, vector-quality PDF certificates using ReportLab.
Uses a predefined, elegant landscape template with decorative borders,
institutional seal graphic, and recipient metadata.
"""

import logging
import uuid
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.core.config import settings

logger = logging.getLogger("bulk_certificate_generator.pdf")


class CertificateGenerator:
    """
    Renders individual PDF certificates with a professional, predefined landscape design.
    """

    def __init__(self, output_dir: Path | None = None):
        self._output_dir = output_dir

    @property
    def output_dir(self) -> Path:
        target = self._output_dir or settings.STORAGE_DIR
        target.mkdir(parents=True, exist_ok=True)
        return target

    @output_dir.setter
    def output_dir(self, value: Path | None) -> None:
        self._output_dir = value

    @staticmethod
    def generate_certificate_id(prefix: str = "CERT") -> str:
        """Generates a cryptographically strong, human-readable unique certificate identifier."""
        short_uuid = uuid.uuid4().hex[:12].upper()
        # Formatted as CERT-XXXX-XXXX-XXXX
        return f"{prefix}-{short_uuid[0:4]}-{short_uuid[4:8]}-{short_uuid[8:12]}"

    def get_certificate_path(self, job_id: str, certificate_id: str) -> Path:
        """Returns safe, deterministic destination path for certificate PDF."""
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        # Sanitize filename
        safe_cert_id = "".join(c for c in certificate_id if c.isalnum() or c in ("-", "_"))
        return job_dir / f"{safe_cert_id}.pdf"

    def render_certificate(
        self,
        job_id: str,
        certificate_id: str,
        recipient_name: str,
        event_name: str,
        issuer_name: str,
        issue_date: str,
        certificate_title: str = "Certificate of Completion",
        custom_remarks: str | None = None,
    ) -> Path:
        """
        Draws and saves the PDF certificate.
        Raises RuntimeError on generation failure to be handled by the caller.
        """
        file_path = self.get_certificate_path(job_id, certificate_id)

        # Dimensions: A4 Landscape is 841.89 x 595.27 points
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(str(file_path), pagesize=(page_width, page_height))
        c.setTitle(f"{certificate_title} - {recipient_name}")
        c.setAuthor(issuer_name)
        c.setSubject(event_name)

        # Color Palette
        navy_dark = colors.HexColor("#0F172A")
        navy_light = colors.HexColor("#1E293B")
        gold_accent = colors.HexColor("#D97706")
        gold_light = colors.HexColor("#FBBF24")
        slate_muted = colors.HexColor("#475569")
        cream_bg = colors.HexColor("#FCFDFD")

        # 1. Background Fill
        c.setFillColor(cream_bg)
        c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # 2. Decorative Outer Border (Navy)
        margin = 28
        c.setStrokeColor(navy_dark)
        c.setLineWidth(3.5)
        c.rect(margin, margin, page_width - (2 * margin), page_height - (2 * margin), fill=0, stroke=1)

        # 3. Decorative Inner Border (Gold)
        inner_margin = margin + 8
        c.setStrokeColor(gold_accent)
        c.setLineWidth(1.2)
        c.rect(
            inner_margin,
            inner_margin,
            page_width - (2 * inner_margin),
            page_height - (2 * inner_margin),
            fill=0,
            stroke=1,
        )

        # 4. Corner Geometric Flourishes
        c.setFillColor(gold_accent)
        corners = [
            (inner_margin, inner_margin),
            (page_width - inner_margin, inner_margin),
            (inner_margin, page_height - inner_margin),
            (page_width - inner_margin, page_height - inner_margin),
        ]
        for cx, cy in corners:
            c.circle(cx, cy, 3.5, fill=1, stroke=0)

        # 5. Header: Issuing Organization
        c.setFillColor(gold_accent)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(page_width / 2.0, page_height - 75, issuer_name.upper())

        # 6. Certificate Title
        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(page_width / 2.0, page_height - 118, certificate_title.upper())

        # Title Accent Line
        c.setStrokeColor(gold_accent)
        c.setLineWidth(2)
        accent_half_len = 80
        c.line(
            (page_width / 2.0) - accent_half_len,
            page_height - 128,
            (page_width / 2.0) + accent_half_len,
            page_height - 128,
        )

        # 7. Presentation Subtitle
        c.setFillColor(slate_muted)
        c.setFont("Helvetica", 12)
        c.drawCentredString(page_width / 2.0, page_height - 165, "THIS IS PROUDLY PRESENTED TO")

        # 8. Recipient Name (Prominent & Elegant)
        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(page_width / 2.0, page_height - 215, recipient_name)

        # Underline for Recipient Name
        c.setStrokeColor(gold_light)
        c.setLineWidth(1)
        name_line_half_len = 160
        c.line(
            (page_width / 2.0) - name_line_half_len,
            page_height - 225,
            (page_width / 2.0) + name_line_half_len,
            page_height - 225,
        )

        # 9. Context Description
        c.setFillColor(slate_muted)
        c.setFont("Helvetica", 12)
        c.drawCentredString(
            page_width / 2.0, page_height - 260, "for successful completion and mastery of the curriculum in"
        )

        # 10. Event / Course Name
        c.setFillColor(navy_light)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(page_width / 2.0, page_height - 295, event_name)

        # Optional Custom Remarks / Honors
        if custom_remarks:
            c.setFillColor(gold_accent)
            c.setFont("Helvetica-Oblique", 11)
            c.drawCentredString(page_width / 2.0, page_height - 325, f"— {custom_remarks} —")

        # 11. Official Seal / Badge Graphic (Center bottom vector drawing)
        seal_x = page_width / 2.0
        seal_y = 120
        # Outer seal circle
        c.setFillColor(gold_accent)
        c.circle(seal_x, seal_y, 28, fill=1, stroke=0)
        # Inner seal ring
        c.setFillColor(navy_dark)
        c.circle(seal_x, seal_y, 24, fill=1, stroke=0)
        # Center core
        c.setFillColor(gold_light)
        c.circle(seal_x, seal_y, 20, fill=1, stroke=0)
        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(seal_x, seal_y + 2, "VERIFIED")
        c.drawCentredString(seal_x, seal_y - 7, "EXCELLENCE")

        # 12. Left Column: Date of Issuance
        left_col_x = 130
        c.setStrokeColor(slate_muted)
        c.setLineWidth(0.8)
        c.line(left_col_x - 50, 105, left_col_x + 50, 105)
        c.setFillColor(slate_muted)
        c.setFont("Helvetica", 10)
        c.drawCentredString(left_col_x, 88, "Date of Issuance")
        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(left_col_x, 112, str(issue_date))

        # 13. Right Column: Authorized Signatory
        right_col_x = page_width - 130
        c.setStrokeColor(slate_muted)
        c.setLineWidth(0.8)
        c.line(right_col_x - 50, 105, right_col_x + 50, 105)
        c.setFillColor(slate_muted)
        c.setFont("Helvetica", 10)
        c.drawCentredString(right_col_x, 88, "Authorized Signatory")
        c.setFillColor(navy_dark)
        c.setFont("Helvetica-Oblique", 11)
        c.drawCentredString(right_col_x, 112, issuer_name)

        # 14. Bottom Verification Banner (Unique ID & Integrity)
        c.setFillColor(slate_muted)
        c.setFont("Courier", 9)
        verification_text = f"Certificate ID: {certificate_id}  |  Issued by {issuer_name}"
        c.drawCentredString(page_width / 2.0, 42, verification_text)

        # Save and verify
        c.showPage()
        c.save()

        # Post-generation assertion
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise RuntimeError(f"PDF generation failed: Output file '{file_path}' was not written.")

        logger.debug(
            "Successfully generated certificate PDF at %s (size: %d bytes)", file_path, file_path.stat().st_size
        )
        return file_path


# Global service instance
certificate_generator = CertificateGenerator()
