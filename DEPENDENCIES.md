# ERA System - Dependencies & Environment Setup

Complete guide to ERA system requirements, dependency management, and environment configuration.

## Quick Summary

| Component | Type | Notes |
|-----------|------|-------|
| **Python** | Required | 3.10+ (tested on 3.12.7) |
| **Ollama** | Required | Local LLM runtime, models downloaded separately |
| **Virtual Environment** | Recommended | Isolation for project dependencies |
| **pip/conda** | Required | Package manager (pip included with Python) |
| **OS** | Supported | Windows 10+, Linux, macOS |

---

## System Requirements

### Minimum Specifications
- **CPU**: 4 cores (8+ recommended for LLM inference)
- **RAM**: 4 GB minimum, 8 GB+ recommended for dual LLM operation
- **Disk**: 5 GB total (1 GB for models, 2 GB for data, 2 GB overhead)
- **Network**: None required (Ollama is local)
- **GPU**: Optional (CPUs only, or CUDA/Metal for acceleration)

### Tested Configurations
- ✅ Windows 11 + Python 3.12.7 + Ollama 0.2.3+
- ✅ Linux (Ubuntu 22.04) + Python 3.11+ + Ollama
- ✅ macOS (Intel/M1/M2) + Python 3.10+ + Ollama

---

## Core Dependencies

### Python Package Dependencies

All Python packages are listed in `requirements.txt`:

```
# Core ML & Data Processing
numpy>=1.24.0
pandas>=1.5.0
scikit-learn>=1.2.0
scipy>=1.10.0

# LLM & Embedding Integration
ollama>=0.0.50  # Ollama Python client
openai>=1.0.0   # OpenAI API (optional)

# Data Handling & Serialization
pydantic>=1.10.0
PyYAML>=6.0
protobuf>=3.20.0

# Async & Concurrency
aiohttp>=3.8.0
aiofiles>=23.1.0
asyncpg>=0.27.0

# Database & Persistence
sqlalchemy>=2.0.0
sqlite3  # Built-in

# Document Processing
PyPDF2>=3.0.0
python-docx>=0.8.11

# Testing & Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0

# Logging & Monitoring
python-dotenv>=1.0.0
structlog>=23.1.0
```

### Installation

```bash
# 1. Navigate to ERA directory
cd c:\era

# 2. (Optional but recommended) Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import numpy, pandas, aiohttp, pydantic; print('All core packages OK')"
```

### Dependency Explanations

| Package | Purpose | Required? | Notes |
|---------|---------|-----------|-------|
| `numpy` | Numerical computing | ✅ Yes | Used by KIS scoring, feature vectors |
| `pandas` | Data frames & analysis | ✅ Yes | Episode analysis, metrics reporting |
| `scikit-learn` | ML algorithms | ✅ Yes | KIS classifier, judgment priors |
| `ollama` | LLM client library | ✅ Yes | Calls local Ollama daemon |
| `aiohttp` | Async HTTP | ✅ Yes | Concurrent LLM calls, embeddings |
| `asyncpg` | Async PostgreSQL | ⚠️ Optional | Only if using PostgreSQL backend |
| `PyYAML` | YAML parsing | ✅ Yes | Doctrine files in YAML format |
| `pydantic` | Data validation | ✅ Yes | KIS output schemas, minister positions |
| `pytest` | Testing framework | ✅ Yes | Test suite has 27 test files |

---

## Runtime Dependencies

### Ollama (Required)

Ollama is a local LLM runtime that runs LLM models on your machine without cloud connectivity.

**Installation:**
```bash
# Download from https://ollama.ai
# Windows: Run installer
# Linux: curl -fsSL https://ollama.ai/install.sh | sh
# macOS: Download DMG from ollama.ai

# Verify installation
ollama --version
```

**Starting Ollama:**
```bash
# In a separate terminal, start Ollama daemon
ollama serve

# Or if Ollama is installed, it may auto-start
```

**Required Models:**
```bash
# Pull the two models used by ERA (one-time)
ollama pull deepseek-r1:8b    # User LLM (exploratory, detailed)
ollama pull qwen3:14b         # Program LLM (structured, systematic)

# Optional models for experimentation
ollama pull mistral:7b        # Alternative (faster)
ollama pull neural-chat:7b    # Chat-optimized
ollama pull llama2:13b        # Larger model (requires 16+ GB RAM)
```

**Verify Models:**
```bash
ollama list
# Should show:
# deepseek-r1:8b      abc123...  4.2 GB
# qwen3:14b            def456...  8.5 GB
```

**Model Performance:**

| Model | Size | Speed | Quality | RAM |
|-------|------|-------|---------|-----|
| deepseek-r1:8b | 4.2 GB | Medium (~2 min/response) | Excellent (reasoning) | 8 GB |
| qwen3:14b | 8.5 GB | Medium (~2 min/response) | Excellent (structured) | 12 GB |
| mistral:7b | 3.8 GB | Fast (~1 min/response) | Good | 6 GB |
| llama2:13b | 7.4 GB | Medium | Very Good | 14 GB |

**Default Configuration (in code):**
- User LLM: `deepseek-r1:8b` (deep reasoning)
- Program LLM: `qwen3:14b` (structured output)
- Both run locally on `http://localhost:11434`

### Python Version

**Required:** Python 3.10 or higher

```bash
# Check Python version
python --version
# Expected: Python 3.10.0 (or 3.11+, or 3.12+)

# If not installed or wrong version:
# Download from https://www.python.org/downloads/
```

**Virtual Environment Setup:**

```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/macOS bash
python3 -m venv .venv
source .venv/bin/activate

# To deactivate
deactivate
```

---

## Data Dependencies

### Directory Structure

All data is stored in `data/` subdirectories. These are created automatically on first run:

```
data/
├── doctrine/              # Minister decision rules (YAML)
│   ├── locked/           # Main doctrine files
│   └── *.yaml            # 10+ domain YAML files (2 MB)
├── books/                # Ingested knowledge documents
│   ├── *.pdf             # 61 PDF books (2 GB total)
│   └── processed/        # Ingestion intermediate files
├── conversations/        # LLM conversation transcripts
│   └── *.json           # Searchable conversation history
├── sessions/            # Multi-turn session records
│   ├── completed/       # Finished session files
│   └── consequences.jsonl   # Outcome tracking log
├── memory/              # Episodic learning storage
│   └── episodes.json    # Decision episode archive
├── RAG/                 # Vector embeddings (optional)
│   └── embeddings.db    # Vectorized knowledge
└── ministers/          # Minister-specific data
    └── *.json          # Domain-specific artifacts
```

**Validation:**
```bash
# Python will auto-validate on startup:
# - Creates missing directories
# - Validates doctrine YAML files exist
# - Confirms books directory (with 61+ PDFs)
# - All paths checked with clear error messages
```

### Knowledge Base (data/books/)

61 PDF documents for knowledge augmentation. These are:
- Optional for core functionality (system works without them)
- Required for RAG semantic search
- Used in KIS for domain context
- Ingested via `ingestion/v2/` pipeline

**Check knowledge base:**
```bash
dir data\books\*.pdf | Measure-Object | Select-Object -ExpandProperty Count
# Expected: 61 (or similar count)
```

---

## Optional Dependencies

### For Vector Database (RAG)

If you want semantic search via vector embeddings:

```bash
pip install faiss-cpu       # Or faiss-gpu for CUDA
pip install pgvector>=0.1.8 # For PostgreSQL vector extension
pip install weaviate-client>=3.15.0  # Alternative vector DB
```

### For Advanced Logging

```bash
pip install structlog>=23.0  # Structured logging
pip install python-json-logger>=2.0  # JSON logging format
```

### For API Server

If you want to expose ERA as a REST API:

```bash
pip install fastapi>=0.100.0
pip install uvicorn>=0.23.0
```

### For Database Backends

```bash
# PostgreSQL async client
pip install asyncpg>=0.28.0

# MongoDB async client
pip install motor>=3.3.0

# DuckDB (embedded analytics)
pip install duckdb>=0.8.0
```

---

## Environment Configuration

### Environment Variables

Create `.env` file in `c:\era\` if you need custom configuration:

```env
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_USER=deepseek-r1:8b
OLLAMA_MODEL_PROGRAM=qwen3:14b
OLLAMA_TIMEOUT=300

# System Paths
ERA_ROOT=c:\era
DATA_ROOT=c:\era\data

# Database
DATABASE_URL=sqlite:///./data/episodes.db
# Or: DATABASE_URL=postgresql://user:pass@localhost/era

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Cache
CACHE_MAX_SIZE_MB=500
CACHE_CLEANUP_DAYS=7

# ML Configuration
ML_BATCH_SIZE=32
ML_LEARNING_RATE=0.001
```

**Load environment:**
```python
from dotenv import load_dotenv
import os

load_dotenv()
ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
```

---

## Verification Checklist

Run this to verify your environment is properly set up:

```bash
# 1. Python version
python --version
# Expected: Python 3.10+

# 2. Virtual environment active
which python  # Linux/Mac: should show .venv path
# Or: echo $env:VIRTUAL_ENV  # Windows

# 3. Core packages
python -c "import numpy, pandas, aiohttp, pydantic; print('Core packages OK')"

# 4. Ollama running
python -c "import requests; requests.get('http://localhost:11434/api/version')" 2>&1
# Expected: Should not error

# 5. Ollama models available
ollama list
# Expected: deepseek-r1:8b and qwen3:14b listed

# 6. Data directory structure
ls data/doctrine/locked/*.yaml | wc -l
# Expected: 10+

# 7. Books directory
ls data/books/*.pdf | wc -l
# Expected: 60+

# 8. Run test check
python -c "from persona.cache_manager import CacheManager; m = CacheManager(); print('Cache manager OK')"
```

**All checks passing?** → You're ready to use ERA!

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'aiohttp'"

```bash
# Solution: Install missing package
pip install aiohttp

# Or reinstall all requirements
pip install -r requirements.txt
```

### "Ollama connection refused"

```bash
# Solution: Start Ollama in separate terminal
ollama serve

# Or verify Ollama is running:
netstat -ano | findstr :11434  # Windows
lsof -i :11434                 # Linux/Mac
```

### "Model not found: deepseek-r1:8b"

```bash
# Solution: Download the model
ollama pull deepseek-r1:8b

# List available models
ollama list
```

### "File not found: data/doctrine/locked/*.yaml"

```bash
# Solution: Run system once to initialize
python system_main.py
# Or manually create directory:
mkdir -p data/doctrine/locked
```

### "Permission denied when creating directories"

```bash
# Solution: Run with appropriate permissions
# Windows: Run PowerShell as Administrator
# Linux: Use sudo (or fix directory permissions)
sudo chmod 755 data/
```

### "Not enough RAM for dual LLMs"

Options:
1. Use smaller models (mistral:7b instead of qwen3:14b)
2. Run only one LLM at a time (modify system config)
3. Use system_main.py instead of llm_conversation.py (uses single LLM)
4. Upgrade to 16+ GB RAM

---

## Updating Dependencies

### Check for outdated packages

```bash
pip list --outdated
```

### Update all packages

```bash
pip install --upgrade -r requirements.txt
```

### Update specific package

```bash
pip install --upgrade numpy
```

---

## Dependency Notes

### Why Ollama + Not Cloud LLMs?

✅ **Advantages:**
- No API keys needed
- Privacy (data stays local)
- No rate limits
- Works offline
- Faster iteration

⚠️ **Tradeoffs:**
- Requires local GPU/CPU (slower inference)
- Manual model management
- Higher quality models take more VRAM

### Why Async (aiohttp, asyncpg)?

✅ **Advantages:**
- Multiple LLM calls in parallel
- 3-5x faster for concurrent operations
- Better resource utilization

⚠️ **Requirement:**
- Must understand async/await patterns
- Some legacy code may use blocking calls

### Version Pinning Policy

Dependencies are pinned to working versions:
- `numpy>=1.24.0` → Supports 1.24+ (allows updates)
- `ollama>=0.0.50` → Supports latest Ollama client

This provides stability while allowing security updates.

---

## Support

**Dependencies Issue?**
1. Check [START_HERE.md](START_HERE.md) - Quick install section
2. Run verification checklist (above)
3. Check [AUDIT_REPORT.txt](AUDIT_REPORT.txt) - Known issues

**Ollama Issues?**
- Ollama Docs: https://github.com/ollama/ollama
- Model Info: https://ollama.ai/library

**Python Package Issues?**
- PyPI: https://pypi.org
- Package docs: https://[package].readthedocs.io

---

**Last Updated:** February 19, 2026
**Python Version:** 3.10+
**Ollama Version:** 0.2.3+
**Status:** ✅ Verified and tested
