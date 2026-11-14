#!/usr/bin/env python3
"""Debug Qdrant API format issue."""

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import json

# Create a sample point to see the expected format
client = QdrantClient(host="localhost", port=6333)

# Check what models are available
import qdrant_client.models as models
print("Available models:")
for name in dir(models):
    if 'Point' in name or 'struct' in name.lower():
        print(f"  - {name}")

# Try to see the payload schema for the collection
try:
    collection_info = client.get_collection("aimemory_docs")
    print("\nCollection info:")
    print(f"  Vector size: {collection_info.config.params.vectors.size}")
    print(f"  Vector count: {collection_info.vectors_count}")
    print(f"  Payload schema: {collection_info.payload_schema}")
except Exception as e:
    print(f"\nError getting collection info: {e}")

# Test creating a point and checking its dict representation
test_point = PointStruct(
    id="test_1",
    vector=[0.1] * 384,
    payload={"content": "Test content", "source": "test"}
)

print(f"\nPointStruct type: {type(test_point)}")
print(f"PointStruct dict: {test_point.dict()}")
print(f"PointStruct to_dict: {test_point.to_dict()}")

# Check if there's an alternative API format
print("\nQdrantClient methods with 'upsert':")
for name in dir(client):
    if 'upsert' in name.lower():
        print(f"  - {name}")
