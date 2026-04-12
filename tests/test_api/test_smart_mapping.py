import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_auto_mapping_ktp_success(client: TestClient, mock_image_bytes):
    """Test automatic document classification and mapping for KTP."""
    # Mock OCR result mimicking a KTP
    mock_ocr_result = {
        "text": "PROVINSI DKI JAKARTA\nNIK : 3171234567890123\nNama : BUDI UTOMO",
        "confidence": 0.95,
        "regions": [
            {"text": "PROVINSI DKI JAKARTA", "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]], "confidence": 0.99},
            {"text": "NIK", "bbox": [[10, 50], [50, 50], [50, 70], [10, 70]], "confidence": 0.99},
            {"text": ":", "bbox": [[60, 50], [70, 50], [70, 70], [60, 70]], "confidence": 0.99},
            {"text": "3171234567890123", "bbox": [[100, 50], [300, 50], [300, 70], [100, 70]], "confidence": 0.99},
            {"text": "Nama", "bbox": [[10, 90], [50, 90], [50, 110], [10, 110]], "confidence": 0.99},
            {"text": ":", "bbox": [[60, 90], [70, 90], [70, 110], [60, 110]], "confidence": 0.99},
            {"text": "BUDI UTOMO", "bbox": [[100, 90], [300, 90], [300, 110], [100, 110]], "confidence": 0.99},
        ],
        "region_count": 7,
        "language": "id"
    }

    # We mock the repository to return the KTP-like OCR result
    with patch("app.repositories.ocr_repository.RapidOCRRepository.extract_text", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_ocr_result
        
        # We don't send any 'fields' to trigger auto-detection
        files = {"file": ("ktp.png", mock_image_bytes, "image/png")}
        data = {"lang": "id"}
        
        response = client.post("/api/v1/ocr/map", files=files, data=data)
        
        if response.status_code != 200:
            print(f"Error Response: {response.json()}")
            
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["document_type"] == "ktp"
        assert result["data"]["nik"] == "3171234567890123"
        assert result["data"]["nama"] == "Budi Utomo"
        # Check that other fields from KTP template are present but null
        assert "agama" in result["data"]

def test_auto_mapping_unknown_document(client: TestClient, mock_image_bytes):
    """Test mapping behavior when document is not recognized."""
    mock_ocr_result = {
        "text": "Some random text that is not a known document type",
        "confidence": 0.90,
        "regions": [
            {"text": "Some random text", "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]], "confidence": 0.99},
        ],
        "region_count": 1,
        "language": "en"
    }

    with patch("app.repositories.ocr_repository.RapidOCRRepository.extract_text", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_ocr_result
        
        files = {"file": ("test.png", mock_image_bytes, "image/png")}
        data = {"lang": "en"}
        
        response = client.post("/api/v1/ocr/map", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["document_type"] is None
        assert result["data"] == {}
