"""
Dynamic Model Selector

Intelligently selects the best LLM based on task requirements, model capabilities,
and user preferences. Supports both local (LM Studio) and remote (LiteLLM) providers.

Strategy:
1. Task Type -> Required Capabilities
2. Available Models -> Best Match
3. Fallback Chain for Resilience
"""

import os
from enum import Enum
from typing import Optional, Dict, List
from dataclasses import dataclass


class TaskType(Enum):
    """Types of tasks that require different model capabilities."""
    CHAT = "chat"
    CODING = "coding"
    REASONING = "reasoning"
    EMBEDDING = "embedding"
    RAG = "rag"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    CONVERSATION_HISTORY = "conversation_history"


class ProviderType(Enum):
    """LLM Provider Types."""
    LM_STUDIO = "lmstudio"
    LITELLM = "litellm"
    LOCAL = "local"


@dataclass
class ModelCapabilities:
    """Model capability requirements for different tasks."""
    task_type: TaskType
    min_context_window: int
    preferred_temperature_range: tuple
    requires_coding_specialization: bool = False
    requires_reasoning_specialization: bool = False
    requires_embedding_specialization: bool = False


# Predefined model capabilities database
MODEL_CAPABILITIES_DB = {
    # Chat Models (General Purpose)
    "qwen/qwen3.6-35b-a3b": {
        "provider": ProviderType.LM_STUDIO,
        "context_window": 32768,
        "capabilities": [TaskType.CHAT, TaskType.RAG, TaskType.SUMMARIZATION],
        "strengths": ["conversational", "general-purpose", "balanced"],
    },
    "openai/qwen-2.5-32b": {
        "provider": ProviderType.LITELLM,
        "context_window": 32768,
        "capabilities": [TaskType.CHAT, TaskType.RAG, TaskType.SUMMARIZATION],
        "strengths": ["conversational", "code-aware", "multi-lingual"],
    },
    
    # Coding Models
    "qwen3-coder-next": {
        "provider": ProviderType.LITELLM,
        "context_window": 256000,
        "capabilities": [TaskType.CODING, TaskType.CHAT],
        "strengths": ["code generation", "debugging", "optimization"],
    },
    "qwen3-coder-30b-a3b-instruct": {
        "provider": ProviderType.LM_STUDIO,
        "context_window": 32768,
        "capabilities": [TaskType.CODING, TaskType.CHAT],
        "strengths": ["code generation", "local-first"],
    },
    
    # Reasoning Models
    "openai/deepseek-r1": {
        "provider": ProviderType.LITELLM,
        "context_window": 65536,
        "capabilities": [TaskType.REASONING, TaskType.CHAT],
        "strengths": ["step-by-step reasoning", "math", "logic"],
    },
    
    # Embedding Models
    "text-embedding-nomic-embed-text-v1.5": {
        "provider": ProviderType.LOCAL,
        "context_window": 8192,
        "capabilities": [TaskType.EMBEDDING],
        "strengths": ["dense embeddings", "semantic search"],
    },
    "openai/thenlper/gte-large": {
        "provider": ProviderType.LITELLM,
        "context_window": 512,
        "capabilities": [TaskType.EMBEDDING],
        "strengths": ["reranking", "semantic similarity"],
    },
    
    # Specialized Models
    "openai/mistralai/mixtral-8x7b-instruct": {
        "provider": ProviderType.LITELLM,
        "context_window": 32768,
        "capabilities": [TaskType.CHAT, TaskType.CONVERSATION_HISTORY],
        "strengths": ["chat history tracking", "multi-turn"],
    },
}


class DynamicModelSelector:
    """
    Selects the optimal LLM for a given task based on capabilities and availability.
    
    Strategy Priority:
    1. Task-specific best-in-class
    2. General-purpose fallback
    3. User preference override
    
    Usage:
        selector = DynamicModelSelector()
        model_id = selector.select(TaskType.CODING)
    """
    
    def __init__(self):
        """Initialize the dynamic model selector."""
        self.strategy = os.getenv("LLM_SELECTION_STRATEGY", "auto")
        self.fallback_chain = [
            "qwen/qwen3.6-35b-a3b",
            "openai/qwen-2.5-32b",
            "openai/mistralai/mixtral-8x7b-instruct",
        ]
        
    def _get_available_models(self) -> List[str]:
        """Get list of available models from environment or detect."""
        # TODO: Query actual providers to get real-time model availability
        # For now, return configured models
        return list(MODEL_CAPABILITIES_DB.keys())
    
    def _calculate_match_score(self, model_id: str, task_type: TaskType) -> int:
        """Calculate how well a model matches a task type."""
        if model_id not in MODEL_CAPABILITIES_DB:
            return 0
        
        capabilities = MODEL_CAPABILITIES_DB[model_id]["capabilities"]
        
        # Direct match
        if task_type in capabilities:
            return 100
        
        # Partial matches (general models can handle multiple tasks)
        general_purpose_tasks = [TaskType.CHAT, TaskType.RAG]
        if task_type in general_purpose_tasks and TaskType.CHAT in capabilities:
            return 75
        
        return 0
    
    def select(self, task_type: TaskType, preferred_model: Optional[str] = None) -> str:
        """
        Select the best model for a given task type.
        
        Args:
            task_type: The type of task to perform
            preferred_model: Optional user-specified model override
            
        Returns:
            Model ID string (e.g., "qwen/qwen3.6-35b-a3b")
        """
        # 1. Check for explicit preference
        if preferred_model and preferred_model in MODEL_CAPABILITIES_DB:
            return preferred_model
        
        # 2. Find best matching models
        available_models = self._get_available_models()
        scored_models = []
        
        for model_id in available_models:
            score = self._calculate_match_score(model_id, task_type)
            if score > 0:
                scored_models.append((model_id, score))
        
        # Sort by score (highest first)
        scored_models.sort(key=lambda x: x[1], reverse=True)
        
        if scored_models:
            return scored_models[0][0]
        
        # 3. Fallback to general-purpose model
        for fallback_model in self.fallback_chain:
            if fallback_model in available_models:
                return fallback_model
        
        # 4. Last resort - first available model
        if available_models:
            return available_models[0]
        
        # 5. Ultimate fallback
        raise ValueError(
            f"No suitable model found for task type '{task_type.value}'. "
            f"Available models: {available_models}"
        )
    
    def select_for_rag(self, query: str = None) -> str:
        """
        Select optimal model for RAG (Retrieval-Augmented Generation).
        
        RAG requires:
        - Strong retrieval understanding
        - Context synthesis
        - Answer grounding
        
        Args:
            query: Optional query text to analyze complexity
            
        Returns:
            Model ID for RAG operations
        """
        # For simple queries, use efficient model
        # For complex queries requiring reasoning, use reasoning model
        if self.strategy == "auto":
            return self.select(TaskType.RAG)
        
        return os.getenv("DEFAULT_CHAT_MODEL", "qwen/qwen3.6-35b-a3b")
    
    def select_for_embedding(self) -> str:
        """Select optimal embedding model."""
        # Prioritize local embeddings for privacy and speed
        preferred = os.getenv("DEFAULT_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
        
        if preferred in MODEL_CAPABILITIES_DB:
            return preferred
        
        # Fallback to first available embedding model
        for model_id, config in MODEL_CAPABILITIES_DB.items():
            if TaskType.EMBEDDING in config["capabilities"]:
                return model_id
        
        raise ValueError("No embedding model available")
    
    def get_model_info(self, model_id: str) -> Dict:
        """Get detailed information about a model."""
        if model_id not in MODEL_CAPABILITIES_DB:
            return {"error": f"Unknown model: {model_id}"}
        
        config = MODEL_CAPABILITIES_DB[model_id]
        return {
            "model_id": model_id,
            "provider": config["provider"].value,
            "context_window": config["context_window"],
            "capabilities": [c.value for c in config["capabilities"]],
            "strengths": config.get("strengths", []),
        }


# Global instance for easy access
_model_selector = None


def get_model_selector() -> DynamicModelSelector:
    """Get or create the global model selector instance."""
    global _model_selector
    if _model_selector is None:
        _model_selector = DynamicModelSelector()
    return _model_selector


def select_model(task_type: TaskType, **kwargs) -> str:
    """
    Convenience function to select a model for a task.
    
    Args:
        task_type: The type of task
        **kwargs: Additional arguments passed to select()
        
    Returns:
        Model ID string
    """
    return get_model_selector().select(task_type, **kwargs)


def get_model_info(model_id: str) -> Dict:
    """Get information about a model by ID."""
    return get_model_selector().get_model_info(model_id)
