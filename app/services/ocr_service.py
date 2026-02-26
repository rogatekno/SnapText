"""OCR service layer for business logic.

This module contains the business logic that orchestrates OCR operations,
coordinates between the API and repository layers, and handles
validation and error handling.
"""

import io
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import (
    FileProcessingError,
    ImageFormatError,
    FileSizeError,
    OCRError,
)
from app.models.schemas import BoundingBox, TextRegion, OCRResult
from app.repositories.base import OCRRepositoryInterface
from app.repositories.ocr_repository import get_ocr_repository

settings = get_settings()


class OCRService:
    """Service for OCR operations.

    Coordinates between API endpoints and the OCR repository,
    handling validation, business logic, and response formatting.
    """

    def __init__(self, repository: Optional[OCRRepositoryInterface] = None):
        """Initialize OCR service.

        Args:
            repository: OCR repository instance (uses singleton if not provided)
        """
        self._repository = repository or get_ocr_repository()

    async def initialize(self) -> None:
        """Initialize the OCR service.

        Should be called on application startup to ensure
        the OCR model is loaded.
        """
        await self._repository.initialize()

    async def extract_text_from_file(
        self, file_content: bytes, filename: str, lang: str = "en"
    ) -> Dict[str, Any]:
        """Extract text from uploaded image file.

        Args:
            file_content: Raw file content as bytes
            filename: Original filename
            lang: OCR language code (e.g., 'en', 'id')

        Returns:
            OCR extraction result dictionary

        Raises:
            ValidationError: If file validation fails
            FileProcessingError: If file processing fails
            OCRError: If OCR extraction fails
        """
        # Validate and load image
        image = await self._validate_and_load_image(file_content, filename)

        # Extract text
        result = await self._repository.extract_text(image, lang)

        # Add metadata
        result["filename"] = filename

        return result

    async def visualize_file(
        self, file_content: bytes, filename: str
    ) -> Tuple[bytes, str, Dict[str, Any]]:
        """Create visualization with bounding boxes marked.

        Args:
            file_content: Raw file content as bytes
            filename: Original filename

        Returns:
            Tuple of (image bytes, format, metadata)

        Raises:
            ValidationError: If file validation fails
            FileProcessingError: If file processing fails
            OCRError: If visualization fails
        """
        # Validate and load image
        image = await self._validate_and_load_image(file_content, filename)

        # Create visualization
        annotated_image, metadata = await self._repository.visualize_detections(image)

        # Convert to bytes
        img_bytes = self._image_to_bytes(annotated_image, "PNG")

        return img_bytes, "PNG", metadata

    async def _validate_and_load_image(
        self, file_content: bytes, filename: str
    ) -> Image.Image:
        """Validate and load image from bytes.

        Args:
            file_content: Raw file content
            filename: Original filename

        Returns:
            PIL Image object

        Raises:
            FileSizeError: If file exceeds size limit
            ImageFormatError: If format is not supported
            FileProcessingError: If image loading fails
        """
        # Check file size
        file_size = len(file_content)
        if file_size > settings.max_upload_size_bytes:
            raise FileSizeError(
                filename=filename,
                size_bytes=file_size,
                max_size_bytes=settings.max_upload_size_bytes,
            )

        # Check file extension
        file_ext = self._get_file_extension(filename)
        if file_ext.lower() not in settings.allowed_extensions:
            raise ImageFormatError(
                filename=filename,
                format=file_ext,
                allowed_formats=settings.allowed_extensions,
            )

        # Try to load the image
        try:
            image = Image.open(io.BytesIO(file_content))

            # Verify image
            image.verify()

            # Reopen after verify (verify closes the file)
            image = Image.open(io.BytesIO(file_content))

            # Convert to RGB if necessary
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")

            return image

        except ImageFormatError:
            raise
        except Exception as e:
            raise FileProcessingError(
                message=f"Failed to process image: {str(e)}",
                filename=filename,
                details={"size_bytes": file_size, "extension": file_ext},
            ) from e

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Extract file extension from filename.

        Args:
            filename: Original filename

        Returns:
            File extension without dot (e.g., 'jpg', 'png')

        Raises:
            FileProcessingError: If no extension found
        """
        parts = filename.rsplit(".", 1)
        if len(parts) != 2:
            raise FileProcessingError(
                message="File has no extension",
                filename=filename,
            )
        return parts[1]

    @staticmethod
    def _image_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
        """Convert PIL Image to bytes.

        Args:
            image: PIL Image object
            format: Image format (PNG, JPEG, etc.)

        Returns:
            Image bytes
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    async def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats.

        Returns:
            List of supported file extensions
        """
        return settings.allowed_extensions.copy()

    async def get_max_file_size(self) -> Dict[str, Any]:
        """Get maximum allowed file size.

        Returns:
            Dict with size in bytes and MB
        """
        return {
            "bytes": settings.max_upload_size_bytes,
            "mb": settings.max_upload_size_mb,
        }

    def is_ready(self) -> bool:
        """Check if OCR service is ready.

        Returns:
            True if service is initialized and ready
        """
        return self._repository.is_model_loaded()


# Singleton instance
_ocr_service: OCRService | None = None


def get_ocr_service() -> OCRService:
    """Get or create singleton OCR service instance.

    Returns:
        Cached OCRService instance
    """
    global _ocr_service

    if _ocr_service is None:
        _ocr_service = OCRService()

    return _ocr_service
