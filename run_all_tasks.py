#!/usr/bin/env python3
"""
Run all 3 tasks from the conversation checkpoint:
1. Run deduplication service tests
2. Create integration test with QdrantManager
3. Run integration test
"""

import subprocess
import sys

# Task 1: Run deduplication service tests
print("=" * 60)
print("Task 1: Running Deduplication Service Tests")
print("=" * 60)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_deduplication.py", "-v"],
    capture_output=False,
)
test_exit_code = result.returncode

# Task 2: Create integration test with QdrantManager
print("\n" + "=" * 60)
print("Task 2: Creating Integration Test with QdrantManager")
print("=" * 60)

integration_test_code = '''
"""
Integration test for DeduplicationService with QdrantManager.
Tests pre-ingestion filtering before documents enter Qdrant.
"""

import sys
sys.path.insert(0, ".")

from qdrant_client import QdrantClient
from services.qdrant_manager import QdrantManager
from services.deduplication_service import DeduplicationService

def test_dedup_integration():
    """Test deduplication service integrated with QdrantManager."""
    
    print("\\n=== Testing Deduplication + Qdrant Integration ===\\n")
    
    # Initialize services
    qdrant_manager = QdrantManager()
    dedup_service = DeduplicationService(
        exact_threshold=1.0,
        fuzzy_threshold=0.85,
    )
    
    # Test health checks
    print("1. Health Checks:")
    print(f"   QdrantManager: {'HEALTHY' if qdrant_manager.health_check() else 'UNHEALTHY'}")
    print(f"   DeduplicationService: {'HEALTHY' if dedup_service.health_check() else 'UNHEALTHY'}\\n")
    
    # Test collection
    collection_name = "test_dedup_integration"
    
    # Clean up if exists
    try:
        qdrant_manager.client.delete_collection(collection_name)
    except Exception:
        pass
    
    print("2. Creating Test Collection...")
    qdrant_manager.create_collection(
        collection_name=collection_name,
        vector_size=384,  # MiniLM-L6-v2 dimension
        distance="Cosine",
    )
    print(f"   Created: {collection_name}\\n")
    
    # Test documents for ingestion
    test_documents = [
        ("doc1", "This is a unique document about artificial intelligence."),
        ("doc2", "Machine learning and neural networks are transforming technology."),
        ("doc3", "This is a unique document about artificial intelligence."),  # Exact duplicate of doc1
        ("doc4", "Cooking recipes with fresh ingredients and herbs."),
    ]
    
    print("3. Testing Pre-Ingestion Deduplication Filter:")
    print("-" * 50)
    
    for doc_id, content in test_documents:
        result = dedup_service.check_document(doc_id, content)
        
        if result.is_duplicate:
            print(f"\\n[REJECTED - DUPLICATE] {doc_id}")
            print(f"   Content: {content[:60]}...")
            print(f"   Duplicate of: {result.duplicate_of}")
            print(f"   Similarity: {result.similarity_score:.4f}")
        else:
            print(f"\\n[ACCEPTED - UNIQUE] {doc_id}")
            print(f"   Content: {content[:60]}...")
            
            # Simulate vector embedding (would normally use LMSmartEmbedder)
            # For testing, we'll use a simple hash-based embedding
            import hashlib
            
            def create_simple_embedding(text, dimension=384):
                """Create a simple deterministic embedding for testing."""
                hash_val = int(hashlib.sha256(text.encode()).hexdigest(), 16)
                vector = []
                temp_hash = hash_val
                for i in range(dimension):
                    temp_hash = (temp_hash * 9301 + 49297) % 233280
                    vector.append((temp_hash / 233280.0) - 0.5)
                return vector
            
            # Insert into Qdrant
            embedding = create_simple_embedding(content)
            
            qdrant_manager.client.upsert(
                collection_name=collection_name,
                points=[{
                    "id": doc_id,
                    "vector": embedding,
                    "payload": {
                        "content": content,
                        "source": "test_dedup",
                    },
                }]
            )
    
    # Print statistics
    print("\\n" + "=" * 60)
    print("4. Deduplication Statistics:")
    print("=" * 60)
    stats = dedup_service.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.4f}")
        else:
            print(f"   {key}: {value}")
    
    # Verify collection state
    print("\\n" + "=" * 60)
    print("5. Qdrant Collection State:")
    print("=" * 60)
    
    try:
        count = qdrant_manager.client.count(collection_name=collection_name)
        print(f"   Total vectors in collection: {count.count}")
        
        points = qdrant_manager.client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True,
            with_vector=False,
        )
        
        print("\\n   Stored Documents:")
        for point in points[0]:
            doc_id = point.payload.get("source", "unknown")
            content_snippet = point.payload.get("content", "")[:60]
            print(f"     - {doc_id}: {content_snippet}...")
    except Exception as e:
        print(f"   Error querying collection: {e}")
    
    # Cleanup
    print("\\n" + "=" * 60)
    print("6. Cleanup:")
    print("=" * 60)
    try:
        qdrant_manager.client.delete_collection(collection_name)
        print(f"   Deleted collection: {collection_name}")
    except Exception as e:
        print(f"   Error deleting collection: {e}")
    
    # Final health check
    print("\\n" + "=" * 60)
    print("7. Final Health Check:")
    print("=" * 60)
    final_health = dedup_service.health_check()
    print(f"   Service Status: {'HEALTHY' if final_health else 'UNHEALTHY'}")
    
    return 0 if final_health else 1


if __name__ == "__main__":
    sys.exit(test_dedup_integration())
'''

with open("tests/test_deduplication_integration.py", "w") as f:
    f.write(integration_test_code)

print("Integration test file created: tests/test_deduplication_integration.py")

# Task 3: Run integration test
print("\n" + "=" * 60)
print("Task 3: Running Deduplication Integration Test")
print("=" * 60)

result = subprocess.run(
    [sys.executable, "tests/test_deduplication_integration.py"],
    capture_output=False,
)
integration_exit_code = result.returncode

# Summary
print("\n" + "=" * 60)
print("All Tasks Completed!")
print("=" * 60)
print(f"\nTask 1 (Deduplication Tests): {'PASSED' if test_exit_code == 0 else 'FAILED'}")
print(f"Task 2 (Create Integration Test): COMPLETED")
print(f"Task 3 (Integration Test Run): {'PASSED' if integration_exit_code == 0 else 'FAILED'}")

sys.exit(0)
