"""
Tests for Template & Signature Asset Management and Pillow Live Fetching
"""

import io
from pathlib import Path

import pypdf
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.core.config import settings
from app.services.certificate_service import certificate_generator


def create_dummy_signature_image() -> bytes:
    """Creates a mock pen-on-paper signature image."""
    img = Image.new("RGB", (300, 100), (245, 245, 240))  # Off-white paper background
    draw = ImageDraw.Draw(img)
    # Draw ink strokes in dark navy/black
    draw.line([(20, 50), (60, 20), (100, 70), (150, 30), (220, 60), (280, 40)], fill=(20, 30, 60), width=4)
    draw.text((80, 65), "J. Doe", fill=(20, 30, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_dummy_template_image() -> bytes:
    """Creates a mock certificate background template image."""
    img = Image.new("RGB", (842, 595), (250, 245, 235))
    draw = ImageDraw.Draw(img)
    # Draw a fancy banner
    draw.rectangle([10, 10, 832, 585], outline=(180, 140, 50), width=6)
    draw.rectangle([20, 20, 822, 575], outline=(30, 45, 80), width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_template_status_endpoint(client: TestClient):
    resp = client.get("/api/v1/templates/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "signature" in data
    assert "background" in data
    assert "active_template_mode" in data
    assert "sample_preview_url" in data


def test_signature_upload_pillow_processing_and_preview(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "SIGNATURES_DIR", tmp_path / "signatures")
    monkeypatch.setattr(settings, "SIGNATURE_IMAGE_PATH", tmp_path / "signature.png")

    sig_bytes = create_dummy_signature_image()
    files = {"file": ("my_signature.jpg", sig_bytes, "image/jpeg")}
    upload_resp = client.post("/api/v1/templates/signature", files=files)

    assert upload_resp.status_code == 200
    res = upload_resp.json()
    assert res["status"] == "success"
    assert "preview_url" in res
    assert "dimensions" in res

    # Check that processed signature is a transparent PNG
    processed_file = tmp_path / "signatures" / "processed_signature.png"
    assert processed_file.exists()
    with Image.open(processed_file) as proc_img:
        assert proc_img.mode == "RGBA"
        # Check that paper background was made transparent (alpha has 0 values)
        alpha = proc_img.split()[3]
        min_a, _ = alpha.getextrema()
        assert min_a == 0  # Paper was converted to transparent!

    # Test preview route
    prev_resp = client.get("/api/v1/templates/signature/preview")
    assert prev_resp.status_code == 200
    assert prev_resp.headers["content-type"] == "image/png"


def test_background_template_upload_and_preview(client: TestClient, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "BACKGROUNDS_DIR", tmp_path / "backgrounds")
    monkeypatch.setattr(settings, "BACKGROUND_TEMPLATE_PATH", tmp_path / "background.png")

    bg_bytes = create_dummy_template_image()
    files = {"file": ("certificate_art.png", bg_bytes, "image/png")}
    upload_resp = client.post("/api/v1/templates/background", files=files)

    assert upload_resp.status_code == 200
    res = upload_resp.json()
    assert res["status"] == "success"
    assert "preview_url" in res

    # Test preview route
    prev_resp = client.get("/api/v1/templates/background/preview")
    assert prev_resp.status_code == 200
    assert "image" in prev_resp.headers["content-type"]


def test_certificate_generation_with_custom_template(tmp_path: Path, monkeypatch):
    """Verifies that render_certificate uses custom background template and signature."""
    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir(parents=True)
    custom_bg = bg_dir / "custom_template.png"
    custom_bg.write_bytes(create_dummy_template_image())

    sig_dir = tmp_path / "signatures"
    sig_dir.mkdir(parents=True)
    raw_sig = sig_dir / "signature.jpg"
    raw_sig.write_bytes(create_dummy_signature_image())

    monkeypatch.setattr(settings, "BACKGROUNDS_DIR", bg_dir)
    monkeypatch.setattr(settings, "SIGNATURES_DIR", sig_dir)
    monkeypatch.setattr(settings, "SIGNATURE_IMAGE_PATH", tmp_path / "signature.png")
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "certs")

    generator = certificate_generator
    generator.output_dir = tmp_path / "certs"

    # Live fetch should find the custom template
    found_bg = generator.get_background_template_path()
    assert found_bg is not None
    assert found_bg.exists()

    pdf_path = generator.render_certificate(
        job_id="test_custom_template_job",
        certificate_id="CERT-CUSTOM-001",
        recipient_name="Grace Hopper",
        event_name="Compiler Architecture",
        issuer_name="ACM Institute",
        issue_date="2026-10-12",
    )
    assert pdf_path.exists()
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 1
    # Check that image XObject exists on the page
    page = reader.pages[0]
    assert len(page.images) > 0


def test_sample_preview_endpoint(client: TestClient):
    resp = client.get("/api/v1/templates/sample-preview")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 1000


def test_layout_config_get_and_update(client: TestClient):
    get_resp = client.get("/api/v1/templates/layout")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "render_title" in data
    assert "recipient_name_y" in data

    # Update config
    data["recipient_name_y"] = 340.0
    data["render_title"] = False
    put_resp = client.post("/api/v1/templates/layout", json=data)
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["recipient_name_y"] == 340.0
    assert updated["render_title"] is False


def test_apply_layout_preset(client: TestClient):
    resp = client.post("/api/v1/templates/layout/preset/preprinted")
    assert resp.status_code == 200
    preprinted = resp.json()
    assert preprinted["template_mode"] == "preprinted"
    assert preprinted["render_title"] is False
    assert preprinted["render_subtitle"] is False

    resp2 = client.post("/api/v1/templates/layout/preset/frame")
    assert resp2.status_code == 200
    frame = resp2.json()
    assert frame["template_mode"] == "frame"
    assert frame["render_title"] is True


def test_ai_analyze_layout_heuristic_fallback(client: TestClient):
    resp = client.post("/api/v1/templates/ai-analyze-layout", json={"api_key": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "layout" in data
    assert data["layout"]["template_mode"] == "preprinted"


def test_render_certificate_with_preprinted_mode_no_overlap(tmp_path: Path, monkeypatch):
    from app.schemas.template_config import TemplateLayoutConfig

    bg_dir = tmp_path / "backgrounds"
    bg_dir.mkdir(parents=True)
    custom_bg = bg_dir / "custom_template.png"
    custom_bg.write_bytes(create_dummy_template_image())

    monkeypatch.setattr(settings, "BACKGROUNDS_DIR", bg_dir)
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path / "certs")

    generator = certificate_generator
    generator.output_dir = tmp_path / "certs"

    # Preprinted config: suppress baked-in title and subtitle
    preprinted_config = TemplateLayoutConfig(
        template_mode="preprinted",
        render_title=False,
        render_subtitle=False,
        render_issuer=False,
        render_description=False,
        render_recipient_underline=False,
        recipient_name_y=335.0,
        event_y=255.0,
    )

    pdf_path = generator.render_certificate(
        job_id="test_no_overlap_job",
        certificate_id="CERT-NO-OVERLAP-001",
        recipient_name="Ada Lovelace",
        event_name="Foundations of Computer Science",
        issuer_name="Babbage Society",
        issue_date="2026-10-12",
        certificate_title="Certificate of Mastery",
        layout_config=preprinted_config,
    )

    assert pdf_path.exists()
    reader = pypdf.PdfReader(str(pdf_path))
    text = reader.pages[0].extract_text()

    # Verify recipient and event are rendered cleanly
    assert "Ada Lovelace" in text
    assert "Foundations of Computer Science" in text
    # Verify suppressed fields are NOT rendered into the PDF text stream
    assert "Certificate of Mastery" not in text
    assert "THIS IS PROUDLY PRESENTED TO" not in text
    assert "for successful completion" not in text
