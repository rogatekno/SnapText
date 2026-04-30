# Multi-stage Dockerfile for SnapText OCR Service
# Optimized for Speed and Small Runtime Image

# Stage 1: Builder
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements first
COPY requirements.txt .

# Install dependencies into a temporary directory
# This uses the extra-index-url from requirements.txt for llama-cpp-python
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/tmp/huggingface_cache

# Install runtime-only dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user and directories
RUN useradd -m -u 1000 -s /bin/bash app && \
    mkdir -p /app/logs /app/models /tmp/ocr_cache /tmp/huggingface_cache && \
    chown -R app:app /app /tmp/ocr_cache /tmp/huggingface_cache

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
