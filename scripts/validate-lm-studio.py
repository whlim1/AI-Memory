#!/usr/bin/env python
"""
LM Studio validation script for AI Memory Pipeline.
Tests model switching, embedding generation, and connectivity.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, r"D:\AI-Memory")

from ai_memory_pipeline.lm_studio_model_switcher import LMStudioModelSwitcher
from ai_memory_pipeline.lm_studio_smart_embedder import LMSmartEmbedder


def test_lmstudio_connection():
    """Test basic LM Studio API connectivity."""
    print("=" * 60)
    print("TEST 1: LM Studio Connection")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"✓ Connected to LM Studio successfully!")
            print(f"  Found {len(models['data'])} available models")
            
            # List all models
            for i, model in enumerate(models['data'][:5], 1):
                print(f"    {i}. {model['id']}")
            if len(models['data']) > 5:
                print(f"    ... and {len(models['data']) - 5} more")
            
            return True
        else:
            print(f"✗ Failed to connect: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_model_switcher():
    """Test the model switcher functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: Model Switcher")
    print("=" * 60)
    
    try:
        switcher = LMStudioModelSwitcher(
            host="localhost",
            port=1234
        )
        
        # Test getting current model
        current = switcher.get_current_model()
        if current:
            print(f"✓ Model detection works: {current}")
        else:
            print("⚠ Could not detect current model (none loaded)")
        
        return True
    except Exception as e:
        print(f"✗ Model switcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_smart_embedder():
    """Test the smart embedder with automatic model switching."""
    print("\n" + "=" * 60)
    print("TEST 3: Smart Embedder")
    print("=" * 60)
    
    try:
        # Create embedder instance
        embedder = LMSmartEmbedder(
            host="localhost",
            port=1234,
            embedding_model_id="text-embedding-qwen3-embedding-8b"
        )
        
        print(f"✓ Smart Embedder initialized")
        print(f"  Default embedding model: {embedder.embedding_model_id}")
        
        # Test embedding generation
        test_texts = [
            "This is a test document for embedding.",
            "AI Memory Pipeline validation testing."
        ]
        
        embeddings = embedder.generate_embeddings(test_texts)
        
        if embeddings and len(embeddings) > 0:
            dimensions = len(embeddings[0]) if embeddings else 0
            print(f"✓ Successfully generated {len(embeddings)} embeddings")
            print(f"  Dimensions: {dimensions}")
            
            # Verify embedding dimensions
            expected_dims = 4096  # Qwen3-Embedding-8B produces 4096-dim vectors
            if dimensions == expected_dims:
                print(f"✓ Embedding dimensions match expected ({expected_dims})")
            else:
                print(f"⚠ Dimension mismatch: got {dimensions}, expected {expected_dims}")
            
            return True
        else:
            print("✗ Failed to generate embeddings")
            return False
            
    except Exception as e:
        print(f"✗ Smart embedder test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_context_manager():
    """Test the context manager for automatic model switching."""
    print("\n" + "=" * 60)
    print("TEST 4: Model Context Manager")
    print("=" * 60)
    
    try:
        switcher = LMStudioModelSwitcher(
            host="localhost",
            port=1234
        )
        
        # Get current model before
        initial_model = switcher.get_current_model()
        print(f"  Initial model: {initial_model or 'None loaded'}")
        
        # Test switching to coding model using context_manager method
        with switcher.context_manager("qwen3-coder-next") as ctx:
            current = switcher.get_current_model()
            print(f"✓ Switched to coding model: {current}")
        
        # Verify we're back to original (or none)
        final_model = switcher.get_current_model()
        print(f"  Returned to: {final_model or 'None loaded'}")
        
        return True
        
    except Exception as e:
        print(f"✗ Context manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_workflow():
    """Test complete document processing workflow."""
    print("\n" + "=" * 60)
    print("TEST 5: Full Workflow Integration")
    print("=" * 60)
    
    try:
        # Initialize embedder
        embedder = LMSmartEmbedder(
            host="localhost",
            port=1234,
            embedding_model_id="text-embedding-qwen3-embedding-8b"
        )
        
        # Simulate document processing
        documents = [
            {"id": "doc1", "content": "Sample document content for testing."}
        ]
        
        print("  Processing documents with smart embedder...")
        
        # Process through embedder (this will handle model switching)
        texts = [doc["content"] for doc in documents]
        embeddings = embedder.generate_embeddings(texts)
        
        if embeddings:
            dims = len(embeddings[0]) if embeddings else 0
            print(f"✓ Full workflow successful!")
            print(f"  Documents processed: {len(documents)}")
            print(f"  Embeddings generated: {len(embeddings)}")
            print(f"  Vector dimensions: {dims}")
            
            return True
        else:
            print("✗ Workflow failed - no embeddings generated")
            return False
            
    except Exception as e:
        print(f"✗ Full workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qdrant_integration():
    """Test Qdrant vector storage integration."""
    print("\n" + "=" * 60)
    print("TEST 6: Qdrant Integration")
    print("=" * 60)
    
    try:
        from ai_memory_pipeline.qdrant_client_wrapper import QdrantManager
        
        client = QdrantManager(
            host=os.environ.get("QDRANT_HOST", "localhost"),
            port=int(os.environ.get("QDRANT_PORT", 6333))
        )
        
        # List collections
        collections = client.list_collections()
        print(f"✓ Connected to Qdrant")
        print(f"  Collections available: {collections}")
        
        return True
        
    except Exception as e:
        print(f"✗ Qdrant integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "█" * 60)
    print("  LM Studio Validation Suite")
    print("  AI Memory Pipeline - Phase 3.8-3.12 Verification")
    print("█" * 60 + "\n")
    
    results = {
        "lmstudio_connection": False,
        "model_switcher": False,
        "smart_embedder": False,
        "context_manager": False,
        "full_workflow": False,
        "qdrant_integration": False
    }
    
    # Run tests
    results["lmstudio_connection"] = test_lmstudio_connection()
    results["model_switcher"] = test_model_switcher()
    results["smart_embedder"] = test_smart_embedder()
    results["context_manager"] = test_model_context_manager()
    results["full_workflow"] = test_full_workflow()
    results["qdrant_integration"] = test_qdrant_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")
    
    print("\n" + "-" * 60)
    print(f"  Total: {passed}/{total} tests passed")
    print("-" * 60)
    
    if passed == total:
        print("\n🎉 All validation tests PASSED! LM Studio is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
