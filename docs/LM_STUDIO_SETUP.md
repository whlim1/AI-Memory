# LM Studio Configuration Guide

## Overview

This document covers the configuration and usage of LM Studio for the AI Memory Pipeline, including automatic model switching between coding (qwen3-coder-next) and embedding (text-embedding-qwen3-embedding-8b) models.

## Prerequisites

- LM Studio installed and running
- Python 3.15 or higher
- Qdrant running on port 6333

## Installation

### Step 1: Install LM Studio

Download and install from [LM Studio](https://lmstudio.ai/)

### Step 2: Load Required Models

Open LM Studio and load the following models:

1. **Coding Model**: `qwen3-coder-next`
   - Use for chat/completions tasks
   - ~20GB VRAM required

2. **Embedding Model**: `text-embedding-qwen3-embedding-8b` (quantized Q4 recommended)
   - Use for vector embeddings
   - ~24GB VRAM required
   - Produces 4096-dimensional vectors

### Step 3: Start LM Studio Server

1. In LM Studio, click the **Server** icon (server with play button) in the top-right corner
2. The server will start on `localhost:1234` by default
3. Verify the server is running by checking the URL: http://localhost:1234

## Configuration

### API Endpoint

The LM Studio API endpoint:
```
http://localhost:1234/v1
```

### Model IDs

| Model Type | Model ID |
|------------|----------|
| Coding     | `qwen3-coder-next` |
| Embedding  | `text-embedding-qwen3-embedding-8b` |

## Usage

### Using the Smart Embedder

The smart embedder automatically manages model switching:

```python
from ai_memory_pipeline import LMSmartEmbedder

# Initialize with automatic model management
embedder = LMSmartEmbedder(
    host="localhost",
    port=1234,
    embedding_model_id="text-embedding-qwen3-embedding-8b"
)

# Generate embeddings - model switching happens automatically
documents = ["Your text here", "More text"]
embeddings = embedder.generate_embeddings(documents)
```

### Using the Model Switcher Directly

For manual control over model switching:

```python
from ai_memory_pipeline import LMStudioModelSwitcher

switcher = LMStudioModelSwitcher(
    host="localhost",
    port=1234,
    coding_model_id="qwen3-coder-next",
    embedding_model_id="text-embedding-qwen3-embedding-8b"
)

# Switch to coding model
if switcher.switch_to_coding_model():
    print("Switched to coding model")

# Switch to embedding model
if switcher.switch_to_embedding_model():
    print("Switched to embedding model")
```

### Using Context Manager

The context manager ensures automatic restoration of the previous model:

```python
from ai_memory_pipeline import LMStudioModelSwitcher

switcher = LMStudioModelSwitcher(host="localhost", port=1234)

# Automatically switch to coding model and restore after block
with switcher.context_manager("qwen3-coder-next"):
    # Do coding work here
    result = switcher.generate_chat_completion(messages)
# Model automatically restored to previous

# Or use the smart embedder with automatic switching
embedder = LMSmartEmbedder(host="localhost", port=1234)

with embedder.use_embedding_model():
    embeddings = embedder.generate_embeddings(documents)
# Embedding model remains loaded for efficiency
```

## Troubleshooting

### Server Not Starting

- Ensure no other application is using port 1234
- Check LM Studio logs in the server view
- Restart LM Studio and try again

### Model Loading Failures

- Verify you have sufficient VRAM (both models need ~44GB total)
- Try loading models one at a time
- Use quantized versions (Q4 or Q5 recommended)

### Connection Issues

```python
# Test connectivity
import requests

try:
    response = requests.get("http://localhost:1234/v1/models")
    print(f"Connected! Models available: {len(response.json().get('data', []))}")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Verification Script

Run the validation script to check your setup:

```bash
python scripts/validate-lm-studio.py
```

## Advanced Configuration

### Custom Model IDs

If you're using different model names:

```python
switcher = LMStudioModelSwitcher(
    host="localhost",
    port=1234,
    coding_model_id="your-coding-model-name",
    embedding_model_id="your-embedding-model-name"
)
```

### Disable Automatic Model Switching

```python
embedder = LMSmartEmbedder(
    host="localhost",
    port=1234,
    auto_switch_models=False  # Disable automatic switching
)
```

## Performance Tips

1. **Keep Embedding Model Loaded**: The embedding model stays loaded during batch processing for better performance
2. **Use Context Manager**: For single operations, use context manager to restore previous state
3. **Monitor VRAM**: Keep an eye on VRAM usage in LM Studio's server view
4. **Batch Processing**: Process documents in batches to optimize memory usage

## API Reference

### LMSmartEmbedder

```python
LMSmartEmbedder(
    host: str = "localhost",
    port: int = 1234,
    embedding_model_id: str = "text-embedding-qwen3-embedding-8b",
    coding_model_id: Optional[str] = None,
    auto_switch_models: bool = True,
    restore_previous_model: bool = True
)
```

**Methods:**

- `generate_embeddings(texts: List[str]) -> List[List[float]]`: Generate embeddings for multiple texts
- `generate_single_embedding(text: str) -> List[float]`: Generate embedding for single text
- `use_embedding_model()`: Context manager to temporarily use embedding model

### LMStudioModelSwitcher

```python
LMStudioModelSwitcher(
    host: str = "localhost",
    port: int = 1234,
    coding_model_id: Optional[str] = None,
    embedding_model_id: Optional[str] = None
)
```

**Methods:**

- `get_current_model() -> Optional[str]`: Get currently loaded model
- `switch_to_model(model_id: str) -> bool`: Switch to specific model
- `switch_to_embedding_model() -> bool`: Switch to embedding model
- `switch_to_coding_model() -> bool`: Switch to coding model
- `context_manager(target_model_id: str)`: Context manager for temporary switching

## Related Documentation

- [Qdrant Setup](./QDRANT_SETUP.md)
- [Ingestion Pipeline](./INGESTION_PIPELINE.md)
- [API Reference](./API_REFERENCE.md)
