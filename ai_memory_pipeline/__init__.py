"""
AI Memory Pipeline - A Python package for processing and indexing documents with Qdrant vector storage.

This package provides functionality for text chunking, redaction, semantic summarization,
metadata handling, dynamic LLM selection, and integration with Qdrant vector database.

Phase 5 Services:
- Embedding Quality Monitor: Real-time tracking of embedding quality and drift detection
- Model Caching Strategy: GPU memory optimization with automatic model swapping
- Dynamic Chunking: Content-type-aware chunking service
"""

__version__ = "0.3.0"
__author__ = "AI Memory Team"

# Import core modules to make them available at package level
from .chunking import split_text_by_sentences, split_text_by_words, chunk_text
from .redaction import Redactor, redact_pii
from .semantic_summary import SemanticSummarizer, summarize_text
from .metadata import DocumentMetadata, extract_metadata_from_text, merge_metadata
from .qdrant_client_wrapper import QdrantManager
from .dynamic_model_selector import (
    DynamicModelSelector,
    TaskType,
    ProviderType,
    get_model_selector,
    select_model,
    get_model_info
)
from .lm_studio_model_switcher import LMStudioModelSwitcher
from .lm_studio_smart_embedder import LMSmartEmbedder

# Import Phase 5 services (from parent-level services directory)
try:
    from services import (
        EmbeddingQualityMonitor,
        ModelCacheManager,
        DynamicChunkingService
    )
except ImportError:
    # If that fails, try relative import for different deployment scenarios
    try:
        from ..services import (
            EmbeddingQualityMonitor,
            ModelCacheManager,
            DynamicChunkingService
        )
    except ImportError:
        pass  # Services may not be available in all deployments

__all__ = [
    'split_text_by_sentences',
    'split_text_by_words',
    'chunk_text',
    'Redactor',
    'redact_pii',
    'SemanticSummarizer',
    'summarize_text',
    'DocumentMetadata',
    'extract_metadata_from_text',
    'merge_metadata',
    'QdrantManager',
    'DynamicModelSelector',
    'TaskType',
    'ProviderType',
    'get_model_selector',
    'select_model',
    'get_model_info',
    'LMStudioModelSwitcher',
    'LMSmartEmbedder'
]

# Add Phase 5 services to __all__ if available
try:
    from ..services import (
        EmbeddingQualityMonitor,
        ModelCacheManager,
        DynamicChunkingService
    )
    __all__.extend([
        'EmbeddingQualityMonitor',
        'ModelCacheManager',
        'DynamicChunkingService'
    ])
except ImportError:
    pass  # Services not available in this deployment