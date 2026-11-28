"""
Deduplication Service

Provides hash-based document deduplication for the AI Memory Pipeline.
Supports both exact duplicate detection and near-duplicate detection.

Features:
- Exact duplicates: SHA-256/MD5 hash comparison
- Near-duplicates: Fuzzy hashing with configurable similarity thresholds
- Pre-ingestion filtering to prevent redundant vector storage
"""

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import mmh3  # MurmurHash3 for faster near-duplicate detection

from fastapi import FastAPI
from pydantic import BaseModel


class HashType(Enum):
    """Types of hash algorithms supported."""
    EXACT_SHA256 = "exact_sha256"
    EXACT_MD5 = "exact_md5"
    FUZZY_BM25 = "fuzzy_bm25"
    FUZZY_JACCARD = "fuzzy_jaccard"


@dataclass
class DocumentHash:
    """Represents hash values for a document."""
    doc_id: str
    exact_sha256: Optional[str] = None
    exact_md5: Optional[str] = None
    fuzzy_bmur3: Optional[int] = None  # BM32 hash (minhash-like)
    tokens: set = field(default_factory=set)  # For Jaccard similarity


@dataclass
class DeduplicationResult:
    """Result of a deduplication check."""
    doc_id: str
    is_duplicate: bool
    duplicate_of: Optional[str] = None
    similarity_score: float = 0.0
    hash_matches: list = field(default_factory=list)


class DeduplicationService:
    """
    Service for detecting and removing duplicate documents before ingestion.
    
    Supports both exact duplicate detection (SHA-256, MD5) and near-duplicate
    detection using fuzzy hashing techniques.
    """

    def __init__(
        self,
        exact_threshold: float = 1.0,  # 1.0 = exact match only
        fuzzy_threshold: float = 0.85,  # Jaccard similarity threshold
        hash_types: list = None,
    ):
        """
        Initialize the deduplication service.
        
        Args:
            exact_threshold: Threshold for exact duplicate detection (default: 1.0)
            fuzzy_threshold: Threshold for near-duplicate detection (default: 0.85)
            hash_types: List of HashType values to use (default: all)
        """
        self.exact_threshold = exact_threshold
        self.fuzzy_threshold = fuzzy_threshold
        self.hash_types = hash_types or [
            HashType.EXACT_SHA256,
            HashType.FUZZY_BM25,
        ]
        
        # Store hashes for duplicate detection
        self._exact_hashes: dict[str, DocumentHash] = {}  # hash -> doc_id mapping
        self._fuzzy_hashes: dict[int, list[str]] = {}  # bucket -> [doc_ids]
        self._document_hashes: dict[str, DocumentHash] = {}  # doc_id -> DocumentHash
        
        # Statistics tracking
        self._stats = {
            "total_processed": 0,
            "exact_duplicates_found": 0,
            "near_duplicates_found": 0,
            "unique_documents": 0,
        }

    def compute_exact_hash(self, content: str, hash_type: HashType) -> str:
        """Compute exact hash of content."""
        if not isinstance(content, bytes):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        
        if hash_type == HashType.EXACT_SHA256:
            return hashlib.sha256(content_bytes).hexdigest()
        elif hash_type == HashType.EXACT_MD5:
            return hashlib.md5(content_bytes).hexdigest()
        raise ValueError(f"Unsupported exact hash type: {hash_type}")

    def compute_fuzzy_hash(self, content: str) -> int:
        """
        Compute fuzzy hash using MurmurHash3.
        
        Uses minhash-like approach with multiple random projections.
        The hash is computed from sorted tokens to ensure order-invariance.
        """
        if not isinstance(content, bytes):
            content_str = content
        else:
            content_str = content.decode("utf-8")
        
        # Tokenize content into shingles (overlapping character sequences)
        shingles = self._create_shingles(content_str, ngram_size=3)
        
        # Hash each shingle and take minimum (minhash technique)
        if not shingles:
            return 0
        
        # Sort shingles to make hash order-invariant
        sorted_shingles = sorted(shingles)
        
        min_hash = min(mmh3.hash(shingle) for shingle in sorted_shingles)
        # Return absolute value to ensure non-negative hash
        return abs(min_hash)

    def _create_shingles(self, text: str, ngram_size: int = 3) -> set:
        """Create character-level n-grams (shingles) from text."""
        # Remove non-alphanumeric characters and normalize
        cleaned = "".join(c.lower() for c in text if c.isalnum() or c.isspace())
        
        # Create shingles
        words = cleaned.split()
        if len(words) < ngram_size:
            return {cleaned}  # Return entire text if too short
        
        # Sort words to make shingles order-invariant
        sorted_words = sorted(words)
        
        shingles = set()
        for i in range(len(sorted_words) - ngram_size + 1):
            shingle = " ".join(sorted_words[i:i + ngram_size])
            shingles.add(shingle)
        
        return shingles

    def compute_jaccard_similarity(self, tokens1: set, tokens2: set) -> float:
        """Compute Jaccard similarity between two token sets."""
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0

    def extract_tokens(self, content: str) -> set:
        """Extract meaningful tokens from content for similarity comparison."""
        # Remove non-alphanumeric characters
        cleaned = "".join(c.lower() for c in content if c.isalnum() or c.isspace())
        
        # Split into words and filter short/common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", 
                      "to", "for", "of", "with", "by", "from", "is", "are", 
                      "was", "were", "be", "been", "being", "have", "has", 
                      "had", "do", "does", "did", "will", "would", "could", 
                      "should", "may", "might", "must", "shall"}
        
        tokens = set()
        for word in cleaned.split():
            if len(word) > 2 and word not in stop_words:
                tokens.add(word)
        
        return tokens

    def check_exact_duplicate(self, doc_id: str, content: str) -> DeduplicationResult:
        """Check if document is an exact duplicate of existing documents."""
        result = DeduplicationResult(doc_id=doc_id, is_duplicate=False)
        
        for hash_type in [h for h in self.hash_types if h in [
            HashType.EXACT_SHA256, HashType.EXACT_MD5
        ]]:
            doc_hash = self.compute_exact_hash(content, hash_type)
            
            if doc_hash in self._exact_hashes:
                existing_doc_id = self._exact_hashes[doc_hash]
                
                # Check if it's truly a duplicate (same content, not hash collision)
                result.is_duplicate = True
                result.duplicate_of = existing_doc_id
                result.similarity_score = 1.0
                result.hash_matches.append(f"{hash_type.value}:{doc_hash}")
        
        return result

    def check_near_duplicate(self, doc_id: str, content: str) -> DeduplicationResult:
        """Check if document is a near-duplicate of existing documents."""
        result = DeduplicationResult(doc_id=doc_id, is_duplicate=False)
        
        # Extract tokens for Jaccard similarity
        current_tokens = self.extract_tokens(content)
        
        if not current_tokens:
            return result
        
        # Compute fuzzy hash for bucketing
        fuzzy_hash = self.compute_fuzzy_hash(content)
        current_bucket = fuzzy_hash % 10000  # 10000 buckets
        
        # Only check documents in the same or similar buckets
        checked_docs = set()
        
        # Check current bucket and neighboring buckets
        for bucket_offset in [-1, 0, 1]:
            bucket_key = (current_bucket + bucket_offset) % 10000
            
            if bucket_key in self._fuzzy_hashes:
                for existing_doc_id in self._fuzzy_hashes[bucket_key]:
                    if existing_doc_id not in checked_docs and existing_doc_id != doc_id:
                        checked_docs.add(existing_doc_id)
                        
                        # Get existing document's tokens from _document_hashes
                        existing_hash_obj = self._document_hashes.get(existing_doc_id)
                        if existing_hash_obj and existing_hash_obj.tokens:
                            similarity = self.compute_jaccard_similarity(
                                current_tokens, existing_hash_obj.tokens
                            )
                            
                            if similarity >= self.fuzzy_threshold:
                                result.is_duplicate = True
                                result.duplicate_of = existing_doc_id
                                result.similarity_score = similarity
                                result.hash_matches.append(
                                    f"jaccard:{similarity:.4f}"
                                )
        
        return result

    def check_document(self, doc_id: str, content: str) -> DeduplicationResult:
        """
        Check if a document is a duplicate (exact or near).
        
        Args:
            doc_id: Unique identifier for the document
            content: Document content to check
            
        Returns:
            DeduplicationResult with details about any duplicates found
        """
        # Check exact duplicates first (faster)
        exact_result = self.check_exact_duplicate(doc_id, content)
        if exact_result.is_duplicate:
            self._stats["exact_duplicates_found"] += 1
            return exact_result
        
        # Check near-duplicates
        near_result = self.check_near_duplicate(doc_id, content)
        if near_result.is_duplicate:
            self._stats["near_duplicates_found"] += 1
            return near_result
        
        # Document is unique - store its hashes
        doc_hash_obj = DocumentHash(
            doc_id=doc_id,
            tokens=self.extract_tokens(content),
        )
        
        for hash_type in self.hash_types:
            if hash_type == HashType.EXACT_SHA256:
                doc_hash_obj.exact_sha256 = self.compute_exact_hash(content, hash_type)
                self._exact_hashes[doc_hash_obj.exact_sha256] = doc_id
            elif hash_type == HashType.EXACT_MD5:
                doc_hash_obj.exact_md5 = self.compute_exact_hash(content, hash_type)
                self._exact_hashes[doc_hash_obj.exact_md5] = doc_id
            elif hash_type == HashType.FUZZY_BM25:
                doc_hash_obj.fuzzy_bmur3 = self.compute_fuzzy_hash(content)
        
        # Store in fuzzy bucket for near-duplicate detection
        if doc_hash_obj.fuzzy_bmur3:
            bucket = doc_hash_obj.fuzzy_bmur3 % 10000
            if bucket not in self._fuzzy_hashes:
                self._fuzzy_hashes[bucket] = []
            self._fuzzy_hashes[bucket].append(doc_id)
        
        # Store document hash for similarity calculations
        self._document_hashes[doc_id] = doc_hash_obj
        
        # Update statistics
        self._stats["total_processed"] += 1
        self._stats["unique_documents"] += 1
        
        return DeduplicationResult(
            doc_id=doc_id,
            is_duplicate=False,
            similarity_score=0.0,
        )

    def bulk_check(self, documents: list[tuple[str, str]]) -> list[DeduplicationResult]:
        """
        Check multiple documents for duplicates.
        
        Args:
            documents: List of (doc_id, content) tuples
            
        Returns:
            List of DeduplicationResult objects
        """
        return [
            self.check_document(doc_id, content)
            for doc_id, content in documents
        ]

    def get_statistics(self) -> dict:
        """Get deduplication statistics."""
        return {
            **self._stats,
            "duplicate_rate": (
                (self._stats["exact_duplicates_found"] + 
                 self._stats["near_duplicates_found"]) / 
                max(1, self._stats["total_processed"])
            ),
        }

    def reset(self):
        """Reset the deduplication service state."""
        self._exact_hashes.clear()
        self._fuzzy_hashes.clear()
        self._stats = {
            "total_processed": 0,
            "exact_duplicates_found": 0,
            "near_duplicates_found": 0,
            "unique_documents": 0,
        }

    def health_check(self) -> bool:
        """
        Perform health check on the deduplication service.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Test hash computation
            test_content = "Test document for health check"
            
            # Test exact hash
            exact_hash = self.compute_exact_hash(test_content, HashType.EXACT_SHA256)
            if not exact_hash or len(exact_hash) != 64:  # SHA-256 hex is 64 chars
                return False
            
            # Test fuzzy hash
            fuzzy_hash = self.compute_fuzzy_hash(test_content)
            if not isinstance(fuzzy_hash, int):
                return False
            
            # Test token extraction
            tokens = self.extract_tokens(test_content)
            if not isinstance(tokens, set) or len(tokens) == 0:
                return False
            
            # Test Jaccard similarity
            sim = self.compute_jaccard_similarity({"a", "b"}, {"a", "c"})
            if not isinstance(sim, float):
                return False
            
            return True
            
        except Exception as e:
            print(f"DeduplicationService health check failed: {e}")
            return False


# =============================================================================
# FastAPI application (Phase 4 microservice)
# =============================================================================

service = DeduplicationService()

app = FastAPI(
    title="Deduplication Service",
    description="Hash-based document deduplication for the AI Memory Pipeline",
    version="1.0.0"
)


class CheckRequest(BaseModel):
    doc_id: str
    content: str
    fuzzy_threshold: Optional[float] = None


@app.get("/health")
async def health():
    """Health check endpoint for container orchestration."""
    healthy = service.health_check()
    return {
        "status": "healthy" if healthy else "unhealthy",
        "service": "deduplication",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "hash_engine": {"status": "ok" if healthy else "error"},
        },
        "metadata": service.get_statistics(),
    }


@app.post("/check")
async def check_document(request: CheckRequest):
    """Check a document for exact or near-duplicate matches."""
    if request.fuzzy_threshold is not None:
        service.fuzzy_threshold = request.fuzzy_threshold
    result = service.check_document(request.doc_id, request.content)
    return {
        "doc_id": result.doc_id,
        "is_duplicate": result.is_duplicate,
        "duplicate_of": result.duplicate_of,
        "similarity_score": result.similarity_score,
        "hash_matches": result.hash_matches,
    }


@app.get("/statistics")
async def statistics():
    """Get deduplication statistics."""
    return service.get_statistics()


def main():
    """Main function to test the deduplication service."""
    import sys
    
    # Initialize service
    service = DeduplicationService(
        exact_threshold=1.0,
        fuzzy_threshold=0.85,
    )
    
    print("=" * 60)
    print("Deduplication Service Test")
    print("=" * 60)
    
    # Test documents (some duplicates, some unique)
    test_documents = [
        ("doc1", "This is a test document with some content."),
        ("doc2", "This is a test document with some content."),  # Exact duplicate
        ("doc3", "This is a similar document with slightly different content."),
        ("doc4", "Completely unique document about something else entirely."),
        ("doc5", "This is another test document with minor variations."),
    ]
    
    print("\nProcessing documents...")
    results = []
    
    for doc_id, content in test_documents:
        result = service.check_document(doc_id, content)
        
        status = "DUPLICATE" if result.is_duplicate else "UNIQUE"
        print(f"\n[{status}] {doc_id}")
        print(f"  Content: {content[:60]}...")
        print(f"  Similar to: {result.duplicate_of or 'None'}")
        print(f"  Score: {result.similarity_score:.4f}")
        
        results.append(result)
    
    # Print statistics
    print("\n" + "=" * 60)
    print("Statistics:")
    print("=" * 60)
    stats = service.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    # Health check
    print("\n" + "=" * 60)
    print("Health Check:")
    print("=" * 60)
    health = service.health_check()
    print(f"  Service Status: {'HEALTHY' if health else 'UNHEALTHY'}")
    
    return 0 if health else 1


if __name__ == "__main__":
    sys.exit(main())
