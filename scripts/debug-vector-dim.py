#!/usr/bin/env python3
"""Debug vector dimension mismatch."""

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Check embedding dimension
print("Checking embedding dimensions...")
embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
test_text = "Test sentence"
embedding = embedder.encode(test_text)
print(f"  Embedding shape: {embedding.shape}")

# Check collection vector size
client = QdrantClient(host="localhost", port=6333)
try:
    collection_info = client.get_collection("aimemory_docs")
    vector_size = collection_info.config.params.vectors.size
    print(f"  Collection vector size: {vector_size}")
    
    if vector_size != embedding.shape[0]:
        print(f"  ⚠️  MISMATCH: Embedding dim ({embedding.shape[0]}) != Collection dim ({vector_size})")
except Exception as e:
    print(f"Error getting collection info: {e}")
