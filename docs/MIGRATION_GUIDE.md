# Migration Guide: AI-Memory → AIPlatform

**Version:** 1.0  
**Date:** 2025-01-28  
**Status:** ✅ Complete

---

## Overview

This guide covers migration from the previous AI-Memory project structure to the new AIPlatform architecture with Phase 6 (Unified Knowledge Management Layer).

---

## 1. Project Renaming

### What Changed

| Old | New |
|-----|-----|
| `AI-Memory` (project name) | `AIPlatform` |
| `ai_memory_pipeline` (package) | `ai_memory_pipeline` (unchanged) |
| `docs/AI-Memory` references | `docs/AIPlatform` |

### Actions Required

1. **Rename the project directory** (if not already done):
   ```bash
   # On Synology NAS
   mv /docker/AI-Memory /docker/AIPlatform
   ```

2. **Update Docker compose references**:
   ```yaml
   # docker-compose.yml
   # Update any volume mounts pointing to the old path
   volumes:
     - /docker/AIPlatform/obsidian-vault:/vault
   ```

3. **Update documentation**:
   - All references to "AI-Memory" should be "AIPlatform"
   - This guide covers remaining changes

---

## 2. From Manual Ingestion to Auto-Sync

### Before (Manual)

```bash
# Old workflow: manually run ingestion scripts
python scripts/ingest.py --path ~/obsidian-vault/Notes
python scripts/embed.py --path ~/obsidian-vault/Notes
python scripts/index.py --collection ai_memory_documents
```

### After (Automatic)

```python
# New workflow: sync engine handles everything
from ai_memory_pipeline.obsidian.sync_engine import SyncEngine

engine = SyncEngine()
engine.start()  # Starts vault watcher + auto-processing
# Notes are automatically: parsed → categorized → embedded → indexed
```

### Migration Steps

1. **Stop manual ingestion scripts** (they still work for backward compatibility)
2. **Set up Obsidian vault path**:
   ```bash
   export OBSIDIAN_VAULT_PATH=/path/to/your/vault
   ```
3. **Enable auto-categorization** (optional, requires LM Studio):
   ```bash
   export OBSIDIAN_AUTO_CATEGORIZE=true
   ```
4. **Start the sync engine** as a background service

---

## 3. From Heuristic-Only to AI-Enhanced

### Before (Heuristic Only)

The `_auto_categorize` function used keyword matching:
```python
# Old: keyword-based categorization
tech_keywords = ["api", "code", "python", "docker"]
if any(kw in body for kw in tech_keywords):
    category = "technology"
```

### After (AI + Heuristic Fallback)

The new service uses a **two-phase approach**:
1. **Heuristic fallback** (fast, < 1ms) — always available
2. **AI enhancement** (90-300s) — when LM Studio is running

```python
# New: AI with automatic fallback
from ai_memory_pipeline.services import ai_categorization_service

analysis = ai_categorization_service.analyze_note(
    body=note_content,
    tags=existing_tags,
    title=note_title,
)
# If LM Studio is down, falls back to heuristic automatically
```

### Configuration

```bash
# Enable AI categorization
export OBSIDIAN_AUTO_CATEGORIZE=true

# Specify the model to use
export AI_CATEGORIZATION_MODEL=local-model

# LM Studio endpoint
export LM_STUDIO_BASE_URL=http://192.168.0.19:1234/v1
```

---

## 4. Configuration Changes

### New Environment Variables

```bash
# AI Categorization (NEW)
AI_CATEGORIZATION_CACHE_TTL=3600        # Cache TTL in seconds
AI_CATEGORIZATION_MODEL=local-model      # Model name

# AI Categorization (existing, no change)
OBSIDIAN_AUTO_CATEGORIZE=true

# Qdrant (existing, no change)
QDRANT_URL=http://192.168.0.16:6333

# LM Studio (existing, no change)
LM_STUDIO_BASE_URL=http://192.168.0.19:1234/v1
```

### Updated `.env.example`

The `.env.example` file has been updated to include:
- `AI_CATEGORIZATION_MODEL` — default `local-model`
- `AI_CATEGORIZATION_CACHE_TTL` — default `3600`

---

## 5. Data Migration

### Qdrant Documents

Existing Qdrant documents remain compatible. The new `DocumentMetadata` class adds fields but is backward compatible:

| Field | Old | New |
|-------|-----|-----|
| `source_file` | ✅ | ✅ |
| `vault` | ✅ | ✅ |
| `category` | ✅ (heuristic) | ✅ (AI-enhanced) |
| `subcategories` | ❌ | ✅ |
| `entities` | ❌ | ✅ |
| `confidence` | ❌ | ✅ |
| `ai_reasoning` | ❌ | ✅ |
| `tags` | ✅ | ✅ |

### Migration Script

For existing documents without AI fields, run this once:

```python
from ai_memory_pipeline.metadata import DocumentMetadata

# For each existing document in Qdrant:
# If entities/confidence/ai_reasoning are missing, set defaults
meta = DocumentMetadata.from_dict(existing_dict)
if not meta.entities:
    meta.entities = {"people": [], "places": [], "organizations": [], "concepts": []}
if meta.confidence == 0.0:
    meta.confidence = 0.5  # Default confidence for pre-AI documents
if not meta.subcategories:
    meta.subcategories = []
if not meta.ai_reasoning:
    meta.ai_reasoning = "Pre-AI categorization"
```

### Knowledge Graph

The knowledge graph is a new component. It starts empty and builds as notes are processed:

```python
from ai_memory_pipeline.obsidian.graph_builder import KnowledgeGraphBuilder

graph = KnowledgeGraphBuilder(persistence_path="/path/to/graph.json")
graph.load()  # Load existing graph (if any)
# ... process notes ...
graph.save()  # Persist to JSON
```

---

## 6. Backward Compatibility

### What Still Works

| Component | Status |
|-----------|--------|
| Manual ingestion scripts | ✅ Still functional |
| Phase 5 services (Qdrant, embeddings) | ✅ Unchanged |
| Existing Qdrant documents | ✅ Compatible |
| Existing Qdrant collections | ✅ Same names |

### What Changed

| Component | Change |
|-----------|--------|
| `_auto_categorize` | Replaced with `ai_categorization_service.analyze_note()` |
| `DocumentMetadata` | Added `entities`, `confidence`, `ai_reasoning` fields |
| `NoteContent` | Added `links` field |
| Sync engine | Now orchestrates full pipeline (was manual) |

---

## 7. Deployment Checklist

### Pre-Migration

- [ ] Back up existing Qdrant data
- [ ] Back up existing knowledge graph (if any)
- [ ] Verify LM Studio is running and accessible
- [ ] Copy `.env.example` to `.env` and fill in secrets

### Migration

- [ ] Rename project directory (if needed)
- [ ] Update Docker compose volume mounts
- [ ] Update `.env` with new variables
- [ ] Run existing ingestion scripts once to seed Qdrant
- [ ] Start sync engine

### Post-Migration

- [ ] Verify vault watcher detects existing notes
- [ ] Check Qdrant for new categorized documents
- [ ] Verify knowledge graph persistence
- [ ] Test mobile input (OpenWebUI or Obsidian)
- [ ] Monitor logs for errors

---

## 8. Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Sync engine fails to start | Check `OBSIDIAN_VAULT_PATH` exists and is readable |
| AI categorization always falls back to heuristic | Verify LM Studio is running and `LM_STUDIO_BASE_URL` is correct |
| Cache not clearing | Use `ai_categorization_service.clear_cache()` or delete `.cache/categorization/` |
| Knowledge graph not persisting | Ensure `persistence_path` directory exists and is writable |
| Qdrant connection failed | Verify `QDRANT_URL` or `QDRANT_HOST`/`QDRANT_PORT` |

### Debug Mode

```bash
# Enable debug logging
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from ai_memory_pipeline.obsidian.sync_engine import SyncEngine
engine = SyncEngine()
engine.start()
"
```

---

## 9. Rollback Plan

If issues arise, you can roll back to the previous setup:

1. **Stop the sync engine**:
   ```python
   engine.stop()
   ```

2. **Disable auto-categorization**:
   ```bash
   export OBSIDIAN_AUTO_CATEGORIZE=false
   ```

3. **Resume manual ingestion**:
   ```bash
   python scripts/ingest.py --path ~/obsidian-vault/Notes
   ```

4. **Restore from backup** (if needed):
   ```bash
   # Restore Qdrant collection
   qdrant snapshot restore /backup/qdrant-snapshot
   
   # Restore knowledge graph
   cp /backup/graph.json /path/to/graph.json
   ```

---

**This migration guide is complete. All changes are backward compatible.**
