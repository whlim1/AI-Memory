# Production Deployment Guide for Phase 5 Services

A step-by-step guide for deploying the three enhanced services in production.

---

## Prerequisites

- ✅ AI Memory Pipeline v0.3.0+ installed
- ✅ Qdrant running (v1.11.0+)
- ✅ LM Studio accessible at configured endpoint
- ✅ Python 3.9+ with virtual environment support
- ✅ Read/Write access to `logs/` directory

---

## Deployment Options

### Option A: Automated Activation (Recommended)

```bash
# Navigate to project directory
cd D:\AI-Memory

# Activate all services
python scripts/activate_services.py
```

### Option B: Manual Configuration

#### 1. Environment Variables

Create `.env.production`:

```bash
# Embedding Quality Monitor
EQM_QUALITY_THRESHOLD=0.85
EQM_DRIFT_THRESHOLD=0.10
EQM_CHECK_INTERVAL=3600
EQM_HISTORY_SIZE=1000

# Model Cache Manager
MCM_MAX_CACHE_SIZE=2
MCM_EVICTION_POLICY=lru
MCM_PERSIST_CACHE=true

# Dynamic Chunking Service
DCS_DEFAULT_CHUNK_SIZE=500
DCS_OVERLAP_RATIO=0.1

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=aimemory_docs

# LM Studio Configuration
LM_STUDIO_BASE_URL=http://localhost:1234
```

#### 2. Apply Configuration

```bash
# Load environment variables
set -a
source .env.production
set +a

# Verify configuration
python -c "import os; print('EQM_QUALITY_THRESHOLD:', os.getenv('EQM_QUALITY_THRESHOLD'))"
```

---

## Service-Specific Deployment

### Embedding Quality Monitor

#### Pre-deployment Checklist

- [ ] Qdrant collection exists and is accessible
- [ ] LM Studio embedding model is loaded
- [ ] Sufficient storage for metrics history
- [ ] Alerting system configured (email/webhook)

#### Activation Steps

```bash
# 1. Run activation in dry-run mode first
python scripts/activate_services.py --dry-run --services embedding_quality

# 2. Review output and confirm activation
python scripts/activate_services.py --services embedding_quality

# 3. Verify service is running
python -c "
from ai_memory_pipeline import QdrantManager, LMSmartEmbedder, EmbeddingQualityMonitor
q = QdrantManager()
e = LMSmartEmbedder()
m = EmbeddingQualityMonitor(q, e)
print('Service Status:', m.health_check())
"
```

#### Post-deployment Verification

```bash
# Check initial metrics collection
python -c "
from ai_memory_pipeline import QdrantManager, LMSmartEmbedder, EmbeddingQualityMonitor
q = QdrantManager()
e = LMSmartEmbedder()
m = EmbeddingQualityMonitor(q, e)

# Get baseline metrics
metrics = m.get_quality_metrics()
print(f'Collected samples: {metrics[\"sample_count\"]}')
print(f'Average quality: {metrics[\"average_quality\"]:.3f}')
print(f'Drift status: {metrics[\"drift_status\"]}')
"
```

---

### Model Caching Strategy

#### Pre-deployment Checklist

- [ ] GPU memory monitoring tools available
- [ ] LM Studio model switching is functional
- [ ] Sufficient disk space for cache persistence (if enabled)
- [ ] Log rotation configured for cache statistics

#### Activation Steps

```bash
# 1. Dry-run test
python scripts/activate_services.py --dry-run --services cache_manager

# 2. Activate with production settings
python scripts/activate_services.py --services cache_manager

# 3. Verify model caching works
python -c "
from ai_memory_pipeline import LMSmartEmbedder, ModelCacheManager
e = LMSmartEmbedder()
cache = ModelCacheManager(e)

status = cache.get_cache_status()
print(f'Current size: {status[\"current_size\"]}/{status[\"max_size\"]}')
"
```

#### Cache Warming (Recommended)

After deployment, warm the cache with frequently-used models:

```bash
python -c "
from ai_memory_pipeline import LMSmartEmbedder, ModelCacheManager

e = LMSmartEmbedder()
cache = ModelCacheManager(e)

# Warm cache with common models
models_to_cache = [
    'text-embedding-qwen3-embedding-8b',
    # Add other frequently-used models here
]

for model_id in models_to_cache:
    print(f'Caching: {model_id}')
    cache.cache_model(model_id)
    
print('Cache warming complete')
"
```

---

### Dynamic Chunking Service

#### Pre-deployment Checklist

- [ ] Sample documents of each type available for testing
- [ ] Testing environment with representative data
- [ ] Monitoring for chunk quality metrics

#### Activation Steps

```bash
# 1. Dry-run test
python scripts/activate_services.py --dry-run --services dynamic_chunking

# 2. Activate service
python scripts/activate_services.py --services dynamic_chunking

# 3. Test with different document types
python -c "
from ai_memory_pipeline import DynamicChunkingService

chunker = DynamicChunkingService()

# Test code detection
code_text = '''def hello():
    print('Hello World')
    return True'''

chunks = chunker.chunk_text(code_text)
print(f'Code chunks: {len(chunks)}')

# Verify content analysis
info = chunker.analyze_content(code_text)
print(f'Detected type: {info[\"type\"]} (confidence: {info[\"confidence\"]:.3f})')
"
```

---

## Integration Testing

### Complete Workflow Test

```bash
python -c "
import os
from ai_memory_pipeline import (
    QdrantManager,
    LMSmartEmbedder,
    EmbeddingQualityMonitor,
    ModelCacheManager,
    DynamicChunkingService
)

# Initialize all services
q = QdrantManager()
e = LMSmartEmbedder()

quality_monitor = EmbeddingQualityMonitor(q, e)
cache_manager = ModelCacheManager(e)
chunker = DynamicChunkingService()

print('=== All Services Initialized ===')

# Test quality monitoring
test_text = 'This is a test document for the production deployment.'
embeddings = e.embed_documents([test_text])
quality_score = quality_monitor.check_embedding_quality(embeddings[0])
print(f'Quality Score: {quality_score:.3f}')

# Test cache manager
cache_status = cache_manager.get_cache_status()
print(f'Cache Status: {cache_status[\"current_size\"]}/{cache_status[\"max_size\"]} models')

# Test dynamic chunking
chunks = chunker.chunk_text(test_text)
print(f'Dynamic chunks created: {len(chunks)}')

print('=== Production Readiness Verified ===')
"
```

---

## Monitoring Setup

### Logging Configuration

Services log to `logs/services.log` with the following structure:

```json
{
  "timestamp": "2026-11-14T17:00:00Z",
  "service": "embedding_quality_monitor",
  "level": "INFO",
  "message": "Quality check completed",
  "metrics": {
    "quality_score": 0.92,
    "drift_detected": false
  }
}
```

### Metrics Endpoints

```python
# Embedding Quality Metrics
python -c "
from ai_memory_pipeline import QdrantManager, LMSmartEmbedder, EmbeddingQualityMonitor
q = QdrantManager()
e = LMSmartEmbedder()
m = EmbeddingQualityMonitor(q, e)
metrics = m.get_quality_metrics()
import json; print(json.dumps(metrics, indent=2))
"

# Cache Statistics
python -c "
from ai_memory_pipeline import LMSmartEmbedder, ModelCacheManager
e = LMSmartEmbedder()
cache = ModelCacheManager(e)
stats = cache.get_cache_statistics()
import json; print(json.dumps(stats, indent=2))
"
```

### Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

echo "=== Phase 5 Services Health Check ==="

python -c "
from ai_memory_pipeline import (
    QdrantManager,
    LMSmartEmbedder,
    EmbeddingQualityMonitor,
    ModelCacheManager,
    DynamicChunkingService
)

try:
    q = QdrantManager()
    e = LMSmartEmbedder()
    
    # Quality Monitor
    quality = EmbeddingQualityMonitor(q, e)
    q_status = 'OK' if quality.health_check()['status'] == 'healthy' else 'DEGRADED'
    print(f'[Quality Monitor] {q_status}')
    
    # Cache Manager
    cache = ModelCacheManager(e)
    c_status = 'OK' if cache.health_check()['status'] == 'healthy' else 'DEGRADED'
    print(f'[Cache Manager] {c_status}')
    
    # Dynamic Chunking
    chunker = DynamicChunkingService()
    d_status = 'OK' if chunker.health_check()['status'] == 'healthy' else 'DEGRADED'
    print(f'[Dynamic Chunking] {d_status}')
    
    all_ok = q_status == 'OK' and c_status == 'OK' and d_status == 'OK'
    exit(0 if all_ok else 1)
    
except Exception as ex:
    print(f'ERROR: {ex}')
    exit(1)
"
```

---

## Rollback Procedure

If issues arise, services can be deactivated:

```bash
# Deactivate a specific service
python scripts/activate_services.py --services embedding_quality --dry-run

# Or modify config.yaml to disable services:
# Set enabled: false for any service

# Restart application to apply changes
```

---

## Maintenance Schedule

| Day | Task | Command |
|-----|------|---------|
| Daily | Check logs for errors | `grep -i error logs/services.log` |
| Weekly | Review quality metrics | `python scripts/metrics-report.py` |
| Bi-weekly | Cache cleanup | `python -c "from ai_memory_pipeline import ModelCacheManager; from ai_memory_pipeline import LMSmartEmbedder; c = ModelCacheManager(LMSmartEmbedder()); c.clear_cache()"` |
| Monthly | Full health audit | Run `scripts/health-check.sh` |

---

## Support

For issues:
1. Check logs: `logs/services.log`
2. Review metrics: `logs/quality_metrics.json`, `logs/cache_stats.json`
3. Run diagnostics: `python scripts/diagnostics.py`
