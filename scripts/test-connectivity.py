#!/usr/bin/env python
"""Test connectivity to LM Studio and Qdrant."""

import os
import sys

# Check LM Studio connectivity
try:
    import requests
    response = requests.get("http://localhost:1234/v1/models", timeout=5)
    models = response.json()
    print(f"LM Studio connected successfully. Found {len(models['data'])} models.")
    for model in models['data']:
        print(f"  - {model['id']}")
except Exception as e:
    print(f"Error connecting to LM Studio: {e}")
    sys.exit(1)

# Check Qdrant connectivity
try:
    qdrant_host = os.environ.get("QDRANT_HOST", "localhost")
    qdrant_port = int(os.environ.get("QDRANT_PORT", 6333))
    print(f"\nChecking Qdrant at {qdrant_host}:{qdrant_port}...")
    
    # Try to import and connect
    sys.path.insert(0, r"D:\AI-Memory")
    from ai_memory_pipeline.qdrant_client_wrapper import QdrantManager
    
    client = QdrantManager(
        host=qdrant_host,
        port=qdrant_port
    )
    
    collections = client.list_collections()
    print(f"Qdrant connected. Collections: {collections}")
except Exception as e:
    print(f"Error connecting to Qdrant: {e}")

print("\nConnectivity check complete.")
