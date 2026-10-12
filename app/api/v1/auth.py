"""
Authentication API Endpoints
Handles Google OAuth 2.0 verification, JWT session tokens, and user profiles.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.errors import AuthenticationError
from app.core.security import create_access_token, verify_google_credential
from app.models.user import User
from app.schemas.auth import AuthResponse, GoogleAuthRequest, UserProfileResponse
from app.services.cloud_storage import cloud_storage

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/config",
    summary="Get Authentication & Storage Configuration",
    description="Returns public authentication configuration (Google Client ID) and active storage provider.",
)
def get_auth_config():
    return {
        "google_client_id": settings.GOOGLE_CLIENT_ID,
        "storage_provider": settings.STORAGE_PROVIDER,
        "cloud_storage_configured": cloud_storage.is_configured(),
        "cloud_storage_provider": cloud_storage.provider,
    }


@router.post(
    "/google",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign in or Register with Google OAuth 2.0",
    description=(
        "Exchanges a Google ID Token or initiates a dev session, verifies token with Google, "
        "persists the user profile, and returns a signed session JWT token."
    ),
)
async def google_auth(
    request: GoogleAuthRequest,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    if request.credential:
        # Verify genuine Google OAuth credential
        google_info = await verify_google_credential(request.credential)
        email = google_info["email"]
        google_id = google_info["google_id"]
        full_name = google_info["name"]
        avatar_url = google_info["avatar_url"]
    elif request.demo or not settings.GOOGLE_CLIENT_ID:
        # Dev / Demo sign-in hook for immediate local onboarding without GCP console setup
        email = (request.email or "developer@certflow.io").lower().strip()
        google_id = f"demo_{email}"
        full_name = request.name or "Demo Developer"
        avatar_url = request.avatar_url or "https://lh3.googleusercontent.com/a/default-user"
    else:
        raise AuthenticationError("Missing Google OAuth credential.")

    # Upsert user record
    stmt = select(User).where((User.email == email) | (User.google_id == google_id))
    user = db.execute(stmt).scalar_one_or_none()

    if user:
        user.google_id = google_id
        user.full_name = full_name
        if avatar_url:
            user.avatar_url = avatar_url
        user.last_login_at = now
    else:
        user = User(
            email=email,
            google_id=google_id,
            full_name=full_name,
            avatar_url=avatar_url,
            created_at=now,
            last_login_at=now,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    token = create_access_token(
        subject=user.id,
        email=user.email,
        name=user.full_name,
        avatar_url=user.avatar_url,
    )

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfileResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile of the currently signed-in user.",
)
def get_me(user: User = Depends(get_current_user)):
    return UserProfileResponse.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Sign Out",
    description="Terminates current session.",
)
def logout():
    return {"status": "ok", "message": "Signed out successfully."}
