# LM Studio Configuration

## Overview
This document describes the LM Studio configuration for the AI Memory Pipeline.

## Prerequisites
- LM Studio installed and running on localhost:1234
- Models loaded: Qwen3-Coder-Next-UD (chat) and Qwen3-Embedding-8B (embeddings)
- Network access to localhost:1234

## Configuration Files

### lm-studio-config.json
```json
{
  "api_url": "http://localhost:1234",
  "default_chat_model": "qwen3-coder-next",
  "default_embedding_model": "text-embedding-qwen3-embedding-8b",
  "timeout_seconds": 60,
  "max_retries": 3
}
```

### Model Configuration

#### Chat Model: qwen3-coder-next
- **Purpose**: Code generation, natural language processing
- **Context Window**: Up to 128K tokens
- **Use Cases**: Document summarization, code comments, content generation

#### Embedding Model: text-embedding-qwen3-embedding-8b
- **Vector Dimensions**: 4096
- **Max Input Length**: 8192 tokens
- **Use Cases**: Semantic search, vector storage in Qdrant

## LM Studio Model Switcher

### Features
- Automatic model switching between chat and embedding models
- State preservation (saves/restores loaded models)
- Context manager support for safe switching
- Error handling with automatic retries

### Configuration
```json
{
  "lm_studio": {
    "base_url": "http://localhost:1234",
    "chat_model_name": "qwen3-coder-next",
    "embedding_model_name": "text-embedding-qwen3-embedding-8b"
  }
}
```

## Usage Examples

### Basic Connection
```python
from ai_memory_pipeline.lm_studio_client import LMStudioClient

client = LMStudioClient("http://localhost:1234")
models = client.get_models()
print(f"Available models: {len(models)}")
```

### Smart Embedder with Automatic Model Switching
```python
from ai_memory_pipeline.lm_studio_smart_embedder import LMSmartEmbedder

embedder = LMSmartEmbedder(
    api_url="http://localhost:1234",
    embedding_model_name="text-embedding-qwen3-embedding-8b"
)

# Embed documents with automatic model switching
documents = ["First document", "Second document"]
embeddings = embedder.embed(documents)
```

### Model Switcher Context Manager
```python
from ai_memory_pipeline.lm_studio_model_switcher import LMStudioModelSwitcher

switcher = LMStudioModelSwitcher("http://localhost:1234")

# Automatically saves current model, switches to chat, restores after
with switcher.use_chat_model():
    result = switcher.generate("Summarize this document...")

# Model is automatically restored to previous state
```

## Troubleshooting

### Connection Issues
- Verify LM Studio is running: `curl http://localhost:1234/v1/models`
- Check firewall settings
- Ensure models are loaded in LM Studio UI

### Model Not Found
- List available models via API or LM Studio UI
- Update configuration with correct model names
- Reload missing models in LM Studio

## Best Practices
1. Always verify connectivity before processing documents
2. Use context managers for safe model switching
3. Implement retry logic for production workloads
4. Monitor VRAM usage when loading multiple models
