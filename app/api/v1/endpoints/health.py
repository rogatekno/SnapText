"""Health check endpoint.

This module provides a simple health check endpoint to verify
that the service is running and OCR model is loaded.
"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.models.schemas import HealthResponse
from app.repositories.ocr_repository import get_ocr_repository
from app.services.ocr_service import get_ocr_service

router = APIRouter()
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the service is healthy and OCR model is loaded",
)
async def health_check() -> HealthResponse:
    """Check service health status.

    Returns:
        HealthResponse with service status, version, and model state
    """
    ocr_service = get_ocr_service()
    ocr_repository = get_ocr_repository()

    # Always return healthy even if OCR not ready yet
    # This prevents 502 errors during initial startup on low-resource servers
    ocr_ready = ocr_repository.is_model_loaded()

    return HealthResponse(
        status="healthy",  # Always healthy - API is responding
        version=settings.app_version,
        ocr_model_loaded=ocr_ready,
        environment=settings.environment,
    )
