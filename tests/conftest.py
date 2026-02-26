"""Pytest configuration and fixtures.

This module provides shared fixtures and configuration for testing.
"""

import io
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, get_settings
from app.repositories.ocr_repository import PaddleOCRRepository
from app.services.ocr_service import get_ocr_service


@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_image():
    """Create a mock test image.

    Returns:
        PIL Image with test content
    """
    # Create a simple test image
    img = Image.new("RGB", (200, 100), color="white")

    # Add some text
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(img)

    # Try to use a font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default()

    draw.text((10, 10), "Hello World", fill="black", font=font)
    draw.text((10, 50), "Test Image", fill="black", font=font)

    return img


@pytest.fixture
def mock_image_bytes(mock_image):
    """Get mock image as bytes.

    Returns:
        Image bytes
    """
    buffer = io.BytesIO()
    mock_image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def mock_ocr_result():
    """Create mock OCR result.

    Returns:
        Mock OCR result dictionary
    """
    return {
        "text": "Hello World\nTest Image",
        "confidence": 0.95,
        "regions": [
            {
                "text": "Hello World",
                "confidence": 0.98,
                "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]],
                "region_id": 1,
            },
            {
                "text": "Test Image",
                "confidence": 0.92,
                "bbox": [[10, 50], [100, 50], [100, 70], [10, 70]],
                "region_id": 2,
            },
        ],
        "region_count": 2,
        "language": "en",
        "processing_time_ms": 150.0,
    }


@pytest.fixture
def mock_ocr_repository(mock_ocr_result):
    """Create mock OCR repository.

    Args:
        mock_ocr_result: Mock OCR result to return

    Returns:
        Mocked OCR repository
    """
    repo = Mock(spec=PaddleOCRRepository)

    # Mock extract_text
    async def mock_extract(image, lang="en"):
        return mock_ocr_result.copy()

    repo.extract_text = AsyncMock(side_effect=mock_extract)

    # Mock visualize_detections
    async def mock_visualize(image):
        vis_image = Image.new("RGB", (200, 100), color="white")
        return vis_image, {
            "regions_count": mock_ocr_result["region_count"],
            "regions": mock_ocr_result["regions"],
            "processing_time_ms": 200.0,
        }

    repo.visualize_detections = AsyncMock(side_effect=mock_visualize)

    # Mock is_model_loaded
    repo.is_model_loaded = Mock(return_value=True)

    # Mock initialize
    async def mock_init():
        pass

    repo.initialize = AsyncMock(side_effect=mock_init)

    return repo


@pytest.fixture
def mock_ocr_service(monkeypatch, mock_ocr_repository):
    """Create mock OCR service with mocked repository.

    Args:
        monkeypatch: Pytest monkeypatch fixture
        mock_ocr_repository: Mocked OCR repository

    Returns:
        Mocked OCR service
    """
    from unittest.mock import MagicMock

    # Create mock service
    mock_service = MagicMock()
    mock_service.extract_text_from_file = AsyncMock(
        return_value={
            "text": "Hello World\nTest Image",
            "confidence": 0.95,
            "regions": [
                {
                    "text": "Hello World",
                    "confidence": 0.98,
                    "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]],
                    "region_id": 1,
                },
                {
                    "text": "Test Image",
                    "confidence": 0.92,
                    "bbox": [[10, 50], [100, 50], [100, 70], [10, 70]],
                    "region_id": 2,
                },
            ],
            "region_count": 2,
            "language": "en",
            "filename": "test.png",
        }
    )

    mock_service.visualize_file = AsyncMock(
        return_value=(b"fake_image_bytes", "PNG", {"regions_count": 2, "processing_time_ms": 200.0})
    )

    mock_service.is_ready = Mock(return_value=True)

    mock_service.get_supported_formats = AsyncMock(return_value=["jpg", "png", "jpeg"])

    mock_service.get_max_file_size = AsyncMock(
        return_value={"bytes": 10485760, "mb": 10}
    )

    return mock_service


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Import and reset singletons
    import app.repositories.ocr_repository as ocr_repo_module
    import app.services.ocr_service as ocr_service_module

    # Store original values
    orig_repo = ocr_repo_module._ocr_repository
    orig_service = ocr_service_module._ocr_service

    # Reset
    ocr_repo_module._ocr_repository = None
    ocr_service_module._ocr_service = None

    yield

    # Restore
    ocr_repo_module._ocr_repository = orig_repo
    ocr_service_module._ocr_service = orig_service


@pytest.fixture
async def initialized_test_app(client):
    """Get test client with initialized OCR service.

    Args:
        client: Test client fixture

    Returns:
        Initialized test client
    """
    # Initialize OCR service
    ocr_service = get_ocr_service()
    await ocr_service.initialize()

    yield client
