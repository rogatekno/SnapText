"""OCR endpoints for Document data extraction and visualization.

This module provides the main OCR API endpoints for extracting data
from Document images.
"""

import time
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import Response
from PIL import Image

from app.core.config import get_settings
from app.core.exceptions import SnapTextException
from app.models.schemas import (
    LLMPerformance,
    OCRMapResponse,
)
from app.core.logging import get_logger
from app.services.ocr_service import get_ocr_service
from app.models.schemas import AsyncJobResponse, JobStatusResponse
from app.tasks.ocr_tasks import process_ocr_task
from app.core.broker import broker

settings = get_settings()
logger = get_logger("ocr_api")
router = APIRouter()


@router.post(
    "/scan",
    response_model=OCRMapResponse,
    summary="Scan Document (KTP, KK, Invoice, etc.)",
    description="Automatically extract structured data from documents using hybrid OCR and Local LLM.",
)
async def scan_document(
    file: UploadFile = File(..., description="Image file of Document to process"),
    lang: str = Form(
        default="id",
        description="OCR language code",
        pattern="^(en|id)$",
    ),
    ):
    """Scan Document and extract mapped data.

    Args:
        file: Uploaded image file
        lang: OCR language code (default: 'id')

    Returns:
        OCRMapResponse with Document data
    """
    start_time = time.time()
    ocr_service = get_ocr_service()

    try:
        # Read file content
        file_content = await file.read()

        # Perform mapping focused on Document
        # Automatic classification will find the template
        mapped_data = await ocr_service.map_text_from_file(
            file_content=file_content,
            filename=file.filename or "unknown",
            fields=[],
            lang=lang
        )

        # Extract metadata keys injected by service/engines
        doc_type = mapped_data.pop("_document_type", "unknown")
        llm_stats_raw = mapped_data.pop("_llm_stats", None)
        ocr_time = mapped_data.pop("_ocr_time_ms", 0)

        # Build LLMPerformance object if stats are available
        llm_perf = None
        llm_time = 0
        if llm_stats_raw and isinstance(llm_stats_raw, dict):
            try:
                # Ensure provider defaults to settings value if not set by engine
                if "provider" not in llm_stats_raw:
                    llm_stats_raw["provider"] = settings.llm_provider
                llm_perf = LLMPerformance(**llm_stats_raw)
                llm_time = llm_stats_raw.get("elapsed_seconds", 0) * 1000
            except Exception:
                llm_perf = None

        processing_time = (time.time() - start_time) * 1000

        # Log performance for immediate visibility
        perf_info = f"DOC_TYPE={doc_type} | TOTAL={processing_time:.0f}ms | OCR={ocr_time:.0f}ms | LLM={llm_time:.0f}ms"
        if llm_perf:
            perf_info += f" | SPEED={llm_perf.tokens_per_second} tok/s"
        logger.info(f"Scan complete: {perf_info}")

        return OCRMapResponse(
            success=True,
            data=mapped_data,
            document_type=doc_type,
            processing_time_ms=processing_time,
            ocr_time_ms=ocr_time,
            llm_time_ms=llm_time,
            llm_performance=llm_perf,
        )

    except SnapTextException:
        raise
    except Exception as e:
        from app.core.exceptions import OCRError

        raise OCRError(
            message=f"Unexpected error during Document scan: {str(e)}",
            details={"filename": file.filename},

        ) from e


@router.post(
    "/preprocess",
    summary="Preview OpenCV Preprocessing",
    description="Upload an image, apply optional OpenCV preprocessing, and return both original and processed images as base64 for side-by-side review.",
)
async def preprocess_image(
    file: UploadFile = File(..., description="Image file to preprocess"),
    apply_opencv: bool = Form(default=True, description="Apply OpenCV Grayscale + Adaptive Thresholding"),
):
    """Preview preprocessing result before submitting to OCR.

    Returns:
        Dict with original_preview and processed_preview as base64 data URIs.
    """
    import base64
    import io

    ocr_service = get_ocr_service()

    try:
        file_content = await file.read()
        filename = file.filename or "unknown"

        # Validate and load
        image = await ocr_service._image_handler.validate_and_load(file_content, filename)

        # Encode original as base64
        orig_buffer = io.BytesIO()
        image.save(orig_buffer, format="JPEG", quality=90)
        original_b64 = f"data:image/jpeg;base64,{base64.b64encode(orig_buffer.getvalue()).decode('utf-8')}"

        # Apply preprocessing if requested
        if apply_opencv:
            processed = ocr_service._image_handler.apply_preprocessing(image)
        else:
            processed = image.copy()

        # Encode processed as base64
        proc_buffer = io.BytesIO()
        processed.save(proc_buffer, format="JPEG", quality=90)
        processed_b64 = f"data:image/jpeg;base64,{base64.b64encode(proc_buffer.getvalue()).decode('utf-8')}"

        return {
            "success": True,
            "original_preview": original_b64,
            "processed_preview": processed_b64,
            "opencv_applied": apply_opencv,
        }

    except SnapTextException:
        raise
    except Exception as e:
        from app.core.exceptions import OCRError
        raise OCRError(
            message=f"Error during preprocessing: {str(e)}",
            details={"filename": file.filename},
        ) from e


@router.post(
    "/scan_stream",
    summary="Scan Document with SSE Progress Streaming",
    description="Extract data and stream progress updates (Server-Sent Events). Accepts an optional preprocessed base64 image to skip the preprocessing step.",
)
async def scan_document_stream(
    file: UploadFile = File(..., description="Image file of Document to process"),
    lang: str = Form(default="id"),
    preprocess: bool = Form(default=False, description="Apply OpenCV Table Preprocessing (ignored if preprocessed_image is provided)"),
    preprocessed_image: Optional[str] = Form(default=None, description="Base64-encoded preprocessed image (data URI). If provided, preprocessing step is skipped."),
):
    import json
    import asyncio
    import base64
    import io
    from fastapi.responses import StreamingResponse
    from app.services.ocr_service import get_ocr_service
    from app.core.templates import get_templates

    # Read file synchronously in the request context before StreamingResponse is returned
    file_content = await file.read()
    filename = file.filename or "unknown"

    async def event_generator():
        start_time = time.time()
        ocr_service = get_ocr_service()

        try:
            # 1. Load image
            yield f"data: {json.dumps({'status': 'uploading', 'message': 'Membaca file gambar...'})}\n\n"

            if preprocessed_image:
                # Decode the base64 preprocessed image provided by the frontend
                # Strip data URI prefix if present
                b64_data = preprocessed_image
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]

                img_bytes = base64.b64decode(b64_data)
                image = Image.open(io.BytesIO(img_bytes))
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGB")

                yield f"data: {json.dumps({'status': 'preprocessing', 'message': 'Menggunakan gambar yang sudah di-preprocess.'})}\n\n"
            else:
                image = await ocr_service._image_handler.validate_and_load(file_content, filename)

                # 2. Preprocessing (only if no preprocessed image was provided)
                if preprocess:
                    image = ocr_service._image_handler.apply_preprocessing(image)

                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=85)
                    base64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    yield f"data: {json.dumps({'status': 'preprocessing', 'message': 'OpenCV Grayscale & Adaptive Thresholding Selesai.', 'processed_image': f'data:image/jpeg;base64,{base64_img}'})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'preprocessing', 'message': 'Bypass Preprocessing...'})}\n\n"

            await asyncio.sleep(0.5)

            # 3. OCR
            yield f"data: {json.dumps({'status': 'ocr', 'message': 'Menjalankan RapidOCR (Mengekstrak teks mentah)...'})}\n\n"
            ocr_result = await ocr_service._repository.extract_text(image, lang)
            regions = ocr_result.get("regions", [])
            ocr_time = ocr_result.get("processing_time_ms", 0)

            # 4. Classification
            yield f"data: {json.dumps({'status': 'classification', 'message': 'Mengklasifikasi jenis dokumen...'})}\n\n"
            from app.services.extraction.base import ExtractionStrategy
            ExtractionStrategy.augment_spatial_metadata(regions)
            templates = get_templates()
            doc_type = ocr_service.classify_document(regions, templates)
            template = templates.get(doc_type) if doc_type else {}
            if template and doc_type:
                template = {**template, "doc_type": doc_type}

            # 5. Extraction
            if ocr_service._llm_engine and settings.llm_enabled:
                yield f"data: {json.dumps({'status': 'llm', 'message': f'Menggunakan Qwen 1.5B untuk structuring JSON ({doc_type})...'})}\n\n"
                mapped_data = await asyncio.to_thread(
                    ocr_service._llm_engine.extract, regions, [], template=template
                )
            else:
                yield f"data: {json.dumps({'status': 'llm', 'message': f'Menggunakan Spatial Engine...'})}\n\n"
                mapped_data = ocr_service._spatial_engine.extract(regions, [], template=template)

            mapped_data = ocr_service._post_process_data(mapped_data)

            # Metadata injection
            mapped_data["_ocr_time_ms"] = ocr_time
            if doc_type:
                mapped_data.setdefault("_document_type", doc_type)

            doc_type = mapped_data.pop("_document_type", "unknown")
            llm_stats_raw = mapped_data.pop("_llm_stats", None)
            ocr_time = mapped_data.pop("_ocr_time_ms", 0)

            llm_perf = None
            llm_time = 0
            if llm_stats_raw and isinstance(llm_stats_raw, dict):
                try:
                    if "provider" not in llm_stats_raw:
                        llm_stats_raw["provider"] = settings.llm_provider
                    llm_perf = llm_stats_raw
                    llm_time = llm_stats_raw.get("elapsed_seconds", 0) * 1000
                except Exception:
                    pass

            processing_time = (time.time() - start_time) * 1000

            final_result = {
                "success": True,
                "data": mapped_data,
                "document_type": doc_type,
                "processing_time_ms": processing_time,
                "ocr_time_ms": ocr_time,
                "llm_time_ms": llm_time,
                "llm_performance": llm_perf,
            }
            yield f"data: {json.dumps({'status': 'complete', 'message': 'Selesai!', 'result': final_result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    summary="Get KTP OCR service information",
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
            "supported_languages": ["en", "id"],
            "default_language": settings.ocr_lang,
            "service_ready": ocr_service.is_ready(),
            "focus_document": "KTP (Indonesian ID Card)"
        },
    }


@router.post(
    "/scan/async",
    response_model=AsyncJobResponse,
    summary="Scan Document Asynchronously",
    description="Submit an OCR job and receive a Job ID immediately. Process runs in the background.",
)
async def scan_document_async(
    file: UploadFile = File(..., description="Image file to process"),
    lang: str = Form(default="id", description="OCR language code"),
):
    """Initiate an asynchronous OCR scan job."""
    file_content = await file.read()
    
    # Send task to worker
    task = await process_ocr_task.kiq(
        file_content=file_content,
        filename=file.filename or "unknown",
        lang=lang
    )
    
    return AsyncJobResponse(
        success=True,
        message="OCR task submitted successfully",
        job_id=task.task_id
    )


@router.get(
    "/scan/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Check Async Job Status",
    description="Check the status and get results of an asynchronous OCR job.",
)
async def get_scan_status(job_id: str):
    """Get the status and result of an async OCR task."""
    # Get result from backend
    result_backend = broker.result_backend
    if not result_backend:
        return JobStatusResponse(
            success=False,
            job_id=job_id,
            status="FAILURE",
            error="Result backend not configured"
        )

    # Check status
    is_ready = await result_backend.is_result_ready(job_id)
    if not is_ready:
        return JobStatusResponse(
            success=True,
            job_id=job_id,
            status="PENDING",
            message="Task is still processing"
        )

    # Get the actual result
    task_result = await result_backend.get_result(job_id)
    
    if task_result.is_err:
        return JobStatusResponse(
            success=False,
            job_id=job_id,
            status="FAILURE",
            error="Task failed during execution"
        )

    data = task_result.return_value
    
    # Check if internal processing failed
    if isinstance(data, dict) and not data.get("success", True):
        return JobStatusResponse(
            success=False,
            job_id=job_id,
            status="FAILURE",
            error=data.get("error", "Unknown internal error"),
            result=data
        )

    return JobStatusResponse(
        success=True,
        job_id=job_id,
        status="SUCCESS",
        result=data,
        processing_time_ms=data.get("_processing_time_ms") if isinstance(data, dict) else None
    )
