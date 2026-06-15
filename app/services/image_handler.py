"""Service for image-related operations.

This module handles image validation and loading.
Image preprocessing has been intentionally removed — raw bytes
are passed directly to the OCR engine for maximum throughput.
"""

import io
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import (
    FileProcessingError,
    ImageFormatError,
    FileSizeError,
)

settings = get_settings()


class ImageHandler:
    """Handles image loading and validation only — no preprocessing."""

    async def validate_and_load(
        self, file_content: bytes, filename: str
    ) -> Image.Image:
        """Validate file size/format and load as PIL Image.

        No resizing, no enhancement, no preprocessing applied.
        The raw image is returned as-is for direct OCR input.
        """
        file_size = len(file_content)
        if file_size > settings.max_upload_size_bytes:
            raise FileSizeError(
                filename=filename,
                size_bytes=file_size,
                max_size_bytes=settings.max_upload_size_bytes,
            )

        file_ext = self._get_file_extension(filename)
        if file_ext.lower() not in settings.allowed_extensions:
            raise ImageFormatError(
                filename=filename,
                format=file_ext,
                allowed_formats=settings.allowed_extensions,
            )

        try:
            image = Image.open(io.BytesIO(file_content))
            image.verify()

            # Reopen after verify (verify closes the stream)
            image = Image.open(io.BytesIO(file_content))

            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")

            return image
        except Exception as e:
            raise FileProcessingError(
                message=f"Failed to process image: {str(e)}",
                filename=filename,
                details={"size_bytes": file_size, "extension": file_ext},
            ) from e

    def apply_preprocessing(self, image: Image.Image) -> Image.Image:
        """Apply OpenCV adaptive thresholding for table documents.
        
        This converts the image to grayscale, applies a light Gaussian blur,
        and then an adaptive threshold to make small text in tables pop out clearly.
        """
        import cv2
        import numpy as np
        
        # Convert PIL to OpenCV format
        img_array = np.array(image)
        if image.mode == 'RGBA':
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        else:
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
        # 1. Grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # 2. Gentle Denoising (Gaussian Blur)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. Adaptive Thresholding (Optimized for Paper Documents)
        processed_img = cv2.adaptiveThreshold(
            blurred, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 5
        )
        
        # Convert back to PIL
        # Convert single channel grayscale back to RGB so it works with the rest of the pipeline seamlessly
        processed_rgb = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
        return Image.fromarray(processed_rgb)

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        parts = filename.rsplit(".", 1)
        if len(parts) != 2:
            raise FileProcessingError(message="File has no extension", filename=filename)
        return parts[1]

    @staticmethod
    def image_to_bytes(image: Image.Image, format: str = "PNG") -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
