# RogaScan

FastAPI OCR service powered by PaddleOCR for text extraction and visualization from images.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)

**Open Source OCR Service for Education & Research**

Created by **amubhya from RogaTekno** - Licensed under MIT License.

## Features

- **FastAPI** - Modern, fast (high-performance) web framework
- **PaddleOCR** - Stable version (2.10.0) with PaddlePaddle 2.6.2 for compatibility
- **Repository Pattern** - Clean architecture for maintainability
- **Type Safety** - Full type hints with Python 3.12+
- **Well Tested** - Comprehensive test suite with coverage
- **Interactive Docs** - Auto-generated API documentation (Swagger/ReDoc)
- **Multi-language** - Support for 10+ languages

## Quick Start

### Windows Installation

```powershell
# Clone or navigate to project
cd rogascan

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install PaddlePaddle 2.6.2 (stable version)
pip install "paddlepaddle>=2.6.0,<3.0.0"

# Install PaddleOCR 2.10.0 (compatible with PaddlePaddle 2.6.x)
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
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions
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
- **PaddlePaddle 2.6.2** (NOT 3.x - compatibility issues)
- **PaddleOCR 2.10.0** (compatible with PaddlePaddle 2.6.x)

## Known Issues & Fixes

### PaddlePaddle 3.x Compatibility
**Issue**: PaddlePaddle 3.x uses PIR (new IR) that is not fully supported by PaddleOCR, causing errors like:
```
ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
```

**Solution**: Use PaddlePaddle 2.6.2 with PaddleOCR 2.10.0 (already configured in requirements.txt)

## License & Usage

### 📜 MIT License

RogaScan is open-source and licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

This means you are **FREE** to:
- ✅ Use for personal or commercial projects
- ✅ Modify and customize the code
- ✅ Distribute and share your modifications
- ✅ Use for educational purposes
- ✅ Use for research and academic work

### Intended Use

RogaScan is designed primarily for:

1. **Educational Purposes**
   - Learning about OCR technology
   - Understanding FastAPI framework
   - Studying REST API design patterns
   - Teaching materials for courses

2. **Research Purposes**
   - Academic research projects
   - Experimentation with OCR techniques
   - Benchmarking different approaches
   - Publishing papers and articles

3. **Development**
   - Building upon for your projects
   - Creating custom OCR solutions
   - Integration into other applications
   - Open-source contributions

### Terms & Conditions

While freely available, please:

- **Respect Privacy**: Comply with data protection laws (GDPR, PDPA, etc.)
- **Give Attribution**: Credit "amubhya from rogatekno" when appropriate
- **Contribute Back**: Share improvements with the community
- **Use Responsibly**: Follow ethical guidelines for AI/OCR usage

For full license terms, see [LICENSE](LICENSE).

### Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas needing contributions:**
- Document field extraction (KTP, KK, BPJS, etc.)
- Batch processing endpoint
- Docker support
- Additional language support
- Performance optimizations
- Test coverage improvements

## Contributing

Contributions welcome! Please see [DEVELOPMENT.md](docs/DEVELOPMENT.md) for guidelines.

## Support

- Issues: GitHub Issues
- Documentation: [docs/](docs/)
- API Docs: http://localhost:8000/docs (when running)

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - OCR engine
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [PaddlePaddle](https://github.com/PaddlePaddle/Paddle) - Deep learning framework

---

## Star & Share

If you find RogaScan useful for your education or research:

- **Star** this repository on GitHub
- **Share** with fellow students/researchers
- **Spread the word** about this free resource
- **Contribute** improvements back to community

## Contact

- **Author**: amubhya
- **Organization**: RogaTekno
- **Project**: RogaScan
- **Year**: 2025

---

**Developed by amubhya from RogaTekno** for the global education and research community.
