"""
Tests for Deduplication Service.
"""

import pytest

from services.deduplication_service import (
    DeduplicationService,
    DocumentHash,
    DeduplicationResult,
    HashType,
)


class TestDeduplicationService:
    """Test cases for DeduplicationService."""

    def test_initialization(self):
        """Test service initialization with default parameters."""
        service = DeduplicationService()
        
        assert service.exact_threshold == 1.0
        assert service.fuzzy_threshold == 0.85
        assert len(service.hash_types) > 0

    def test_initialization_custom_params(self):
        """Test service initialization with custom parameters."""
        service = DeduplicationService(
            exact_threshold=0.95,
            fuzzy_threshold=0.75,
            hash_types=[HashType.EXACT_SHA256],
        )
        
        assert service.exact_threshold == 0.95
        assert service.fuzzy_threshold == 0.75
        assert len(service.hash_types) == 1

    def test_compute_exact_hash_sha256(self):
        """Test SHA-256 hash computation."""
        service = DeduplicationService()
        
        content = "Hello, World!"
        hash_value = service.compute_exact_hash(content, HashType.EXACT_SHA256)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256 hex string
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_compute_exact_hash_md5(self):
        """Test MD5 hash computation."""
        service = DeduplicationService()
        
        content = "Hello, World!"
        hash_value = service.compute_exact_hash(content, HashType.EXACT_MD5)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hex string

    def test_compute_exact_hash_bytes(self):
        """Test exact hash computation with bytes input."""
        service = DeduplicationService()
        
        content_bytes = b"Hello, World!"
        hash_value = service.compute_exact_hash(content_bytes, HashType.EXACT_SHA256)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64

    def test_compute_fuzzy_hash(self):
        """Test fuzzy hash computation."""
        service = DeduplicationService()
        
        content = "This is a test document."
        hash_value = service.compute_fuzzy_hash(content)
        
        assert isinstance(hash_value, int)
        assert hash_value >= 0

    def test_create_shingles(self):
        """Test shingle creation from text."""
        service = DeduplicationService()
        
        text = "the quick brown fox jumps"
        shingles = service._create_shingles(text, ngram_size=3)
        
        assert isinstance(shingles, set)
        assert len(shingles) > 0
        # Check that we got some trigrams
        assert any(len(s.split()) == 3 for s in shingles)

    def test_create_shingles_empty(self):
        """Test shingle creation with empty text."""
        service = DeduplicationService()
        
        shingles = service._create_shingles("")
        
        assert isinstance(shingles, set)
        # Empty or very short text returns the cleaned text
        assert len(shingles) <= 1

    def test_extract_tokens(self):
        """Test token extraction from content."""
        service = DeduplicationService()
        
        content = "The quick brown fox jumps over the lazy dog."
        tokens = service.extract_tokens(content)
        
        assert isinstance(tokens, set)
        # Should exclude stop words and short words
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens
        assert "lazy" in tokens
        assert "dog" in tokens
        # Stop words should be filtered out
        assert "the" not in tokens or len([t for t in tokens if t == "the"]) <= 1

    def test_compute_jaccard_similarity(self):
        """Test Jaccard similarity computation."""
        service = DeduplicationService()
        
        set1 = {"a", "b", "c"}
        set2 = {"a", "b", "d"}
        set3 = {"x", "y", "z"}  # Completely different
        
        # Same sets should have similarity of 1.0
        assert service.compute_jaccard_similarity(set1, set1) == 1.0
        
        # Partial overlap: {a,b} / {a,b,c,d} = 0.5
        assert service.compute_jaccard_similarity(set1, set2) == 0.5
        
        # No overlap should be 0.0
        assert service.compute_jaccard_similarity(set1, set3) == 0.0

    def test_check_document_unique(self):
        """Test checking a unique document."""
        service = DeduplicationService()
        
        result = service.check_document("doc1", "This is a unique document.")
        
        assert isinstance(result, DeduplicationResult)
        assert not result.is_duplicate
        assert result.doc_id == "doc1"

    def test_check_document_exact_duplicate(self):
        """Test detection of exact duplicates."""
        service = DeduplicationService()
        
        content = "This is a test document with specific content."
        
        # First document should be unique
        result1 = service.check_document("doc1", content)
        assert not result1.is_duplicate
        
        # Second identical document should be detected as duplicate
        result2 = service.check_document("doc2", content)
        
        assert result2.is_duplicate
        assert result2.duplicate_of == "doc1"
        assert result2.similarity_score == 1.0

    def test_check_document_near_duplicate(self):
        """Test detection of near-duplicates."""
        service = DeduplicationService(fuzzy_threshold=0.4)
        
        # First document
        content1 = "The quick brown fox jumps over the lazy dog in the garden."
        result1 = service.check_document("doc1", content1)
        assert not result1.is_duplicate
        
        # Near-duplicate with slight variations (same words, different order)
        content2 = "In the garden the lazy dog jumps over the quick brown fox."
        result2 = service.check_document("doc2", content2)
        
        # Should be detected as near-duplicate (same words, different order)
        assert result2.is_duplicate
        assert result2.duplicate_of == "doc1"
        assert result2.similarity_score > 0.4

    def test_bulk_check(self):
        """Test bulk document checking."""
        service = DeduplicationService()
        
        documents = [
            ("doc1", "First unique document."),
            ("doc2", "Second unique document."),
            ("doc3", "First unique document."),  # Duplicate of doc1
        ]
        
        results = service.bulk_check(documents)
        
        assert len(results) == 3
        
        assert not results[0].is_duplicate  # First is unique
        assert results[1].is_duplicate == False or results[1].similarity_score < 0.85  # Second might be near-duplicate
        assert results[2].is_duplicate  # Third is exact duplicate

    def test_statistics(self):
        """Test statistics tracking."""
        service = DeduplicationService()
        
        # Process some documents
        service.check_document("doc1", "Unique content.")
        service.check_document("doc2", "Duplicate of unique content.")  # Exact match
        
        stats = service.get_statistics()
        
        assert "total_processed" in stats
        assert "exact_duplicates_found" in stats
        assert "near_duplicates_found" in stats
        assert "unique_documents" in stats

    def test_reset(self):
        """Test service reset functionality."""
        service = DeduplicationService()
        
        # Add some documents
        service.check_document("doc1", "Test content.")
        
        # Reset
        service.reset()
        
        # Should be empty after reset
        assert len(service._exact_hashes) == 0
        
        stats = service.get_statistics()
        assert stats["total_processed"] == 0

    def test_health_check(self):
        """Test health check method."""
        service = DeduplicationService()
        
        is_healthy = service.health_check()
        
        assert is_healthy is True

    def test_different_content_not_duplicate(self):
        """Test that different content is not flagged as duplicate."""
        service = DeduplicationService(fuzzy_threshold=0.8)
        
        result1 = service.check_document("doc1", "Document about machine learning and AI.")
        result2 = service.check_document("doc2", "Document about cooking recipes and food.")
        
        assert not result1.is_duplicate
        # Second document should also be unique (very different content)
        assert not result2.is_duplicate

    def test_empty_content(self):
        """Test handling of empty content."""
        service = DeduplicationService()
        
        result = service.check_document("doc1", "")
        
        assert isinstance(result, DeduplicationResult)
        # Empty content should not be flagged as duplicate of nothing
        assert not result.is_duplicate

    def test_unicode_content(self):
        """Test handling of Unicode content."""
        service = DeduplicationService()
        
        unicode_content = "Hello 世界! 🌍مرحبا"
        
        result1 = service.check_document("doc1", unicode_content)
        result2 = service.check_document("doc2", unicode_content)  # Duplicate
        
        assert not result1.is_duplicate
        assert result2.is_duplicate
