"""Base repository interface definitions.

This module defines abstract interfaces for repositories, following the
Repository Pattern for separation of concerns and testability.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from PIL import Image


class OCRRepositoryInterface(ABC):
    """Abstract interface for OCR repository.

    This interface defines the contract for OCR operations,
    allowing for different implementations (PaddleOCR, Tesseract, etc.)
    and enabling easy mocking in tests.
    """

    @abstractmethod
    async def extract_text(
        self, image: Image.Image, lang: str = "en"
    ) -> Dict[str, Any]:
        """Extract text from image.

        Args:
            image: PIL Image object to process
            lang: Language code for OCR (e.g., 'en', 'id')

        Returns:
            Dictionary containing:
                - text: Full extracted text
                - confidence: Average confidence score (0-1)
                - regions: List of text regions with bbox and confidence

        Raises:
            OCRError: If OCR processing fails
        """
        pass

    @abstractmethod
    async def visualize_detections(
        self, image: Image.Image
    ) -> tuple[Image.Image, Dict[str, Any]]:
        """Create visualization with bounding boxes marked.

        Args:
            image: PIL Image object to process

        Returns:
            Tuple of (annotated image, metadata dict)
            Metadata contains:
                - regions_count: Number of regions detected
                - regions: List of region details

        Raises:
            OCRError: If visualization fails
        """
        pass

    @abstractmethod
    def is_model_loaded(self) -> bool:
        """Check if OCR model is loaded and ready.

        Returns:
            True if model is loaded, False otherwise
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize OCR model.

        This method should be called before using other methods.
        Can be called multiple times safely (idempotent).
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Release OCR model resources.

        Call this when shutting down the application or
        when the OCR model will no longer be used.
        """
        pass
