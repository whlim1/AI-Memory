"""
AI Memory Pipeline - A Python package for processing and indexing documents with Qdrant vector storage.

This package provides functionality for text chunking, redaction, semantic summarization,
metadata handling, dynamic LLM selection, and integration with Qdrant vector database.
"""

__version__ = "0.2.0"
__author__ = "AI Memory Team"

# Import core modules to make them available at package level
from .chunking import split_text_by_sentences, split_text_by_words, chunk_text
from .redaction import Redactor, redact_pii
from .semantic_summary import SemanticSummarizer, summarize_text
from .metadata import DocumentMetadata, extract_metadata_from_text, merge_metadata
from .qdrant_client import QdrantManager
from .dynamic_model_selector import (
    DynamicModelSelector,
    TaskType,
    ProviderType,
    get_model_selector,
    select_model,
    get_model_info
)

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
    'get_model_info'
]