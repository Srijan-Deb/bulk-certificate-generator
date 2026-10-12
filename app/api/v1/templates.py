"""
Template & Signature Asset Management Endpoints
Provides live fetching, upload, preview, and reset for custom certificate
background templates and authorized signatures processed via Pillow.
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.template_config import TemplateLayoutConfig
from app.services.certificate_service import certificate_generator
from app.services.llm_template_analyzer import llm_template_analyzer

router = APIRouter(prefix="/templates", tags=["Templates & Assets"])

ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


class AIAnalyzeRequest(BaseModel):
    api_key: str | None = Field(default=None, description="Optional Google Gemini API key")


def _get_file_info(path: Path | None) -> dict:
    if not path or not path.exists():
        return {
            "exists": False,
            "filename": None,
            "preview_url": None,
            "updated_at": None,
            "size_bytes": 0,
        }
    stat = path.stat()
    dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return {
        "exists": True,
        "filename": path.name,
        "preview_url": None,  # Will be filled by caller with route URL
        "updated_at": dt,
        "size_bytes": stat.st_size,
    }


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get Active Template and Signature Status",
    description="Returns live metadata on the currently active certificate background template and Pillow-processed signature.",
)
def get_template_assets_status():
    sig_path = certificate_generator.get_signature_image_path()
    bg_path = certificate_generator.get_background_template_path()

    sig_info = _get_file_info(sig_path)
    if sig_info["exists"]:
        sig_info["preview_url"] = "/api/v1/templates/signature/preview"

    bg_info = _get_file_info(bg_path)
    if bg_info["exists"]:
        bg_info["preview_url"] = "/api/v1/templates/background/preview"

    return {
        "signature": sig_info,
        "background": bg_info,
        "active_template_mode": "custom" if bg_info["exists"] else "executive_classic",
        "sample_preview_url": "/api/v1/templates/sample-preview",
        "layout": llm_template_analyzer.get_active_layout_config(),
    }


@router.post(
    "/signature",
    status_code=status.HTTP_200_OK,
    summary="Upload and Live-Process Signatory Signature with Pillow",
    description="Uploads a signature photo/scan (JPG/PNG). Pillow live-removes the paper background, leaves clean transparent ink, and stores it in templates/signatures/.",
)
async def upload_signature(
    file: UploadFile = File(..., description="Signature image (JPG, PNG, WEBP)"),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: PNG, JPG, JPEG, WEBP.",
        )

    settings.SIGNATURES_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = settings.SIGNATURES_DIR / f"raw_signature{ext}"
    processed_path = settings.SIGNATURES_DIR / "processed_signature.png"

    # Save uploaded file
    try:
        content = await file.read()
        raw_path.write_bytes(content)
        # Validate that Pillow can open it
        with Image.open(raw_path) as img:
            img.verify()
    except Exception as exc:
        if raw_path.exists():
            raw_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted image file: {exc}",
        ) from exc

    # Run Pillow live-processing to generate clean transparent vector PNG
    processed = certificate_generator.process_raw_signature_image(raw_path, processed_path)
    if not processed or not processed.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pillow failed to process signature transparency.",
        )

    # Sync to default signature path as well
    try:
        shutil.copyfile(processed_path, settings.SIGNATURE_IMAGE_PATH)
    except Exception:
        pass

    with Image.open(processed_path) as img:
        width, height = img.size

    return {
        "status": "success",
        "message": "Signature uploaded and processed to transparent PNG successfully via Pillow.",
        "preview_url": "/api/v1/templates/signature/preview",
        "dimensions": {"width": width, "height": height},
        "filename": "processed_signature.png",
    }


@router.delete(
    "/signature",
    status_code=status.HTTP_200_OK,
    summary="Reset Signature to Text Fallback",
    description="Removes custom uploaded signature graphic and resets to issuer text line.",
)
def reset_signature():
    # Remove files from templates/signatures/
    if settings.SIGNATURES_DIR.exists():
        for p in settings.SIGNATURES_DIR.iterdir():
            if p.is_file() and not p.name.lower().startswith("readme"):
                try:
                    p.unlink()
                except Exception:
                    pass

    # Remove default signature.png if it exists
    if settings.SIGNATURE_IMAGE_PATH.exists():
        try:
            settings.SIGNATURE_IMAGE_PATH.unlink()
        except Exception:
            pass

    return {
        "status": "success",
        "message": "Custom signature removed. Certificates will use authorized text fallback.",
    }


@router.get(
    "/signature/preview",
    status_code=status.HTTP_200_OK,
    summary="Preview Active Clean Transparent Signature",
    description="Streams the Pillow-processed transparent signature PNG graphic.",
)
def preview_signature():
    sig_path = certificate_generator.get_signature_image_path()
    if not sig_path or not sig_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No signature graphic found.")

    return FileResponse(
        path=str(sig_path),
        media_type="image/png",
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


@router.post(
    "/background",
    status_code=status.HTTP_200_OK,
    summary="Upload Custom Certificate Background Template",
    description="Uploads a custom certificate template graphic (from Canva, Figma, etc.). Live-fetches for all subsequent certificate rendering.",
)
async def upload_background_template(
    file: UploadFile = File(..., description="Certificate background image (PNG, JPG, WEBP)"),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: PNG, JPG, JPEG, WEBP.",
        )

    settings.BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    bg_target = settings.BACKGROUNDS_DIR / f"custom_template{ext}"

    try:
        content = await file.read()
        bg_target.write_bytes(content)
        with Image.open(bg_target) as img:
            img.verify()
    except Exception as exc:
        if bg_target.exists():
            bg_target.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted image file: {exc}",
        ) from exc

    # Sync to default background path
    try:
        shutil.copyfile(bg_target, settings.BACKGROUND_TEMPLATE_PATH)
    except Exception:
        pass

    with Image.open(bg_target) as img:
        width, height = img.size

    return {
        "status": "success",
        "message": "Custom certificate background template uploaded and live-activated successfully.",
        "preview_url": "/api/v1/templates/background/preview",
        "dimensions": {"width": width, "height": height},
        "filename": bg_target.name,
    }


@router.delete(
    "/background",
    status_code=status.HTTP_200_OK,
    summary="Reset Certificate Background Template to Executive Classic",
    description="Clears custom template graphic and reverts to the built-in Executive Classic vector design.",
)
def reset_background_template():
    if settings.BACKGROUNDS_DIR.exists():
        for p in settings.BACKGROUNDS_DIR.iterdir():
            if p.is_file() and not p.name.lower().startswith("readme"):
                try:
                    p.unlink()
                except Exception:
                    pass

    if settings.BACKGROUND_TEMPLATE_PATH.exists():
        try:
            settings.BACKGROUND_TEMPLATE_PATH.unlink()
        except Exception:
            pass

    # Reset layout configuration to frame default
    llm_template_analyzer.save_layout_config(llm_template_analyzer.get_preset("frame"))

    return {
        "status": "success",
        "message": "Custom template removed. System reverted to Executive Classic vector template.",
    }


@router.get(
    "/background/preview",
    status_code=status.HTTP_200_OK,
    summary="Preview Active Certificate Background Template",
    description="Streams the currently active custom background template image.",
)
def preview_background_template():
    bg_path = certificate_generator.get_background_template_path()
    if not bg_path or not bg_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No custom template graphic found.")

    media_type = "image/png" if bg_path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(
        path=str(bg_path),
        media_type=media_type,
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


@router.get(
    "/sample-preview",
    status_code=status.HTTP_200_OK,
    summary="Generate Instant Live Sample Certificate Preview",
    description="Generates a live sample PDF using the active template and signature to let users preview their changes instantly.",
)
def sample_preview_certificate():
    preview_job_id = "sample_preview"
    sample_cert_id = "CERT-SAMPLE-PREVIEW-001"

    pdf_path = certificate_generator.render_certificate(
        job_id=preview_job_id,
        certificate_id=sample_cert_id,
        recipient_name="Dr. Alexander Montgomery",
        event_name="Executive Leadership & AI Innovation",
        issuer_name="Global Certification Institute",
        issue_date=datetime.now(timezone.utc).strftime("%B %d, %Y"),
        certificate_title="Certificate of Mastery",
        custom_remarks="Graduated with Highest Honors",
        verification_code="V-DEMO-SAMPLE-2026",
        allow_overwrite=True,
    )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="sample_certificate.pdf"'},
    )


@router.get(
    "/layout",
    response_model=TemplateLayoutConfig,
    summary="Get Active Template Layout Configuration",
    description="Returns current component toggles and coordinates for certificate rendering.",
)
def get_layout_config():
    return llm_template_analyzer.get_active_layout_config()


@router.post(
    "/layout",
    response_model=TemplateLayoutConfig,
    summary="Update Template Layout Configuration",
    description="Updates and persists component toggles and coordinates.",
)
def update_layout_config(config: TemplateLayoutConfig):
    return llm_template_analyzer.save_layout_config(config)


@router.post(
    "/layout/preset/{preset_name}",
    response_model=TemplateLayoutConfig,
    summary="Apply Battle-Tested Template Layout Preset",
    description="Applies preset layout: 'preprinted' (for Canva/Figma certificates with baked-in text) or 'frame' (blank borders).",
)
def apply_preset(preset_name: str):
    if preset_name not in ("preprinted", "frame"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid preset '{preset_name}'. Allowed: 'preprinted', 'frame'.",
        )
    preset = llm_template_analyzer.get_preset(preset_name)  # type: ignore
    return llm_template_analyzer.save_layout_config(preset)


@router.post(
    "/ai-analyze-layout",
    summary="Analyze Template Layout with Google Gemini Vision",
    description="Uses Multimodal LLM to analyze the background template, detect baked-in text, and generate optimal collision-free coordinates.",
)
async def ai_analyze_layout(req: AIAnalyzeRequest | None = None):
    bg_path = certificate_generator.get_background_template_path()
    if not bg_path or not bg_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom certificate template uploaded yet. Please upload a template image first.",
        )

    api_key = req.api_key if req else None
    config, message = await llm_template_analyzer.analyze_template_with_gemini(bg_path, api_key=api_key)
    return {
        "status": "success",
        "message": message,
        "layout": config,
    }
