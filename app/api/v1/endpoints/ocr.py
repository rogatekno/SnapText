"""OCR endpoints for text extraction and visualization.

This module provides the main OCR API endpoints for extracting text
from images and creating visualizations with bounding boxes.
"""

import time
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.exceptions import SnapTextException
from app.models.schemas import (
    OCRExtractResponse,
    OCRMapResponse,
    BoundingBox,
    TextRegion,
    OCRResult,
)
from app.services.ocr_service import get_ocr_service

router = APIRouter()
settings = get_settings()


class ExtractResponseModel(BaseModel):
    """Response model for extract endpoint."""

    success: bool = True
    data: OCRResult
    processing_time_ms: float


@router.post(
    "/extract",
    response_model=ExtractResponseModel,
    summary="Extract text from image",
    description="Extract text content from an uploaded image using OCR",
)
async def extract_text(
    file: UploadFile = File(..., description="Image file to process"),
    lang: str = Form(
        default="en",
        description="OCR language code (e.g., 'en', 'id', 'ch')",
        pattern="^(en|id|ch|japan|korean|vi|fr|german|it|portuguese|spanish)$",
    ),
):
    """Extract text from uploaded image.

    Args:
        file: Uploaded image file
        lang: OCR language code (default: 'en')

    Returns:
        ExtractResponseModel with extracted text and metadata

    Raises:
        ValidationError: If file validation fails
        OCRError: If OCR processing fails
    """
    start_time = time.time()
    ocr_service = get_ocr_service()

    try:
        # Read file content
        file_content = await file.read()

        # Extract text
        result = await ocr_service.extract_text_from_file(
            file_content=file_content,
            filename=file.filename or "unknown",
            lang=lang,
        )

        # Convert to response models
        regions = [
            TextRegion(
                text=r["text"],
                confidence=r["confidence"],
                bbox=BoundingBox(coordinates=r["bbox"]),
                region_id=r.get("region_id"),
            )
            for r in result["regions"]
        ]

        ocr_result = OCRResult(
            text=result["text"],
            confidence=result["confidence"],
            regions=regions,
            region_count=result["region_count"],
            language=result.get("language"),
        )

        processing_time = (time.time() - start_time) * 1000

        return ExtractResponseModel(
            success=True,
            data=ocr_result,
            processing_time_ms=processing_time,
        )

    except SnapTextException:
        raise
    except Exception as e:
        from app.core.exceptions import OCRError

        raise OCRError(
            message=f"Unexpected error during text extraction: {str(e)}",
            details={"filename": file.filename, "lang": lang},
        ) from e


@router.post(
    "/visualize",
    summary="Visualize OCR detections",
    description="Return an image with bounding boxes marking detected text regions",
    responses={
        200: {
            "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}},
            "description": "Image with bounding box annotations",
        }
    },
)
async def visualize(
    file: UploadFile = File(..., description="Image file to process"),
):
    """Create visualization with bounding boxes.

    Args:
        file: Uploaded image file

    Returns:
        PNG image with bounding boxes marked

    Raises:
        ValidationError: If file validation fails
        OCRError: If visualization fails
    """
    start_time = time.time()
    ocr_service = get_ocr_service()

    try:
        # Read file content
        file_content = await file.read()

        # Create visualization
        img_bytes, img_format, metadata = await ocr_service.visualize_file(
            file_content=file_content,
            filename=file.filename or "unknown",
        )

        processing_time = metadata.get("processing_time_ms", (time.time() - start_time) * 1000)

        # Return image with metadata headers
        return Response(
            content=img_bytes,
            media_type=f"image/{img_format.lower()}",
            headers={
                "X-Regions-Count": str(metadata["regions_count"]),
                "X-Processing-Time-Ms": f"{processing_time:.2f}",
                "X-Format": img_format,
            },
        )

    except SnapTextException:
        raise
    except Exception as e:
        from app.core.exceptions import OCRError

        raise OCRError(
            message=f"Unexpected error during visualization: {str(e)}",
            details={"filename": file.filename},
        ) from e


@router.post(
    "/map",
    response_model=OCRMapResponse,
    summary="Map OCR results to specific fields",
    description="Extract specific data fields from an image by providing their labels",
)
async def map_fields(
    file: UploadFile = File(..., description="Image file to process"),
    fields: str = Form(..., description="Comma-separated labels (e.g., 'Nama, NIK')"),
    lang: str = Form(
        default="en",
        description="OCR language code",
        pattern="^(en|id|ch|japan|korean|vi|fr|german|it|portuguese|spanish)$",
    ),
):
    """Extract specific fields from document based on labels.

    Args:
        file: Uploaded image file
        fields: Comma-separated list of labels or JSON array
        lang: OCR language code

    Returns:
        OCRMapResponse with mapped key-value pairs
    """
    start_time = time.time()
    ocr_service = get_ocr_service()

    # Parse field list from form string
    try:
        import json
        field_list = json.loads(fields)
        if not isinstance(field_list, list):
            field_list = [f.strip() for f in str(fields).split(",") if f.strip()]
    except (json.JSONDecodeError, TypeError):
        field_list = [f.strip() for f in str(fields).split(",") if f.strip()]

    try:
        # Read file content
        file_content = await file.read()

        # Perform mapping
        mapped_data = await ocr_service.map_text_from_file(
            file_content=file_content,
            filename=file.filename or "unknown",
            fields=field_list,
            lang=lang,
        )

        processing_time = (time.time() - start_time) * 1000

        return OCRMapResponse(
            success=True,
            data=mapped_data,
            processing_time_ms=processing_time,
        )

    except SnapTextException:
        raise
    except Exception as e:
        from app.core.exceptions import OCRError

        raise OCRError(
            message=f"Unexpected error during field mapping: {str(e)}",
            details={"filename": file.filename, "fields": field_list},
        ) from e


@router.get(
    "/info",
    summary="Get OCR service information",
    description="Get information about supported formats and limits",
)
async def get_info():
    """Get OCR service information.

    Returns:
        Dict with service configuration and limits
    """
    ocr_service = get_ocr_service()

    return {
        "success": True,
        "data": {
            "supported_formats": await ocr_service.get_supported_formats(),
            "max_file_size": await ocr_service.get_max_file_size(),
            "supported_languages": [
                "en",
                "id",
                "ch",
                "japan",
                "korean",
                "vi",
                "fr",
                "german",
                "it",
                "portuguese",
                "spanish",
            ],
            "default_language": settings.ocr_lang,
            "service_ready": ocr_service.is_ready(),
        },
    }
