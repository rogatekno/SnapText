# RogaScan Troubleshooting Guide

This guide covers common issues and their solutions when setting up and running RogaScan.

## Table of Contents

- [Dependency Issues](#dependency-issues)
- [PaddleOCR Errors](#paddleocr-errors)
- [Startup Issues](#startup-issues)
- [Performance Issues](#performance-issues)
- [API Issues](#api-issues)

---

## Dependency Issues

### PaddlePaddle 3.x Compatibility Error

**Error Message**:
```
ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
(at ..\paddle\fluid\framework\new_executor\instruction\onednn\onednn_instruction.cc:118)
```

**Cause**: PaddlePaddle 3.x uses a new Intermediate Representation (PIR) that is not fully supported by PaddleOCR.

**Solution**:
```bash
# Uninstall incompatible versions
pip uninstall paddlepaddle paddleocr -y

# Install compatible versions
pip install "paddlepaddle>=2.6.0,<3.0.0"
pip install "paddleocr>=2.7.0,<3.0.0"

# Verify installation
python -c "import paddle; import paddleocr; print(f'PaddlePaddle: {paddle.__version__}'); print(f'PaddleOCR: {paddleocr.__version__}')"
```

**Expected Output**:
```
PaddlePaddle: 2.6.2
PaddleOCR: 2.10.0
```

---

### set_optimization_level Attribute Error

**Error Message**:
```python
AttributeError: 'paddle.base.libpaddle.AnalysisConfig' object has no attribute 'set_optimization_level'
```

**Cause**: Version mismatch between PaddleOCR 3.4.0+ and PaddlePaddle 2.6.x.

**Solution**: Downgrade PaddleOCR to 2.10.0:
```bash
pip uninstall paddleocr paddlex -y
pip install "paddleocr>=2.7.0,<3.0.0"
```

---

## PaddleOCR Errors

### Model Download Timeout

**Symptom**: Long wait on first OCR request, timeout errors.

**Cause**: PaddleOCR downloads detection/recognition models on first use (~40MB).

**Solution**:
```bash
# Pre-download models (do this once)
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(lang='en'); print('Models downloaded')"

# Models are cached in ~/.paddleocr/ on Linux/Mac
# Models are cached in C:\Users\<username>\.paddleocr\ on Windows
```

---

### GPU Not Detected

**Symptom**: `PADDLEOCR_USE_GPU=true` but processing is slow.

**Diagnosis**:
```bash
# Check if GPU is available
python -c "import paddle; print(paddle.device.cuda.device_count())"
# Output should be > 0

# For NVIDIA GPUs
nvidia-smi
```

**Solution**:
```bash
# If no GPU, keep CPU version
# Set in .env: PADDLEOCR_USE_GPU=false

# If GPU exists but not detected, install GPU version
pip uninstall paddlepaddle
pip install paddlepaddle-gpu>=2.6.0,<3.0.0
```

---

## Startup Issues

### Port Already in Use

**Error**: `[Errno 48] Address already in use`

**Solution**:
```bash
# Option 1: Use different port
uvicorn app.main:app --port 8001

# Option 2: Kill existing process
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

---

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'app'`

**Cause**: Wrong working directory or missing dependencies.

**Solution**:
```bash
# Ensure you're in project root
cd /path/to/rogascan

# Verify virtual environment is activated
# Windows: echo %VIRTUAL_ENV%
# Linux/macOS: echo $VIRTUAL_ENV

# Reinstall dependencies
pip install -r requirements.txt

# Verify imports
python -c "from app.main import app; print('OK')"
```

---

### Configuration File Missing

**Error**: `.env file not found`

**Solution**:
```bash
# Copy example file
cp .env.example .env

# Edit with your settings
nano .env  # Linux/Mac
notepad .env  # Windows
```

---

## Performance Issues

### Slow First Request

**Symptom**: First OCR request takes 10-30 seconds, subsequent requests are fast.

**Cause**: Model loading is lazy (on first use).

**Solution**: This is normal behavior. To pre-load models:
```bash
# Add to startup script or manually run
python -c "from app.repositories.ocr_repository import get_ocr_repository; import asyncio; asyncio.run(get_ocr_repository().initialize())"
```

---

### Out of Memory Errors

**Error**: `OutOfMemoryError` or process killed.

**Solution**:
```bash
# Option 1: Reduce max file size in .env
MAX_UPLOAD_SIZE_MB=5

# Option 2: Process smaller images
# Resize images before upload

# Option 3: Close unused applications
# Free up system memory

# Option 4: Add swap space (Linux)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### CPU Usage Always 100%

**Symptom**: System becomes unresponsive during OCR.

**Cause**: Large images or multiple concurrent requests.

**Solution**:
```bash
# Add rate limiting (future feature)
# For now, reduce worker count
uvicorn app.main:app --workers 1

# Resize images before upload
# Recommended: 1000-2000px width
```

---

## API Issues

### 422 Unprocessable Entity

**Error Response**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Unsupported image format: tiff",
    "details": {
      "allowed_formats": ["jpg", "jpeg", "png", "bmp", "webp"]
    }
  }
}
```

**Solution**: Convert image to supported format:
```bash
# Using ImageMagick
convert input.tiff output.jpg

# Using Python
from PIL import Image
img = Image.open('input.tiff')
img.save('output.jpg')
```

---

### File Size Limit Exceeded

**Error Response**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "File size exceeds maximum allowed size",
    "details": {
      "size_mb": 15.5,
      "max_size_mb": 10
    }
  }
}
```

**Solution**:
```bash
# Option 1: Increase limit in .env
MAX_UPLOAD_SIZE_MB=20

# Option 2: Compress image
# Using ImageMagick
convert input.jpg -quality 85 output.jpg

# Using Python
from PIL import Image
img = Image.open('input.jpg')
img.save('output.jpg', quality=85, optimize=True)
```

---

### Empty OCR Results

**Symptom**: API returns success but `text` field is empty.

**Causes**:
1. Image has no text
2. Image quality too poor
3. Wrong language selected
4. Text is in script/font not recognized

**Debugging**:
```bash
# Try visualization endpoint to see what's detected
curl -X POST http://localhost:8000/api/v1/ocr/visualize \
  -F "file=@problem_image.jpg" \
  --output debug.jpg

# Check if green boxes appear around text
```

**Solutions**:
```bash
# Try different language
curl -X POST http://localhost:8000/api/v1/ocr/extract \
  -F "file=@image.jpg" \
  -F "lang=ch"  # Try Chinese for similar scripts

# Improve image quality
# - Increase resolution
# - Improve contrast
# - Reduce noise
# - Correct skew
```

---

## Windows-Specific Issues

### Path Too Long Error

**Error**: `Path too long` during installation.

**Solution**:
```powershell
# Enable long path support (requires admin)
# Open PowerShell as Administrator and run:
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Or install to shorter path
# Instead of: C:\Very\Long\Path\To\Project
# Use: C:\Projects\rogascan
```

---

### PowerShell Execution Policy

**Error**: `cannot be loaded because running scripts is disabled`

**Solution**:
```powershell
# Check current policy
Get-ExecutionPolicy

# Allow scripts for current session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Or allow permanently (not recommended for security)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

### Virtual Environment Activation Fails

**Error**: `cannot run the script` when running `.venv\Scripts\Activate.ps1`

**Solution**:
```powershell
# Option 1: Use cmd.exe instead
cmd.exe
.venv\Scripts\activate.bat

# Option 2: Use Python directly
.venv\Scripts\python.exe -m app.main

# Option 3: Bypass execution policy
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

---

## Getting Help

If none of the solutions work:

1. **Check Logs**:
   ```bash
   # Application logs
   tail -f logs/app.log

   # Enable debug mode in .env
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

2. **Verify Installation**:
   ```bash
   # Run verification script
   python -c "
   import sys
   import paddle
   import paddleocr
   from app.main import app

   print(f'Python: {sys.version}')
   print(f'PaddlePaddle: {paddle.__version__}')
   print(f'PaddleOCR: {paddleocr.__version__}')
   print('All imports successful!')
   "
   ```

3. **Report Issues**:
   - Include error message
   - Include Python version
   - Include PaddlePaddle/PaddleOCR versions
   - Include OS and environment details
   - Attach minimal reproduction code

---

## Prevention Tips

1. **Always use compatible versions**:
   - PaddlePaddle 2.6.2
   - PaddleOCR 2.10.0
   - Never auto-upgrade without testing

2. **Use virtual environment**:
   - Prevents conflicts with system packages
   - Easy to recreate if broken

3. **Backup working configuration**:
   ```bash
   pip freeze > requirements-working.txt
   ```

4. **Test changes in development first**:
   - Don't upgrade in production without testing
   - Use feature flags for new functionality

5. **Monitor resources**:
   - Check disk space before large operations
   - Monitor memory usage during development
   - Set appropriate limits in configuration
