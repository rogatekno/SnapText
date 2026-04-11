"""Custom exceptions for SnapText application.

This module defines application-specific exceptions for better error handling
and meaningful error responses to API clients.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings


class SnapTextException(Exception):
    """Base exception for all SnapText errors."""

    def __init__(
        self,
        message: str,
        code: str = "ROGA_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize base exception.

        Args:
            message: Human-readable error message
            code: Error code for programmatic handling
            details: Additional error context
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SnapTextException):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize validation error.

        Args:
            message: Validation error message
            details: Specific validation failures
        """
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
        )


class FileProcessingError(SnapTextException):
    """Raised when file processing fails."""

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize file processing error.

        Args:
            message: Error message
            filename: Name of the file that failed
            details: Additional context
        """
        details = details or {}
        if filename:
            details["filename"] = filename
        super().__init__(
            message=message,
            code="FILE_PROCESSING_ERROR",
            details=details,
        )


class OCRError(SnapTextException):
    """Raised when OCR processing fails."""

    def __init__(
        self,
        message: str,
        ocr_engine: str = "RapidOCR",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize OCR error.

        Args:
            message: Error message
            ocr_engine: OCR engine that failed
            details: Additional context
        """
        details = details or {}
        details["ocr_engine"] = ocr_engine
        super().__init__(
            message=message,
            code="OCR_ERROR",
            details=details,
        )


class ImageFormatError(ValidationError):
    """Raised when image format is not supported."""

    def __init__(
        self,
        filename: str,
        format: str,
        allowed_formats: Optional[list[str]] = None,
    ):
        """Initialize image format error.

        Args:
            filename: Name of the invalid file
            format: The file format that was detected
            allowed_formats: List of allowed formats
        """
        details = {"filename": filename, "detected_format": format}
        if allowed_formats:
            details["allowed_formats"] = allowed_formats
        super().__init__(
            message=f"Unsupported image format: {format}",
            details=details,
        )


class FileSizeError(ValidationError):
    """Raised when file size exceeds limit."""

    def __init__(
        self,
        filename: str,
        size_bytes: int,
        max_size_bytes: int,
    ):
        """Initialize file size error.

        Args:
            filename: Name of the oversized file
            size_bytes: Actual file size in bytes
            max_size_bytes: Maximum allowed size in bytes
        """
        super().__init__(
            message=f"File size exceeds maximum allowed size",
            details={
                "filename": filename,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "max_size_mb": round(max_size_bytes / (1024 * 1024), 2),
            },
        )


class ModelLoadError(SnapTextException):
    """Raised when OCR model fails to load."""

    def __init__(
        self,
        model_name: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize model load error.

        Args:
            model_name: Name of the model that failed to load
            details: Additional context
        """
        details = details or {}
        details["model_name"] = model_name
        super().__init__(
            message=f"Failed to load OCR model: {model_name}",
            code="MODEL_LOAD_ERROR",
            details=details,
        )


# HTTP Exception Helpers


def create_http_exception(
    status_code: int,
    message: str,
    code: str = "HTTP_ERROR",
    details: Optional[Dict[str, Any]] = None,
) -> HTTPException:
    """Create an HTTPException with standardized format.

    Args:
        status_code: HTTP status code
        message: Error message
        code: Error code
        details: Additional error context

    Returns:
        HTTPException with formatted details
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details or {},
        },
    )


# Exception Handlers for FastAPI


async def snaptext_exception_handler(
    request: Any, exc: SnapTextException
) -> JSONResponse:
    """Handle SnapTextException instances.

    Args:
        request: FastAPI request
        exc: SnapTextException instance

    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def http_exception_handler(request: Any, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException instances.

    Args:
        request: FastAPI request
        exc: HTTPException instance

    Returns:
        JSONResponse with error details
    """
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": exc.detail}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": detail.get("code", "HTTP_ERROR"),
                "message": detail.get("message", str(exc.detail)),
                "details": detail.get("details", {}),
            },
        },
    )


async def generic_exception_handler(request: Any, exc: Exception) -> JSONResponse:
    """Handle all other exceptions.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"detail": str(exc)} if get_settings().debug else {},
            },
        },
    )
