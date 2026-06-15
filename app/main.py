"""FastAPI application entry point.

This module creates and configures the FastAPI application with
all routes, middleware, and exception handlers.
"""

import os

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import health, ocr
from app.core.config import get_settings
from app.core.exceptions import (
    SnapTextException,
    snaptext_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from app.core.logging import setup_logging
from app.repositories.ocr_repository import get_ocr_repository
from app.services.ocr_service import get_ocr_service

# Initialize logging
setup_logging()

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager.

    Handles startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Models will be pre-loaded in the background
    logger.info("Initializing background warmup for OCR models...")
    import asyncio
    async def background_warmup():
        try:
            from app.services.ocr_service import get_ocr_service
            ocr_service = get_ocr_service()
            await ocr_service.initialize()
            logger.info("Background Warmup Complete: OCR ready for inference!")
        except Exception as e:
            logger.error(f"Background Warmup Failed: {str(e)}")

    # Initialize Taskiq Broker
    from app.core.broker import broker
    if not broker.is_worker_process:
        await broker.startup()

    # Start the task without waiting
    asyncio.create_task(background_warmup())

    yield

    # Shutdown Taskiq Broker
    if not broker.is_worker_process:
        await broker.shutdown()

    # Shutdown
    logger.info("Shutting down application...")

    try:
        # Cleanup OCR resources
        ocr_repository = get_ocr_repository()
        await ocr_repository.cleanup()
        logger.info("OCR resources cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="SnapText - OCR Service",
        description="""## SnapText - OCR Service
        
**Created by RogaTekno**

### Focus
This service is specifically optimized for extracting data.

### Features
- Text extraction from images using RapidOCR (ONNX Runtime)
- Automatic detection of data fields
- Bounding box visualization
- Clean API design for easy integration

### License
MIT License - Free to use, modify, and distribute.
""",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        contact={
            "name": "amubhya",
            "organization": "RogaTekno",
        },
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register exception handlers
    app.add_exception_handler(SnapTextException, snaptext_exception_handler)
    app.add_exception_handler(status.HTTP_422_UNPROCESSABLE_ENTITY, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Register routers
    app.include_router(
        health.router,
        prefix=settings.api_v1_prefix,
        tags=["health"],
    )

    app.include_router(
        ocr.router,
        prefix=f"{settings.api_v1_prefix}/ocr",
        tags=["ocr"],
    )

    from fastapi.staticfiles import StaticFiles
    import os
    from app.core.config import BASE_DIR
    
    static_dir = os.path.join(BASE_DIR, "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir, exist_ok=True)
        
    app.mount("/demo", StaticFiles(directory=static_dir, html=True), name="static")

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "name": "SnapText KTP OCR",
            "version": settings.app_version,
            "description": "Indonesian KTP OCR Extraction Service",
            "docs_url": "/docs",
            "api_prefix": settings.api_v1_prefix,
            "health_check": f"{settings.api_v1_prefix}/health",
        }

    return app


# Create app instance
app = create_app()


def main() -> None:
    """Run the application directly (for development)."""
    import uvicorn

    from app.core.logging import get_logger

    logger = get_logger("main")
    logger.info(f"Starting development server on {settings.host}:{settings.port}")

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
