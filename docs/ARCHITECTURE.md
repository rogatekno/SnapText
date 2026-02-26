# RogaScan Architecture

This document provides comprehensive context about the RogaScan system architecture for developers and AI agents.

## Overview

RogaScan is a FastAPI-based OCR (Optical Character Recognition) service built with the **Repository Pattern** for clean separation of concerns. The system uses PaddleOCR 2.10.0 with PaddlePaddle 2.6.2 as the text extraction engine and provides RESTful API endpoints for text extraction and visualization.

## Dependency Version Compatibility

**IMPORTANT**: RogaScan uses specific versions for compatibility:
- **PaddlePaddle 2.6.2** (NOT 3.x)
- **PaddleOCR 2.10.0** (2.7.x - 2.10.x range)

PaddlePaddle 3.x has PIR (new IR) that is incompatible with PaddleOCR, causing errors like:
```
ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
```

## Architecture Pattern: Repository Pattern

### Why Repository Pattern?

The Repository Pattern abstracts data access logic, providing several benefits:

1. **Separation of Concerns**: Business logic (Service layer) is separate from data access (Repository layer)
2. **Testability**: Easy to mock repositories for unit testing
3. **Flexibility**: Can swap OCR engines without changing service/API code
4. **Maintainability**: Clear boundaries make code easier to understand and modify

### Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│                 (app/api/)                               │
│  - FastAPI endpoints                                     │
│  - Request/response validation                           │
│  - Route definitions                                     │
│  Files: ocr.py, health.py                                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Service Layer                           │
│                (app/services/)                           │
│  - Business logic coordination                           │
│  - Input validation                                      │
│  - Orchestration of repository operations                │
│  - Error handling and translation                        │
│  File: ocr_service.py                                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                Repository Layer                          │
│              (app/repositories/)                         │
│  - Abstract interface (base.py)                          │
│  - Concrete implementation (ocr_repository.py)           │
│  - Direct integration with PaddleOCR                     │
│  - Image preprocessing and format conversion             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              External Services                           │
│  - PaddleOCR (text extraction engine)                   │
│  - PIL/OpenCV (image processing)                        │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure and Purpose

```
rogascan/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, lifespan, middleware
│   │
│   ├── api/                        # API Layer - Routes and endpoints
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── ocr.py          # POST /extract, /visualize, GET /info
│   │           └── health.py       # GET /health
│   │
│   ├── core/                       # Core application infrastructure
│   │   ├── __init__.py
│   │   ├── config.py               # Settings from env vars, BaseSettings
│   │   ├── exceptions.py           # Custom exception classes
│   │   └── logging.py              # Loguru configuration
│   │
│   ├── models/                     # Data models and schemas
│   │   ├── __init__.py
│   │   └── schemas.py              # Pydantic models (request/response)
│   │
│   ├── repositories/               # Repository Layer - Data access
│   │   ├── __init__.py
│   │   ├── base.py                 # OCRRepositoryInterface (ABC)
│   │   └── ocr_repository.py       # PaddleOCRRepository implementation
│   │
│   ├── services/                   # Service Layer - Business logic
│   │   ├── __init__.py
│   │   └── ocr_service.py          # OCRService class
│   │
│   └── utils/                      # Utility functions
│       ├── __init__.py
│       └── image_utils.py          # Image processing helpers
│
├── docs/                           # Project documentation
│   ├── README.md                   # Documentation index
│   ├── ARCHITECTURE.md             # This file
│   ├── SETUP.md                    # Installation guide
│   ├── API.md                      # API reference
│   └── DEVELOPMENT.md              # Development workflow
│
├── tests/                          # Test suite
│   ├── conftest.py                 # Pytest fixtures
│   └── test_api/
│       ├── __init__.py
│       └── test_ocr.py             # Endpoint tests
│
├── .env.example                    # Environment variables template
├── .gitignore
├── pyproject.toml                  # Python 3.12+ project config
├── requirements.txt                # Pip compatibility
└── README.md                       # Main project README
```

## Key Components Explained

### 1. API Layer (`app/api/`)

**Responsibility**: Handle HTTP requests/responses, delegate to services

**Key Files**:
- `ocr.py`: Main OCR endpoints
  - `POST /extract` - Extract text from image
  - `POST /visualize` - Get image with bounding boxes
  - `GET /info` - Service information

- `health.py`: Health check endpoint
  - `GET /health` - Service health status

**Conventions**:
- Use FastAPI router pattern
- Validate with Pydantic models
- Return typed response models
- Handle exceptions via middleware

### 2. Service Layer (`app/services/`)

**Responsibility**: Business logic, validation, orchestration

**Key Class**: `OCRService`

**Key Methods**:
```python
async def extract_text_from_file(file_content, filename, lang)
    # 1. Validate file (size, format)
    # 2. Load and convert image
    # 3. Call repository.extract_text()
    # 4. Add metadata and return result

async def visualize_file(file_content, filename)
    # 1. Validate file
    # 2. Call repository.visualize_detections()
    # 3. Convert result to bytes
    # 4. Return image with metadata
```

**Conventions**:
- Don't know about HTTP (no FastAPI types)
- Return domain objects (dicts, not response models)
- Raise domain exceptions (from `app.core.exceptions`)
- Use repositories for data access

### 3. Repository Layer (`app/repositories/`)

**Responsibility**: Abstract data access, interface to external services

**Interface**: `OCRRepositoryInterface` (Abstract Base Class)
```python
class OCRRepositoryInterface(ABC):
    @abstractmethod
    async def extract_text(image, lang) -> Dict: pass

    @abstractmethod
    async def visualize_detections(image) -> Tuple[Image, Dict]: pass

    @abstractmethod
    def is_model_loaded() -> bool: pass
```

**Implementation**: `PaddleOCRRepository`
- Wraps PaddleOCR 2.10.0 library
- Handles image format conversion (PIL ↔ OpenCV)
- Manages model lifecycle (lazy loading)
- Returns structured data (not HTTP responses)
- Environment variables disable OneDNN/MKLDNN for compatibility

**Conventions**:
- No business logic
- No knowledge of services/APIs
- Pure data access and transformation
- Return plain Python types (dicts, tuples)

### 4. Core Module (`app/core/`)

**Purpose**: Cross-cutting concerns and infrastructure

#### config.py
- `Settings` class (Pydantic BaseSettings)
- Loads from `.env` file
- Cached via `@lru_cache`
- Access via `get_settings()`

#### exceptions.py
- `RogaScanException` (base)
- `ValidationError`, `OCRError`, `FileProcessingError`
- Exception handlers for FastAPI

#### logging.py
- Loguru configuration
- Console and file handlers
- Rotation and retention
- `LoggingMiddleware` for request logging

### 5. Models (`app/models/`)

**Purpose**: Pydantic schemas for validation

**Key Models**:
- `OCRResult`: Extraction result
- `TextRegion`: Individual text region with bbox
- `BoundingBox`: 4-point polygon
- `HealthResponse`: Health check data
- `ErrorResponse`: Standard error format

**Conventions**:
- Use Pydantic v2 syntax
- Field descriptions for OpenAPI docs
- Validators for complex constraints
- Separate request/response models

## Data Flow

### Text Extraction Flow

```
Client Request
    │
    ▼
[API Layer] app/api/v1/endpoints/ocr.py
    │ 1. Parse multipart form data
    │ 2. Extract file bytes and params
    ▼
[Service Layer] app/services/ocr_service.py
    │ 3. Validate file size
    │ 4. Validate file extension
    │ 5. Load PIL Image from bytes
    │ 6. Convert to RGB if needed
    ▼
[Repository Layer] app/repositories/ocr_repository.py
    │ 7. Convert PIL to OpenCV format
    │ 8. Call PaddleOCR.ocr()
    │ 9. Parse results into dict
    ▼
[Return Path]
    │ 10. Service adds metadata (filename)
    │ 11. API converts to response model
    │ 12. FastAPI serializes to JSON
    ▼
Client Response
```

### Visualization Flow

```
Client Request
    │
    ▼
[API Layer] ocr.py
    │ 1. Receive image file
    ▼
[Service Layer] ocr_service.py
    │ 2. Validate file
    │ 3. Load PIL Image
    ▼
[Repository Layer] ocr_repository.py
    │ 4. Get OCR results (text regions)
    │ 5. Draw bounding boxes on image copy
    │ 6. Return annotated PIL Image
    ▼
[Service Layer] ocr_service.py
    │ 7. Convert PIL Image to bytes (PNG)
    ▼
[API Layer] ocr.py
    │ 8. Return Response with:
    │    - Image bytes
    │    - Content-Type: image/png
    │    - X-Regions-Count header
    │    - X-Processing-Time-Ms header
    ▼
Client Response (PNG image)
```

## Error Handling Strategy

### Exception Hierarchy

```
Exception
    │
    ├── RogaScanException (base)
    │    ├── ValidationError
    │    │    ├── ImageFormatError
    │    │    └── FileSizeError
    │    ├── FileProcessingError
    │    ├── OCRError
    │    └── ModelLoadError
    │
    └── HTTPException (FastAPI)
```

### Error Response Format

All errors return consistent JSON:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {
      "key": "additional context"
    }
  }
}
```

### Exception Handlers

Located in `app/core/exceptions.py`:
- `rogascan_exception_handler` - Custom exceptions → 400
- `http_exception_handler` - HTTPException → preserve status
- `generic_exception_handler` - Unexpected → 500

## Configuration

### Environment Variables

Loaded from `.env` file (see `.env.example`):

```bash
# Application
APP_NAME=RogaScan
ENVIRONMENT=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000

# PaddleOCR
PADDLEOCR_USE_GPU=false
PADDLEOCR_LANG=en

# Upload limits
MAX_UPLOAD_SIZE_MB=10
ALLOWED_EXTENSIONS=["jpg","jpeg","png","bmp"]

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text
```

### Settings Access Pattern

```python
from app.core.config import get_settings

settings = get_settings()
# Settings are cached (singleton)
max_size = settings.max_upload_size_bytes
is_dev = settings.is_development
```

## Conventions and Standards

### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`

### Type Hints
- All functions have return types
- All parameters have type hints
- Use `|` for unions (Python 3.12+)
- Use `Optional[T]` for nullable values

### Async/Await
- All I/O operations are async
- Repository methods are async
- Service methods are async
- Endpoints are async

### Import Organization
```python
# 1. Standard library
import io
from typing import Dict

# 2. Third-party
from fastapi import APIRouter
from pydantic import BaseModel

# 3. Local imports
from app.core.config import get_settings
from app.models.schemas import OCRResult
```

### Docstrings
- Use Google-style docstrings
- Include Args, Returns, Raises sections
- Document complex logic inline

### Logging
```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Informational message")
logger.error("Error occurred", exc_info=True)
```

## Testing Strategy

### Test Organization
```
tests/
├── conftest.py           # Shared fixtures
└── test_api/
    └── test_ocr.py       # Endpoint tests
```

### Key Fixtures (conftest.py)
- `client` - TestClient for FastAPI
- `mock_image` - PIL Image for testing
- `mock_image_bytes` - Image as bytes
- `mock_ocr_repository` - Mocked repository
- `mock_ocr_service` - Mocked service

### Testing Patterns
1. **Unit Tests**: Test services/repositories in isolation
2. **Integration Tests**: Test endpoints with mocked dependencies
3. **Async Tests**: Use pytest-asyncio
4. **Fixtures**: Use fixtures for common test data

## Performance Considerations

1. **Lazy Loading**: PaddleOCR model loaded on first use
2. **Singleton Pattern**: Single repository/service instance
3. **Async Processing**: Non-blocking I/O throughout
4. **Request Logging**: Track processing times

## Future Scalability

The architecture supports:
- **Caching**: Add cache layer in service
- **Queue**: Move to async task queue (Celery)
- **Multi-engine**: Swap PaddleOCR for other engines
- **Distributed**: Run workers separately
- **Monitoring**: Add metrics in middleware

## Summary for AI Agents

When working with this codebase:

1. **To add a new endpoint**:
   - Create route in `app/api/v1/endpoints/`
   - Use `get_ocr_service()` to get service
   - Call service methods (don't use repository directly)
   - Return typed response models

2. **To modify business logic**:
   - Edit `app/services/ocr_service.py`
   - Keep HTTP concerns out of service layer
   - Raise custom exceptions from `app.core.exceptions`

3. **To change OCR engine**:
   - Implement `OCRRepositoryInterface` in new file
   - Update `get_ocr_repository()` to return new implementation
   - No changes needed in service or API layers

4. **To add configuration**:
   - Add field to `Settings` in `app/core/config.py`
   - Add to `.env.example`
   - Access via `get_settings()`

5. **Follow the layers**:
   - API: HTTP, FastAPI, responses
   - Service: Business logic, validation
   - Repository: Data access, external APIs
   - Core: Cross-cutting concerns

The key principle: **Each layer has a single responsibility and clear boundaries**.
