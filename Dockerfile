# Multi-stage Dockerfile for SnapText OCR Service
# Optimized for Ultra-Fast Build and Automatic Permission Handling

# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 1. Upgrade pip only — NOT setuptools/wheel (avoids 'packaging' landing in
# global site-packages and being skipped when we install to /install later).
RUN pip install --upgrade pip

# 2. Install everything into /install in one shot.
# --prefer-binary: use prebuilt wheels (avoids 60-120s C++ source compilation).
# --extra-index-url: provides prebuilt CPU wheels for llama-cpp-python.
COPY requirements.txt .
RUN pip install --prefix=/install --prefer-binary \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
    -r requirements.txt

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

# Create app user
RUN useradd -m -u 1000 -s /bin/bash app

# Copy packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Setup entrypoint script for automatic permission handling
RUN chmod +x scripts/entrypoint.sh
ENTRYPOINT ["/bin/bash", "scripts/entrypoint.sh"]

# Default command (passed to entrypoint.sh)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
