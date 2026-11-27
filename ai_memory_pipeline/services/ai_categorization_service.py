"""
Performance optimization for AI categorization service.

Phase 6.4: Reduces inference latency by:
1. Adding response caching to avoid redundant LLM calls
2. Implementing a two-tier cache (in-memory + file-based)
3. Adding configurable timeout and retry logic
4. Providing a --benchmark mode for performance measurement
"""

import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------------------------

# Default cache TTL in seconds (1 hour)
CACHE_TTL = int(os.environ.get("AI_CATEGORIZATION_CACHE_TTL", 3600))

# Cache directory (relative to project root)
_CACHE_DIR = Path(__file__).parent.parent.parent / ".cache" / "categorization"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CategorizationResult:
    """Result of AI-powered note categorization."""
    category: str
    confidence: float
    subcategories: List[str] = field(default_factory=list)
    reasoning: str = ""

@dataclass
class EntityExtractionResult:
    """Result of AI-powered entity extraction."""
    people: List[str] = field(default_factory=list)
    places: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    concepts: List[str] = field(default_factory=list)

@dataclass
class TagExtractionResult:
    """Result of AI-powered tag extraction."""
    tags: List[str] = field(default_factory=list)
    reasoning: str = ""

@dataclass
class EnrichedNoteAnalysis:
    """Complete analysis result combining categorization, entities, and tags."""
    category: str
    confidence: float
    subcategories: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=lambda: {
        "people": [], "places": [], "organizations": [], "concepts": []
    })
    tags: List[str] = field(default_factory=list)
    reasoning: str = ""
    processing_time_ms: float = 0.0
    cache_hit: bool = False

# ---------------------------------------------------------------------------
# Cache layer
# ---------------------------------------------------------------------------

class CategorizationCache:
    """Two-tier cache for categorization results.
    
    Tier 1: In-memory dict (fast, process-scoped)
    Tier 2: File-based JSON cache (persists across restarts)
    """
    
    def __init__(self, ttl: int = CACHE_TTL):
        self._memory: Dict[str, Tuple[float, Any]] = {}
        self._file_cache = _CACHE_DIR
        self._ttl = ttl
        self._load_file_cache()
    
    def _load_file_cache(self):
        """Load file-based cache into memory."""
        if self._file_cache.exists():
            try:
                data = json.loads(self._file_cache.read_text())
                now = time.time()
                for key, (timestamp, value) in data.items():
                    if now - timestamp < self._ttl:
                        self._memory[key] = (timestamp, value)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load cache file: %s", e)
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cached result by key."""
        now = time.time()
        entry = self._memory.get(key)
        if entry is None:
            return None
        timestamp, value = entry
        if now - timestamp > self._ttl:
            del self._memory[key]
            return None
        return value
    
    def set(self, key: str, value: Any):
        """Cache a result."""
        self._memory[key] = (time.time(), value)
        self._save_file_cache()
    
    def invalidate(self):
        """Clear all cache entries."""
        self._memory.clear()
        self._file_cache.unlink(missing_ok=True)
    
    def _save_file_cache(self):
        """Persist in-memory cache to file."""
        now = time.time()
        data = {
            key: (ts, val)
            for key, (ts, val) in self._memory.items()
            if now - ts < self._ttl
        }
        try:
            self._file_cache.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except OSError as e:
            logger.warning("Failed to save cache file: %s", e)


# ---------------------------------------------------------------------------
# Content processor helper (for hashing)
# ---------------------------------------------------------------------------

def _normalize_content(body: str) -> str:
    """Normalize note content for cache key generation."""
    import re
    # Remove markdown headers, extra whitespace, and empty lines
    text = re.sub(r'^#{1,6}\s+', '', body, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()


def _make_cache_key(body: str, tags: List[str]) -> str:
    """Generate a cache key from note content and tags."""
    normalized = _normalize_content(body)
    tag_key = "|".join(sorted(tags)) if tags else ""
    raw = f"{normalized}||{tag_key}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Cache instance (module-level singleton)
# ---------------------------------------------------------------------------

_cache = CategorizationCache()


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def analyze_note(
    body: str,
    tags: List[str] = None,
    title: str = "",
    force_refresh: bool = False,
) -> EnrichedNoteAnalysis:
    """Analyze a note body with AI-powered categorization, entity extraction,
    and tag generation.
    
    Args:
        body: The note content.
        tags: Existing tags on the note (used for heuristic fallback).
        title: Note title (used for heuristic fallback).
        force_refresh: If True, bypass cache and force fresh inference.
    
    Returns:
        EnrichedNoteAnalysis with category, entities, tags, and metadata.
    """
    tags = tags or []
    start_time = time.time()
    
    # Check cache
    if not force_refresh:
        cache_key = _make_cache_key(body, tags)
        cached = _cache.get(cache_key)
        if cached is not None:
            result = EnrichedNoteAnalysis(**cached)
            result.cache_hit = True
            result.processing_time_ms = (time.time() - start_time) * 1000
            logger.debug("Cache hit for note (title: %s)", title[:30] if title else "(no title)")
            return result
    
    # Step 1: Categorize
    categorization = _categorize(body, tags, title)
    
    # Step 2: Extract entities
    entities = _extract_entities(body)
    
    # Step 3: Generate tags
    tag_result = _generate_tags(body, tags, categorization.category)
    
    # Combine
    result = EnrichedNoteAnalysis(
        category=categorization.category,
        confidence=categorization.confidence,
        subcategories=categorization.subcategories,
        entities={
            "people": entities.people,
            "places": entities.places,
            "organizations": entities.organizations,
            "concepts": entities.concepts,
        },
        tags=tag_result.tags,
        reasoning=categorization.reasoning,
    )
    
    result.processing_time_ms = (time.time() - start_time) * 1000
    result.cache_hit = False
    
    # Cache the result (serialize for storage)
    try:
        _cache.set(_make_cache_key(body, tags), asdict(result))
    except Exception as e:
        logger.warning("Failed to cache result: %s", e)
    
    logger.info(
        "Analysis complete: category=%s, confidence=%.2f, time=%.0fms",
        result.category, result.confidence, result.processing_time_ms,
    )
    
    return result


def _categorize(body: str, tags: List[str], title: str = "") -> CategorizationResult:
    """Step 1: Classify note into a category."""
    # Heuristic fallback (fast path)
    heuristic_cat, heuristic_conf = _heuristic_categorize(body, tags, title)
    
    # Try AI categorization
    ai_cat = _call_lm_studio_categorize(body)
    if ai_cat and ai_cat.confidence > heuristic_conf:
        return ai_cat
    
    logger.debug("Using heuristic category: %s (conf=%.2f)", heuristic_cat, heuristic_conf)
    return CategorizationResult(
        category=heuristic_cat,
        confidence=heuristic_conf,
        reasoning=f"Heuristic fallback: category={heuristic_cat}",
    )


def _heuristic_categorize(
    body: str, tags: List[str], title: str = ""
) -> Tuple[str, float]:
    """Fast heuristic categorization as fallback."""
    text = (body + " " + title).lower()
    
    # Check tags first (highest priority)
    tag_categories = {
        "tech": ("technology", 0.90),
        "technology": ("technology", 0.90),
        "ai": ("technology", 0.85),
        "personal": ("personal", 0.95),
        "work": ("work", 0.90),
        "life": ("personal", 0.85),
        "idea": ("ideas", 0.80),
        "meeting": ("work", 0.85),
    }
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower in tag_categories:
            return tag_categories[tag_lower]
    
    # Check body content
    tech_keywords = [
        "api", "code", "python", "docker", "database", "server",
        "algorithm", "model", "training", "inference", "embedding",
        "vector", "neural", "machine learning", "deep learning",
        "software", "programming", "development", "deployment",
    ]
    personal_keywords = [
        "family", "friend", "health", "exercise", "food", "travel",
        "home", "shopping", "birthday", "anniversary", "gift",
    ]
    work_keywords = [
        "meeting", "project", "deadline", "report", "email",
        "presentation", "client", "customer", "budget", "schedule",
    ]
    idea_keywords = [
        "idea", "concept", "thought", "brainstorm", "suggestion",
        "proposal", "plan", "dream", "vision",
    ]
    
    tech_score = sum(1 for kw in tech_keywords if kw in text)
    personal_score = sum(1 for kw in personal_keywords if kw in text)
    work_score = sum(1 for kw in work_keywords if kw in text)
    idea_score = sum(1 for kw in idea_keywords if kw in text)
    
    scores = {
        "technology": tech_score,
        "personal": personal_score,
        "work": work_score,
        "ideas": idea_score,
    }
    
    best_cat = max(scores, key=scores.get)
    best_score = scores[best_cat]
    
    # Normalize confidence
    total = sum(scores.values())
    confidence = min(best_score / max(total, 1), 1.0)
    confidence = max(confidence, 0.5)  # Minimum confidence for heuristic
    
    return best_cat, confidence


def _extract_entities(body: str) -> EntityExtractionResult:
    """Step 2: Extract named entities from the note."""
    # Heuristic fallback (fast path)
    entities = EntityExtractionResult()
    
    # Try AI extraction
    ai_entities = _call_lm_studio_entities(body)
    if ai_entities:
        return ai_entities
    
    logger.debug("Using heuristic entity extraction")
    return entities


def _generate_tags(
    body: str, existing_tags: List[str], category: str
) -> TagExtractionResult:
    """Step 3: Generate additional tags for the note."""
    # Heuristic fallback (fast path)
    tags = list(existing_tags)
    
    # Try AI tag generation
    ai_tags = _call_lm_studio_tags(body, category)
    if ai_tags:
        tags.extend(ai_tags)
    
    # Deduplicate
    tags = list(dict.fromkeys(tags))
    
    return TagExtractionResult(tags=tags, reasoning="Heuristic fallback")


# ---------------------------------------------------------------------------
# LM Studio integration
# ---------------------------------------------------------------------------

def _get_lm_studio_url() -> str:
    """Get the LM Studio base URL from environment or default."""
    return os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")


def _get_lm_studio_api_url() -> str:
    """Get the LM Studio API URL (non-v1 path for /api/tags)."""
    base = os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    # Remove /v1 suffix to get base API URL
    if base.endswith("/v1"):
        return base[:-3]
    return base


def _call_lm_studio_categorize(body: str) -> Optional[CategorizationResult]:
    """Call LM Studio for categorization. Returns None on failure."""
    prompt = (
        "Classify the following note into one category: technology, personal, work, or ideas. "
        "Return ONLY a JSON object with keys: category, confidence (0-1), subcategories (array), reasoning.\n\n"
        f"Note:\n{body[:2000]}\n\nJSON:"
    )
    
    result = _call_lm_studio(prompt, "categorization")
    if result is None:
        return None
    
    category = result.get("category", "uncategorized")
    confidence = min(max(result.get("confidence", 0.5), 0.0), 1.0)
    
    return CategorizationResult(
        category=category,
        confidence=confidence,
        subcategories=result.get("subcategories", []),
        reasoning=result.get("reasoning", ""),
    )


def _call_lm_studio_entities(body: str) -> Optional[EntityExtractionResult]:
    """Call LM Studio for entity extraction. Returns None on failure."""
    prompt = (
        "Extract named entities from the following note. "
        "Return ONLY a JSON object with keys: people, places, organizations, concepts (all arrays of strings).\n\n"
        f"Note:\n{body[:2000]}\n\nJSON:"
    )
    
    result = _call_lm_studio(prompt, "entities")
    if result is None:
        return None
    
    return EntityExtractionResult(
        people=result.get("people", []),
        places=result.get("places", []),
        organizations=result.get("organizations", []),
        concepts=result.get("concepts", []),
    )


def _call_lm_studio_tags(body: str, category: str) -> Optional[List[str]]:
    """Call LM Studio for tag generation. Returns None on failure."""
    prompt = (
        f"Generate up to 5 relevant tags for this {category} note. "
        "Return ONLY a JSON array of strings.\n\n"
        f"Note:\n{body[:2000]}\n\nJSON:"
    )
    
    result = _call_lm_studio(prompt, "tags")
    if result is None:
        return None
    
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("tags", [])
    
    return None


def _call_lm_studio(prompt: str, task: str) -> Optional[Any]:
    """Make a single call to LM Studio with timeout and retry.
    
    Uses a connection timeout of 5 seconds and a read timeout of 300 seconds
    (5 minutes) to handle slow local inference.
    """
    url = f"{_get_lm_studio_url()}/chat/completions"
    
    payload = {
        "model": os.environ.get("AI_CATEGORIZATION_MODEL", "local-model"),
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that analyzes notes. Return ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
    }
    
    headers = {"Content-Type": "application/json"}
    
    # Retry logic (2 attempts)
    for attempt in range(2):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=(5, 300),  # (connect, read)
            )
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                # Parse JSON from the response
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("LM Studio returned invalid JSON for %s task", task)
                    return None
            else:
                logger.warning("LM Studio returned status %d for %s task", response.status_code, task)
        except requests.exceptions.Timeout:
            logger.warning("LM Studio timeout for %s task (attempt %d/2)", task, attempt + 1)
        except requests.exceptions.ConnectionError:
            logger.warning("LM Studio connection error for %s task (attempt %d/2)", task, attempt + 1)
        except Exception as e:
            logger.warning("Unexpected error calling LM Studio for %s: %s", task, e)
        
        if attempt < 1:
            time.sleep(1)  # Brief pause before retry
    
    return None


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def clear_cache():
    """Clear all categorization cache entries."""
    _cache.invalidate()
    logger.info("Categorization cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return {
        "memory_entries": len(_cache._memory),
        "ttl_seconds": _cache._ttl,
        "cache_dir": str(_cache._file_cache),
    }


# ---------------------------------------------------------------------------
# Benchmark mode
# ---------------------------------------------------------------------------

def _benchmark():
    """Run performance benchmark and print results."""
    test_notes = [
        {
            "title": "Tech Note",
            "body": "# RAG Pipeline Architecture\n\nThis note describes the Retrieval-Augmented Generation pipeline.\n\n## Key Components\n\n- **Embedding Model**: text-embedding-nomic-embed-text-v1.5\n- **Vector Store**: Qdrant\n- **LLM Backend**: LM Studio (qwen/qwen3.6-35b-a3b)\n\n## Workflow\n\n1. User submits a question\n2. System retrieves relevant documents from Qdrant\n3. LLM generates a response using retrieved context",
            "tags": ["rag", "architecture", "ai"],
        },
        {
            "title": "Personal Note",
            "body": "# Weekly Review\n\n## Accomplishments\n\n- Completed Phase 6.1 (Obsidian Sync Engine)\n- Finished Phase 6.3 (AI Categorization Service)\n\n## Next Steps\n\n- Performance optimization\n- Write integration tests",
            "tags": ["personal", "review"],
        },
        {
            "title": "Empty Note",
            "body": "Just some random notes.",
            "tags": [],
        },
    ]
    
    print("=" * 60)
    print("AI Categorization Service - Performance Benchmark")
    print("=" * 60)
    
    # Clear cache for fresh benchmark
    clear_cache()
    
    results = []
    for note in test_notes:
        start = time.time()
        result = analyze_note(
            body=note["body"],
            tags=note["tags"],
            title=note["title"],
        )
        elapsed = time.time() - start
        
        results.append({
            "title": note["title"],
            "category": result.category,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms,
            "total_time_s": elapsed,
            "cache_hit": result.cache_hit,
            "entities_count": sum(len(v) for v in result.entities.values()),
            "tags_count": len(result.tags),
        })
        
        status = "cache hit" if result.cache_hit else "AI call"
        print(f"\n  {note['title']}:")
        print(f"    Category: {result.category} (confidence: {result.confidence:.2f})")
        print(f"    Processing time: {result.processing_time_ms:.0f}ms")
        print(f"    Total time: {elapsed:.1f}s ({status})")
        print(f"    Entities: {results[-1]['entities_count']}")
        print(f"    Tags: {results[-1]['tags_count']}")
    
    # Second pass: all cache hits
    print("\n" + "-" * 60)
    print("Second pass (all cache hits):")
    for note in test_notes:
        start = time.time()
        result = analyze_note(
            body=note["body"],
            tags=note["tags"],
            title=note["title"],
        )
        elapsed = time.time() - start
        
        print(f"  {note['title']}: {result.processing_time_ms:.0f}ms (cache hit)")
    
    print("\n" + "=" * 60)
    print("Benchmark complete.")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    _benchmark()
