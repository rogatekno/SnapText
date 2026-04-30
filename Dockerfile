# Multi-stage Dockerfile for SnapText OCR Service
# Optimized for Ultra-Fast Build and CPU Performance

# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Build dependencies (minimal for wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 1. Install llama-cpp-python FIRST from pre-built wheels
# This is the most time-consuming part if compiled. 
# We use the CPU-only wheel index for Python 3.11
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install "llama-cpp-python>=0.3.0" \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# 2. Install remaining requirements
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/tmp/huggingface_cache

# Minimal runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Non-root user and permission setup
RUN useradd -m -u 1000 -s /bin/bash app && \
    mkdir -p /app/logs /app/models /tmp/ocr_cache /tmp/huggingface_cache && \
    chown -R app:app /app /tmp/ocr_cache /tmp/huggingface_cache

# Copy packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=app:app . .

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
