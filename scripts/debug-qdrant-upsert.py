#!/usr/bin/env python3
"""Debug Qdrant upsert API format."""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, PointsBatch
import json

# Create client
client = QdrantClient(host="localhost", port=6333)

# Check the actual upsert method signature
print("QdrantClient.upsert signature:")
import inspect
sig = inspect.signature(client.upsert)
print(f"  {sig}")

# Try PointsBatch instead of a list of PointStruct
test_points = [
    PointStruct(
        id="test_1",
        vector=[0.1] * 384,
        payload={"content": "Test content", "source": "test"}
    ),
    PointStruct(
        id="test_2",
        vector=[0.2] * 384,
        payload={"content": "Second test", "source": "test"}
    )
]

print("\nPointsBatch:")
batch = PointsBatch(points=test_points)
print(f"  Type: {type(batch)}")
print(f"  Dict: {batch.model_dump()}")

# Check what the API expects
print("\nChecking qdrant-client version...")
import qdrant_client
print(f"  Version: {qdrant_client.__version__}")
