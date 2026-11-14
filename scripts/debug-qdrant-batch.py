#!/usr/bin/env python3
"""Debug Qdrant upsert API format with Batch."""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, PointsBatch, Batch
import json

# Create client
client = QdrantClient(host="localhost", port=6333)

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

# Try PointsBatch with correct field name
print("PointsBatch:")
try:
    batch = PointsBatch(points=test_points)
    print(f"  Type: {type(batch)}")
    print(f"  Dict: {batch.model_dump()}")
except Exception as e:
    print(f"  Error: {e}")

# Try Batch (the correct format for multiple vectors per point)
print("\nBatch:")
try:
    # Batch is for when each point has multiple vectors
    batch = Batch(
        ids=["test_1", "test_2"],
        vectors=[[0.1] * 384, [0.2] * 384],
        payloads=[
            {"content": "Test content", "source": "test"},
            {"content": "Second test", "source": "test"}
        ]
    )
    print(f"  Type: {type(batch)}")
    print(f"  Dict: {batch.model_dump()}")
except Exception as e:
    print(f"  Error: {e}")

# Test upsert with PointsList (raw dict format)
print("\nTrying direct list of PointStruct:")
try:
    result = client.upsert(
        collection_name="aimemory_docs",
        points=test_points
    )
    print(f"  Success: {result}")
except Exception as e:
    print(f"  Error: {e}")
