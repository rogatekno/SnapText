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
        assert "ocr_model_loaded" in data
        assert "environment" in data

    def test_health_check_when_initialized(self, initialized_test_app: TestClient):
        """Test health check when OCR is initialized."""
        response = initialized_test_app.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["ocr_model_loaded"] is True


class TestSmartScanEndpoint:
    """Tests for OCR smart-scan endpoint."""

    def test_smart_scan_success(self, client: TestClient, mock_image_bytes):
        """Test successful smart scan."""
        # Mock the OCR service
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
                "/api/v1/ocr/smart-scan",
                files=files,
                data=data,
            )

        assert response.status_code == 200
        result = response.json()

        assert result["success"] is True
        assert result["data"]["nama"] == "John Doe"
        assert result["document_type"] == "ktp"
        assert "processing_time_ms" in result

    def test_smart_scan_auto_classify(self, client: TestClient, mock_image_bytes):
        """Test smart scan with auto-classification (no fields)."""
        with patch("app.api.v1.endpoints.ocr.get_ocr_service") as mock_get_service:
            mock_service = Mock()
            mock_service.map_text_from_file = AsyncMock(
                return_value={
                    "nama": "Jane Doe",
                    "_document_type": "ktp"
                }
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}
            # No fields provided

            response = client.post(
                "/api/v1/ocr/smart-scan",
                files=files,
            )

        assert response.status_code == 200
        result = response.json()
        assert result["document_type"] == "ktp"

    def test_smart_scan_missing_file(self, client: TestClient):
        """Test smart scan without file returns error."""
        response = client.post("/api/v1/ocr/smart-scan")

        assert response.status_code == 422

    def test_smart_scan_invalid_language(self, client: TestClient, mock_image_bytes):
        """Test smart scan with invalid language code."""
        files = {"file": ("test.png", mock_image_bytes, "image/png")}
        data = {"lang": "invalid_lang"}

        response = client.post(
            "/api/v1/ocr/smart-scan",
            files=files,
            data=data,
        )

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
            mock_service.map_text_from_file = AsyncMock(
                side_effect=OCRError(
                    message="OCR processing failed",
                    details={"error": "Model error"}
                )
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("test.png", mock_image_bytes, "image/png")}

            response = client.post(
                "/api/v1/ocr/smart-scan",
                files=files,
            )

        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "OCR_ERROR"


class TestOCRServiceLogic:
    """Tests for individual OCR service logic (Title Case, Delimiters)."""

    def test_format_value_title_case(self):
        """Test that names are properly title-cased."""
        from app.services.ocr_service import OCRService
        service = OCRService(repository=Mock())
        
        # Names should be title case
        assert service._format_value("nama", "JOHN DOE") == "John Doe"
        assert service._format_value("nama_lengkap", "jANE dOE") == "Jane Doe"
        
        # Other fields remain as is (except if in name_patterns)
        assert service._format_value("alamat", "JL. RAYA NO. 1") == "Jl. Raya No. 1"
        assert service._format_value("pekerjaan", "PEGAWAI SWASTA") == "Pegawai Swasta"
        assert service._format_value("agama", "ISLAM") == "Islam"
        assert service._format_value("jenis_kelamin", "PEREMPUAN") == "Perempuan"
        assert service._format_value("kecamatan", "KALIDERES") == "Kalideres"

    def test_delimiter_cleaning(self):
        """Test that full-width and common delimiters are cleaned."""
        from app.services.ocr_service import OCRService
        service = OCRService(repository=Mock())
        
        regions = [
            {"text": "Nama", "bbox": [[0,0],[10,0],[10,10],[0,10]]},
            {"text": "：John Doe", "bbox": [[20,0],[40,0],[40,10],[20,10]]} # Full-width colon
        ]
        
        result = service._perform_mapping(regions, ["Nama"])
        assert result["nama"] == "John Doe"
        
        regions_2 = [
            {"text": "NIK", "bbox": [[0,0],[10,0],[10,10],[0,10]]},
            {"text": "= 12345", "bbox": [[20,0],[40,0],[40,10],[20,10]]}
        ]
        result_2 = service._perform_mapping(regions_2, ["NIK"])
        assert result_2["nik"] == "12345"

    def test_multi_box_joining(self):
        """Test that multiple horizontal boxes are joined with spaces (Fix Mira Setiawan bug)."""
        from app.services.ocr_service import OCRService
        service = OCRService(repository=Mock())
        
        # Simulated regions: "Nama" (label), then "Mira" and "Setiawan" as separate boxes
        regions = [
            {"text": "Nama", "bbox": [[0,0],[100,0],[100,50],[0,50]]},
            {"text": "Mira", "bbox": [[150,0],[250,0],[250,50],[150,50]]},
            {"text": "Setiawan", "bbox": [[260,0],[360,0],[360,50],[260,50]]}
        ]
        
        result = service._perform_mapping(regions, ["Nama"])
        assert result["nama"] == "Mira Setiawan"

    def test_sequential_mapping_bpjs_tk(self):
        """Test the sequential mapping strategy used for label-less documents (BPJS TK)."""
        from app.services.ocr_service import OCRService
        service = OCRService(repository=Mock())
        
        # Simulated regions for BPJS TK
        regions = [
            {"text": "KARTU PESERTA", "bbox": [[0,0],[100,0],[100,20],[0,20]]},
            {"text": "3306 0445 0195 0002", "bbox": [[0,30],[200,30],[200,50],[0,50]]},
            {"text": "13032513510", "bbox": [[0,60],[150,60],[150,80],[0,80]]},
            {"text": "CANDRA RESMI", "bbox": [[0,100],[150,100],[150,120],[0,120]]},
            {"text": "10 2013", "bbox": [[0,150],[100,150],[100,170],[0,170]]}
        ]
        
        fields = ["Nomor Kartu", "Nomor KPJ", "Nama", "Tgl Terdaftar"]
        result = service._perform_sequential_mapping(regions, fields, "bpjs_tk")
        
        assert result["nomor_kartu"] == "3306 0445 0195 0002"
        assert result["nomor_kpj"] == "13032513510"
        assert result["nama"] == "CANDRA RESMI"
        assert result["tgl_terdaftar"] == "10 2013"

    def test_horizontal_gap_protection(self):
        """Test that regions with a large gap are NOT joined (to avoid blood type leakage)."""
        from app.services.ocr_service import OCRService
        service = OCRService(repository=Mock())
        
        # Simulated regions for Jenis Kelamin: "Jenis Kelamin" (label), "PEREMPUAN" (value), then a large gap, then "Gol. Darah"
        regions = [
            {"text": "Jenis Kelamin", "bbox": [[0,0],[100,0],[100,20],[0,20]]},
            {"text": "PEREMPUAN", "bbox": [[120,0],[200,0],[200,20],[120,20]]},
            {"text": "Gol. Darah : B", "bbox": [[500,0],[650,0],[650,20],[500,20]]} # Large gap
        ]
        
        result = service._perform_mapping(regions, ["Jenis Kelamin"])
        # Should only contain PEREMPUAN
        assert result["jenis_kelamin"] == "PEREMPUAN"
