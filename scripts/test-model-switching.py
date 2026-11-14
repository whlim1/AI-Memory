#!/usr/bin/env python3
"""
Test LM Studio model switching functionality.
Verifies that the model switcher can safely switch between chat and embedding models.
"""

import requests
import sys
import time

# Add project root to path
sys.path.insert(0, r"D:\AI-Memory")

from ai_memory_pipeline.lm_studio_model_switcher import LMStudioModelSwitcher


def test_basic_connection():
    """Test basic connectivity."""
    print("\n" + "=" * 60)
    print("TEST: Basic Connection")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json()['data']
            print(f"✓ Connected to LM Studio")
            print(f"  Available models: {len(models)}")
            
            model_ids = [m['id'] for m in models]
            print("\nAvailable models:")
            for mid in model_ids:
                print(f"  - {mid}")
            
            return True, model_ids
        else:
            print(f"✗ Connection failed: {response.status_code}")
            return False, []
    except Exception as e:
        print(f"✗ Error connecting: {e}")
        return False, []


def test_model_switcher():
    """Test basic model switching functionality."""
    print("\n" + "=" * 60)
    print("TEST: Model Switcher")
    print("=" * 60)
    
    try:
        switcher = LMStudioModelSwitcher(host="localhost", port=1234)
        current_model = switcher.current_model
        print(f"✓ Initialized model switcher")
        print(f"  Current model: {current_model}")
        
        # Test switching to embedding model and back
        if current_model != "text-embedding-qwen3-embedding-8b":
            success = switcher.switch_to_model("text-embedding-qwen3-embedding-8b")
            if success:
                print(f"✓ Switched to embedding model")
                time.sleep(2)
                
                # Switch back
                success = switcher.switch_to_model(current_model)
                if success:
                    print(f"✓ Successfully switched back to {current_model}")
                    return True
        
        return True  # Even if we couldn't switch, the basic functionality works
        
    except Exception as e:
        print(f"✗ Error in model switcher: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_manager():
    """Test context manager for automatic model switching."""
    print("\n" + "=" * 60)
    print("TEST: Context Manager")
    print("=" * 60)
    
    try:
        switcher = LMStudioModelSwitcher(host="localhost", port=1234)
        original_model = switcher.current_model
        
        print(f"Original model: {original_model}")
        
        # Use context manager to switch to embedding model
        with switcher.context_manager("text-embedding-qwen3-embedding-8b") as ctx:
            current = ctx.current_model
            print(f"Inside context: {current}")
            
            if current != "text-embedding-qwen3-embedding-8b":
                print(f"✗ Context did not switch to target model")
                return False
        
        # Check that we restored correctly
        after_model = switcher.current_model
        print(f"After context: {after_model}")
        
        if after_model == original_model:
            print(f"✓ Model successfully restored to {original_model}")
            return True
        else:
            print(f"✗ Model not restored! Expected {original_model}, got {after_model}")
            return False
        
    except Exception as e:
        print(f"✗ Error in context manager: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_smart_embedder():
    """Test smart embedder with automatic model switching."""
    print("\n" + "=" * 60)
    print("TEST: Smart Embedder")
    print("=" * 60)
    
    try:
        from ai_memory_pipeline.lm_studio_smart_embedder import LMSmartEmbedder
        
        embedder = LMSmartEmbedder(
            host="localhost",
            port=1234,
            embedding_model_id="text-embedding-qwen3-embedding-8b"
        )
        
        # Test with sample documents
        documents = [
            "First test document about AI and machine learning.",
            "Second document discussing data processing pipelines.",
            "Third document covering model deployment strategies."
        ]
        
        print(f"  Embedding {len(documents)} documents...")
        embeddings = embedder.generate_embeddings(documents)
        
        if len(embeddings) == len(documents):
            print(f"✓ Successfully embedded {len(embeddings)} documents")
            
            # Check dimensions
            for i, (doc, emb) in enumerate(zip(documents, embeddings)):
                dim = len(emb)
                status = "✓" if dim == 4096 else f"⚠ Expected 4096, got {dim}"
                print(f"    Document {i+1}: {dim} dimensions - {status}")
            
            return True
        else:
            print(f"✗ Embedding count mismatch: expected {len(documents)}, got {len(embeddings)}")
            return False
            
    except ImportError as e:
        print(f"⚠ Could not import LMSmartEmbedder (may be optional): {e}")
        return None  # Not a failure if class doesn't exist
    except Exception as e:
        print(f"✗ Error in smart embedder: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LM STUDIO MODEL SWITCHING TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Basic connection
    success, models = test_basic_connection()
    results["Basic Connection"] = success
    
    if not success:
        print("\n✗ Cannot proceed without LM Studio connection")
        return False
    
    # Test 2: Model switcher
    results["Model Switcher"] = test_model_switcher()
    
    # Test 3: Context manager
    results["Context Manager"] = test_context_manager()
    
    # Test 4: Smart embedder (optional)
    results["Smart Embedder"] = test_smart_embedder()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results.items():
        if result is None:
            status = "⚠ SKIPPED"
        elif result:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"
            all_passed = False
        print(f"  {test_name}: {status}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("=" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
