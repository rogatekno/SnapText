# SnapText Setup Guide

This guide covers installation, configuration, and verification of the SnapText OCR service.

## Prerequisites

- **Python**: 3.12 or 3.13
- **Operating System**: Windows, macOS, or Linux
- **Disk Space**: ~2GB for PaddleOCR models
- **Memory**: 4GB RAM minimum (8GB recommended)
- **PaddlePaddle**: 2.6.2 (do NOT use 3.x - see Known Issues below)
- **PaddleOCR**: 2.10.0 (compatible with PaddlePaddle 2.6.x)

## Installation

### 1. Clone or Create Project

```bash
# If cloning from git
git clone <repository-url>
cd snaptext

# Or if starting fresh, ensure you're in the project directory
cd snaptext
```

### 2. Create Virtual Environment

**Windows (PowerShell)**:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (CMD)**:
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS/Linux**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

**Option A: Using pip (recommended for most users)**
```bash
pip install -r requirements.txt
```

**Option B: Using pip with development tools**
```bash
pip install -e ".[dev]"
```

**Option C: Using pyproject.toml (modern approach)**
```bash
pip install -e .
```

### 4. Verify Installation

```bash
# Verify PaddleOCR
python -c "from paddleocr import PaddleOCR; print('PaddleOCR installed successfully')"

# Verify FastAPI
python -c "from fastapi import FastAPI; print('FastAPI installed successfully')"

# Verify project imports
python -c "from app.main import app; print('SnapText imports OK')"
```

## Configuration

### 1. Create Environment File

```bash
# Copy the example file
cp .env.example .env

# Edit with your settings
# Windows: notepad .env
# macOS/Linux: nano .env
```

### 2. Configure Settings

Edit `.env` file as needed:

```bash
# Development settings
ENVIRONMENT=development
DEBUG=true

# Server settings
HOST=0.0.0.0
PORT=8000

# PaddleOCR settings
PADDLEOCR_USE_GPU=false        # Set true if you have CUDA GPU
PADDLEOCR_LANG=en              # Default language
PADDLEOCR_USE_ANGLE_CLS=true   # Use angle classifier

# Upload limits
MAX_UPLOAD_SIZE_MB=10          # Max file size

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=text                # Use 'json' for production
```

### 3. Create Logs Directory

```bash
mkdir logs
```

## Running the Service

### Development Mode

**Using uvicorn directly**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Using the module**:
```bash
python -m app.main
```

**With custom workers** (production testing):
```bash
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

### Expected Output

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Verification

### 1. Check API Documentation

Open browser: http://localhost:8000/docs

You should see the interactive Swagger UI.

### 2. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "paddleocr_loaded": true,
  "environment": "development"
}
```

### 3. Test OCR Extraction

```bash
# Create a test image or use an existing one
curl -X POST http://localhost:8000/api/v1/ocr/extract \
  -F "file=@test_image.jpg" \
  -F "lang=en"
```

### 4. Test Visualization

```bash
curl -X POST http://localhost:8000/api/v1/ocr/visualize \
  -F "file=@test_image.jpg" \
  --output visualized.png
```

Open `visualized.png` to see bounding boxes.

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

View coverage report:
```bash
# Windows
start htmlcov/index.html

# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

### Run Specific Test File

```bash
pytest tests/test_api/test_ocr.py -v
```

### Run with Debug Output

```bash
pytest -v -s tests/test_api/test_ocr.py
```

## Code Quality Checks

### Type Checking

```bash
mypy app/
```

### Linting

```bash
# Check only
ruff check app/

# Auto-fix
ruff check app/ --fix
```

### Formatting

```bash
# Check format
black --check app/

# Format code
black app/
```

### Run All Checks

```bash
# Format first
black app/

# Then lint
ruff check app/

# Then type check
mypy app/

# Finally test
pytest --cov=app
```

## Troubleshooting

### PaddlePaddle 3.x Compatibility Issues

**Error**: `ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`

**Cause**: PaddlePaddle 3.x uses a new IR (PIR) that is not fully supported by PaddleOCR.

**Solution**:
```bash
# Uninstall incompatible versions
pip uninstall paddlepaddle paddleocr -y

# Install compatible versions
pip install "paddlepaddle>=2.6.0,<3.0.0"
pip install "paddleocr>=2.7.0,<3.0.0"
```

**Verification**:
```bash
python -c "import paddle; import paddleocr; print(f'PaddlePaddle: {paddle.__version__}'); print(f'PaddleOCR: {paddleocr.__version__}')"
# Expected output:
# PaddlePaddle: 2.6.2
# PaddleOCR: 2.10.0
```

### PaddleOCR Model Download Slow

PaddleOCR downloads models on first run. To speed up:

```bash
# Pre-download models
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(lang='en'); print('Models downloaded')"
```

Models are cached in `~/.paddleocr/`.

### Import Errors

If you get import errors:

```bash
# Ensure virtual environment is activated
# Windows: echo $VIRTUAL_ENV
# macOS/Linux: echo $VIRTUAL_ENV

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Port Already in Use

If port 8000 is busy:

```bash
# Use different port
uvicorn app.main:app --port 8001

# Or kill process on port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### GPU Not Detected

If `PADDLEOCR_USE_GPU=true` but GPU isn't used:

1. Verify CUDA installation:
   ```bash
   nvidia-smi  # NVIDIA GPU
   ```

2. Install GPU version of PaddlePaddle:
   ```bash
   pip uninstall paddlepaddle
   pip install paddlepaddle-gpu
   ```

3. Keep `PADDLEOCR_USE_GPU=false` if no GPU available.

### Memory Issues

If you encounter out-of-memory errors:

1. Reduce `MAX_UPLOAD_SIZE_MB` in `.env`
2. Process smaller images
3. Close unused applications
4. Consider adding swap space (Linux)

## Production Deployment

### Using Docker (Recommended)

Create `Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t snaptext .
docker run -p 8000:8000 --env-file .env snaptext
```

### Using Gunicorn (Production)

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Environment Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Use `LOG_FORMAT=json`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up reverse proxy (nginx/caddy)
- [ ] Configure SSL/TLS
- [ ] Set up log aggregation
- [ ] Configure rate limiting
- [ ] Set up monitoring

## Next Steps

- Read [API.md](API.md) for API usage details
- Read [DEVELOPMENT.md](DEVELOPMENT.md) for development workflow
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design

## Support

If issues persist:
1. Check logs in `logs/app.log`
2. Run with `DEBUG=true` for more details
3. Verify all dependencies are installed
4. Try running tests to identify issues
