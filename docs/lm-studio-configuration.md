# LM Studio Configuration Guide

## Overview
LM Studio provides an OpenAI-compatible API endpoint for local LLM inference. This document describes the configuration and validation process.

## Endpoint Details
- **Base URL**: `http://localhost:1234/v1`
- **Models**: Loaded via LM Studio UI (e.g., Qwen3.8-27B)
- **Authentication**: Bearer token from Infisical

## Configuration Files
1. `.env.example` - Template for environment variables (copy to `.env`)
2. `opencode/opencode.json` - OpenCode agent configuration with LM Studio model provider

## Validation Steps

### 1. Verify LM Studio is Running
Open LM Studio and ensure:
- Server is started on port 1234
- Model is loaded (e.g., Qwen3.8-27B)

### 2. Test API Endpoint

#### Using curl:
```bash
curl -X GET http://localhost:1234/v1/models ^
  -H "Authorization: Bearer your_api_key"
```

#### Using Python:
```python
import requests

response = requests.get(
    "http://localhost:1234/v1/models",
    headers={"Authorization": "Bearer your_api_key"}
)
print(response.json())
```

### 3. Verify Model List
Expected response:
```json
{
  "data": [
    {
      "id": "lmstudio-qwen3-27b",
      "object": "model",
      "created": 1234567890,
      "owned_by": "lm-studio"
    }
  ]
}
```

## OpenCode Integration
The OpenCode agent is configured to use LM Studio as its default model provider:

```json
{
  "models": {
    "default": "lmstudio-qwen3-27b",
    "providers": {
      "lmstudio": {
        "type": "openai",
        "baseURL": "http://localhost:1234/v1",
        "apiKey": "${INFISICAL_API_KEY}",
        "models": [
          {
            "id": "lmstudio-qwen3-27b",
            "name": "Qwen3.8-27B (LM Studio)",
            "contextWindow": 32768
          }
        ]
      }
    }
  }
}
```

## Troubleshooting

### Connection Refused
- Ensure LM Studio server is running
- Verify port 1234 is not blocked by firewall
- Check if another service is using port 1234

### Authentication Failed
- Verify INFISICAL_API_KEY is set in environment
- Check that the API key format matches Infisical requirements

### Model Not Found
- Load a model via LM Studio UI before making API calls
- Verify the model ID matches what's shown in LM Studio

## Next Steps
After confirming LM Studio connectivity, start Qdrant and test the full retrieval pipeline.
