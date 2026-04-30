import time
from app.core.broker import broker
from app.core.logging import get_logger

logger = get_logger("ocr_tasks")

@broker.task(task_name="process_ocr")
async def process_ocr_task(
    file_content: bytes,
    filename: str,
    lang: str = "id"
) -> dict:
    """Background task to process OCR and LLM extraction.
    
    Args:
        file_content: Raw image bytes
        filename: Original filename
        lang: OCR language
        
    Returns:
        Structured data dictionary
    """
    from app.services.ocr_service import get_ocr_service
    
    start_time = time.time()
    logger.info(f"Starting async OCR task for file: {filename}")
    
    try:
        service = get_ocr_service()
        
        # Ensure model is ready (worker-side)
        if not service.is_ready():
            logger.info("Service not ready in worker, initializing...")
            await service.initialize()
            
        # Execute mapping
        result = await service.map_text_from_file(
            file_content=file_content,
            filename=filename,
            fields=[],
            lang=lang
        )
        
        processing_time = (time.time() - start_time) * 1000
        logger.info(f"Async OCR task complete: {filename} in {processing_time:.0f}ms")
        
        # Inject metadata for the result view
        result["_processing_time_ms"] = processing_time
        
        return result
        
    except Exception as e:
        logger.error(f"Error in async OCR task: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "filename": filename
        }
