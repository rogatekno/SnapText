# SnapText Development Guide

This guide covers the development workflow, coding standards, and contribution guidelines for SnapText.

## Development Environment Setup

### 1. Install Development Dependencies

```bash
# Install with dev extras
pip install -e ".[dev]"

# Or manually
pip install pytest pytest-asyncio pytest-cov
pip install black ruff mypy
pip install pre-commit
```

### 2. Install Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### 3. Configure Your IDE

**VS Code** - Install extensions:
- Python
- Pylance
- Black Formatter
- Ruff

**PyCharm**:
- Enable Black formatter
- Configure pytest as test runner
- Enable type checking with mypy

## Development Workflow

### Running Development Server

```bash
# Auto-reload on file changes
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# With custom log level
uvicorn app.main:app --reload --log-level debug

# With multiple workers (testing concurrency)
uvicorn app.main:app --workers 2 --reload
```

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the architecture patterns:
   - API changes → `app/api/v1/endpoints/`
   - Business logic → `app/services/`
   - Data access → `app/repositories/`
   - Models → `app/models/schemas.py`

3. **Format code**:
   ```bash
   black app/ tests/
   ```

4. **Lint code**:
   ```bash
   ruff check app/ tests/ --fix
   ```

5. **Type check**:
   ```bash
   mypy app/
   ```

6. **Run tests**:
   ```bash
   pytest --cov=app -v
   ```

7. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test updates

## Coding Standards

### Code Style

We follow **PEP 8** with these tools:
- **Black**: Code formatting (line length: 100)
- **Ruff**: Fast linting
- **MyPy**: Type checking

### Type Hints

All functions must have type hints:

```python
# Good
def process_image(file_path: str) -> Image.Image:
    ...

async def extract_text(image: Image.Image, lang: str = "en") -> dict[str, Any]:
    ...

# Bad
def process_image(file_path):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def extract_text_from_file(
    self, file_content: bytes, filename: str, lang: str = "en"
) -> dict[str, Any]:
    """Extract text from uploaded image file.

    Args:
        file_content: Raw file content as bytes
        filename: Original filename for validation
        lang: Language code for OCR (default: 'en')

    Returns:
        Dictionary containing extracted text and metadata

    Raises:
        ValidationError: If file format is invalid
        OCRError: If text extraction fails

    Example:
        >>> result = await service.extract_text_from_file(b'...', 'doc.jpg')
        >>> print(result['text'])
    """
    ...
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Module | `snake_case` | `ocr_service.py` |
| Class | `PascalCase` | `OCRService` |
| Function | `snake_case` | `extract_text()` |
| Variable | `snake_case` | `image_bytes` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_SIZE` |
| Private | `_leading_underscore` | `_internal_method()` |

### Import Organization

```python
# 1. Standard library
import io
from typing import Any, Dict

# 2. Third-party
from fastapi import APIRouter
from pydantic import BaseModel
from PIL import Image

# 3. Local imports
from app.core.config import get_settings
from app.models.schemas import OCRResult
from app.services.ocr_service import get_ocr_service
```

### Error Handling

```python
# Define custom exceptions
from app.core.exceptions import OCRError

# Raise exceptions for domain errors
if not image:
    raise FileProcessingError(
        message="Image could not be loaded",
        filename=filename
    )

# Let unexpected exceptions propagate
# They will be caught by generic handler
```

## Testing

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_api/
│   ├── test_ocr.py          # OCR endpoint tests
│   └── test_health.py       # Health check tests
├── test_services/
│   └── test_ocr_service.py  # Service layer tests
└── test_repositories/
    └── test_ocr_repository.py  # Repository tests
```

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, Mock

class TestOCRService:
    """Tests for OCR service."""

    @pytest.mark.asyncio
    async def test_extract_text_success(self, mock_image_bytes):
        """Test successful text extraction."""
        # Arrange
        service = OCRService()
        with patch.object(service._repository, 'extract_text') as mock_extract:
            mock_extract.return_value = {
                "text": "Sample",
                "confidence": 0.95,
                "regions": [],
                "region_count": 0
            }

            # Act
            result = await service.extract_text_from_file(
                mock_image_bytes, "test.jpg"
            )

            # Assert
            assert result["text"] == "Sample"
            assert result["confidence"] == 0.95
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_invalid_format(self):
        """Test extraction with invalid format."""
        service = OCRService()

        with pytest.raises(ImageFormatError):
            await service.extract_text_from_file(
                b"invalid content", "test.xyz"
            )
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific file
pytest tests/test_api/test_ocr.py -v

# Run specific test
pytest tests/test_api/test_ocr.py::TestExtractEndpoint::test_extract_success -v

# Run with debug output
pytest -v -s

# Run only fast tests
pytest -m "not slow"
```

### Fixtures

Key fixtures in `conftest.py`:

```python
@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_image():
    """Create test image."""
    return Image.new("RGB", (200, 100), color="white")

@pytest.fixture
def mock_ocr_repository():
    """Mocked OCR repository."""
    repo = Mock(spec=PaddleOCRRepository)
    repo.extract_text = AsyncMock(return_value={...})
    return repo
```

## Code Review Checklist

Before submitting PR, verify:

- [ ] Code follows style guidelines (Black formatted)
- [ ] No linting errors (Ruff passes)
- [ ] Type checking passes (MyPy clean)
- [ ] All tests pass (pytest)
- [ ] New tests added for new features
- [ ] Coverage not decreased
- [ ] Docstrings on public functions
- [ ] Error handling appropriate
- [ ] No hardcoded values (use config)
- [ ] Documentation updated if needed

## Adding New Features

### New Endpoint Example

```python
# 1. Create endpoint in app/api/v1/endpoints/

from fastapi import APIRouter, File, UploadFile

router = APIRouter()

@router.post("/batch")
async def batch_extract(files: list[UploadFile] = File(...)):
    """Process multiple images."""
    ocr_service = get_ocr_service()

    results = []
    for file in files:
        content = await file.read()
        result = await ocr_service.extract_text_from_file(
            content, file.filename or "unknown"
        )
        results.append(result)

    return {"success": True, "results": results}

# 2. Register in app/main.py

app.include_router(
    batch_router,
    prefix=settings.api_v1_prefix,
    tags=["batch"],
)
```

### Adding Configuration

```python
# 1. Add to app/core/config.py

class Settings(BaseSettings):
    new_feature_enabled: bool = Field(default=True, alias="NEW_FEATURE_ENABLED")
    new_feature_limit: int = Field(default=100, alias="NEW_FEATURE_LIMIT")

# 2. Add to .env.example
NEW_FEATURE_ENABLED=true
NEW_FEATURE_LIMIT=100

# 3. Use in code
from app.core.config import get_settings

settings = get_settings()
if settings.new_feature_enabled:
    ...
```

## Debugging

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
DEBUG=true

# Or via command line
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

### Using Python Debugger

```python
import pdb; pdb.set_trace()  # Breakpoint

# Or with IPython
import ipdb; ipdb.set_trace()
```

### VS Code Debugging

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "console": "integratedTerminal",
      "env": {
        "LOG_LEVEL": "debug"
      }
    }
  ]
}
```

## Performance Profiling

### Profile Request Time

```python
import time
from functools import wraps

def timer(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        logger.info(f"{func.__name__} took {duration:.2f}ms")
        return result
    return wrapper

@timer
async def extract_text(...):
    ...
```

### Memory Profiling

```bash
pip install memory_profiler

python -m memory_profiler app/main.py
```

## Common Tasks

### Updating Dependencies

⚠️ **IMPORTANT**: Before updating PaddlePaddle or PaddleOCR, check the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for known compatibility issues. Currently:
- **PaddlePaddle 2.6.2** (DO NOT upgrade to 3.x)
- **PaddleOCR 2.10.0** (compatible with 2.7.x - 2.10.x)

```bash
# For non-PaddleOCR dependencies
pip install --upgrade package-name
pip freeze > requirements.txt

# Or use pip-compile (recommended)
pip install pip-tools
pip-compile pyproject.toml -o requirements.txt
```

### Database Changes (if added later)

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Generating Documentation

```bash
# Install tools
pip install sphinx sphinx-rtd-theme

# Generate
cd docs
sphinx-build -b html . _build
```

## Contributing

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes (following standards)
4. Add/update tests
5. Update documentation
6. Submit PR with:
   - Description of changes
   - Related issues
   - Testing instructions
   - Screenshots (if applicable)

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add batch processing endpoint
fix: handle empty images gracefully
refactor: simplify image validation
docs: update API documentation
test: add tests for visualization
chore: upgrade dependencies
```

### Getting Help

- Check existing issues
- Read [ARCHITECTURE.md](ARCHITECTURE.md)
- Ask in discussions
- Create issue with bug report

## Release Process

1. Update version in `app/core/config.py`
2. Update CHANGELOG.md
3. Create git tag
4. Build and publish (if packaging)
5. Deploy to production

## Additional Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PaddleOCR Docs](https://github.com/PaddlePaddle/PaddleOCR)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

---

Happy coding! 🚀
