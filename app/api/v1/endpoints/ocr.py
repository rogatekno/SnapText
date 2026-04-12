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


@router.post(
    "/smart-scan",
    response_model=OCRMapResponse,
    summary="Perform smart document scan",
    description="Automatically classify document (KTP, KK, etc.) and extract relevant data fields. "
                "Can also be used with specific field labels or table definitions.",
)
async def smart_scan(
    file: UploadFile = File(..., description="Image file to process"),
    fields: str = Form(default="", description="Optional: Comma-separated labels or JSON array"),
    tables: Optional[str] = Form(None, description="Optional: JSON-encoded list of table definitions"),
    lang: str = Form(
        default="id",
        description="OCR language code",
        pattern="^(en|id|ch|japan|korean|vi|fr|german|it|portuguese|spanish)$",
    ),
    debug: bool = Form(
        default=False,
        description="If true, includes a base64 debug image (preprocessed + OCR boxes) in the response"
    ),
):
    """Smart document scan with auto-classification and mapping.

    Args:
        file: Uploaded image file
        fields: Optional labels to look for (auto-classification if empty)
        tables: Optional table definitions
        lang: OCR language code (default: 'id')
        debug: Return a base64 annotated debug image in the response

    Returns:
        OCRMapResponse with mapped data and document type
    """
    start_time = time.time()
    ocr_service = get_ocr_service()

    # Parse field list from form string
    try:
        import json
        field_list = json.loads(fields) if fields else []
        if not isinstance(field_list, list):
            field_list = [f.strip() for f in str(fields).split(",") if f.strip()]
    except (json.JSONDecodeError, TypeError):
        field_list = [f.strip() for f in str(fields).split(",") if f.strip()]

    # Parse table definitions
    table_definitions = None
    if tables:
        try:
            import json
            table_definitions = json.loads(tables)
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        # Read file content
        file_content = await file.read()

        # Perform smart mapping
        mapped_data = await ocr_service.map_text_from_file(
            file_content=file_content,
            filename=file.filename or "unknown",
            fields=field_list,
            tables=table_definitions,
            lang=lang,
        )

        # Extract document type if it was auto-detected
        doc_type = mapped_data.pop("_document_type", None)

        # Optionally generate debug image
        debug_image = None
        if debug:
            debug_image = await ocr_service.generate_debug_image(
                file_content=file_content,
                filename=file.filename or "unknown",
                lang=lang,
            )

        processing_time = (time.time() - start_time) * 1000

        return OCRMapResponse(
            success=True,
            data=mapped_data,
            document_type=doc_type,
            processing_time_ms=processing_time,
            debug_image_base64=debug_image,
        )

    except SnapTextException:
        raise
    except Exception as e:
        from app.core.exceptions import OCRError

        raise OCRError(
            message=f"Unexpected error during smart scan: {str(e)}",
            details={"filename": file.filename},
        ) from e


@router.post(
    "/map",
    response_model=OCRMapResponse,
    summary="Map OCR results to specific fields (Alias for /smart-scan)",
    description="This is an alias for /smart-scan for backward compatibility.",
    deprecated=True,
)
async def map_fields(
    file: UploadFile = File(..., description="Image file to process"),
    fields: str = Form(default="", description="Comma-separated labels"),
    tables: Optional[str] = Form(None, description="JSON table definitions"),
    lang: str = Form(default="id", description="OCR language"),
    debug: bool = Form(
        default=False,
        description="If true, includes a base64 debug image (preprocessed + OCR boxes) in the response"
    ),
):
    """Alias for smart_scan."""
    return await smart_scan(file=file, fields=fields, tables=tables, lang=lang, debug=debug)


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
    """
    start_time = time.time()
    ocr_service = get_ocr_service()

    try:
        file_content = await file.read()
        img_bytes, img_format, metadata = await ocr_service.visualize_file(
            file_content=file_content,
            filename=file.filename or "unknown",
        )
        processing_time = metadata.get("processing_time_ms", (time.time() - start_time) * 1000)

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
