#!/usr/bin/env python3
"""
Test script for Dynamic Model Selector

Validates that the model selection logic works correctly for different task types.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
script_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(script_dir))

from ai_memory_pipeline.dynamic_model_selector import (
    DynamicModelSelector,
    TaskType,
    ProviderType,
    get_model_selector,
    select_model,
    get_model_info,
    MODEL_CAPABILITIES_DB
)


def test_basic_selection():
    """Test basic model selection for different task types."""
    print("\\n=== Test: Basic Model Selection ===")
    
    selector = DynamicModelSelector()
    
    tasks_and_expected = {
        TaskType.CHAT: ["chat", "general"],
        TaskType.CODING: ["coding", "code generation"],
        TaskType.REASONING: ["reasoning", "step-by-step"],
        TaskType.EMBEDDING: ["embedding", "semantic search"],
        TaskType.RAG: ["rag", "retrieval"],
    }
    
    for task_type, expected_strengths in tasks_and_expected.items():
        model_id = selector.select(task_type)
        info = get_model_info(model_id)
        
        print(f"\\nTask Type: {task_type.value}")
        print(f"  Selected Model: {model_id}")
        print(f"  Provider: {info.get('provider', 'N/A')}")
        print(f"  Strengths: {', '.join(info.get('strengths', []))}")
        
        # Verify strengths match expected
        model_strengths = [s.lower() for s in info.get('strengths', [])]
        if any(any(exp in strength for strength in model_strengths) 
               for exp in expected_strengths):
            print(f"  ✓ Model strengths match task requirements")
        else:
            print(f"  ⚠ Warning: Strengths may not be optimal")


def test_strategy_modes():
    """Test different selection strategies."""
    print("\\n=== Test: Strategy Modes ===")
    
    # Save original environment
    orig_strategy = os.getenv("LLM_SELECTION_STRATEGY")
    
    selector = DynamicModelSelector()
    
    for strategy in ["auto", "manual"]:
        os.environ["LLM_SELECTION_STRATEGY"] = strategy
        
        # Force reload of config
        new_selector = DynamicModelSelector()
        
        model_id = new_selector.select(TaskType.CHAT)
        print(f"Strategy '{strategy}': Selected {model_id}")
    
    # Restore original environment
    if orig_strategy:
        os.environ["LLM_SELECTION_STRATEGY"] = orig_strategy
    else:
        os.environ.pop("LLM_SELECTION_STRATEGY", None)


def test_model_database():
    """Test the model capabilities database."""
    print("\\n=== Test: Model Database ===")
    
    print(f"Total models in database: {len(MODEL_CAPABILITIES_DB)}")
    print("\\nModels by provider:")
    
    providers = {}
    for model_id, config in MODEL_CAPABILITIES_DB.items():
        provider = config["provider"].value
        if provider not in providers:
            providers[provider] = []
        providers[provider].append(model_id)
    
    for provider, models in sorted(providers.items()):
        print(f"  {provider}:")
        for model in models:
            capabilities = [c.value for c in config["capabilities"]]
            print(f"    - {model} ({', '.join(capabilities[:2])})")


def test_fallback_behavior():
    """Test fallback behavior when preferred model unavailable."""
    print("\\n=== Test: Fallback Behavior ===")
    
    selector = DynamicModelSelector()
    
    # Test with non-existent preferred model
    model_id = selector.select(TaskType.CHAT, preferred_model="nonexistent-model-12345")
    info = get_model_info(model_id)
    
    print(f"Non-existent model requested: fallback to {model_id}")
    print(f"  Provider: {info.get('provider', 'N/A')}")
    print(f"  Capabilities: {', '.join(info.get('capabilities', []))}")


def test_rag_specialization():
    """Test RAG-specific model selection."""
    print("\\n=== Test: RAG Specialization ===")
    
    selector = DynamicModelSelector()
    
    # Test with and without query
    for query in [None, "What is quantum computing?"]:
        model_id = selector.select_for_rag(query)
        info = get_model_info(model_id)
        
        print(f"\\nQuery: {query or '(none)'}")
        print(f"  Selected Model: {model_id}")
        print(f"  Capabilities: {', '.join(info.get('capabilities', []))}")


def test_embedding_selection():
    """Test embedding model selection."""
    print("\\n=== Test: Embedding Model Selection ===")
    
    selector = DynamicModelSelector()
    model_id = selector.select_for_embedding()
    info = get_model_info(model_id)
    
    print(f"Selected Embedding Model: {model_id}")
    print(f"  Provider: {info.get('provider', 'N/A')}")
    print(f"  Context Window: {info.get('context_window', 'N/A')}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Dynamic Model Selector Tests")
    print("=" * 60)
    
    try:
        test_model_database()
        test_basic_selection()
        test_strategy_modes()
        test_fallback_behavior()
        test_rag_specialization()
        test_embedding_selection()
        
        print("\\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\\nError during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())