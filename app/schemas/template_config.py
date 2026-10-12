"""
Template Layout Configuration Schema
Defines field toggles, coordinate placements, and typography settings
for custom certificate background templates (e.g. Canva, Figma, blank frames).
"""

from typing import Literal

from pydantic import BaseModel, Field


class TemplateLayoutConfig(BaseModel):
    template_mode: Literal["preprinted", "frame", "custom"] = Field(
        default="preprinted",
        description="preprinted: Canva/Figma with baked-in text; frame: blank border only; custom: custom coordinates",
    )

    # Component Visibility Toggles
    render_issuer: bool = Field(default=False, description="Render organization / issuer header text")
    render_title: bool = Field(default=False, description="Render certificate title (e.g. Certificate of Completion)")
    render_title_line: bool = Field(default=False, description="Render title underline accent line")
    render_subtitle: bool = Field(default=False, description="Render presentation subtitle (e.g. Proudly presented to)")
    render_description: bool = Field(default=False, description="Render default description paragraph")
    render_event: bool = Field(default=True, description="Render course / event name")
    render_remarks: bool = Field(default=False, description="Render custom remarks / honors")
    render_seal: bool = Field(default=False, description="Render vector seal medallion")
    render_recipient_underline: bool = Field(default=False, description="Draw line underneath recipient name")
    render_date: bool = Field(default=True, description="Render issuance date")
    render_signature: bool = Field(default=True, description="Render transparent signature image")
    render_signatory_line: bool = Field(default=False, description="Draw line above signatory")
    render_signatory_title: bool = Field(default=False, description="Draw 'Authorized Signatory' label")
    render_verification_code: bool = Field(
        default=True, description="Render Certificate ID & verification code audit footer"
    )

    # Coordinate Placement (Points in A4 Landscape: 841.89 pt width x 595.27 pt height, origin bottom-left)
    recipient_name_y: float = Field(default=335.0, description="Center Y coordinate for recipient name")
    recipient_name_font_size: int = Field(default=30, ge=12, le=52, description="Base font size for recipient name")
    recipient_name_color: str = Field(default="#0F172A", description="Hex color for recipient name")

    event_y: float = Field(default=255.0, description="Center Y coordinate for course / event name")
    event_font_size: int = Field(default=15, ge=10, le=32, description="Font size for event name")
    event_color: str = Field(default="#1E293B", description="Hex color for event name")

    date_x: float = Field(default=160.0, description="Center X coordinate for date")
    date_y: float = Field(default=115.0, description="Center Y coordinate for date")

    signature_x: float = Field(default=680.0, description="Center X coordinate for signature")
    signature_y: float = Field(default=135.0, description="Bottom Y coordinate for signature")
    signature_width: float = Field(default=115.0, ge=40, le=300, description="Width of signature image")
    signature_height: float = Field(default=52.0, ge=20, le=150, description="Height of signature image")

    verification_code_y: float = Field(default=28.0, description="Y coordinate for bottom verification text")
