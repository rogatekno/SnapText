#!/bin/bash
# Script untuk monitoring resource usage container SnapText OCR

echo "=== Checking SnapText OCR Container Status ==="
echo ""

# Check container status
echo "📦 Container Status:"
docker ps -a | grep snaptext || echo "Container not found"
echo ""

# Check resource usage
echo "💻 Resource Usage:"
docker stats snaptext-ocr --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null || echo "Container not running"
echo ""

# Check recent logs
echo "📋 Recent Logs (last 20 lines):"
docker logs snaptext-ocr --tail 20 2>&1
echo ""

# Check for OOM errors
echo "⚠️  Checking for OOM (Out Of Memory) errors:"
docker logs snaptext-ocr 2>&1 | grep -i "oom\|killed\|memory" | tail -5
echo ""

echo "=== End of Report ==="
