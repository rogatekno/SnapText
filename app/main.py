"""FastAPI application entry point.

This module creates and configures the FastAPI application with
all routes, middleware, and exception handlers.
"""

# IMPORTANT: Set environment variables BEFORE any PaddlePaddle imports
# This prevents OneDNN compatibility issues
import os

os.environ["INFERENCE_ENFORCE_USE_ONEDNN"] = "0"
os.environ["FLAGS_use_mkldnn"] = "false"
os.environ["XLAN_ENABLE"] = "0"

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import health, ocr
from app.core.config import get_settings
from app.core.exceptions import (
    RogaScanException,
    rogascan_exception_handler,
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

    logger = get_logger("lifespan")
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    try:
        # Initialize OCR service (loads model)
        ocr_service = get_ocr_service()
        await ocr_service.initialize()

        logger.info("OCR service initialized successfully")
    except Exception as e:
        logger.warning(f"OCR service initialization failed: {e}")
        logger.warning("OCR will be initialized on first request")

    yield

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
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
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
    app.add_exception_handler(RogaScanException, rogascan_exception_handler)
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
        prefix=settings.api_v1_prefix,
        tags=["ocr"],
    )

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "description": settings.app_description,
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
