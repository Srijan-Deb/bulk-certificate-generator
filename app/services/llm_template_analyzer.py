"""
LLM Template Layout Analyzer
Integrates with Google Gemini Vision APIs (gemini-2.5-flash / gemini-1.5-flash)
to analyze custom certificate templates, detect baked-in text, and automatically
generate optimal field coordinates and visibility toggles to eliminate overlaps.
Includes smart zero-key heuristic presets.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Literal

import httpx

from app.core.config import settings
from app.schemas.template_config import TemplateLayoutConfig

logger = logging.getLogger("bulk_certificate_generator.llm")


class LLMTemplateAnalyzer:
    """Analyzes certificate templates via Gemini Vision or intelligent layout presets."""

    def get_preset(self, preset_name: Literal["preprinted", "frame", "custom"] = "preprinted") -> TemplateLayoutConfig:
        """Returns standard battle-tested presets for common certificate templates."""
        if preset_name == "preprinted":
            # Optimized for Canva/Figma certificates with baked-in title, subtitle, and ribbon
            return TemplateLayoutConfig(
                template_mode="preprinted",
                render_issuer=False,
                render_title=False,
                render_title_line=False,
                render_subtitle=False,
                render_description=False,
                render_event=True,
                render_remarks=False,
                render_seal=False,
                render_recipient_underline=False,
                render_date=True,
                render_signature=True,
                render_signatory_line=False,
                render_signatory_title=False,
                render_verification_code=True,
                recipient_name_y=335.0,
                recipient_name_font_size=30,
                recipient_name_color="#0F172A",
                event_y=255.0,
                event_font_size=15,
                event_color="#1E293B",
                date_x=160.0,
                date_y=115.0,
                signature_x=680.0,
                signature_y=135.0,
                signature_width=115.0,
                signature_height=52.0,
                verification_code_y=28.0,
            )
        elif preset_name == "frame":
            # For blank border frames where all titles and labels must be rendered by code
            return TemplateLayoutConfig(
                template_mode="frame",
                render_issuer=True,
                render_title=True,
                render_title_line=True,
                render_subtitle=True,
                render_description=True,
                render_event=True,
                render_remarks=True,
                render_seal=True,
                render_recipient_underline=True,
                render_date=True,
                render_signature=True,
                render_signatory_line=True,
                render_signatory_title=True,
                render_verification_code=True,
                recipient_name_y=380.0,
                recipient_name_font_size=30,
                recipient_name_color="#0F172A",
                event_y=300.0,
                event_font_size=18,
                event_color="#1E293B",
                date_x=130.0,
                date_y=112.0,
                signature_x=711.0,
                signature_y=104.0,
                signature_width=115.0,
                signature_height=52.0,
                verification_code_y=42.0,
            )
        return TemplateLayoutConfig()

    def get_active_layout_config(self) -> TemplateLayoutConfig:
        """Loads the active saved layout configuration or defaults based on active background."""
        config_path = settings.TEMPLATE_CONFIG_PATH
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                return TemplateLayoutConfig.model_validate(data)
            except Exception as exc:
                logger.warning("Failed to parse %s, reverting to preset: %s", config_path, exc)

        # Default fallback: if custom template background exists, default to preprinted
        bg_dir = settings.BACKGROUNDS_DIR
        has_custom_bg = False
        if bg_dir.exists():
            has_custom_bg = any(p.is_file() and not p.name.lower().startswith("readme") for p in bg_dir.iterdir())
        if not has_custom_bg and settings.BACKGROUND_TEMPLATE_PATH.exists():
            has_custom_bg = True

        preset = self.get_preset("preprinted" if has_custom_bg else "frame")
        self.save_layout_config(preset)
        return preset

    def save_layout_config(self, config: TemplateLayoutConfig) -> TemplateLayoutConfig:
        """Persists the layout configuration to disk for immediate live preview and batch rendering."""
        config_path = settings.TEMPLATE_CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved certificate layout configuration to %s", config_path)
        return config

    async def analyze_template_with_gemini(
        self,
        image_path: Path,
        api_key: str | None = None,
    ) -> tuple[TemplateLayoutConfig, str]:
        """
        Sends the certificate background template to Google Gemini Vision.
        Analyzes pre-printed elements and calculates collision-free coordinates.
        Falls back smoothly to pre-printed preset if no key or on API error.
        """
        active_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")

        if not active_key or not active_key.strip():
            logger.info("No Gemini API key supplied. Applying intelligent Canva pre-printed layout preset.")
            preset = self.get_preset("preprinted")
            self.save_layout_config(preset)
            return (
                preset,
                "Auto-applied Pre-printed Canva Preset (No Gemini API key provided. Overlap eliminated!).",
            )

        if not image_path.exists():
            raise FileNotFoundError(f"Template image not found at {image_path}")

        # Read and base64-encode template image
        img_bytes = image_path.read_bytes()
        b64_img = base64.b64encode(img_bytes).decode("utf-8")
        mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

        prompt = (
            "You are an expert certificate layout engine. "
            "Examine this certificate background template image. "
            "The standard printable canvas is A4 Landscape with dimensions: "
            "width = 841.89 points, height = 595.27 points (origin 0,0 is at the bottom-left corner; "
            "Y increases UPWARDS towards 595.27 pt, X increases RIGHTWARDS towards 841.89 pt). "
            "\n"
            "Analyze which texts or design elements are ALREADY printed/baked into this background image:\n"
            "- Does it already have a title like 'Certificate of Appreciation' or 'Certificate of Achievement'? If yes, render_title: false, render_title_line: false\n"
            "- Does it already have a presentation subtitle like 'This is proudly presented to'? If yes, render_subtitle: false\n"
            "- Does it already have an organization/issuer header or logo? If yes, render_issuer: false\n"
            "- Does it already have context description text? If yes, render_description: false\n"
            "- Does it already have a gold medal or seal badge? If yes, render_seal: false\n"
            "- Does it have pre-printed signatory labels? If yes, render_signatory_line: false, render_signatory_title: false\n"
            "\n"
            "Calculate optimal coordinates (in points, origin bottom-left):\n"
            "- recipient_name_y: Y center where the recipient name belongs (typically 320 to 360 pt)\n"
            "- recipient_name_font_size: recommended integer font size (24 to 36)\n"
            "- recipient_name_color: recommended hex color code (e.g. #0F172A)\n"
            "- event_y: Y center where the event/course title belongs (typically 230 to 270 pt)\n"
            "- event_font_size: recommended integer font size (14 to 18)\n"
            "- event_color: recommended hex color code (e.g. #1E293B)\n"
            "- date_x, date_y: center coordinates for issuance date (typically X: 120-180 pt, Y: 90-130 pt)\n"
            "- signature_x, signature_y: coordinates for signature image (typically X: 640-720 pt, Y: 110-145 pt)\n"
            "- verification_code_y: Y coordinate for bottom audit code (typically 24 to 35 pt)\n"
            "\n"
            "Return ONLY a valid JSON object matching these schema fields: "
            "template_mode, render_issuer, render_title, render_title_line, render_subtitle, "
            "render_description, render_event, render_remarks, render_seal, render_recipient_underline, "
            "render_date, render_signature, render_signatory_line, render_signatory_title, "
            "render_verification_code, recipient_name_y, recipient_name_font_size, recipient_name_color, "
            "event_y, event_font_size, event_color, date_x, date_y, signature_x, signature_y, "
            "signature_width, signature_height, verification_code_y."
        )

        models = ["gemini-2.5-flash", "gemini-1.5-flash"]
        last_error = None

        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={active_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"inlineData": {"mimeType": mime_type, "data": b64_img}},
                            {"text": prompt},
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            }

            try:
                async with httpx.AsyncClient(timeout=35.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        candidates = res_json.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                parsed_dict = json.loads(parts[0]["text"])
                                parsed_dict["template_mode"] = "preprinted"
                                config = TemplateLayoutConfig.model_validate(parsed_dict)
                                self.save_layout_config(config)
                                logger.info("Successfully analyzed template using %s", model)
                                return (config, f"AI layout successfully detected and applied using {model}.")
                    else:
                        last_error = f"{model} returned HTTP {resp.status_code}: {resp.text}"
                        logger.warning(last_error)
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Error calling %s: %s", model, exc)

        logger.warning("Gemini Vision API call failed (%s). Falling back to preprinted preset.", last_error)
        preset = self.get_preset("preprinted")
        self.save_layout_config(preset)
        return (
            preset,
            f"Pre-printed layout applied successfully (AI fallback: {last_error or 'Network error'}).",
        )


llm_template_analyzer = LLMTemplateAnalyzer()
