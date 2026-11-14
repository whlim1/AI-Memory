"""
Phase 5 Services Package for AI Memory Pipeline.

This package provides production-ready monitoring and optimization services:
- Embedding Quality Monitor: Real-time tracking of embedding quality and drift detection
- Model Caching Strategy: GPU memory optimization with automatic model swapping
- Dynamic Chunking: Content-type-aware chunking service
"""

from .embedding_quality_monitor import EmbeddingQualityMonitor
from .model_caching_strategy import ModelCacheManager
from .dynamic_chunking_service import DynamicChunkingService

__version__ = "1.0.0"
__all__ = [
    'EmbeddingQualityMonitor',
    'ModelCacheManager', 
    'DynamicChunkingService'
]
