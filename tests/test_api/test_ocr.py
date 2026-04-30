"""Tests for OCR API endpoints (Modular & KTP focused)."""

import io
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns correct response."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["healthy", "initializing"]
        assert "version" in data
        assert "ocr_model_loaded" in data
        assert "environment" in data

    def test_health_check_when_initialized(self, initialized_test_app: TestClient):
        """Test health check when OCR is initialized."""
        response = initialized_test_app.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["ocr_model_loaded"] is True


class TestKTPScanEndpoint:
    """Tests for OCR KTP scan endpoint."""

    def test_scan_ktp_success(self, client: TestClient, mock_image_bytes):
        """Test successful KTP scan."""
        # Mock the OCR service coordinator
        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
            mock_service.map_text_from_file = AsyncMock(
                return_value={
                    "nama": "John Doe",
                    "nik": "1234567890",
                    "_document_type": "ktp"
                }
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}
            data = {"fields": "Nama, NIK", "lang": "id"}

            response = client.post(
                "/api/v1/ocr/scan",
                files=files,
                data=data,
            )

        assert response.status_code == 200
        result = response.json()

        assert result["success"] is True
        assert result["data"]["nama"] == "John Doe"
        assert result["document_type"] == "ktp"
        assert "processing_time_ms" in result

    def test_scan_ktp_auto_classify(self, client: TestClient, mock_image_bytes):
        """Test KTP scan with auto-classification."""
        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
            mock_service.map_text_from_file = AsyncMock(
                return_value={
                    "nama": "Jane Doe"
                }
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}

            response = client.post(
                "/api/v1/ocr/scan",
                files=files,
            )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_scan_missing_file(self, client: TestClient):
        """Test scan without file returns error."""
        response = client.post("/api/v1/ocr/scan")

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


