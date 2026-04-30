# SnapText

FastAPI OCR service powered by **PaddleOCR** and **Local SLM (Qwen)** for high-fidelity structured data extraction.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.133+-green.svg)
![Status: Hybrid SLM](https://img.shields.io/badge/Status-Hybrid%20SLM-brightgreen.svg)

**Lightweight Modular OCR for VPS Deployment**

SnapText is designed to run efficiently on standard VPS specifications, providing a powerful hybrid pipeline: OCR for spatial detection and a Local Small Language Model (SLM) for zero-shot structured data mapping.

---

## 🚀 Key Features

### 🧠 Hybrid Extraction Engine
- **OCR-Only Mode**: Fast spatial mapping using rule-based heuristics.
- **LLM-Enhanced Mode**: Zero-shot extraction using **Qwen2.5-0.5B** via `llama-cpp-python`. No templates required.
- **Complex Documents**: Built-in support for Family Cards (KK), Invoices, and Receipts with structured array outputs.

### 🏗️ Modular Architecture
- **ImageHandler**: Optimization and preprocessing logic.
- **Extraction Engines**: Plugin-based engine system (Rule-based, Local LLM).
- **Coordinator Pattern**: Clean orchestration between image, OCR, and mapping layers.

### 💻 VPS Friendly
- **Low Memory Footprint**: Runs on systems with as little as **1GB - 2GB RAM**.
- **CPU Optimized**: Parallel execution optimized for standard vCPU environments.

---

## 📊 Performance & Specs

Typical performance on a standard CPU-only VPS:

| Operation | Model | RAM Use | Speed |
|-----------|-------|---------|-------|
| OCR Detection | PaddleOCR | ~600MB | 200-800ms |
| SLM Extraction | Qwen 0.5B | ~400MB | 1-3s |
| **Total Pipeline** | **Hybrid** | **~1.2GB** | **2-5s** |

**Minimum Specs**:
- CPU: 1-2 vCPU
- RAM: 1GB (Minimum), 2GB (Recommended)
- Disk: 3GB free space

---

## 🛠️ Quick Start

### Installation

```bash
# Clone and enter directory
cd rogascan

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# Health Check
curl http://localhost:8000/api/v1/health

# Scan Document (Hybrid OCR + LLM)
curl -X POST http://localhost:8000/api/v1/ocr/scan \
  -F "file=@invoice.jpg" \
  -F "use_llm=true"
```

---

## 📖 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and modular layers.
- **[API.md](docs/API.md)** - Complete API reference and examples.
- **[SETUP.md](docs/SETUP.md)** - Local LLM and environment setup.
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - How to contribute and add new engines.

---

## 📝 License

Licensed under the MIT License. Created by **RogaTekno**.
