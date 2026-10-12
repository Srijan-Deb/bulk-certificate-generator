"""
Certificate Generation Engine
Renders high-resolution, vector-quality PDF certificates using ReportLab.
Uses a predefined, elegant landscape template with decorative borders,
institutional seal graphic, and recipient metadata.

Features:
- Dynamic font auto-scaling for long recipient names and event titles.
- Cryptographic verification code generation.
- Post-generation PDF integrity verification via pypdf.
- Path sanitization and overwrite protection.
- Unicode character normalization.
"""

import hashlib
import logging
import unicodedata
import uuid
from pathlib import Path

import pypdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.schemas.template_config import TemplateLayoutConfig

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

    @staticmethod
    def generate_verification_code(job_id: str, certificate_id: str, recipient_name: str) -> str:
        """
        Generates a deterministic 16-character SHA-256 verification code
        binding the certificate to the job and recipient.
        """
        payload = f"{job_id}:{certificate_id}:{recipient_name}".encode("utf-8")
        raw_hash = hashlib.sha256(payload).hexdigest().upper()
        # Formatted as V-XXXX-XXXX-XXXX
        return f"V-{raw_hash[0:4]}-{raw_hash[4:8]}-{raw_hash[8:12]}"

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Normalizes unicode text to Latin-1/ASCII compatible representation
        while preserving standard accents to ensure safe PDF rendering.
        """
        if not text:
            return ""
        # Normalize unicode combining characters
        normalized = unicodedata.normalize("NFKC", text.strip())
        return "".join(c for c in normalized if ord(c) < 256)

    def get_certificate_path(self, job_id: str, certificate_id: str) -> Path:
        """Returns safe, deterministic destination path for certificate PDF."""
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        # Sanitize filename to alphanumeric and safe hyphens
        safe_cert_id = "".join(c for c in certificate_id if c.isalnum() or c in ("-", "_"))
        return job_dir / f"{safe_cert_id}.pdf"

    @staticmethod
    def process_raw_signature_image(source_path: Path, output_path: Path) -> Path | None:
        """
        Converts a raw photo/scan of a signature (JPEG/PNG) into a clean,
        background-free transparent PNG suitable for vector certificates.
        Handles EXIF rotation, vignette removal, alpha thresholding, and existing transparency.
        """
        try:
            from PIL import Image, ImageOps

            if not source_path.exists():
                return None

            raw_img = Image.open(source_path)
            # Correct orientation from camera EXIF tags
            oriented = ImageOps.exif_transpose(raw_img)

            # Check if image already has transparency (RGBA/LA/palette with alpha)
            if oriented.mode in ("RGBA", "LA") or (oriented.mode == "P" and "transparency" in oriented.info):
                rgba = oriented.convert("RGBA")
                alpha_channel = rgba.split()[3]
                min_alpha, _ = alpha_channel.getextrema()
                if min_alpha < 240:
                    bbox = rgba.getbbox()
                    if bbox:
                        pad = 10
                        final_sig = rgba.crop(
                            (
                                max(0, bbox[0] - pad),
                                max(0, bbox[1] - pad),
                                min(rgba.width, bbox[2] + pad),
                                min(rgba.height, bbox[3] + pad),
                            )
                        )
                    else:
                        final_sig = rgba
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    final_sig.save(output_path, format="PNG")
                    logger.info("Preserved and saved transparent signature to %s", output_path)
                    return output_path

            # Image is opaque photo or scan (pen on paper)
            gray = oriented.convert("L")

            # Crop margin vignette/shadows if image is large enough
            w, h = gray.size
            if w > 400 and h > 200:
                crop_box = (
                    int(w * 0.08),
                    int(h * 0.08),
                    int(w * 0.95),
                    int(h * 0.95),
                )
                gray = gray.crop(crop_box)

            # Build smooth alpha mask: ink (<65) -> 255, paper (>120) -> 0
            lut = []
            for g in range(256):
                if g >= 120:
                    lut.append(0)
                elif g <= 65:
                    lut.append(255)
                else:
                    t = (120 - g) / (120 - 65)
                    lut.append(int(255 * (t**1.2)))

            alpha = gray.point(lut, mode="L")
            # Deep midnight navy ink color matching certificate palette (#14213D / 20, 33, 61)
            color_img = Image.new("RGB", gray.size, (20, 33, 61))
            color_img.putalpha(alpha)

            bbox = color_img.getbbox()
            if bbox:
                pad = 10
                final_sig = color_img.crop(
                    (
                        max(0, bbox[0] - pad),
                        max(0, bbox[1] - pad),
                        min(color_img.width, bbox[2] + pad),
                        min(color_img.height, bbox[3] + pad),
                    )
                )
            else:
                final_sig = color_img

            output_path.parent.mkdir(parents=True, exist_ok=True)
            final_sig.save(output_path, format="PNG")
            logger.info("Successfully processed and saved transparent signature to %s", output_path)
            return output_path
        except Exception as exc:
            logger.warning("Failed to process signature image from %s: %s", source_path, exc)
            return None

    def get_signature_image_path(self) -> Path | None:
        """
        Locates the authorized signature graphic with dynamic live fetching.
        Prioritizes:
        1. settings.SIGNATURES_DIR (templates/signatures/):
           - Checks for newer raw images (.jpg, .jpeg, .png, .webp).
           - Auto-processes with Pillow into processed_signature.png if needed.
           - Returns processed_signature.png or the latest signature graphic.
        2. settings.SIGNATURE_IMAGE_PATH if it exists.
        3. Raw image files in workspace root or templates/ converted on the fly.
        """
        signatures_dir = settings.SIGNATURES_DIR
        processed_png = signatures_dir / "processed_signature.png"
        default_png = settings.SIGNATURE_IMAGE_PATH

        if signatures_dir.exists():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
            raw_candidates = [
                p
                for p in signatures_dir.iterdir()
                if p.is_file() and p.suffix.lower() in image_extensions and p.name != "processed_signature.png"
            ]

            if raw_candidates:
                latest_raw = max(raw_candidates, key=lambda p: p.stat().st_mtime)
                if not processed_png.exists() or latest_raw.stat().st_mtime > processed_png.stat().st_mtime:
                    processed = self.process_raw_signature_image(latest_raw, processed_png)
                    if processed and processed.exists():
                        try:
                            import shutil

                            shutil.copyfile(processed_png, default_png)
                        except Exception:
                            pass
                        return processed
                elif processed_png.exists():
                    return processed_png

            if processed_png.exists():
                return processed_png

        # Option 2: Configured default path already exists
        if default_png and default_png.exists():
            return default_png

        # Option 3: Search for raw signature images in workspace root
        candidate_names = [
            "IMG_20261011_230046.jpg.jpeg",
            "signature.jpg",
            "signature.png",
            "signature.jpeg",
        ]
        for name in candidate_names:
            candidate = Path(name)
            if candidate.exists():
                processed = self.process_raw_signature_image(candidate, processed_png)
                if processed and processed.exists():
                    try:
                        import shutil

                        shutil.copyfile(processed_png, default_png)
                    except Exception:
                        pass
                    return processed

        return None

    def get_background_template_path(self) -> Path | None:
        """
        Locates the custom certificate background template graphic with dynamic live fetching.
        Prioritizes:
        1. settings.BACKGROUNDS_DIR (templates/backgrounds/):
           - Scans for latest image file (.png, .jpg, .jpeg, .webp).
        2. settings.BACKGROUND_TEMPLATE_PATH (templates/background.png) if it exists.
        3. Common candidate filenames in templates/ (background.jpg, template.png, etc.).
        """
        backgrounds_dir = settings.BACKGROUNDS_DIR
        if backgrounds_dir.exists():
            image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
            candidates = [
                p
                for p in backgrounds_dir.iterdir()
                if p.is_file() and p.suffix.lower() in image_extensions and not p.name.lower().startswith("readme")
            ]
            if candidates:
                return max(candidates, key=lambda p: p.stat().st_mtime)

        default_bg = settings.BACKGROUND_TEMPLATE_PATH
        if default_bg and default_bg.exists():
            return default_bg

        for candidate_name in ["background.jpg", "background.jpeg", "template.png", "template.jpg"]:
            cand = settings.TEMPLATES_DIR / candidate_name
            if cand.exists():
                return cand

        return None

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
        verification_code: str | None = None,
        allow_overwrite: bool = True,
        background_path: Path | None = None,
        signature_path: Path | None = None,
        layout_config: TemplateLayoutConfig | None = None,
    ) -> Path:
        """
        Draws, verifies, and saves the PDF certificate.
        Supports dynamic layout configuration (AI Vision / Preset based) to prevent text collision
        on pre-printed background templates. Includes font scaling, verification code, and pypdf validation.
        Raises RuntimeError on generation failure.
        """
        file_path = self.get_certificate_path(job_id, certificate_id)

        # Overwrite protection check
        if file_path.exists() and not allow_overwrite:
            raise FileExistsError(f"Certificate file '{file_path}' already exists.")

        # Load active layout configuration if not explicitly provided
        if layout_config is None:
            from app.services.llm_template_analyzer import llm_template_analyzer

            layout_config = llm_template_analyzer.get_active_layout_config()

        # Sanitize input strings for PDF rendering
        clean_recipient = self.sanitize_text(recipient_name)
        clean_event = self.sanitize_text(event_name)
        clean_issuer = self.sanitize_text(issuer_name)
        clean_title = self.sanitize_text(certificate_title)
        clean_date = self.sanitize_text(issue_date)
        clean_remarks = self.sanitize_text(custom_remarks) if custom_remarks else None

        # Compute verification code if not provided
        v_code = verification_code or self.generate_verification_code(job_id, certificate_id, clean_recipient)

        # Canvas Dimensions: A4 Landscape is 841.89 x 595.27 points
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(str(file_path), pagesize=(page_width, page_height))
        c.setTitle(f"{clean_title} - {clean_recipient}")
        c.setAuthor(clean_issuer)
        c.setSubject(clean_event)

        # Curated Color Palette
        navy_dark = colors.HexColor("#0F172A")
        navy_light = colors.HexColor("#1E293B")
        gold_accent = colors.HexColor("#D97706")
        gold_light = colors.HexColor("#FBBF24")
        slate_muted = colors.HexColor("#475569")
        cream_bg = colors.HexColor("#FCFDFD")

        # Live Custom Background Template Check
        bg_template_path = background_path or self.get_background_template_path()
        has_custom_bg = bg_template_path is not None and bg_template_path.exists()

        if has_custom_bg:
            try:
                c.drawImage(
                    str(bg_template_path),
                    0,
                    0,
                    width=page_width,
                    height=page_height,
                    preserveAspectRatio=False,
                )
            except Exception as exc:
                logger.warning("Failed to draw background template from %s: %s", bg_template_path, exc)
                has_custom_bg = False

        margin = 28
        if not has_custom_bg:
            # 1. Background Fill (Executive Classic Cream)
            c.setFillColor(cream_bg)
            c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

            # 2. Decorative Outer Border (Navy)
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

        # 5. Header: Issuing Organization (Render only if enabled)
        if layout_config.render_issuer:
            c.setFillColor(gold_accent)
            c.setFont("Helvetica-Bold", 13)
            c.drawCentredString(page_width / 2.0, page_height - 75, clean_issuer.upper())

        # 6. Certificate Title (Render only if enabled)
        if layout_config.render_title:
            c.setFillColor(navy_dark)
            c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(page_width / 2.0, page_height - 118, clean_title.upper())

        # Title Accent Line (Render only if enabled)
        if layout_config.render_title_line:
            c.setStrokeColor(gold_accent)
            c.setLineWidth(2)
            accent_half_len = 80
            c.line(
                (page_width / 2.0) - accent_half_len,
                page_height - 128,
                (page_width / 2.0) + accent_half_len,
                page_height - 128,
            )

        # 7. Presentation Subtitle (Render only if enabled)
        if layout_config.render_subtitle:
            c.setFillColor(slate_muted)
            c.setFont("Helvetica", 12)
            c.drawCentredString(page_width / 2.0, page_height - 165, "THIS IS PROUDLY PRESENTED TO")

        # 8. Recipient Name with Dynamic Auto-Scaling & Collision-Free Coordinate Positioning
        max_name_width = page_width - (2 * (margin + 60))
        name_font_size = layout_config.recipient_name_font_size
        font_name = "Helvetica-Bold"
        while c.stringWidth(clean_recipient, font_name, name_font_size) > max_name_width and name_font_size > 14:
            name_font_size -= 2

        try:
            name_color = colors.HexColor(layout_config.recipient_name_color)
        except Exception:
            name_color = navy_dark

        c.setFillColor(name_color)
        c.setFont(font_name, name_font_size)
        c.drawCentredString(page_width / 2.0, layout_config.recipient_name_y, clean_recipient)

        # Underline for Recipient Name (Render only if enabled)
        if layout_config.render_recipient_underline:
            c.setStrokeColor(gold_light)
            c.setLineWidth(1)
            name_line_half_len = min(
                220, max(120, int(c.stringWidth(clean_recipient, font_name, name_font_size) / 2) + 20)
            )
            c.line(
                (page_width / 2.0) - name_line_half_len,
                layout_config.recipient_name_y - 10,
                (page_width / 2.0) + name_line_half_len,
                layout_config.recipient_name_y - 10,
            )

        # 9. Context Description (Render only if enabled)
        if layout_config.render_description:
            c.setFillColor(slate_muted)
            c.setFont("Helvetica", 12)
            c.drawCentredString(
                page_width / 2.0, page_height - 260, "for successful completion and mastery of the curriculum in"
            )

        # 10. Event / Course Name with Dynamic Auto-Scaling (Render only if enabled)
        if layout_config.render_event:
            max_event_width = page_width - (2 * (margin + 50))
            event_font_size = layout_config.event_font_size
            while (
                c.stringWidth(clean_event, "Helvetica-Bold", event_font_size) > max_event_width and event_font_size > 11
            ):
                event_font_size -= 1

            try:
                ev_color = colors.HexColor(layout_config.event_color)
            except Exception:
                ev_color = navy_light

            c.setFillColor(ev_color)
            c.setFont("Helvetica-Bold", event_font_size)
            c.drawCentredString(page_width / 2.0, layout_config.event_y, clean_event)

        # Optional Custom Remarks / Honors (Render only if enabled)
        if clean_remarks and layout_config.render_remarks:
            c.setFillColor(gold_accent)
            c.setFont("Helvetica-Oblique", 11)
            c.drawCentredString(page_width / 2.0, layout_config.event_y - 25, f"— {clean_remarks} —")

        # 11. Official Seal / Badge Graphic (Render only if enabled)
        if layout_config.render_seal and not has_custom_bg:
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

        # 12. Date of Issuance
        if layout_config.render_date:
            date_x = layout_config.date_x
            date_y = layout_config.date_y
            if not has_custom_bg or layout_config.render_signatory_line:
                c.setStrokeColor(slate_muted)
                c.setLineWidth(0.8)
                c.line(date_x - 50, date_y - 7, date_x + 50, date_y - 7)
                c.setFillColor(slate_muted)
                c.setFont("Helvetica", 10)
                c.drawCentredString(date_x, date_y - 24, "Date of Issuance")

            c.setFillColor(navy_dark)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(date_x, date_y, clean_date)

        # 13. Authorized Signatory / Signature Graphic
        if layout_config.render_signature:
            sig_x_center = layout_config.signature_x
            sig_y_center = layout_config.signature_y

            if not has_custom_bg or layout_config.render_signatory_line:
                c.setStrokeColor(slate_muted)
                c.setLineWidth(0.8)
                c.line(sig_x_center - 60, sig_y_center - 10, sig_x_center + 60, sig_y_center - 10)

            if not has_custom_bg or layout_config.render_signatory_title:
                c.setFillColor(slate_muted)
                c.setFont("Helvetica", 10)
                c.drawCentredString(sig_x_center, sig_y_center - 27, "Authorized Signatory")

            sig_path = signature_path or self.get_signature_image_path()
            sig_drawn = False
            if sig_path and sig_path.exists():
                try:
                    sig_w = layout_config.signature_width
                    sig_h = layout_config.signature_height
                    c.drawImage(
                        str(sig_path),
                        sig_x_center - (sig_w / 2.0),
                        sig_y_center - (sig_h / 2.0),
                        width=sig_w,
                        height=sig_h,
                        mask="auto",
                        preserveAspectRatio=True,
                    )
                    sig_drawn = True
                    if not has_custom_bg or layout_config.render_signatory_title:
                        c.setFillColor(navy_dark)
                        c.setFont("Helvetica", 8)
                        c.drawCentredString(sig_x_center, sig_y_center - 40, clean_issuer)
                except Exception as exc:
                    logger.warning("Failed to draw signature image from %s: %s", sig_path, exc)

            if not sig_drawn and (not has_custom_bg or layout_config.render_signatory_title):
                c.setFillColor(navy_dark)
                c.setFont("Helvetica-Oblique", 11)
                c.drawCentredString(sig_x_center, sig_y_center, clean_issuer)

        # 14. Bottom Verification Banner (Unique ID & Cryptographic Verification Code)
        if layout_config.render_verification_code:
            c.setFillColor(slate_muted)
            c.setFont("Courier", 8.5)
            verification_text = (
                f"Certificate ID: {certificate_id}  |  Verification Code: {v_code}  |  Issuer: {clean_issuer}"
            )
            c.drawCentredString(page_width / 2.0, layout_config.verification_code_y, verification_text)

        # Commit Canvas
        c.showPage()
        c.save()

        # Step 15: Post-generation Verification (File size & Opening Validation)
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise RuntimeError(f"PDF generation failed: Output file '{file_path}' was not written.")

        # Validate that the generated PDF can be successfully opened and parsed
        try:
            reader = pypdf.PdfReader(str(file_path))
            if len(reader.pages) < 1:
                raise ValueError("Generated PDF has 0 readable pages.")
        except Exception as exc:
            if file_path.exists():
                file_path.unlink()
            raise RuntimeError(f"PDF validation failed: Generated file is corrupted ({exc})") from exc

        logger.debug(
            "Successfully generated and verified certificate PDF at %s (size: %d bytes)",
            file_path,
            file_path.stat().st_size,
        )
        return file_path


# Global service instance
certificate_generator = CertificateGenerator()
