"""Tests for OCR mapping endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

def test_map_fields_success(client: TestClient):
    """Test successful field mapping."""
    # Mock OCR service response
    mock_ocr_result = {
        "text": "Nama: JOHN DOE\nNIK: 123456789",
        "confidence": 0.95,
        "regions": [
            {
                "text": "Nama: JOHN DOE",
                "confidence": 0.98,
                "bbox": [[10, 10], [150, 10], [150, 30], [10, 30]],
            },
            {
                "text": "NIK:",
                "confidence": 0.99,
                "bbox": [[10, 40], [50, 40], [50, 60], [10, 60]],
            },
            {
                "text": "123456789",
                "confidence": 0.97,
                "bbox": [[60, 40], [150, 40], [150, 60], [60, 60]],
            }
        ],
        "region_count": 3,
        "language": "id"
    }

    with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
        mock_service = AsyncMock()
        # The endpoint calls map_text_from_file which we should mock
        mock_service.map_text_from_file.return_value = {
            "nama": "JOHN DOE",
            "nik": "123456789"
        }
        mock_get_service.return_value = mock_service

        # Mock image content
        image_content = b"fake image content"
        files = {"file": ("test.png", image_content, "image/png")}
        data = {"fields": "Nama, NIK", "lang": "id"}

        response = client.post("/api/v1/ocr/map", files=files, data=data)

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["data"]["nama"] == "JOHN DOE"
    assert result["data"]["nik"] == "123456789"
    assert "processing_time_ms" in result
