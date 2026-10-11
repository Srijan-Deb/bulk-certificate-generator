"""
Domain Exceptions and Error Definitions
Provides standardized error objects that translate smoothly into clean HTTP responses.
"""

from typing import Any


class AppError(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 400, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class JobNotFoundError(AppError):
    def __init__(self, job_id: str):
        super().__init__(message=f"Generation job '{job_id}' was not found.", status_code=404)


class CertificateNotFoundError(AppError):
    def __init__(self, certificate_id: str):
        super().__init__(message=f"Certificate '{certificate_id}' was not found.", status_code=404)


class BatchSizeExceededError(AppError):
    def __init__(self, actual_size: int, max_size: int):
        super().__init__(
            message=f"Batch recipient size of {actual_size} exceeds configured maximum limit of {max_size}.",
            status_code=422,
            details={"actual_size": actual_size, "max_size": max_size},
        )


class StorageAccessError(AppError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=500)


class SecurityViolationError(AppError):
    def __init__(self, message: str = "Invalid file path or access request"):
        super().__init__(message=message, status_code=403)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Invalid or missing API key."):
        super().__init__(message=message, status_code=401)


class InvalidFileFormatError(AppError):
    def __init__(
        self,
        message: str = "Unsupported file format. Please upload an Excel (.xlsx) or CSV (.csv) file.",
    ):
        super().__init__(message=message, status_code=400)


class SpreadsheetParsingError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=422, details=details)
