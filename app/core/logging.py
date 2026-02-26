"""Logging configuration using Loguru.

This module configures structured logging for the application,
supporting both JSON and text formats with rotation and retention.
"""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure Loguru logger for the application.

    Removes default handlers and adds custom handlers for:
    - Console output (with formatting based on LOG_FORMAT)
    - File output (with rotation and retention)
    """
    # Remove default handler
    logger.remove()

    # Determine log format
    log_format = get_log_format()
    use_json = settings.log_format == "json"

    # Add console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=not use_json,  # Only colorize text format
        backtrace=True,
        diagnose=settings.debug,
        serialize=use_json,  # Use built-in JSON serialization
    )

    # Add file handler with rotation
    log_file_path = Path(settings.log_file_path)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        settings.log_file_path,
        format=log_format,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        backtrace=True,
        diagnose=settings.debug,
        enqueue=True,  # Async logging
        serialize=use_json,  # Use built-in JSON serialization
    )

    logger.info(
        f"Logging initialized - Level: {settings.log_level}, "
        f"Format: {settings.log_format}"
    )


def get_log_format() -> str:
    """Get log format based on configuration.

    Returns:
        Log format string for Loguru
    """
    if settings.log_format == "json":
        # For JSON, use simple format - serialization is handled by serialize=True
        return "{message}"
    else:
        # Human-readable format
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )


class LoggingMiddleware:
    """Middleware for logging HTTP requests and responses."""

    def __init__(self, app: Any):
        """Initialize middleware.

        Args:
            app: ASGI application
        """
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Process request and log details.

        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] == "http":
            import time

            start_time = time.time()

            # Log request
            method = scope["method"]
            path = scope.get("path", "")
            query_string = scope.get("query_string", b"").decode("utf-8")
            full_path = f"{path}?{query_string}" if query_string else path

            logger.info(f"Request: {method} {full_path}")

            # Process request
            status_code = None

            async def send_wrapper(message: Any) -> None:
                """Wrap send to capture status code."""
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message["status"]
                await send(message)

            try:
                await self.app(scope, receive, send_wrapper)
            except Exception as e:
                logger.error(f"Request failed: {e}")
                raise
            finally:
                # Log response
                process_time = (time.time() - start_time) * 1000  # ms
                if status_code:
                    level = "info" if status_code < 400 else "error" if status_code >= 500 else "warning"
                    log_func = getattr(logger, level)
                    log_func(
                        f"Response: {method} {full_path} - "
                        f"Status: {status_code} - Time: {process_time:.2f}ms"
                    )
        else:
            await self.app(scope, receive, send)


def get_logger(name: str):
    """Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Logger instance
    """
    return logger.bind(name=name)
