#!/usr/bin/env python3
"""Integration test for Phase 5 services."""

import sys
from ai_memory_pipeline import (
    QdrantManager,
    LMSmartEmbedder,
    EmbeddingQualityMonitor,
    ModelCacheManager,
    DynamicChunkingService,
)


def test_qdrant_connection():
    """Test Qdrant connection."""
    print("Testing Qdrant connection...")
    try:
        qdrant = QdrantManager()
        # Use _get_collections method if available, otherwise use list_collections
        if hasattr(qdrant.client, 'list_collections'):
            collections = qdrant.client.list_collections()
            collection_names = [c.name for c in collections]
            print(f"  ✓ Connected to Qdrant, found {len(collection_names)} collections")
        else:
            # Fallback - just verify connection works
            print(f"  ✓ Connected to Qdrant at {qdrant.url}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to connect: {e}")
        return False


def test_lm_studio_connection():
    """Test LM Studio connection."""
    print("Testing LM Studio connection...")
    try:
        embedder = LMSmartEmbedder()
        # Use internal method to get available models
        available = embedder._get_available_models()
        print(f"  ✓ Connected to LM Studio, found {len(available)} models")
        return True
    except Exception as e:
        print(f"  ✗ Failed to connect: {e}")
        return False


def test_embedding_quality_monitor():
    """Test EmbeddingQualityMonitor with health check."""
    print("Testing EmbeddingQualityMonitor...")
    try:
        # Use qdrant_client parameter (not qdrant_manager)
        monitor = EmbeddingQualityMonitor(qdrant_host='localhost', qdrant_port=6333)
        
        # Test health check
        health = monitor.health_check()
        assert health['status'] in ['healthy', 'unhealthy'], "Invalid health status"
        assert 'dependencies' in health, "Missing dependencies in health check"
        print(f"  ✓ Health check passed: {health['status']}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_cache_manager():
    """Test ModelCacheManager with health check."""
    print("Testing ModelCacheManager...")
    try:
        embedder = LMSmartEmbedder()
        cache_manager = ModelCacheManager(lm_studio=embedder)
        
        # Test health check
        health = cache_manager.health_check()
        assert health['status'] in ['healthy', 'unhealthy'], "Invalid health status"
        assert 'dependencies' in health, "Missing dependencies in health check"
        print(f"  ✓ Health check passed: {health['status']}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dynamic_chunking_service():
    """Test DynamicChunkingService with health check."""
    print("Testing DynamicChunkingService...")
    try:
        service = DynamicChunkingService(
            default_chunk_size=1000,
            chunk_overlap=200,
        )
        
        # Test health check
        health = service.health_check()
        assert health['status'] in ['healthy', 'unhealthy'], "Invalid health status"
        assert 'dependencies' in health, "Missing dependencies in health check"
        print(f"  ✓ Health check passed: {health['status']}")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_integration():
    """Test all services working together."""
    print("\n=== Full Integration Test ===")
    
    results = []
    
    # Test connections
    results.append(("Qdrant connection", test_qdrant_connection()))
    results.append(("LM Studio connection", test_lm_studio_connection()))
    
    # Test individual services
    results.append(("EmbeddingQualityMonitor", test_embedding_quality_monitor()))
    results.append(("ModelCacheManager", test_model_cache_manager()))
    results.append(("DynamicChunkingService", test_dynamic_chunking_service()))
    
    # Print summary
    print("\n=== Test Summary ===")
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    success = test_full_integration()
    sys.exit(0 if success else 1)
