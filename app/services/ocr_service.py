"""OCR service layer for business logic (Modular Coordinator).

This module orchestrates the OCR pipeline by coordinating between
ImageHandler, OCRRepository, and ExtractionStrategies.
"""

from typing import Any, Dict, List, Optional, Tuple
import re

from app.core.config import get_settings
from app.core.templates import get_templates
from app.repositories.base import OCRRepositoryInterface
from app.repositories.ocr_repository import get_ocr_repository
from app.services.image_handler import ImageHandler
from app.services.extraction.spatial_engine import SpatialExtractionEngine
from app.services.extraction.llm_engine import LLMExtractionEngine
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("ocr_service")


class OCRService:
    """Orchestrator for OCR operations."""

    def __init__(self, repository: Optional[OCRRepositoryInterface] = None):
        self._repository = repository or get_ocr_repository()
        self._image_handler = ImageHandler()
        self._spatial_engine = SpatialExtractionEngine()
        self._llm_engine = LLMExtractionEngine() if settings.llm_enabled else None

    async def initialize(self) -> None:
        """Initialize models."""
        await self._repository.initialize()
        # Only local LLM needs async initialization (model loading)
        if isinstance(self._llm_engine, LLMExtractionEngine):
            import asyncio
            await asyncio.to_thread(self._llm_engine.initialize)

    async def map_text_from_file(
        self,
        file_content: bytes,
        filename: str,
        fields: Optional[List[str]] = None,
        lang: str = "id",
        preprocess: bool = False,
    ) -> Dict[str, Any]:
        """Orchestrate the OCR and extraction pipeline.

        Args:
            file_content: Raw image bytes
            filename: Original filename
            fields: Specific fields to extract
            lang: OCR language
            preprocess: Whether to apply OpenCV table preprocessing
        """
        # 1. Validate and load image
        image = await self._image_handler.validate_and_load(file_content, filename)
        
        # Apply OpenCV pre-processing if requested
        if preprocess:
            logger.info("Applying OpenCV table pre-processing to image...")
            image = self._image_handler.apply_preprocessing(image)

        # 2. OCR Extraction
        ocr_result = await self._repository.extract_text(image, lang)
        regions = ocr_result.get("regions", [])
        ocr_time = ocr_result.get("processing_time_ms", 0)

        # 3. Spatial augmentation (shared for all engines)
        from app.services.extraction.base import ExtractionStrategy
        ExtractionStrategy.augment_spatial_metadata(regions)

        # 4. Classify document (shared for both engines)
        templates = get_templates()
        doc_type = self.classify_document(regions, templates)
        template = templates.get(doc_type) if doc_type else {}
        if template and doc_type:
            # Inject doc_type into template so LLM engine can use it
            template = {**template, "doc_type": doc_type}

        # 5. Data Extraction
        if self._llm_engine and settings.llm_enabled:
            logger.info(f"Using LLM Engine for extraction (doc_type={doc_type or 'unknown'})...")
            import asyncio
            mapped_data = await asyncio.to_thread(
                self._llm_engine.extract, regions, fields, template=template
            )
            
            # Ensure _llm_stats and _ocr_time_ms are preserved
            mapped_data["_ocr_time_ms"] = ocr_time
            if doc_type:
                mapped_data.setdefault("_document_type", doc_type)
            
            if not mapped_data.get("_llm_stats"):
                logger.warning("LLM engine returned no stats. This usually means extraction failed or was bypassed.")
        else:
            if doc_type and not fields:
                fields = template.get("fields", [])

            logger.info("Using Advanced Spatial Engine for extraction...")
            mapped_data = self._spatial_engine.extract(regions, fields, template=template)
            mapped_data["_ocr_time_ms"] = ocr_time
            if doc_type:
                mapped_data["_document_type"] = doc_type

        return self._post_process_data(mapped_data)

    def classify_document(self, regions: List[Dict[str, Any]], templates: dict = None) -> Optional[str]:
        """Classify document dynamically based on template anchors."""
        if not regions:
            return None
        from rapidfuzz import fuzz

        if templates is None:
            templates = get_templates()

        raw_text = " ".join([r["text"] for r in regions]).lower()

        best_match = None
        highest_score = 0

        for doc_key, template in templates.items():
            anchors = template.get("anchors", [])
            matches = sum(1 for a in anchors if fuzz.partial_ratio(a.lower(), raw_text) >= 85)
            score = matches / len(anchors) if anchors else 0
            if score > highest_score and (matches >= 2 or score >= 0.3):
                highest_score = score
                best_match = doc_key

        return best_match

    async def generate_debug_image(
        self, file_content: bytes, filename: str, lang: str = "id"
    ) -> Optional[str]:
        """Generate a debug image with OCR bounding boxes (no preprocessing)."""
        import base64
        import cv2
        import numpy as np

        try:
            image = await self._image_handler.validate_and_load(file_content, filename)

            ocr_result = await self._repository.extract_text(image, lang)
            regions = ocr_result.get("regions", [])

            # Convert PIL to OpenCV
            img_array = np.array(image.convert("RGB"))
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            for r in regions:
                bbox = r.get("bbox", [])
                text = r.get("text", "")
                if len(bbox) < 4:
                    continue
                pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
                cv2.polylines(img, [pts], isClosed=True, color=(0, 200, 80), thickness=2)
                x, y = int(bbox[0][0]), max(int(bbox[0][1]) - 4, 12)
                cv2.putText(img, text[:40], (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 100, 255), 1, cv2.LINE_AA)

            _, buf = cv2.imencode(".png", img)
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        except Exception:
            return None

    def _post_process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply global formatting rules iteratively."""
        for key, val in data.items():
            if isinstance(val, str):
                processed_val = val
                processed_val = re.sub(r'^[,\s·:;=\-|]+|[,\s·:;=\-|]+$', '', processed_val).strip()
                data[key] = processed_val
            elif isinstance(val, list):
                processed_list = []
                for item in val:
                    if isinstance(item, dict):
                        processed_list.append(self._post_process_data(item))
                data[key] = processed_list
        return data

    async def visualize_file(self, file_content: bytes, filename: str) -> Tuple[bytes, str, Dict[str, Any]]:
        """Proxy to visualize detections."""
        image = await self._image_handler.validate_and_load(file_content, filename)
        annotated_image, metadata = await self._repository.visualize_detections(image)
        return self._image_handler.image_to_bytes(annotated_image), "PNG", metadata

    def is_ready(self) -> bool:
        return self._repository.is_model_loaded()


# Singleton
_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
