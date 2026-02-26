"""Application configuration settings.

This module manages all configuration for the RogaScan FastAPI OCR service,
using environment variables with sensible defaults.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

# Project base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings.

    All settings can be overridden via environment variables.
    Defaults are provided for development environments.
    """

    # Application Info
    app_name: str = Field(default="RogaScan", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    app_description: str = Field(
        default="FastAPI OCR Service with PaddleOCR", alias="APP_DESCRIPTION"
    )
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=1, alias="WORKERS")

    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")

    # PaddleOCR Configuration
    paddleocr_lang: str = Field(default="en", alias="PADDLEOCR_LANG")
    paddleocr_use_angle_cls: bool = Field(
        default=True, alias="PADDLEOCR_USE_ANGLE_CLS"
    )

    # Upload Configuration
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")
    allowed_extensions: List[str] = Field(
        default=["jpg", "jpeg", "png", "bmp", "tiff", "webp"],
        alias="ALLOWED_EXTENSIONS",
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="text", alias="LOG_FORMAT")  # 'json' or 'text'
    log_file_path: str = Field(default="logs/app.log", alias="LOG_FILE_PATH")
    log_rotation: str = Field(default="500 MB", alias="LOG_ROTATION")
    log_retention: str = Field(default="10 days", alias="LOG_RETENTION")

    # Performance Configuration
    request_timeout_seconds: int = Field(default=60, alias="REQUEST_TIMEOUT_SECONDS")
    async_processing_enabled: bool = Field(
        default=True, alias="ASYNC_PROCESSING_ENABLED"
    )

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert max upload size from MB to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def log_file_dir(self) -> Path:
        """Get log file directory."""
        return BASE_DIR / self.log_file_path.rsplit("/", 1)[0]

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins from various formats."""
        # Handle both string and list formats
        if isinstance(self.cors_origins, str):
            # Try to parse as JSON-like list
            import json

            try:
                origins = json.loads(self.cors_origins)
                return origins if isinstance(origins, list) else [origins]
            except json.JSONDecodeError:
                # Split by comma if not valid JSON
                return [o.strip() for o in self.cors_origins.split(",")]
        return self.cors_origins


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    Call this function throughout the application to access settings.

    Returns:
        Settings: Cached application settings
    """
    return Settings()


# Global settings instance for easy imports
settings = get_settings()
