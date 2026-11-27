# LM Studio Configuration

## Overview
This document describes the LM Studio configuration for the AI Memory Pipeline.

## Prerequisites
- LM Studio installed and running on localhost:1234
- Models loaded: qwen/qwen3.6-35b-a3b (chat), text-embedding-qwen3-embedding-8b (embeddings), deepseek-r1-distill-qwen-32b (reasoning)
- Network access to localhost:1234

## Configuration Files

### lm-studio-config.json
```json
{
  "api_url": "http://localhost:1234",
  "default_chat_model": "qwen/qwen3.6-35b-a3b",
  "default_embedding_model": "text-embedding-qwen3-embedding-8b",
  "default_reasoning_model": "deepseek-r1-distill-qwen-32b",
  "default_code_model": "qwen3-coder-next",
  "timeout_seconds": 60,
  "max_retries": 3
}
```

### Model Configuration

#### Chat Model: qwen/qwen3.6-35b-a3b (default)
- **Purpose**: General chat, document summarization, content generation
- **Alternative chat**: `qwen3.8-flash-next` (faster), `qwen3.8-27b` (lighter)
- **Context Window**: Up to 131K tokens
- **Use Cases**: Document summarization, code comments, content generation

#### Reasoning Model: deepseek-r1-distill-qwen-32b
- **Purpose**: Complex reasoning, multi-step problem solving
- **Alternative**: `qwen3.5-14b-a3b-claude-4.6-opus-reasoning-distilled-reap` (lighter reasoning)

#### Code Model: qwen3-coder-next
- **Purpose**: Code generation, code review, development tasks
- **Alternative**: `qwen3-coder-30b-a3b-instruct` (larger, more capable)

#### Embedding Model: text-embedding-qwen3-embedding-8b (default)
- **Vector Dimensions**: 4096
- **Max Input Length**: 8192 tokens
- **Alternative**: `text-embedding-bge-m3` (multi-lingual), `text-embedding-nomic-embed-text-v1.5` (lightweight)
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
    "chat_model_name": "qwen/qwen3.6-35b-a3b",
    "embedding_model_name": "text-embedding-qwen3-embedding-8b",
    "reasoning_model_name": "deepseek-r1-distill-qwen-32b",
    "code_model_name": "qwen3-coder-next"
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
