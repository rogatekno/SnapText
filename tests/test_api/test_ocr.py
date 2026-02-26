"""Tests for OCR API endpoints."""

import io
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns correct response."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["healthy", "initializing"]
        assert "version" in data
        assert "paddleocr_loaded" in data
        assert "environment" in data

    def test_health_check_when_initialized(self, initialized_test_app: TestClient):
        """Test health check when OCR is initialized."""
        response = initialized_test_app.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["paddleocr_loaded"] is True


class TestExtractEndpoint:
    """Tests for OCR extract endpoint."""

    def test_extract_success(self, client: TestClient, mock_image_bytes):
        """Test successful text extraction."""
        # Mock the OCR service
        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
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
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}
            data = {"lang": "en"}

            response = client.post(
                "/api/v1/ocr/extract",
                files=files,
                data=data,
            )

        assert response.status_code == 200
        result = response.json()

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["text"] == "Hello World\nTest Image"
        assert result["data"]["confidence"] == 0.95
        assert result["data"]["region_count"] == 2
        assert len(result["data"]["regions"]) == 2
        assert "processing_time_ms" in result

    def test_extract_with_different_language(self, client: TestClient, mock_image_bytes):
        """Test extraction with different language parameter."""
        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
            mock_service.extract_text_from_file = AsyncMock(
                return_value={
                    "text": "Indonesian text",
                    "confidence": 0.90,
                    "regions": [],
                    "region_count": 0,
                    "language": "id",
                }
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}
            data = {"lang": "id"}

            response = client.post(
                "/api/v1/ocr/extract",
                files=files,
                data=data,
            )

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["language"] == "id"

    def test_extract_missing_file(self, client: TestClient):
        """Test extract without file returns error."""
        response = client.post("/api/v1/ocr/extract")

        # FastAPI returns 422 for missing required field
        assert response.status_code == 422

    def test_extract_invalid_language(self, client: TestClient, mock_image_bytes):
        """Test extract with invalid language code."""
        files = {"file": ("test.png", mock_image_bytes, "image/png")}
        data = {"lang": "invalid_lang"}

        response = client.post(
            "/api/v1/ocr/extract",
            files=files,
            data=data,
        )

        # Should fail validation
        assert response.status_code == 422


class TestVisualizeEndpoint:
    """Tests for OCR visualize endpoint."""

    def test_visualize_success(self, client: TestClient, mock_image_bytes):
        """Test successful visualization."""
        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
            mock_service.visualize_file = AsyncMock(
                return_value=(
                    b"fake_image_bytes",
                    "PNG",
                    {"regions_count": 2, "processing_time_ms": 200.0},
                )
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}

            response = client.post(
                "/api/v1/ocr/visualize",
                files=files,
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "x-regions-count" in response.headers
        assert "x-processing-time-ms" in response.headers
        assert "x-format" in response.headers
        assert response.headers["x-regions-count"] == "2"

    def test_visualize_missing_file(self, client: TestClient):
        """Test visualize without file returns error."""
        response = client.post("/api/v1/ocr/visualize")

        assert response.status_code == 422


class TestInfoEndpoint:
    """Tests for OCR info endpoint."""

    def test_get_info(self, client: TestClient):
        """Test getting OCR service information."""
        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
            mock_service.get_supported_formats = AsyncMock(
                return_value=["jpg", "png", "jpeg", "bmp"]
            )
            mock_service.get_max_file_size = AsyncMock(
                return_value={"bytes": 10485760, "mb": 10}
            )
            mock_service.is_ready = Mock(return_value=True)
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/ocr/info")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert "supported_formats" in data["data"]
        assert "max_file_size" in data["data"]
        assert "supported_languages" in data["data"]
        assert len(data["data"]["supported_formats"]) > 0


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "docs_url" in data
        assert data["docs_url"] == "/docs"


class TestErrorHandling:
    """Tests for error handling."""

    def test_ocr_error_returns_proper_response(self, client: TestClient, mock_image_bytes):
        """Test that OCR errors are properly formatted."""
        from app.core.exceptions import OCRError

        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
            mock_service.extract_text_from_file = AsyncMock(
                side_effect=OCRError(
                    message="OCR processing failed",
                    details={"error": "Model error"}
                )
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}

            response = client.post(
                "/api/v1/ocr/extract",
                files=files,
            )

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "OCR_ERROR"
