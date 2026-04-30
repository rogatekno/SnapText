import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_ktp_scan_success(client: TestClient, mock_image_bytes):
    """Test KTP scanning and mapping."""
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

    with patch("app.repositories.ocr_repository.RapidOCRRepository.extract_text", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_ocr_result
        
        # Test the /scan endpoint
        files = {"file": ("ktp.png", mock_image_bytes, "image/png")}
        data = {"lang": "id"}
        
        response = client.post("/api/v1/ocr/scan", files=files, data=data)
        
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

def test_scan_unknown_document(client: TestClient, mock_image_bytes):
    """Test scanning behavior when document is not recognized."""
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
        
        response = client.post("/api/v1/ocr/scan", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["document_type"] == "unknown"

def test_ktp_scan_bleeding_prevention(client: TestClient, mock_image_bytes):
    """Test that spatial engine doesn't bleed into nearby labels or far-away text."""
    mock_ocr_result = {
        "text": "NIK : 317\nNama : MIRA\nJENIS KELAMIN : PEREMPUAN Gol. Darah : B\nKEWARGANEGARAAN : WNI  JAKARTA BARAT",
        "confidence": 0.95,
        "regions": [
            # NIK with a gap
            {"text": "NIK", "bbox": [[10, 1], [50, 1], [50, 5], [10, 5]], "confidence": 0.99},
            {"text": "317", "bbox": [[250, 1], [300, 1], [300, 5], [250, 5]], "confidence": 0.99},
            
            # Nama with a large gap (simulating the issue)
            {"text": "Nama", "bbox": [[10, 10], [50, 10], [50, 15], [10, 15]], "confidence": 0.99},
            {"text": "MIRA SETIAWAN", "bbox": [[250, 10], [450, 10], [450, 15], [250, 15]], "confidence": 0.99},

            # "Agama" label (potential false positive for Nama)
            # It's on a different line, but if fuzzy matching was too loose it might conflict
            {"text": "Agama", "bbox": [[10, 100], [60, 100], [60, 115], [10, 115]], "confidence": 0.99},
            {"text": "ISLAM", "bbox": [[250, 100], [350, 100], [350, 115], [250, 115]], "confidence": 0.99},

            # Line 3: Jenis Kelamin + Gol Darah
            {"text": "JENIS KELAMIN", "bbox": [[10, 20], [100, 20], [100, 40], [10, 40]], "confidence": 0.99},
            {"text": ":", "bbox": [[110, 20], [120, 20], [120, 40], [110, 40]], "confidence": 0.99},
            {"text": "PEREMPUAN", "bbox": [[300, 20], [420, 20], [420, 40], [300, 40]], "confidence": 0.99},
            {"text": "Gol. Darah", "bbox": [[450, 20], [550, 20], [550, 40], [450, 40]], "confidence": 0.99},
            {"text": ": B", "bbox": [[560, 20], [590, 20], [590, 40], [560, 40]], "confidence": 0.99},
            
            # Line 4: Kewarganegaraan + Distant Footer Noise
            # Width of card is 800 in this mock (based on max_x of noise)
            {"text": "KEWARGANEGARAAN", "bbox": [[10, 50], [150, 50], [150, 70], [10, 70]], "confidence": 0.99},
            {"text": ":", "bbox": [[160, 50], [170, 50], [170, 70], [160, 70]], "confidence": 0.99},
            {"text": "WNI", "bbox": [[180, 50], [230, 50], [230, 70], [180, 70]], "confidence": 0.99},
            {"text": "JAKARTA BARAT", "bbox": [[700, 50], [850, 50], [850, 70], [700, 70]], "confidence": 0.99},
        ],
        "region_count": 15,
        "language": "id"
    }

    with patch("app.repositories.ocr_repository.RapidOCRRepository.extract_text", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_ocr_result
        
        files = {"file": ("ktp_bleeding.png", mock_image_bytes, "image/png")}
        response = client.post("/api/v1/ocr/scan", files=files)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        
        # 1. Verify Nama is extracted even with large gap
        assert result["data"]["nama"] == "Mira Setiawan"
        
        # 2. Verify Agama correctly matches its own line, not Nama's
        assert result["data"]["agama"] == "Islam"

        # 3. Verify Jenis Kelamin DOES NOT include Gol. Darah
        assert result["data"]["jenis_kelamin"] == "PEREMPUAN"
        
        # 4. Verify Kewarganegaraan DOES NOT include the far-away JAKARTA BARAT
        # Gap is 700 - 230 = 470. Multiplier 4x20 = 80. Adaptive should skip it.
        assert result["data"]["kewarganegaraan"] == "Wni"

