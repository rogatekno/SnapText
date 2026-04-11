"""OCR service layer for business logic.

This module contains the business logic that orchestrates OCR operations,
coordinates between the API and repository layers, and handles
validation and error handling.
"""

import io
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from pydantic import ValidationError
from rapidfuzz import process, fuzz

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

    async def map_text_from_file(
        self, file_content: bytes, filename: str, fields: List[str], lang: str = "en"
    ) -> Dict[str, Any]:
        """Extract specific fields from document based on labels.

        Args:
            file_content: Raw file content
            filename: Original filename
            fields: List of label strings to look for
            lang: OCR language code

        Returns:
            Dictionary of mapped fields and their values
        """
        # 1. OCR the image to get all regions
        ocr_result = await self.extract_text_from_file(file_content, filename, lang)
        regions = ocr_result.get("regions", [])

        if not regions:
            return {re.sub(r'[^a-zA-Z0-9]', '_', f).lower().strip('_'): None for f in fields}

        # 2. Perform mapping based on spatial heuristics
        mapped_data = self._perform_mapping(regions, fields)

        return mapped_data

    def _perform_mapping(self, regions: List[Dict[str, Any]], target_labels: List[str]) -> Dict[str, Any]:
        """Perform spatial mapping of labels to values.

        Heuristics:
        - Labels are matched using fuzzy matching (RapidFuzz).
        - Values are expected to be either to the right of or below the label.
        - Common delimiters (:, =, -) are stripped.
        """
        results = {}

        # Augment regions with spatial metadata for easier searching
        for r in regions:
            bbox = r["bbox"]
            # bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            r["_min_x"], r["_max_x"] = min(xs), max(xs)
            r["_min_y"], r["_max_y"] = min(ys), max(ys)
            r["_center_x"] = (r["_min_x"] + r["_max_x"]) / 2
            r["_center_y"] = (r["_min_y"] + r["_max_y"]) / 2
            r["_height"] = r["_max_y"] - r["_min_y"]
            r["_width"] = r["_max_x"] - r["_min_x"]

        region_texts = [r["text"] for r in regions]

        for label in target_labels:
            # Create a slugified key for the response
            clean_key = re.sub(r'[^a-zA-Z0-9]', '_', label).lower().strip('_')
            results[clean_key] = None

            # Find best match for label using fuzzy matching
            # threshold 80 is usually safe for OCR errors
            matches = process.extractOne(label, region_texts, scorer=fuzz.WRatio)
            if not matches or matches[1] < 70:
                continue

            best_match_text, score, match_idx = matches
            label_region = regions[match_idx]

            # Try to see if the value is already in the same region (e.g., "Nama: John")
            # If label is in Indonesian, it might contain ":"
            label_parts = re.split(r'[:=]', best_match_text, 1)
            if len(label_parts) > 1 and len(label_parts[1].strip()) > 1:
                results[clean_key] = label_parts[1].strip()
                continue

            # Look for values in other regions based on proximity
            potential_values = []
            for i, r in enumerate(regions):
                if i == match_idx:
                    continue

                # HEURISTIC A: Same line (horizontal), to the right
                # Vertical centers should be close, and r should be after label_region
                v_dist = abs(r["_center_y"] - label_region["_center_y"])
                h_dist = r["_min_x"] - label_region["_max_x"]
                
                if v_dist < label_region["_height"] * 0.7 and 0 < h_dist < label_region["_width"] * 3:
                    potential_values.append((r, h_dist, "horizontal"))

                # HEURISTIC B: Directly below (vertical)
                # Horizontal centers should be close, and r should be below label_region
                elif abs(r["_center_x"] - label_region["_center_x"]) < label_region["_width"] * 0.4:
                    v_gap = r["_min_y"] - label_region["_max_y"]
                    if 0 < v_gap < label_region["_height"] * 1.5:
                        potential_values.append((r, v_gap, "vertical"))

            if potential_values:
                # Sort by distance
                potential_values.sort(key=lambda x: x[1])
                best_val_region = potential_values[0][0]
                val_text = best_val_region["text"]
                
                # Cleanup: remove leading colons/symbols
                val_text = re.sub(r'^[:=\- ]+', '', val_text).strip()
                results[clean_key] = val_text if len(val_text) > 0 else None

        return results

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

            # Optimize image size for memory efficiency
            image = self._optimize_image(image)

            return image

        except ImageFormatError:
            raise
        except Exception as e:
            raise FileProcessingError(
                message=f"Failed to process image: {str(e)}",
                filename=filename,
                details={"size_bytes": file_size, "extension": file_ext},
            ) from e

    def _optimize_image(self, image: Image.Image) -> Image.Image:
        """Optimize image by resizing if it exceeds max dimensions.

        This prevents excessive memory usage and potential crashes on 
        low-spec systems when processing very large images.

        Args:
            image: PIL Image object

        Returns:
            Optimized PIL Image object
        """
        max_dim = settings.ocr_max_dimension
        width, height = image.size

        if max(width, height) > max_dim:
            if width > height:
                new_width = max_dim
                new_height = int(height * (max_dim / width))
            else:
                new_height = max_dim
                new_width = int(width * (max_dim / height))

            from app.core.logging import get_logger
            logger = get_logger("ocr_service")
            logger.info(f"Optimizing image: resizing from {width}x{height} to {new_width}x{new_height}")

            # Use Lanczos for high-quality downsampling
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return image

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
