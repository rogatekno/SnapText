"""Tests for OCR table mapping extraction."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

def test_map_tables_success(client: TestClient):
    """Test successful tabular data extraction."""
    # Mock OCR service result with regions representing a table
    # Row 1: Header
    # Row 2: Data 1
    # Row 3: Data 2
    mock_ocr_result = {
        "text": "Nama NIK\nBudi 123\nAni 456",
        "confidence": 0.95,
        "regions": [
            # Headers
            {"text": "Nama", "bbox": [[10, 10], [50, 10], [50, 30], [10, 30]], "confidence": 0.99},
            {"text": "NIK", "bbox": [[100, 10], [150, 10], [150, 30], [100, 30]], "confidence": 0.99},
            # Row 1
            {"text": "Budi", "bbox": [[10, 50], [50, 50], [50, 70], [10, 70]], "confidence": 0.98},
            {"text": "123", "bbox": [[100, 50], [150, 50], [150, 70], [100, 70]], "confidence": 0.98},
            # Row 2
            {"text": "Ani", "bbox": [[10, 90], [50, 90], [50, 110], [10, 110]], "confidence": 0.98},
            {"text": "456", "bbox": [[100, 90], [150, 90], [150, 110], [100, 110]], "confidence": 0.98},
        ],
        "region_count": 6,
        "language": "id"
    }

    with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
        mock_service = AsyncMock()
        mock_service.map_text_from_file.return_value = {
            "no_kk": "340408...",
            "anggota_keluarga": [
                {"nama": "Budi", "nik": "123"},
                {"nama": "Ani", "nik": "456"}
            ]
        }
        mock_get_service.return_value = mock_service

        table_defs = [
            {
                "name": "anggota_keluarga",
                "columns": ["Nama", "NIK"]
            }
        ]
        
        files = {"file": ("kk.png", b"fake content", "image/png")}
        data = {
            "fields": "No KK",
            "tables": json.dumps(table_defs),
            "lang": "id"
        }

        response = client.post("/api/v1/ocr/map", files=files, data=data)

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert "anggota_keluarga" in result["data"]
    assert len(result["data"]["anggota_keluarga"]) == 2
    assert result["data"]["anggota_keluarga"][0]["nama"] == "Budi"
    assert result["data"]["anggota_keluarga"][1]["nik"] == "456"
