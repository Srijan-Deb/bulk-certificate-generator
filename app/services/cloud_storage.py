"""
Cloud Storage Service (S3-Compatible)
Supports Cloudflare R2, Supabase Storage, AWS S3, and MinIO with zero egress cost.
Falls back to local file storage when cloud credentials are not supplied.
"""

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger("bulk_certificate_generator.storage")


class CloudStorageService:
    """Manages cloud storage operations for certificate files and ZIP archives."""

    def __init__(self):
        self._client: Any = None
        self._initialized = False

    @property
    def provider(self) -> str:
        return settings.STORAGE_PROVIDER.lower().strip()

    def is_configured(self) -> bool:
        """Returns True if a cloud provider is selected and credentials are present."""
        if self.provider == "local":
            return False
        return bool(settings.S3_ACCESS_KEY_ID and settings.S3_SECRET_ACCESS_KEY)

    def _get_client(self):
        if not self.is_configured():
            return None

        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                config = Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                )

                kwargs: dict[str, Any] = {
                    "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
                    "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
                    "config": config,
                }
                if settings.S3_ENDPOINT_URL:
                    kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
                if settings.S3_REGION_NAME:
                    kwargs["region_name"] = settings.S3_REGION_NAME

                self._client = boto3.client("s3", **kwargs)
                self._ensure_bucket_exists()
            except Exception as exc:
                logger.error("Failed to initialize S3 cloud client: %s", exc)
                return None

        return self._client

    def _ensure_bucket_exists(self) -> None:
        """Attempts to verify or create bucket if needed."""
        if not self._client:
            return
        try:
            self._client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        except Exception as exc:
            logger.debug("Bucket verification check: %s. Attempting creation...", exc)
            try:
                self._client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                logger.info("Created cloud storage bucket: %s", settings.S3_BUCKET_NAME)
            except Exception:
                # Creation may fail if already exists or permission lacks PutBucket; continue
                pass

    def upload_file(self, local_path: Path, remote_key: str, content_type: str = "application/pdf") -> str | None:
        """
        Uploads a local file to S3-compatible cloud storage.
        Returns the remote key or public URL if configured, or None on failure/local mode.
        """
        client = self._get_client()
        if not client or not local_path.exists():
            return None

        try:
            extra_args = {"ContentType": content_type}
            client.upload_file(
                Filename=str(local_path),
                Bucket=settings.S3_BUCKET_NAME,
                Key=remote_key,
                ExtraArgs=extra_args,
            )
            logger.info("Uploaded '%s' to cloud storage bucket '%s'", remote_key, settings.S3_BUCKET_NAME)

            if settings.S3_PUBLIC_URL_PREFIX:
                prefix = settings.S3_PUBLIC_URL_PREFIX.rstrip("/")
                return f"{prefix}/{remote_key}"
            return remote_key
        except Exception as exc:
            logger.error("Failed to upload '%s' to cloud storage: %s", remote_key, exc)
            return None

    def download_file(self, remote_key: str, local_destination: Path) -> Path | None:
        """Downloads a remote file from cloud storage to local disk."""
        client = self._get_client()
        if not client:
            return None

        try:
            local_destination.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(
                Bucket=settings.S3_BUCKET_NAME,
                Key=remote_key,
                Filename=str(local_destination),
            )
            return local_destination
        except Exception as exc:
            logger.error("Failed to download '%s' from cloud storage: %s", remote_key, exc)
            return None

    def get_file_bytes(self, remote_key: str) -> bytes | None:
        """Fetches object bytes directly from cloud storage."""
        client = self._get_client()
        if not client:
            return None

        try:
            resp = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=remote_key)
            return resp["Body"].read()
        except Exception as exc:
            logger.error("Failed to read object '%s' from cloud storage: %s", remote_key, exc)
            return None

    def generate_presigned_url(self, remote_key: str, expires_in: int = 3600) -> str | None:
        """Generates a secure presigned GET URL for cloud direct download."""
        client = self._get_client()
        if not client:
            return None

        try:
            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": settings.S3_BUCKET_NAME, "Key": remote_key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as exc:
            logger.error("Failed to generate presigned URL for '%s': %s", remote_key, exc)
            return None

    def check_health(self) -> dict[str, Any]:
        """Returns provider status and connectivity."""
        if not self.is_configured():
            return {
                "provider": "local",
                "configured": False,
                "status": "ready",
                "note": "Using local zero-cost storage directory. Configure Cloudflare R2 / Supabase in .env for cloud backup.",
            }

        client = self._get_client()
        if not client:
            return {
                "provider": self.provider,
                "configured": True,
                "status": "error",
                "note": "Cloud client initialization failed. Check credentials.",
            }

        try:
            client.list_objects_v2(Bucket=settings.S3_BUCKET_NAME, MaxKeys=1)
            return {
                "provider": self.provider,
                "configured": True,
                "status": "connected",
                "bucket": settings.S3_BUCKET_NAME,
                "note": f"Connected to {self.provider.upper()} cloud storage.",
            }
        except Exception as exc:
            return {
                "provider": self.provider,
                "configured": True,
                "status": "degraded",
                "error": str(exc),
            }


cloud_storage = CloudStorageService()
