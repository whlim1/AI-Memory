# Phase 5 Enhanced Services Guide

A comprehensive guide to the three new production services for AI Memory Pipeline:

- **Embedding Quality Monitor**: Track embedding quality and detect drift
- **Model Caching Strategy**: Optimize GPU memory with intelligent caching
- **Dynamic Chunking Service**: Content-aware chunking for diverse document types

## Overview

Phase 5 introduces optional, independent services that enhance the core pipeline without blocking operations. All services can be enabled/disabled independently based on your needs.

---

## 1. Embedding Quality Monitor

### Purpose
Track embedding quality metrics in real-time and detect distribution drift before it impacts search relevance.

### Features
- Real-time embedding quality scoring
- Statistical drift detection (KS test)
- Performance trend analysis
- Automated alerts for quality degradation

### Configuration

**Environment Variables:**
```bash
EQM_QUALITY_THRESHOLD=0.85    # Minimum acceptable quality score (0-1)
EQM_DRIFT_THRESHOLD=0.10      # Maximum acceptable drift (0-1)
EQM_CHECK_INTERVAL=3600       # Check frequency in seconds
EQM_HISTORY_SIZE=1000         # Samples for baseline calculation
```

**config.yaml:**
```yaml
embedding_quality_monitor:
  quality_threshold: 0.85
  drift_threshold: 0.10
  check_interval_seconds: 3600
  history_size: 1000
```

### Usage

```python
from ai_memory_pipeline import (
    QdrantManager,
    LMSmartEmbedder,
    EmbeddingQualityMonitor
)

# Initialize
qdrant = QdrantManager()
embedder = LMSmartEmbedder()
monitor = EmbeddingQualityMonitor(qdrant, embedder)

# Check quality of new embeddings
def process_document(text):
    # Get embeddings
    embeddings = embedder.embed_documents([text])
    
    # Monitor quality
    quality_score = monitor.check_embedding_quality(embeddings[0])
    
    if quality_score < monitor.quality_threshold:
        print(f"⚠️  Quality alert: {quality_score:.3f}")
    
    return embeddings

# Get comprehensive metrics
metrics = monitor.get_quality_metrics()
print(f"Average Quality: {metrics['average_quality']:.3f}")
print(f"Drift Status: {metrics['drift_status']}")

# Reset baseline (after model changes)
monitor.reset_baseline()
```

---

## 2. Model Caching Strategy

### Purpose
Optimize GPU memory usage by intelligently caching embedding models and automatically swapping when needed.

### Features
- LRU cache eviction
- Automatic model loading/unloading
- Cache statistics and monitoring
- Configurable cache size limits

### Configuration

**Environment Variables:**
```bash
MCM_MAX_CACHE_SIZE=2          # Maximum models in cache
MCM_EVICTION_POLICY=lru       # Eviction policy: lru, fifo, random
MCM_PERSIST_CACHE=true        # Persist cache across restarts
```

**config.yaml:**
```yaml
model_cache_manager:
  max_cache_size: 2
  eviction_policy: lru
  persist_cache: true
```

### Usage

```python
from ai_memory_pipeline import LMSmartEmbedder, ModelCacheManager

# Initialize
embedder = LMSmartEmbedder()
cache = ModelCacheManager(embedder)

# Get status
status = cache.get_cache_status()
print(f"Cache Size: {status['current_size']}/{status['max_size']}")
print(f"Models in Cache:")
for model_id, info in status['cached_models'].items():
    print(f"  - {model_id}: last used {info['last_used']}")

# Manually cache a model (optional)
cache.cache_model("text-embedding-qwen3-embedding-8b")

# Get cache statistics
stats = cache.get_cache_statistics()
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")
print(f"Hit Rate: {stats['hit_rate']:.2%}")

# Clear specific model from cache
cache.clear_model("text-embedding-qwen3-embedding-8b")

# Clear entire cache
cache.clear_cache()
```

---

## 3. Dynamic Chunking Service

### Purpose
Adapt chunking strategy based on document content type for optimal embedding quality.

### Features
- Content-type detection (code, prose, mixed)
- Adaptive chunk sizes per content type
- Overlap optimization
- Fallback to default chunking

### Configuration

**Environment Variables:**
```bash
DCS_DEFAULT_CHUNK_SIZE=500    # Default chunk size in tokens
DCS_OVERLAP_RATIO=0.1         # Chunk overlap ratio (10%)
DCS_CODE_CHUNK_SIZE=300       # Code-specific chunk size
DCS_PROSE_CHUNK_SIZE=600      # Prose-specific chunk size
```

**config.yaml:**
```yaml
dynamic_chunking:
  default_chunk_size: 500
  overlap_ratio: 0.1
  content_types:
    code:
      chunk_size: 300
      overlap_ratio: 0.05
    prose:
      chunk_size: 600
      overlap_ratio: 0.15
```

### Usage

```python
from ai_memory_pipeline import DynamicChunkingService

# Initialize
chunker = DynamicChunkingService()

# Auto-detect content type and chunk
document_text = "def hello():\n    print('Hello World')"
chunks = chunker.chunk_text(document_text)

# Explicit content type specification
code_chunks = chunker.chunk_text(document_text, content_type="code")
prose_chunks = chunker.chunk_text("This is a long document...", content_type="prose")

# Get detected content type
content_info = chunker.analyze_content(document_text)
print(f"Detected Type: {content_info['type']}")
print(f"Confidence: {content_info['confidence']:.3f}")

# Custom chunking parameters
custom_chunks = chunker.chunk_text(
    document_text,
    chunk_size=400,
    overlap_ratio=0.2
)
```

---

## Activation and Deployment

### Quick Start
```bash
# Test activation without changes
python scripts/activate_services.py --dry-run

# Activate all services
python scripts/activate_services.py
```

### Production Checklist

1. **Pre-deployment**
   - [ ] Review environment variable configurations
   - [ ] Verify Qdrant connection settings
   - [ ] Confirm LM Studio API accessibility
   - [ ] Test services in dry-run mode

2. **Activation**
   ```bash
   # Set environment variables (if using .env file)
   cp .env.example .env
   # Edit .env with your values
   
   # Run activation
   python scripts/activate_services.py
   ```

3. **Post-deployment Verification**
   - [ ] Check service logs for errors
   - [ ] Verify metrics are being recorded
   - [ ] Test cache warming with sample queries
   - [ ] Validate chunking quality on test documents

---

## Monitoring and Maintenance

### Health Checks
```python
# All services support health check
monitor = EmbeddingQualityMonitor(qdrant, embedder)
cache = ModelCacheManager(embedder)
chunker = DynamicChunkingService()

print("Quality Monitor:", monitor.health_check())
print("Cache Manager:", cache.health_check())
print("Dynamic Chunking:", chunker.health_check())
```

### Log Locations
- Services log to `logs/services.log`
- Quality metrics: `logs/quality_metrics.json`
- Cache statistics: `logs/cache_stats.json`

### Maintenance Tasks

| Task | Frequency | Command |
|------|-----------|---------|
| Review quality alerts | Daily | Check logs for warnings |
| Clear old metrics | Weekly | `monitor.clear_history(days=7)` |
| Monitor cache hit rate | Weekly | `cache.get_cache_statistics()` |
| Update baseline | After model changes | `monitor.reset_baseline()` |

---

## Troubleshooting

### Common Issues

**1. Quality scores consistently low**
- Check embedding model is appropriate for your data
- Verify text preprocessing is consistent
- Consider adjusting `EQM_QUALITY_THRESHOLD`

**2. Cache evictions too aggressive**
- Increase `MCM_MAX_CACHE_SIZE`
- Review `MCM_EVICTION_POLICY` (lru vs fifo)
- Enable persistence for faster reloads

**3. Dynamic chunking not detecting content type**
- Verify training data is representative
- Check document length (very short texts may be ambiguous)
- Adjust detection thresholds in config

### Getting Help
1. Run diagnostics: `python scripts/diagnostics.py`
2. Check service logs in `logs/services.log`
3. Review metrics: `logs/quality_metrics.json`, `logs/cache_stats.json`
