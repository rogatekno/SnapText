# RogaScan

FastAPI OCR service powered by PaddleOCR for text extraction and visualization from images.

## Features

- 🚀 **FastAPI** - Modern, fast (high-performance) web framework
- 🔍 **PaddleOCR** - Latest version (2.9.0+) with improved accuracy
- 📊 **Repository Pattern** - Clean architecture for maintainability
- 🎯 **Type Safety** - Full type hints with Python 3.12+
- 🧪 **Well Tested** - Comprehensive test suite with coverage
- 📝 **Interactive Docs** - Auto-generated API documentation (Swagger/ReDoc)
- 🌍 **Multi-language** - Support for 10+ languages

## Quick Start

### Windows Installation

#### Option 1: Automated Installation (Recommended)

```powershell
# Clone or navigate to project
cd rogascan

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Run installation script
.\install.ps1

# Start server
.\start.ps1
```

#### Option 2: Manual Installation

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install PyMuPDF first (to avoid compilation issues)
pip install "PyMuPDF>=1.24.0"

# Install PaddlePaddle 3.x
pip install "paddlepaddle>=3.0.0"

# Install PaddleOCR latest
pip install "paddleocr>=2.9.0"

# Install remaining dependencies
pip install -r requirements.txt

# Create configuration
copy .env.example .env

# Start server (use start.bat or start.ps1)
.\start.bat
```

### Linux/macOS Installation

```bash
# Clone repository
git clone <repository-url>
cd rogascan

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

### Usage

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Extract text
curl -X POST http://localhost:8000/api/v1/ocr/extract \
  -F "file=@document.jpg" \
  -F "lang=en"

# Visualize with bounding boxes
curl -X POST http://localhost:8000/api/v1/ocr/visualize \
  -F "file=@document.jpg" \
  --output visualized.png
```

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/ocr/extract` | Extract text from image |
| POST | `/api/v1/ocr/visualize` | Get image with bounding boxes |
| GET | `/api/v1/ocr/info` | Service information and capabilities |

See [API.md](docs/API.md) for complete API documentation.

## Project Structure

```
rogascan/
├── app/                    # Application source
│   ├── api/               # FastAPI endpoints
│   ├── core/              # Config, exceptions, logging
│   ├── models/            # Pydantic schemas
│   ├── repositories/      # Data access layer (OCR)
│   ├── services/          # Business logic
│   └── utils/             # Utilities
├── docs/                  # Documentation
├── tests/                 # Test suite
├── .env.example           # Configuration template
├── pyproject.toml         # Python project config
└── requirements.txt       # Dependencies
```

## Supported Languages

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

## Supported Image Formats

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- BMP (`.bmp`)
- WebP (`.webp`)

Maximum file size: 10 MB (configurable)

## Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api/test_ocr.py -v
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ --fix

# Type check
mypy app/
```

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guide.

## Configuration

Key environment variables (see `.env.example`):

```bash
# Application
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

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text
```

See [SETUP.md](docs/SETUP.md) for detailed setup instructions.

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and patterns
- [SETUP.md](docs/SETUP.md) - Installation and configuration
- [API.md](docs/API.md) - Complete API reference
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) - Development workflow

## Architecture

RogaScan follows the **Repository Pattern** for clean separation of concerns:

```
API Layer (FastAPI)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Data Access)
    ↓
PaddleOCR (OCR Engine)
```

This design enables:
- Easy testing (mock repositories)
- Swappable OCR engines
- Clear boundaries between layers
- Maintainable codebase

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Requirements

- Python 3.12 or 3.13
- 4GB RAM minimum (8GB recommended)
- ~2GB disk space for models

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please see [DEVELOPMENT.md](docs/DEVELOPMENT.md) for guidelines.

## Support

- Issues: GitHub Issues
- Documentation: [docs/](docs/)
- API Docs: http://localhost:8000/docs (when running)

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - OCR engine
- [Pydantic](https://docs.pydantic.dev/) - Data validation
