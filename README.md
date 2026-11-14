# AI Memory Pipeline

A Python-based document processing and indexing pipeline with Qdrant vector storage integration, LM Studio model switching for embeddings, and automated backup capabilities.

## Project Structure

```
.
├── docker-compose.yml          # Docker Compose configuration for Qdrant
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── config.yaml                 # Pipeline configuration
├── ai_memory_pipeline/         # Core Python package
│   ├── __init__.py             # Package initialization
│   ├── chunking.py             # Text chunking functionality
│   ├── redaction.py            # Sensitive data redaction
│   ├── semantic_summary.py     # Semantic summarization
│   ├── metadata.py             # Metadata handling
│   ├── qdrant_client.py        # Qdrant vector database integration
│   ├── dynamic_model_selector.py  # LLM model selection
│   ├── lm_studio_model_switcher.py # Model switching logic
│   └── lm_studio_smart_embedder.py # Smart embedding interface
├── services/                   # Phase 5 Enhanced Services
│   ├── __init__.py             # Services package initialization
│   ├── embedding_quality_monitor.py # Embedding quality tracking
│   ├── model_cache_manager.py    # GPU memory optimization
│   └── dynamic_chunking_service.py # Content-aware chunking
├── scripts/                    # Utility scripts
│   ├── run-ingestion.py        # Main ingestion pipeline
│   ├── activate_services.py    # Phase 5 services activation
│   ├── auto-backup.ps1         # Automated backup script (Windows)
│   ├── validate-lm-studio.ps1  # LM Studio validation
│   └── AUTO_BACKUP_SETUP.md    # Backup setup guide
└── docs/                       # Documentation
    ├── QUICK_START.md          # Quick start guide
    ├── DEPLOYMENT_CHECKLIST.md # Deployment checklist
    ├── MONITORING_GUIDE.md     # Monitoring and alerting
    ├── BACKUP_RESTORE.md       # Backup procedures
    └── LM_STUDIO_SETUP.md      # LM Studio configuration
```

## Documentation

| Document | Description |
|----------|-------------|
| **QUICK_START.md** | Get started in 15 minutes - installation and basic usage |
| **DEPLOYMENT_CHECKLIST.md** | Comprehensive deployment verification checklist |
| **MONITORING_GUIDE.md** | VRAM monitoring, alerting thresholds, and health checks |
| **BACKUP_RESTORE.md** | Complete backup and restore procedures |
| **LM_STUDIO_SETUP.md** | LM Studio model configuration guide |

## Getting Started

## Getting Started

### Prerequisites

- Docker Desktop 29.9.2 or higher
- Python 3.15.2 with pip 26.2.2
- Docker Compose v5.6.1 or higher
- LM Studio installed and configured (for model switching)
- At least 56GB system RAM for model loading

### Quick Start (15 minutes)

#### Step 1: Start Qdrant Database

```bash
# Navigate to the project root directory
cd D:/AI-Memory

# Start Qdrant service using Docker Compose
docker-compose up -d

# Check if Qdrant is running
docker-compose ps
```

#### Step 2: Load Models in LM Studio

1. Open **LM Studio**
2. Navigate to **Model Catalog**
3. Download and load the following models:
   - `qwen3-coder-next` (Q4 quantization recommended)
   - `text-embedding-qwen3-embedding-8b` (Q4 quantization recommended)

#### Step 3: Verify Installation

```bash
# Test Qdrant connectivity
curl http://localhost:6333/readyz

# Test LM Studio API
curl http://localhost:1234/v1/models
```

#### Step 4: Run Ingestion Pipeline

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run ingestion on sample documents
python scripts/run-ingestion.py
```

## Full Documentation

For detailed instructions, see:

- **[Quick Start Guide](docs/QUICK_START.md)** - Step-by-step setup and daily operations
- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Comprehensive verification procedures
- **[Monitoring Guide](docs/MONITORING_GUIDE.md)** - VRAM monitoring, alerting, and health checks
- **[Backup & Restore](docs/BACKUP_RESTORE.md)** - Complete backup procedures and disaster recovery

## Development Setup

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - On Windows: `.venv\Scripts\activate`
   - On Linux/Mac: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install in development mode:
   ```bash
   pip install -e .
   ```

5. Configure LM Studio (if using model switching):
   - Load coding and embedding models
   - Verify API is accessible at localhost:1234
   - See [LM Studio Setup Guide](docs/LM_STUDIO_SETUP.md) for details

## Automated Backup Setup

For Windows users, set up automated backups:

```powershell
# Configure scheduled backup tasks (run as Administrator)
.\scripts\auto-backup.ps1

# Or use the setup guide:
.\scripts\AUTO_BACKUP_SETUP.md
```

Daily backups are automatically created:
- **LM Studio Config**: Daily at 2 AM
- **Qdrant Full Backup**: Sunday at 2 AM  
- **Qdrant Incremental**: Mon-Sat at 2 AM

## API Endpoints

## Phase 5 Services Usage

### Activating Enhanced Services

Use the activation script to enable Phase 5 services:

```bash
# Dry-run test (no changes made)
python scripts/activate_services.py --dry-run

# Activate all services with default configuration
python scripts/activate_services.py

# Activate specific services
python scripts/activate_services.py --services embedding_quality,cache_manager,dynamic_chunking
```

### Using Services in Code

```python
from ai_memory_pipeline import (
    QdrantManager,
    LMSmartEmbedder,
    EmbeddingQualityMonitor,
    ModelCacheManager,
    DynamicChunkingService
)

# Initialize services
qdrant = QdrantManager()
embedder = LMSmartEmbedder()

# Embedding Quality Monitor
quality_monitor = EmbeddingQualityMonitor(qdrant, embedder)
quality_metrics = quality_monitor.get_quality_metrics()

# Model Cache Manager (GPU optimization)
cache_manager = ModelCacheManager(embedder)
cache_status = cache_manager.get_cache_status()

# Dynamic Chunking Service
chunking_service = DynamicChunkingService()
chunks = chunking_service.chunk_text(document_text)
```

### Environment Variables

Configure services via environment variables:

```bash
# Embedding Quality Monitor
export EQM_QUALITY_THRESHOLD=0.85
export EQM_DRIFT_THRESHOLD=0.10
export EQM_CHECK_INTERVAL=3600

# Model Cache Manager
export MCM_MAX_CACHE_SIZE=2
export MCM_EVICTION_POLICY=lru
export MCM_PERSIST_CACHE=true

# Dynamic Chunking Service
export DCS_DEFAULT_CHUNK_SIZE=500
export DCS_OVERLAP_RATIO=0.1
```

## API Endpoints

- **Health Check**: `http://localhost:6333/readyz` (Qdrant)

## Configuration

The Qdrant service is configured to run on ports 6333 (HTTP) and 6334 (gRPC). The data will be persisted in the `qdrant_storage` volume.

LM Studio models are managed automatically by the smart embedder. Default configuration:

- **Coding Model**: qwen3-coder-next
- **Embedding Model**: text-embedding-qwen3-embedding-8b

Configuration files:
- `config.yaml` - Pipeline settings (chunking, batch sizes, thresholds)
- `lm-studio.json` - LM Studio model configuration (auto-generated)

## Key Features

### Core Pipeline
- ✅ Automated document ingestion with chunking and embedding
- ✅ Smart model switching between coding and embedding models
- ✅ Qdrant vector database integration for semantic search
- ✅ Sensitive data redaction and semantic summarization
- ✅ Automated backup system with Windows Task Scheduler support

### Phase 5 Enhanced Services (Optional)
- ✅ **Embedding Quality Monitor**: Real-time tracking of embedding quality, drift detection, and performance metrics
- ✅ **Model Caching Strategy**: GPU memory optimization with automatic model swapping and LRU eviction
- ✅ **Dynamic Chunking Service**: Content-type-aware chunking for different document types

### Additional Features
- ✅ VRAM monitoring and alerting
- ✅ Comprehensive logging and health checks

## Troubleshooting

See the [Quick Start Guide](docs/QUICK_START.md#troubleshooting) for common issues:
- VRAM exhaustion
- Connection refused errors
- Slow embedding generation

For detailed diagnostics, run:
```bash
python scripts/health-check.py
```

## License

This project is licensed under the MIT License.