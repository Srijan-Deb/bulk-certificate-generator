"""
Authentication Pydantic Schemas
Defines request and response schemas for Google OAuth 2.0 and session management.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GoogleAuthRequest(BaseModel):
    """Payload sent by frontend after completing Google OAuth 2.0."""

    credential: str | None = Field(default=None, description="Google OAuth ID Token / Credential")
    demo: bool = Field(
        default=False, description="Enable instant dev sign-in when Google Client ID is not yet configured"
    )
    email: EmailStr | None = Field(default=None, description="Email for dev/demo mode")
    name: str | None = Field(default=None, description="Display name for dev/demo mode")
    avatar_url: str | None = Field(default=None, description="Avatar image URL for dev/demo mode")


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    avatar_url: str | None = None
    created_at: datetime
    last_login_at: datetime | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
