"""OCR repository implementation using PaddleOCR.

This module provides a concrete implementation of the OCR repository
interface using PaddleOCR as the OCR engine.
"""

import os
import time
from functools import lru_cache
from typing import Any, Dict

# Disable OneDNN/MKLDNN to avoid compatibility issues
os.environ["INFERENCE_ENFORCE_USE_ONEDNN"] = "0"
os.environ["FLAGS_use_mkldnn"] = "false"

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from paddleocr import PaddleOCR

from app.core.config import get_settings
from app.core.exceptions import OCRError, ModelLoadError
from app.repositories.base import OCRRepositoryInterface

settings = get_settings()


class PaddleOCRRepository(OCRRepositoryInterface):
    """PaddleOCR implementation of OCR repository.

    Handles PaddleOCR model lifecycle and provides text extraction
    and visualization capabilities.
    """

    def __init__(
        self,
        lang: str | None = None,
        use_angle_cls: bool | None = None,
    ):
        """Initialize PaddleOCR repository.

        Args:
            lang: Default language for OCR
            use_angle_cls: Whether to use angle classifier
        """
        self._lang = lang if lang is not None else settings.paddleocr_lang
        self._use_angle_cls = (
            use_angle_cls if use_angle_cls is not None else settings.paddleocr_use_angle_cls
        )

        self._ocr_engine: PaddleOCR | None = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize PaddleOCR model (lazy loading).

        The model is only loaded when first needed to reduce startup time.
        """
        if self._is_initialized:
            return

        try:
            start_time = time.time()

            self._ocr_engine = PaddleOCR(
                use_angle_cls=self._use_angle_cls,
                lang=self._lang,
            )

            load_time = time.time() - start_time
            self._is_initialized = True

            from app.core.logging import get_logger

            logger = get_logger("ocr_repository")
            logger.info(f"PaddleOCR model loaded in {load_time:.2f}s")

        except Exception as e:
            raise ModelLoadError(
                model_name=f"PaddleOCR ({self._lang})",
                details={"error": str(e), "lang": self._lang},
            ) from e

    async def extract_text(
        self, image: Image.Image, lang: str = "en"
    ) -> Dict[str, Any]:
        """Extract text from image using PaddleOCR.

        Args:
            image: PIL Image object to process
            lang: Language code for OCR (e.g., 'en', 'id')

        Returns:
            Dictionary containing:
                - text: Full extracted text
                - confidence: Average confidence score (0-1)
                - regions: List of text regions with bbox and confidence
                - language: The language used

        Raises:
            OCRError: If OCR processing fails
        """
        # Lazy initialization if not already initialized
        if not self._is_initialized or self._ocr_engine is None:
            await self.initialize()

        start_time = time.time()

        try:
            # Convert PIL Image to OpenCV format (numpy array)
            img_array = self._pil_to_opencv(image)

            # Run OCR
            result = self._ocr_engine.ocr(img_array)

            # Parse results
            regions = []
            full_text_lines = []
            confidences = []

            if result and result[0]:
                for idx, line in enumerate(result[0]):
                    bbox = line[0]  # Bounding box coordinates
                    text_info = line[1]  # (text, confidence)

                    text = text_info[0]
                    confidence = float(text_info[1])

                    regions.append(
                        {
                            "text": text,
                            "confidence": confidence,
                            "bbox": [[int(p[0]), int(p[1])] for p in bbox],
                            "region_id": idx + 1,
                        }
                    )

                    full_text_lines.append(text)
                    confidences.append(confidence)

            # Calculate overall confidence
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            # Join text with newlines
            full_text = "\n".join(full_text_lines)

            processing_time = (time.time() - start_time) * 1000  # ms

            from app.core.logging import get_logger

            logger = get_logger("ocr_repository")
            logger.debug(
                f"Extracted {len(regions)} regions in {processing_time:.2f}ms, "
                f"avg confidence: {avg_confidence:.2f}"
            )

            return {
                "text": full_text,
                "confidence": avg_confidence,
                "regions": regions,
                "region_count": len(regions),
                "language": lang,
                "processing_time_ms": processing_time,
            }

        except OCRError:
            raise
        except Exception as e:
            raise OCRError(
                message=f"Failed to extract text: {str(e)}",
                details={"lang": lang, "image_size": image.size},
            ) from e

    async def visualize_detections(
        self, image: Image.Image
    ) -> tuple[Image.Image, Dict[str, Any]]:
        """Create visualization with bounding boxes marked.

        Args:
            image: PIL Image object to process

        Returns:
            Tuple of (annotated image, metadata dict)

        Raises:
            OCRError: If visualization fails
        """
        # Lazy initialization if not already initialized
        if not self._is_initialized or self._ocr_engine is None:
            await self.initialize()

        start_time = time.time()

        try:
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Get OCR results
            ocr_result = await self.extract_text(image)

            # Create a copy for drawing
            annotated = image.copy()
            draw = ImageDraw.Draw(annotated)

            # Define colors
            bbox_color = (0, 255, 0)  # Green
            text_color = (255, 0, 0)  # Red

            # Try to load a font
            try:
                # Try to use a common font
                font = ImageFont.truetype("arial.ttf", 16)
            except Exception:
                # Fallback to default font
                font = ImageFont.load_default()

            # Draw bounding boxes and text
            for region in ocr_result["regions"]:
                bbox = region["bbox"]
                text = region["text"]
                confidence = region["confidence"]

                # Draw bounding box polygon
                draw.polygon(
                    [(p[0], p[1]) for p in bbox], outline=bbox_color, width=3
                )

                # Draw text label above bbox
                label = f"{confidence:.2f}"
                label_position = (bbox[0][0], bbox[0][1] - 20)

                # Draw background for text
                text_bbox = draw.textbbox(label_position, label, font=font)
                draw.rectangle(text_bbox, fill=bbox_color)

                # Draw text
                draw.text(label_position, label, fill=text_color, font=font)

            # Add watermark
            watermark_text = "amubhya from rogatekno"
            watermark_font_size = 14
            try:
                watermark_font = ImageFont.truetype("arial.ttf", watermark_font_size)
            except Exception:
                watermark_font = font

            # Position watermark at bottom right
            img_width, img_height = image.size
            watermark_bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
            watermark_width = watermark_bbox[2] - watermark_bbox[0]
            watermark_height = watermark_bbox[3] - watermark_bbox[1]

            # Add padding
            padding = 10
            watermark_x = img_width - watermark_width - padding
            watermark_y = img_height - watermark_height - padding

            # Draw semi-transparent background for watermark
            watermark_bg_bbox = (
                watermark_x - padding,
                watermark_y - padding // 2,
                watermark_x + watermark_width + padding,
                watermark_y + watermark_height + padding // 2
            )

            # Create transparent overlay for watermark background
            watermark_overlay = Image.new('RGBA', annotated.size, (255, 255, 255, 0))
            watermark_draw = ImageDraw.Draw(watermark_overlay)
            watermark_draw.rectangle(watermark_bg_bbox, fill=(0, 0, 0, 128))

            # Composite the overlay
            annotated = Image.alpha_composite(annotated.convert('RGBA'), watermark_overlay).convert('RGB')
            draw = ImageDraw.Draw(annotated)

            # Draw watermark text
            draw.text(
                (watermark_x, watermark_y),
                watermark_text,
                fill=(255, 255, 255, 255),
                font=watermark_font
            )

            processing_time = (time.time() - start_time) * 1000  # ms

            metadata = {
                "regions_count": ocr_result["region_count"],
                "regions": ocr_result["regions"],
                "processing_time_ms": processing_time,
            }

            from app.core.logging import get_logger

            logger = get_logger("ocr_repository")
            logger.debug(
                f"Created visualization with {metadata['regions_count']} regions "
                f"in {processing_time:.2f}ms"
            )

            return annotated, metadata

        except OCRError:
            raise
        except Exception as e:
            raise OCRError(
                message=f"Failed to create visualization: {str(e)}",
                details={"image_size": image.size},
            ) from e

    def is_model_loaded(self) -> bool:
        """Check if OCR model is loaded and ready.

        Returns:
            True if model is loaded, False otherwise
        """
        return self._is_initialized and self._ocr_engine is not None

    async def cleanup(self) -> None:
        """Release OCR model resources."""
        if self._ocr_engine is not None:
            # PaddleOCR doesn't have explicit cleanup, but we can set to None
            self._ocr_engine = None
            self._is_initialized = False

            from app.core.logging import get_logger

            logger = get_logger("ocr_repository")
            logger.info("PaddleOCR resources released")

    @staticmethod
    def _pil_to_opencv(image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format.

        Args:
            image: PIL Image object

        Returns:
            OpenCV image as numpy array
        """
        # Convert PIL to RGB if not already
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Convert to numpy array
        img_array = np.array(image)

        # Convert RGB to BGR (OpenCV format)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        return img_array


# Singleton instance
_ocr_repository: PaddleOCRRepository | None = None


@lru_cache
def get_ocr_repository() -> PaddleOCRRepository:
    """Get or create singleton OCR repository instance.

    Returns:
        Cached PaddleOCRRepository instance
    """
    global _ocr_repository

    if _ocr_repository is None:
        _ocr_repository = PaddleOCRRepository()

    return _ocr_repository
