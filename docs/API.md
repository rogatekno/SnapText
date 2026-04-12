# SnapText API Reference

Complete API documentation for the SnapText OCR service.

## Base URL

```
http://localhost:8000
```

## API Endpoints

### Health & Info

#### GET `/api/v1/health`

Check service health and OCR model status.

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "paddleocr_loaded": true,
  "environment": "development"
}
```

**Status Codes**:
- `200` - Service is healthy

---

#### GET `/api/v1/ocr/info`

Get service configuration and capabilities.

**Response**:
```json
{
  "success": true,
  "data": {
    "supported_formats": ["jpg", "jpeg", "png", "bmp", "tiff", "webp"],
    "max_file_size": {
      "bytes": 10485760,
      "mb": 10
    },
    "supported_languages": [
      "en", "id", "ch", "japan", "korean",
      "vi", "fr", "german", "it", "portuguese", "spanish"
    ],
    "default_language": "en",
    "service_ready": true
  }
}
```

---

### OCR Operations

#### POST `/api/v1/ocr/smart-scan`

Automatically classify document and extract specific fields or tabular data.

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `file` (required): Image file
  - `fields` (optional): Comma-separated labels to extract. If empty, auto-classification is used.
  - `tables` (optional): JSON-encoded table definitions.
  - `lang` (optional): Language code, default `"id"`

**Example cURL**:
```bash
# Auto-classification
curl -X POST http://localhost:8000/api/v1/ocr/smart-scan \
  -F "file=@document.jpg" \
  -F "lang=id"

# Specific Mapping
curl -X POST http://localhost:8000/api/v1/ocr/smart-scan \
  -F "file=@document.jpg" \
  -F "fields=Nama,NIK"
```

**Example Python (requests)****:
```python
import requests

with open("document.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/ocr/smart-scan",
        files={"file": f},
        data={"lang": "id"}
    )
result = response.json()
```

**Response** (Success):
```json
{
  "success": true,
  "data": {
    "nama": "JOHN DOE",
    "nik": "1234567890",
    "alamat": "JL. CONTOH NO. 1"
  },
  "document_type": "ktp",
  "processing_time_ms": 245.5
}
```

**Status Codes**:
- `200` - Success
- `400` - Validation error (file size, format)
- `422` - Invalid request parameters
- `500` - Internal error

**Supported Languages**:
| Code | Language |
|------|----------|
| `en` | English |
| `id` | Indonesian |
| `ch` | Chinese |
| `japan` | Japanese |
| `korean` | Korean |
| `vi` | Vietnamese |
| `fr` | French |
| `german` | German |
| `it` | Italian |
| `portuguese` | Portuguese |
| `spanish` | Spanish |

---

#### POST `/api/v1/ocr/map` (Legacy Alias)

**Deprecated**: Alias for `/api/v1/ocr/smart-scan`. Maintained for backward compatibility.

---

#### POST `/api/v1/ocr/visualize`

Return image with bounding boxes marking detected text regions.

**Request**:
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `file` (required): Image file

**Example cURL**:
```bash
curl -X POST http://localhost:8000/api/v1/ocr/visualize \
  -F "file=@document.jpg" \
  --output visualized.jpg
```

**Example Python (requests)**:
```python
import requests

with open("document.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/ocr/visualize",
        files={"file": f}
    )

# Save the image
with open("visualized.jpg", "wb") as out:
    out.write(response.content)

# Check metadata
print(f"Regions: {response.headers['x-regions-count']}")
print(f"Time: {response.headers['x-processing-time-ms']}ms")
```

**Response**:
- Content-Type: `image/png` or `image/jpeg`
- Headers:
  - `X-Regions-Count`: Number of detected regions
  - `X-Processing-Time-Ms`: Processing time in milliseconds
  - `X-Format`: Image format

**Visualized Image Features**:
- Green bounding boxes around detected text
- Red confidence scores above each box
- High-contrast visibility

**Status Codes**:
- `200` - Success (image bytes)
- `400` - Validation error
- `422` - Invalid request
- `500` - Internal error

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "additional": "context"
    }
  }
}
```

### Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `VALIDATION_ERROR` | Request validation failed | 400 |
| `FILE_PROCESSING_ERROR` | File could not be processed | 400 |
| `OCR_ERROR` | OCR processing failed | 400 |
| `MODEL_LOAD_ERROR` | Failed to load OCR model | 400 |
| `INTERNAL_ERROR` | Unexpected server error | 500 |

### Validation Error Example

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Unsupported image format: tiff",
    "details": {
      "filename": "document.tiff",
      "detected_format": "tiff",
      "allowed_formats": ["jpg", "jpeg", "png", "bmp", "webp"]
    }
  }
}
```

### File Size Error Example

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "File size exceeds maximum allowed size",
    "details": {
      "filename": "large.jpg",
      "size_mb": 15.5,
      "max_size_mb": 10
    }
  }
}
```

---

## Request Limits

### File Size
- Maximum: 10 MB (configurable via `MAX_UPLOAD_SIZE_MB`)
- Measured before processing

### Supported Image Formats
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- BMP (`.bmp`)
- WebP (`.webp`)

### Image Dimensions
- Minimum: 10x10 pixels
- Maximum: 10000x10000 pixels
- Recommended: > 100px width for best results

---

## Rate Limiting

Currently not implemented. Consider adding for production:
- Token bucket or leaky bucket algorithm
- Per-IP limits
- Endpoint-specific limits

---

## Interactive Documentation

When the service is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

These provide:
- Interactive API testing
- Request/response schemas
- Parameter descriptions
- Try-it-out functionality

---

## Usage Examples

### Extract Text from Multiple Images

```python
import requests
import os
from pathlib import Path

API_URL = "http://localhost:8000/api/v1/ocr/smart-scan"
IMAGE_DIR = Path("documents")

for image_path in IMAGE_DIR.glob("*.jpg"):
    with open(image_path, "rb") as f:
        response = requests.post(
            API_URL,
            files={"file": f},
            data={"lang": "en"}
        )

    if response.status_code == 200:
        result = response.json()
        print(f"{image_path.name}: {result['data']['text'][:50]}...")

        # Save text
        txt_path = image_path.with_suffix(".txt")
        with open(txt_path, "w") as out:
            out.write(result["data"]["text"])
```

### Process and Visualize

```python
import requests

API_URL = "http://localhost:8000"

# Smart scan
with open("document.jpg", "rb") as f:
    extract_response = requests.post(
        f"{API_URL}/api/v1/ocr/smart-scan",
        files={"file": f},
        data={"lang": "id"}
    )

result = extract_response.json()
print(f"Detected document: {result['document_type']}")

# Visualize
with open("document.jpg", "rb") as f:
    viz_response = requests.post(
        f"{API_URL}/api/v1/ocr/visualize",
        files={"file": f}
    )

with open("document_visualized.png", "wb") as out:
    out.write(viz_response.content)
```

### Batch Processing with Error Handling

```python
import requests
from typing import Optional

class OCRClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def extract(self, image_path: str, lang: str = "en") -> Optional[dict]:
        """Extract text with error handling."""
        try:
            with open(image_path, "rb") as f:
                response = requests.post(
                    f"{self.base_url}/api/v1/ocr/smart-scan",
                    files={"file": f},
                    data={"lang": lang},
                    timeout=30
                )

            if response.status_code == 200:
                return response.json()
            else:
                error = response.json()
                print(f"Error: {error['error']['message']}")
                return None

        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return None

# Usage
client = OCRClient()
result = client.extract("document.jpg", lang="en")
if result:
    print(result["data"]["text"])
```

---

## Performance Tips

1. **Image Optimization**:
   - Resize large images before upload
   - Use JPEG for photos (smaller size)
   - Use PNG for text/documents (better accuracy)

2. **Language Selection**:
   - Specify correct language for better accuracy
   - Use multilingual models for mixed content

3. **Batch Processing**:
   - Send requests concurrently (async)
   - Consider implementing batch endpoint

4. **Caching**:
   - Cache results by file hash
   - Store text for repeated documents

---

## Integration Examples

### FastAPI Client

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

with open("test.jpg", "rb") as f:
    response = client.post(
        "/api/v1/ocr/smart-scan",
        files={"file": ("test.jpg", f, "image/jpeg")},
        data={"lang": "en"}
    )
print(response.json())
```

### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('lang', 'en');

fetch('http://localhost:8000/api/v1/ocr/smart-scan', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## WebSocket Support (Future Enhancement)

Consider adding WebSocket for:
- Real-time processing updates
- Streaming results for large documents
- Progress notifications

---

## API Versioning

Current version: `v1`
URL prefix: `/api/v1/`

Future versions will maintain backward compatibility where possible.
