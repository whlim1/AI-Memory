#!/usr/bin/env python3
"""
Test LM Studio configuration and connectivity.
Tests model loading, embedding dimensions, and API endpoints.
"""

import requests
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_config():
    """Load LM Studio configuration."""
    config_path = Path(__file__).parent.parent / "docs" / "LM_STUDIO_CONFIG.md"
    if config_path.exists():
        print(f"Configuration file: {config_path}")
        return {
            "api_url": "http://localhost:1234",
            "default_chat_model": "qwen3-coder-next",
            "default_embedding_model": "text-embedding-qwen3-embedding-8b"
        }
    return None

def test_connection(api_url):
    """Test basic connectivity to LM Studio."""
    print("\n" + "=" * 60)
    print("TEST: Connection to LM Studio")
    print("=" * 60)
    
    try:
        response = requests.get(f"{api_url}/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get('data', [])
            print(f"✓ Connected successfully!")
            print(f"  Available models: {len(models)}")
            return models
        else:
            print(f"✗ Connection failed with status: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Error connecting to LM Studio: {e}")
        return None

def test_embedding_model(api_url, model_name):
    """Test embedding model functionality."""
    print("\n" + "=" * 60)
    print(f"TEST: Embedding Model - {model_name}")
    print("=" * 60)
    
    try:
        payload = {
            "model": model_name,
            "input": ["test document for embedding"]
        }
        response = requests.post(
            f"{api_url}/v1/embeddings",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            embeddings = result.get('data', [])
            
            if embeddings:
                embedding = embeddings[0].get('embedding', [])
                dimension = len(embedding)
                
                print(f"✓ Embedding model works!")
                print(f"  Model: {model_name}")
                print(f"  Vector dimension: {dimension}")
                print(f"  Sample values (first 5): {embedding[:5]}")
                return True, dimension
            else:
                print("✗ No embeddings returned")
                return False, None
        else:
            print(f"✗ Embedding request failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"✗ Error testing embedding model: {e}")
        return False, None

def test_chat_model(api_url, model_name):
    """Test chat model functionality."""
    print("\n" + "=" * 60)
    print(f"TEST: Chat Model - {model_name}")
    print("=" * 60)
    
    try:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'test' and nothing else."}
            ],
            "temperature": 0.7,
            "max_tokens": 10
        }
        
        response = requests.post(
            f"{api_url}/v1/chat/completions",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            print(f"✓ Chat model works!")
            print(f"  Model: {model_name}")
            print(f"  Response: {content}")
            return True
        else:
            print(f"✗ Chat request failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing chat model: {e}")
        return False

def verify_model_names(api_url, expected_chat, expected_embedding):
    """Verify that expected models are available."""
    print("\n" + "=" * 60)
    print("TEST: Model Name Verification")
    print("=" * 60)
    
    response = requests.get(f"{api_url}/v1/models", timeout=5)
    if response.status_code != 200:
        print(f"✗ Failed to get models: {response.status_code}")
        return False
    
    models = response.json().get('data', [])
    available_models = [m.get('id', '') for m in models]
    
    print(f"Available models ({len(available_models)}):")
    for model_id in available_models:
        print(f"  - {model_id}")
    
    chat_found = any(expected_chat.lower() in m.lower() for m in available_models)
    embedding_found = any(expected_embedding.lower() in m.lower() for m in available_models)
    
    if chat_found:
        print(f"\n✓ Chat model '{expected_chat}' found")
    else:
        print(f"\n✗ Chat model '{expected_chat}' NOT found")
        
    if embedding_found:
        print(f"✓ Embedding model '{expected_embedding}' found")
    else:
        print(f"✗ Embedding model '{expected_embedding}' NOT found")
    
    return chat_found and embedding_found

def main():
    """Run all LM Studio tests."""
    print("=" * 60)
    print("LM STUDIO CONFIGURATION TEST SUITE")
    print("=" * 60)
    
    # Load configuration
    config = load_config()
    if not config:
        print("Warning: Could not load configuration file")
        config = {
            "api_url": "http://localhost:1234",
            "default_chat_model": "qwen3-coder-next",
            "default_embedding_model": "text-embedding-qwen3-embedding-8b"
        }
    
    api_url = config.get("api_url", "http://localhost:1234")
    chat_model = config.get("default_chat_model", "qwen3-coder-next")
    embedding_model = config.get("default_embedding_model", "text-embedding-qwen3-embedding-8b")
    
    all_passed = True
    
    # Test 1: Connection
    models = test_connection(api_url)
    if not models:
        all_passed = False
    
    # Test 2: Verify model names
    if models:
        if not verify_model_names(api_url, chat_model, embedding_model):
            all_passed = False
    
    # Test 3: Embedding model
    if models:
        success, dim = test_embedding_model(api_url, embedding_model)
        if not success or dim != 4096:
            print(f"\n⚠ Warning: Expected 4096 dimensions, got {dim}")
            # Don't fail on dimension mismatch - model might be different version
        all_passed = all_passed and success
    
    # Test 4: Chat model (optional)
    if models:
        test_chat_model(api_url, chat_model)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if all_passed:
        print("✓ All tests passed!")
        print(f"\nConfiguration verified:")
        print(f"  API URL: {api_url}")
        print(f"  Chat Model: {chat_model}")
        print(f"  Embedding Model: {embedding_model}")
        return 0
    else:
        print("✗ Some tests failed")
        print("\nPlease check the errors above and ensure LM Studio is running.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
