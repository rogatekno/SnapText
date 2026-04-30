# Setup Guide

SnapText is designed for easy deployment on both local machines and VPS servers.

## 1. Prerequisites
- Python 3.12 or 3.13
- Git

## 2. Installation

```bash
# Clone the repository
git clone <repo_url>
cd rogascan

# Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Local LLM Setup (Optional but Recommended)
To enable high-accuracy template-less extraction, SnapText uses `llama-cpp-python`.

**Windows**:
Ensure you have "Desktop development with C++" installed via Visual Studio Installer.
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install build-essential python3-dev
pip install llama-cpp-python
```

## 4. Configuration
Create a `.env` file based on `.env.example`:

```bash
# Model Selection (0.5B for low RAM, 1.5B for higher accuracy)
LLM_MODEL_REPO=Qwen/Qwen2.5-0.5B-Instruct-GGUF
LLM_N_THREADS=4
```

## 5. VPS Optimization (RAM Management)
If you are running on a VPS with **1GB RAM**:
1. Use the **0.5B** model (set in `.env`).
2. Add **2GB Swap Memory** to prevent out-of-memory errors during model load.
3. Set `WORKERS=1` in your deployment.

## 6. Running the Service
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Upon the first request, the service will download approximately 1.5GB of model files (OCR + SLM). Ensure you have a stable internet connection.
