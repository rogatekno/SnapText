"""OCR repository implementation using RapidOCR with ONNX Runtime.

This module provides a concrete implementation of the OCR repository
interface using RapidOCR as the OCR engine, which runs on ONNX Runtime
for better performance and lower memory usage on CPU.
"""

import os
import time
from functools import lru_cache
from typing import Any, Dict, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rapidocr_onnxruntime import RapidOCR

from app.core.config import get_settings
from app.core.exceptions import OCRError, ModelLoadError
from app.repositories.base import OCRRepositoryInterface

settings = get_settings()


class RapidOCRRepository(OCRRepositoryInterface):
    """RapidOCR implementation of OCR repository.

    Handles RapidOCR model lifecycle and provides text extraction
    and visualization capabilities using ONNX Runtime.
    """

    def __init__(
        self,
        lang: str | None = None,
        use_angle_cls: bool | None = None,
    ):
        """Initialize RapidOCR repository.

        Args:
            lang: Default language for OCR
            use_angle_cls: Whether to use angle classifier
        """
        self._lang = lang if lang is not None else settings.ocr_lang
        self._use_angle_cls = (
            use_angle_cls if use_angle_cls is not None else settings.ocr_use_angle_cls
        )

        self._ocr_engine: Optional[RapidOCR] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize RapidOCR model (lazy loading).

        The model is only loaded when first needed to reduce startup time.
        """
        if self._is_initialized:
            return

        try:
            start_time = time.time()

            # Initialize RapidOCR
            # RapidOCR automatically handles model downloading and ONNX Runtime provider setup
            self._ocr_engine = RapidOCR(
                width_height_info={'det_limit_side_len': 960},
                # Additional configuration can be passed here if needed
            )

            load_time = time.time() - start_time
            self._is_initialized = True

            from app.core.logging import get_logger
            logger = get_logger("ocr_repository")
            logger.info(f"RapidOCR (ONNX Runtime) model loaded in {load_time:.2f}s")

        except Exception as e:
            raise ModelLoadError(
                model_name=f"RapidOCR ({self._lang})",
                details={"error": str(e), "lang": self._lang},
            ) from e

    async def extract_text(
        self, image: Image.Image, lang: str = "en"
    ) -> Dict[str, Any]:
        """Extract text from image using RapidOCR.

        Args:
            image: PIL Image object to process
            lang: Language code for OCR (currently RapidOCR handles this via model selection)

        Returns:
            Dictionary containing OCR results

        Raises:
            OCRError: If OCR processing fails
        """
        if not self._is_initialized or self._ocr_engine is None:
            await self.initialize()

        start_time = time.time()

        try:
            # Convert PIL Image to OpenCV format (numpy array)
            img_array = self._pil_to_opencv(image)

            # Run OCR
            # result is a list of [bbox, text, confidence]
            # elapse is [det_time, cls_time, rec_time]
            result, elapse = self._ocr_engine(img_array)

            # Parse results
            regions = []
            full_text_lines = []
            confidences = []

            if result:
                for idx, line in enumerate(result):
                    bbox = line[0]  # Bounding box coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text = line[1]
                    confidence = float(line[2])

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
                "det_time_ms": elapse[0] * 1000 if elapse else 0,
                "rec_time_ms": elapse[2] * 1000 if elapse else 0,
            }

        except Exception as e:
            if isinstance(e, OCRError):
                raise
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
        """
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
                font = ImageFont.truetype("arial.ttf", 16)
            except Exception:
                font = ImageFont.load_default()

            # Draw bounding boxes and confidence labels
            for region in ocr_result["regions"]:
                bbox = region["bbox"]
                confidence = region["confidence"]

                # Draw bounding box polygon
                draw.polygon(
                    [(p[0], p[1]) for p in bbox], outline=bbox_color, width=3
                )

                # Draw confidence label above bbox
                label = f"{confidence:.2f}"
                label_position = (bbox[0][0], bbox[0][1] - 20)

                # Draw background for text
                try:
                    text_bbox = draw.textbbox(label_position, label, font=font)
                    draw.rectangle(text_bbox, fill=bbox_color)
                except Exception:
                    pass

                # Draw text
                draw.text(label_position, label, fill=text_color, font=font)

            # Add watermark "RogaTekno"
            self._add_watermark(annotated)

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

        except Exception as e:
            if isinstance(e, OCRError):
                raise
            raise OCRError(
                message=f"Failed to create visualization: {str(e)}",
                details={"image_size": image.size},
            ) from e

    def _add_watermark(self, image: Image.Image) -> None:
        """Add RogaTekno watermark to the image.

        Args:
            image: PIL Image to watermark (modified in place)
        """
        draw = ImageDraw.Draw(image)
        watermark_text = "RogaTekno"
        
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()

        # Position at bottom right
        width, height = image.size
        try:
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            text_width, text_height = 100, 20

        padding = 10
        x = width - text_width - padding
        y = height - text_height - padding

        # Draw semi-transparent background
        bg_bbox = [x - 5, y - 5, x + text_width + 5, y + text_height + 5]
        draw.rectangle(bg_bbox, fill=(0, 0, 0, 128))
        
        # Draw text
        draw.text((x, y), watermark_text, fill=(255, 255, 255, 255), font=font)

    def is_model_loaded(self) -> bool:
        """Check if OCR model is loaded and ready."""
        return self._is_initialized and self._ocr_engine is not None

    async def cleanup(self) -> None:
        """Release OCR model resources."""
        if self._ocr_engine is not None:
            self._ocr_engine = None
            self._is_initialized = False
            from app.core.logging import get_logger
            logger = get_logger("ocr_repository")
            logger.info("RapidOCR resources released")

    @staticmethod
    def _pil_to_opencv(image: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format (BGR)."""
        if image.mode != "RGB":
            image = image.convert("RGB")
        img_array = np.array(image)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)


# Singleton instance
_ocr_repository: Optional[RapidOCRRepository] = None


@lru_cache
def get_ocr_repository() -> RapidOCRRepository:
    """Get or create singleton OCR repository instance."""
    global _ocr_repository
    if _ocr_repository is None:
        _ocr_repository = RapidOCRRepository()
    return _ocr_repository
