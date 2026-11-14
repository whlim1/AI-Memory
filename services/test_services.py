#!/usr/bin/env python3
"""
Test script for Phase 5 services: Embedding Quality Monitor, Model Caching Strategy, and Dynamic Chunking.
"""

import sys
sys.path.insert(0, r"D:\AI-Memory")

def test_embedding_quality_monitor():
    """Test the Embedding Quality Monitor service."""
    print("=== Testing Embedding Quality Monitor ===\n")
    
    try:
        from services.embedding_quality_monitor import (
            EmbeddingQualityMonitor, EmbeddingQualityMetrics
        )
        
        # Create monitor
        monitor = EmbeddingQualityMonitor()
        print("✓ EmbeddingQualityMonitor instantiated successfully")
        print(f"  - Thresholds: drift={monitor.drift_threshold}, norm_std={monitor.norm_std_threshold}")
        
        # Test vector statistics tracking
        import numpy as np
        
        # Simulate some embeddings
        embeddings = [np.random.rand(384).tolist() for _ in range(10)]
        
        # Use the metrics class directly
        metrics = EmbeddingQualityMetrics("test_collection")
        
        # Calculate norm stats
        vectors_array = np.array(embeddings)
        stats = metrics.calculate_vector_norm_stats(vectors_array)
        print(f"\n✓ Vector statistics calculated:")
        print(f"  - Mean norm: {stats['mean_norm']:.4f}")
        print(f"  - Std norm: {stats['std_norm']:.4f}")
        print(f"  - Norm range: [{stats['min_norm']:.4f}, {stats['max_norm']:.4f}]")
        
        # Test drift detection
        drifted_embeddings = [np.random.rand(384).tolist() for _ in range(10)]
        drifted_array = np.array(drifted_embeddings)
        
        drift_result = metrics.calculate_embedding_drift(drifted_array, embeddings[:5])
        print(f"\n✓ Drift detection completed:")
        print(f"  - Cosine similarity: {drift_result['average_cosine_similarity']:.4f}")
        print(f"  - Is drifted: {drift_result['drift_detected']}")
        
        # Test quality scoring
        quality_score = monitor._calculate_quality_score(
            stats, 
            zero_vector_count=0,
            total_vectors=len(embeddings),
            avg_similarity=drift_result['average_cosine_similarity']
        )
        print(f"\n✓ Quality score calculated: {quality_score:.2f}/100")
        
        # Test threshold violation detection
        violations = monitor.check_thresholds(stats)
        print(f"\n✓ Threshold check completed: {len(violations)} violations found")
        for v in violations:
            print(f"  - {v}")
        
        print("\n✅ Embedding Quality Monitor: PASSED\n")
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ Embedding Quality Monitor: FAILED - {e}\n")
        traceback.print_exc()
        print()
        return False


def test_model_caching_strategy():
    """Test the Model Caching Strategy service."""
    print("=== Testing Model Caching Strategy ===\n")
    
    try:
        from datetime import datetime, timezone
        from services.model_caching_strategy import (
            ModelCacheManager, ModelSwitcher, ModelStatus, ModelInfo
        )
        
        # Create cache manager (won't connect to LM Studio if not running)
        cache_mgr = ModelCacheManager(lm_studio_url="http://localhost:1234")
        
        print("✓ ModelCacheManager instantiated successfully")
        print(f"  - LM Studio URL: {cache_mgr.lm_studio_url}")
        print(f"  - Max GPU memory: {cache_mgr.max_gpu_memory_gb}GB")
        print(f"  - Hot model count: {cache_mgr.hot_model_count}")
        
        # Test switcher
        switcher = ModelSwitcher(cache_mgr)
        print("\n✓ ModelSwitcher instantiated successfully")
        
        # Test model state transitions (via cache_manager directly)
        # Simulate a model by manually adding to models dict (for testing purposes)
        cache_mgr.models["test-model"] = ModelInfo(
            model_id="test-model",
            model_name="Test Model",
            status=ModelStatus.COLD,
            last_used=datetime.now(timezone.utc),
            usage_count=0,
            estimated_vram_usage=1.5
        )
        
        cache_mgr.models["test-model"].status = ModelStatus.HOT
        status = cache_mgr.models["test-model"].status.value
        print(f"\n✓ Model state transition test:")
        print(f"  - Set 'test-model' to HOT: {status}")
        
        cache_mgr.models["test-model"].status = ModelStatus.WARM
        status = cache_mgr.models["test-model"].status.value
        print(f"  - Set 'test-model' to WARM: {status}")
        
        # Test cache persistence
        try:
            cache_mgr._save_state()
            print("\n✓ Cache state saved successfully")
        except Exception as e:
            print(f"\n⚠ Could not save cache state: {e}")
        
        print("\n✅ Model Caching Strategy: PASSED\n")
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ Model Caching Strategy: FAILED - {e}\n")
        traceback.print_exc()
        print()
        return False


def test_dynamic_chunking_service():
    """Test the Dynamic Chunking Service."""
    print("=== Testing Dynamic Chunking Service ===\n")
    
    try:
        from services.dynamic_chunking_service import (
            DynamicChunkingService, ContentTypeDetector, 
            ContentChunker, ContentType
        )
        
        # Create service
        chunker = DynamicChunkingService(default_chunk_size=1000, chunk_overlap=200)
        print("✓ DynamicChunkingService instantiated successfully")
        
        # Test content detection
        detector = ContentTypeDetector()
        
        test_cases = [
            ("test.py", "def hello():\n    return 'world'"),
            ("readme.md", "# Title\n\nSome text here."),
            ("config.json", '{"key": "value"}'),
            ("script.js", "const x = 1; console.log(x);"),
        ]
        
        print("\n✓ Content type detection:")
        for filename, content in test_cases:
            detected_type, info = detector.detect(filename, content)
            print(f"  {filename}: {detected_type} (source: {info['source']})")
        
        # Test chunking
        demo_text = """
This is a demonstration of the dynamic chunking service.
The service automatically detects content types and applies appropriate chunking strategies.

For code files, it respects function and class boundaries.
For text documents, it uses sentence-level chunking.
For markdown, it preserves header structure.

You can use this service to preprocess your documents before embedding them.
"""
        
        chunks = chunker.chunk_content(demo_text, filename="demo.txt")
        print(f"\n✓ Text chunking successful: {len(chunks)} chunks created")
        for i, chunk in enumerate(chunks):
            preview = chunk.content[:50] + "..." if len(chunk.content) > 50 else chunk.content
            print(f"  Chunk {i+1} ({chunk.content_type}, size={len(chunk.content)}): {preview}")
        
        # Test code chunking
        code_text = """
def hello():
    print("Hello World")

def goodbye():
    return "See you"

class MyClass:
    def method(self):
        pass
"""
        code_chunks = chunker.chunk_content(code_text, filename="test.py")
        print(f"\n✓ Code chunking successful: {len(code_chunks)} chunks created")
        
        # Test statistics
        stats = chunker.get_statistics()
        print("\n✓ Chunking statistics:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        
        print("\n✅ Dynamic Chunking Service: PASSED\n")
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ Dynamic Chunking Service: FAILED - {e}\n")
        traceback.print_exc()
        print()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 5 SERVICES TEST SUITE")
    print("=" * 60 + "\n")
    
    results = {
        "Embedding Quality Monitor": test_embedding_quality_monitor(),
        "Model Caching Strategy": test_model_caching_strategy(),
        "Dynamic Chunking Service": test_dynamic_chunking_service(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} services passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
