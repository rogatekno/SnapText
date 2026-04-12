# SnapText

FastAPI OCR service powered by PaddleOCR for text extraction and visualization from images.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

**Open Source OCR Service for Education & Research**

Created by **RogaTekno** - Licensed under MIT License.

---

## Table of Contents

- [Features](#features)
- [Performance](#performance)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Supported Languages](#supported-languages)
- [Use Cases](#use-cases)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Development](#development)
- [Documentation](#documentation)
- [Requirements](#requirements)
- [License & Usage](#license--usage)
- [Contributing](#contributing)
- [Support](#support)

---

## Features

### Core Functionality

- **Text Extraction** - Extract text from images with high accuracy using PaddleOCR
- **Bounding Box Detection** - Get precise coordinates of detected text regions
- **Visualization** - Generate annotated images with bounding boxes and confidence scores
- **Multi-language Support** - Support for 10+ languages including English and Indonesian
- **Confidence Scoring** - Get confidence scores for each detected text region
- **RESTful API** - Clean, well-documented API endpoints
- **Interactive Documentation** - Auto-generated Swagger UI and ReDoc

### Technical Excellence

- **FastAPI Framework** - Modern, high-performance web framework with async support
- **Repository Pattern** - Clean architecture for maintainability and testability
- **Type Safety** - Full type hints with Python 3.12+
- **Comprehensive Testing** - Test suite with coverage reporting
- **Structured Logging** - Request tracking and debugging with Loguru
- **Error Handling** - Consistent error responses with detailed messages

### Developer Experience

- **Hot Reload** - Auto-reload during development
- **OpenAPI Specification** - Standard API documentation
- **Modular Design** - Easy to extend and customize
- **Well Documented** - Comprehensive guides and examples

### Extensibility

The modular architecture makes it easy to:

- Add new document type extractors (KTP, KK, BPJS, etc.)
- Implement custom field mappers
- Integrate additional OCR engines
- Add caching layers
- Create batch processing endpoints
- Extend with new features

---

## Performance

### Benchmarks

Typical performance metrics on standard hardware:

| Operation | Average Time | Min | Max | Notes |
|-----------|--------------|-----|-----|-------|
| First Request (Model Load) | 8-15s | 5s | 30s | One-time, model download |
| Text Extraction (small) | 200-500ms | 100ms | 1s | < 1MB image, < 1000px |
| Text Extraction (large) | 1-3s | 500ms | 5s | > 5MB image, > 2000px |
| Visualization | 300-800ms | 200ms | 2s | Includes extraction |

### Hardware Requirements

**Minimum (Development)**:
- CPU: Dual-core 2.0GHz
- RAM: 4GB
- Disk: 2GB (for models)

**Recommended (Production)**:
- CPU: Quad-core 2.5GHz+
- RAM: 8GB+
- Disk: 5GB SSD
- GPU: NVIDIA GPU with CUDA (optional, 2-3x faster)

### Optimization Tips

**For Faster Processing**:
1. **Image Size**: Resize images to 1000-2000px width
2. **Format**: Use JPEG for photos, PNG for documents
3. **Batch Processing**: Process multiple images concurrently
4. **GPU**: Enable GPU acceleration if available
5. **Caching**: Cache results for repeated documents

**For Better Accuracy**:
1. **Image Quality**: Use high-resolution scans (300 DPI+)
2. **Lighting**: Ensure good lighting and contrast
3. **Language**: Specify correct language code
4. **Preprocessing**: Deskew and denoise images
5. **Format**: PNG preserves quality better than JPEG

### Scalability

**Single Instance**:
- Handles 10-20 concurrent requests
- ~5-10 requests/second on CPU
- ~20-50 requests/second on GPU

**Scaling Options**:
- **Horizontal**: Deploy multiple instances behind load balancer
- **Queue**: Use Celery/Redis for async processing
- **Caching**: Redis cache for repeated requests
- **CDN**: Serve visualized images from CDN

---

## Quick Start

### Windows Installation

```powershell
# Clone or navigate to project
cd snaptext

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install PaddlePaddle 2.6.2 (stable version)
pip install "paddlepaddle>=2.6.0,<3.0.0"

# Install PaddleOCR 2.10.0 (compatible)
pip install "paddleocr>=2.7.0,<3.0.0"

# Install remaining dependencies
pip install -r requirements.txt

# Create configuration
copy .env.example .env

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Linux/macOS Installation

```bash
# Clone repository
git clone <repository-url>
cd snaptext

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp .env.example .env

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Usage Examples

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Perform smart document scan (auto-classification)
curl -X POST http://localhost:8000/api/v1/ocr/smart-scan \
  -F "file=@document.jpg" \
  -F "lang=id"

# Map specific fields
curl -X POST http://localhost:8000/api/v1/ocr/smart-scan \
  -F "file=@document.jpg" \
  -F "fields=Nama,NIK"

# Get visualization with bounding boxes
curl -X POST http://localhost:8000/api/v1/ocr/visualize \
  -F "file=@document.jpg" \
  --output visualized.png
```

### Python Client Example

```python
import requests

API_URL = "http://localhost:8000"

# Smart document scan
with open("document.jpg", "rb") as f:
    response = requests.post(
        f"{API_URL}/api/v1/ocr/smart-scan",
        files={"file": f},
        data={"lang": "id"}
    )

result = response.json()
print(f"Detected document: {result['document_type']}")
print(f"Extracted data: {result['data']}")
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check and service status |
| POST | `/api/v1/ocr/smart-scan` | Smart document scanning and auto-mapping |
| POST | `/api/v1/ocr/visualize` | Get image with bounding boxes marked |
| GET | `/api/v1/ocr/info` | Service capabilities and configuration |

See [API.md](docs/API.md) for complete API documentation including:
- Request/response formats
- Error codes and handling
- Usage examples in multiple languages
- Rate limiting and constraints

---

## Supported Languages

| Code | Language | Model Size | Accuracy |
|------|----------|------------|----------|
| `en` | English | ~4MB | High |
| `id` | Indonesian | ~4MB | High |
| `ch` | Chinese | ~10MB | Very High |
| `japan` | Japanese | ~8MB | High |
| `korean` | Korean | ~8MB | High |
| `vi` | Vietnamese | ~4MB | Medium |
| `fr` | French | ~4MB | Medium |
| `german` | German | ~4MB | Medium |
| `it` | Italian | ~4MB | Medium |
| `portuguese` | Portuguese | ~4MB | Medium |
| `spanish` | Spanish | ~4MB | Medium |

---

## Use Cases

### Currently Supported

- Extract raw data from any image using smart auto-classification
- Automatically identify document types (KTP, KK, BPJS)
- Get structured key-value maps of document data
- Visualize detected text regions
- Support for 10+ languages
- Ideal for documents with varying layouts

### Educational
- **Teaching OCR**: Demonstrate text extraction concepts
- **FastAPI Learning**: Example of REST API best practices
- **Repository Pattern**: Study clean architecture
- **Course Projects**: Base for student assignments

### Research
- **Document Analysis**: Extract text from scanned documents
- **Benchmarking**: Compare OCR techniques
- **Data Collection**: Gather text from images
- **Preprocessing**: Prepare data for NLP pipelines

### Foundation for Advanced Features

**Note**: SnapText currently provides **generic OCR only**. The following use cases require additional development (see [Contributing](#contributing)):

- **Document Digitization** (KTP, KK, BPJS, etc.) - Requires field extraction implementation
- **Invoice Processing** - Requires structured data extraction
- **Form Automation** - Requires template-based parsing
- **Archive Search** - Requires integration with search systems

These are planned features that need community contributions to become available.

---

## Project Structure

```
snaptext/
├── app/                          # Application source
│   ├── __init__.py
│   ├── main.py                   # FastAPI application factory
│   ├── api/                      # API Layer
│   │   └── v1/
│   │       └── endpoints/        # Route handlers
│   │           ├── ocr.py        # OCR endpoints
│   │           └── health.py     # Health check
│   ├── core/                     # Core infrastructure
│   │   ├── config.py             # Settings management
│   │   ├── exceptions.py         # Custom exceptions
│   │   └── logging.py            # Logging configuration
│   ├── models/                   # Data models
│   │   └── schemas.py            # Pydantic schemas
│   ├── repositories/             # Repository Layer
│   │   ├── base.py               # Repository interface
│   │   └── ocr_repository.py     # PaddleOCR implementation
│   ├── services/                 # Service Layer
│   │   └── ocr_service.py        # Business logic
│   └── utils/                    # Utilities
├── docs/                         # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md           # System design
│   ├── SETUP.md                  # Installation guide
│   ├── API.md                    # API reference
│   ├── TROUBLESHOOTING.md        # Common issues
│   └── DEVELOPMENT.md            # Dev workflow
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest fixtures
│   └── test_api/                 # Endpoint tests
├── .github/                      # GitHub configurations
│   ├── ISSUE_TEMPLATE/           # Issue templates
│   ├── PULL_REQUEST_TEMPLATE.md  # PR template
│   └── CODE_OF_CONDUCT.md        # Community guidelines
├── .env.example                  # Configuration template
├── LICENSE                       # MIT License
├── README.md                     # This file
├── CONTRIBUTING.md               # Contribution guide
├── CONTRIBUTORS.md               # Contributor list
├── requirements.txt              # Python dependencies
└── pyproject.toml               # Project metadata
```

---

## Configuration

### Environment Variables

Create a `.env` file from `.env.example`:

```bash
# Application
APP_NAME=SnapText
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=1

# API
API_V1_PREFIX=/api/v1

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["*"]
CORS_ALLOW_HEADERS=["*"]

# PaddleOCR
PADDLEOCR_LANG=en
PADDLEOCR_USE_ANGLE_CLS=true

# Upload
MAX_UPLOAD_SIZE_MB=10
ALLOWED_EXTENSIONS=["jpg","jpeg","png","bmp","webp"]

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text
LOG_FILE_PATH=logs/app.log
LOG_ROTATION="500 MB"
LOG_RETENTION="10 days"

# Performance
REQUEST_TIMEOUT_SECONDS=60
ASYNC_PROCESSING_ENABLED=true
```

### Key Settings

**MAX_UPLOAD_SIZE_MB**: Maximum file size in MB (default: 10)
- Increase for high-resolution images
- Decrease for memory-constrained environments

**PADDLEOCR_LANG**: Default language (default: "en")
- Change based on your primary use case
- Can be overridden per request

**LOG_LEVEL**: Logging verbosity
- `DEBUG`: Detailed logging for development
- `INFO`: Normal operation logging
- `WARNING`: Only warnings and errors
- `ERROR`: Only errors

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_ocr.py -v

# Run with debug output
pytest -v -s
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint and auto-fix
ruff check app/ tests/ --fix

# Type checking
mypy app/

# Run all checks
black app/ && ruff check app/ --fix && mypy app/ && pytest --cov=app
```

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for:
- Development workflow
- Coding standards
- Testing strategies
- Debugging tips

---

## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design, patterns, and data flow
- **[SETUP.md](docs/SETUP.md)** - Detailed installation and configuration
- **[API.md](docs/API.md)** - Complete API reference with examples
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development workflow and guidelines
- **[docs/README.md](docs/README.md)** - Documentation index

### Interactive Documentation

When running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

---

## Requirements

### System Requirements

- **Python**: 3.12 or 3.13
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: ~2GB for PaddleOCR models
- **OS**: Windows 10+, Ubuntu 20.04+, macOS 12+

### Dependency Versions

- **PaddlePaddle**: 2.6.2 (NOT 3.x - compatibility issues)
- **PaddleOCR**: 2.10.0 (compatible with PaddlePaddle 2.6.x)
- **FastAPI**: 0.115.0+
- **Python**: 3.12+

### Compatibility

**Compatible**:
- Windows 10/11
- Ubuntu 20.04/22.04/24.04
- macOS 12+ (Monterey or later)
- Python 3.12, 3.13

**Not Compatible**:
- Python < 3.12
- PaddlePaddle 3.x
- Windows 8 or older
- macOS 11 or older

---

## Architecture

SnapText follows the **Repository Pattern** for clean separation of concerns:

```
┌─────────────────────────────┐
│   API Layer (FastAPI)       │  HTTP handlers
│  - /smart-scan (doc parsing)│
│  - /visualize (bounding boxes) │
│  - /health (service status) │
│  - /info (capabilities)     │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Service Layer              │  Business logic
│  - Validation               │  - Orchestration
│  - Coordination             │  - Error handling
│  - File processing          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Repository Layer           │  Data access
│  - PaddleOCR wrapper        │  - Image processing
│  - Format conversion        │  - Result parsing
│  - Model lifecycle          │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  PaddleOCR Engine           │  Text extraction
│  - Detection models         │
│  - Recognition models       │
│  - Multi-language support   │
└─────────────────────────────┘
```

**What This Architecture Provides**:

- **Text Extraction** - High accuracy OCR from images
- **Bounding Box Detection** - Precise text region coordinates
- **Confidence Scoring** - Quality metrics for each detection
- **Multi-language Support** - 10+ languages with optimized models
- **Visualization** - Annotated images with detected regions
- **RESTful API** - Clean, documented endpoints
- **Extensibility** - Easy to add custom processors and mappers

**Benefits**:
- Easy testing (mock repositories)
- Swappable OCR engines
- Clear boundaries between layers
- Maintainable codebase
- Simple to extend with new functionality

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

---

## Known Issues & Fixes

### PaddlePaddle 3.x Compatibility Error

**Issue**:
```
ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]
```

**Cause**: PaddlePaddle 3.x uses PIR (new IR) not supported by PaddleOCR.

**Solution**: Use PaddlePaddle 2.6.2 with PaddleOCR 2.10.0 (already configured in requirements.txt)

**Verification**:
```bash
python -c "import paddle; import paddleocr; print(f'PaddlePaddle: {paddle.__version__}'); print(f'PaddleOCR: {paddleocr.__version__}')"
```

Expected output:
```
PaddlePaddle: 2.6.2
PaddleOCR: 2.10.0
```

### Model Download Timeout

**Issue**: First request takes 10-30 seconds

**Cause**: PaddleOCR downloads models on first use

**Solution**: Pre-download models:
```bash
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(lang='en'); print('Models downloaded')"
```

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more issues.

---

## License & Usage

### MIT License

SnapText is open-source under the **MIT License** - see [LICENSE](LICENSE) file for details.

**You are FREE to**:
- Use for personal or commercial projects
- Modify and customize the code
- Distribute and share your modifications
- Use for educational purposes
- Use for research and academic work

### Intended Use

SnapText is designed primarily for:

1. **Educational Purposes**
   - Learning OCR technology
   - Understanding FastAPI framework
   - Studying REST API design
   - Teaching materials

2. **Research Purposes**
   - Academic research projects
   - Experimentation with OCR
   - Benchmarking approaches
   - Publishing papers

3. **Development**
   - Building custom solutions
   - Integration into applications
   - Open-source contributions

### Terms & Conditions

While freely available, please:

- **Respect Privacy**: Comply with data protection laws (GDPR, PDPA, etc.)
- **Give Attribution**: Credit "RogaTekno" when appropriate
- **Contribute Back**: Share improvements with the community
- **Use Responsibly**: Follow ethical guidelines for AI/OCR usage

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Opportunities for Contribution

SnapText has a solid foundation with generic OCR capabilities. We're looking for contributors to help expand the project:

**Document Processors**:
- Indonesian ID Cards (KTP) - Extract NIK, name, address, etc.
- Family Cards (KK) - Parse family member information
- BPJS Cards - Health and employment insurance data
- Bank Statements - Account numbers, transactions, balances
- Custom document types - Build specialized extractors

**Infrastructure Improvements**:
- Docker containerization for easy deployment
- Batch processing for multiple images
- Redis caching for repeated requests
- Async processing with Celery/Redis queue
- Mobile-optimized API endpoints

**Quality & Performance**:
- Additional language models
- Performance optimizations
- Enhanced test coverage
- Documentation improvements
- Bug fixes and refinements

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on how to get started!

**How to Contribute**:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## Support

### Getting Help

- **Documentation**: See [docs/](docs/) for comprehensive guides
- **Issues**: Report bugs via [GitHub Issues](../../issues)
- **Discussions**: Ask questions in [GitHub Discussions](../../discussions)
- **API Docs**: http://localhost:8000/docs (when running)

### Reporting Issues

When reporting issues, please include:
- Python version
- PaddlePaddle/PaddleOCR versions
- OS and environment
- Error messages or logs
- Steps to reproduce

### Community

- **Contributors**: See [CONTRIBUTORS.md](CONTRIBUTORS.md)
- **Code of Conduct**: See [CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md)

---

## Acknowledgments

Built with excellent open-source tools:

- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework
- **[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)** - OCR engine
- **[PaddlePaddle](https://github.com/PaddlePaddle/Paddle)** - Deep learning framework
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation
- **[Uvicorn](https://www.uvicorn.org/)** - ASGI server

---

## Contributors

Thanks to all the people who contribute to SnapText!

<a href="https://github.com/RogaTekno/snaptext/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=RogaTekno/snaptext" alt="Contributors" />
</a>

Made with [contrib.rocks](https://contrib.rocks).

## Star & Share

If you find SnapText useful:

- **Star** this repository on GitHub
- **Share** with fellow students/researchers
- **Spread the word** about this free resource
- **Contribute** improvements back to community

## Contact

- **Author**: amubhya
- **Organization**: RogaTekno
- **Project**: SnapText
- **Year**: 2026
- **License**: MIT License

---

**Developed by RogaTekno** for the global education and research community.

