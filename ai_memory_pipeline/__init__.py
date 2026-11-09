"""
AI Memory Pipeline - A Python package for processing and indexing documents with Qdrant vector storage.

This package provides functionality for text chunking, redaction, semantic summarization,
metadata handling, and integration with Qdrant vector database.
"""

__version__ = "0.1.0"
__author__ = "AI Memory Team"

# Import core modules to make them available at package level
from .chunking import split_text_by_sentences, split_text_by_words, chunk_text
from .redaction import Redactor, redact_sensitive_data
from .semantic_summary import generate_semantic_summary
from .metadata import extract_metadata, validate_metadata
from .qdrant_client import QdrantManager

__all__ = [
    'split_text_by_sentences',
    'split_text_by_words', 
    'chunk_text',
    'Redactor',
    'redact_sensitive_data',
    'generate_semantic_summary',
    'extract_metadata',
    'validate_metadata',
    'QdrantManager'
]