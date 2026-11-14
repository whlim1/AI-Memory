#!/usr/bin/env python3
"""Test LM Studio connectivity and embedding dimensions."""
import requests
import sys

def test_lm_studio():
    """Test LM Studio API connectivity and embeddings."""
    base_url = "http://localhost:1234"
    
    # Test models endpoint
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get('data', [])
            print(f"LM Studio Models Available: {len(models)}")
            for m in models[:5]:
                print(f"  - {m.get('id', 'unknown')}")
        else:
            print(f"Error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"Error connecting to LM Studio models: {e}")
        return False
    
    # Test embeddings endpoint with Qwen3 model
    try:
        payload = {
            "model": "text-embedding-qwen3-embedding-8b",
            "input": ["test embedding"]
        }
        response = requests.post(f"{base_url}/v1/embeddings", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            embedding = result.get('data', [{}])[0].get('embedding', [])
            print(f"Embedding dimension: {len(embedding)}")
            return True
        else:
            print(f"Embeddings endpoint error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"Error testing embeddings: {e}")
        return False

if __name__ == "__main__":
    success = test_lm_studio()
    sys.exit(0 if success else 1)
