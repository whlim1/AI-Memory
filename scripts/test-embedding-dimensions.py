#!/usr/bin/env python3
"""
Test LM Studio embedding dimensions.
Verifies that embeddings are 4096-dimensional as expected.
"""

import requests
import sys
import numpy as np

def test_embedding_dimensions(api_url="http://localhost:1234", model_name=None):
    """Test embedding model produces correct dimensions."""
    
    # Default to Qwen3 embedding model
    if not model_name:
        model_name = "text-embedding-qwen3-embedding-8b"
    
    print(f"Testing embedding dimensions for model: {model_name}")
    print("=" * 60)
    
    test_texts = [
        "Short text",
        "This is a longer text with multiple sentences to test the embedding model's handling of varying input lengths.",
        "",
        "A" * 100,  # Long text
    ]
    
    expected_dimension = 4096
    
    all_passed = True
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        try:
            payload = {
                "model": model_name,
                "input": [text]
            }
            
            response = requests.post(
                f"{api_url}/v1/embeddings",
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"  ✗ Request failed with status {response.status_code}")
                all_passed = False
                continue
            
            result = response.json()
            data = result.get('data', [])
            
            if not data:
                print("  ✗ No embedding data returned")
                all_passed = False
                continue
            
            embedding = data[0].get('embedding', [])
            actual_dimension = len(embedding)
            
            # Check dimension
            if actual_dimension == expected_dimension:
                print(f"  ✓ Correct dimension: {actual_dimension}")
            else:
                print(f"  ✗ Dimension mismatch: expected {expected_dimension}, got {actual_dimension}")
                all_passed = False
            
            # Print statistics
            arr = np.array(embedding)
            print(f"    Min: {arr.min():.6f}")
            print(f"    Max: {arr.max():.6f}")
            print(f"    Mean: {arr.mean():.6f}")
            print(f"    Std: {arr.std():.6f}")
            
        except requests.exceptions.Timeout:
            print("  ✗ Request timed out")
            all_passed = False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All embedding dimension tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test LM Studio embedding dimensions")
    parser.add_argument("--url", default="http://localhost:1234", help="LM Studio API URL")
    parser.add_argument("--model", default=None, help="Model name (default: text-embedding-qwen3-embedding-8b)")
    
    args = parser.parse_args()
    sys.exit(test_embedding_dimensions(args.url, args.model))
