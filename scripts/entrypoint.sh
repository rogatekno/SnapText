#!/bin/bash
set -e

# This script runs as root to fix volume permissions before dropping to 'app' user
# Only works if the container is started as root (the default in our Dockerfile)

echo "Ensuring volume permissions..."
mkdir -p /app/logs /app/models /tmp/ocr_cache /tmp/huggingface_cache
chown -R app:app /app/logs /app/models /tmp/ocr_cache /tmp/huggingface_cache

# Execute the application using the 'app' user
echo "Starting application as app user..."
exec runuser -u app -- "$@"
