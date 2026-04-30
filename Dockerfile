# Optimized Dockerfile for SnapText OCR Service
# Focused on Build Speed and Resource Efficiency

FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/tmp/huggingface_cache

# Install minimal runtime dependencies (needed by OpenCV and Llama.cpp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash app && \
    mkdir -p /app/logs /app/models /tmp/ocr_cache /tmp/huggingface_cache && \
    chown -R app:app /app /tmp/ocr_cache /tmp/huggingface_cache

# Copy requirements first to leverage Docker layer caching
COPY --chown=app:app requirements.txt .

# Install dependencies as root (to /usr/local) for simplicity and speed
# Use the extra index for llama-cpp-python CPU wheels to avoid compilation
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run uvicorn (optimized for single-worker CPU usage)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
