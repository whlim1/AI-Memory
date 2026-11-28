# =============================================================================
# AI Memory Pipeline - API Gateway
# =============================================================================
# Provides unified entry point for all pipeline services:
#   POST /api/v1/process    chunking (/chunk) -> deduplication (/check) per chunk
#   GET|POST /api/v1/search LM Studio embedding + Qdrant similarity search
#   GET  /api/v1/status     aggregated health of peer services and infrastructure
# =============================================================================

import asyncio
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gateway")

# Initialize FastAPI app
app = FastAPI(
    title="AI Memory Pipeline API",
    description="Unified entry point for document processing and memory management",
    version="1.0.0"
)


# ---------------------------------------------------------------------------
# Configuration — peer services are addressed by compose service name; Docker
# DNS resolves the names on the shared AI-Memory network. All peers listen on
# port 8001 inside their containers.
# ---------------------------------------------------------------------------
CHUNKING_URL = os.getenv("CHUNKING_URL", "http://chunking:8001").rstrip("/")
DEDUP_URL = os.getenv("DEDUP_URL", "http://deduplication:8001").rstrip("/")
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://embedding:8001").rstrip("/")
MODEL_CACHE_URL = os.getenv("MODEL_CACHE_URL", "http://model-cache:8001").rstrip("/")

# Infrastructure endpoints (Qdrant URL with scheme; LM Studio as host:port)
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333").rstrip("/")
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "localhost:1234")

PEER_SERVICES: Dict[str, str] = {
    "chunking": CHUNKING_URL,
    "deduplication": DEDUP_URL,
    "embedding": EMBEDDING_URL,
    "model-cache": MODEL_CACHE_URL,
}

REQUEST_TIMEOUT = float(os.getenv("GATEWAY_REQUEST_TIMEOUT", "10"))  # peer API calls
HEALTH_TIMEOUT = float(os.getenv("GATEWAY_HEALTH_TIMEOUT", "3"))     # health probes


class PeerError(Exception):
    """Raised when a downstream service call fails.

    status_code is set when the peer answered with an HTTP error (so the
    gateway can mirror 4xx client errors), and None for connection failures.
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


async def _http_post(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST JSON to a peer service and return the parsed response body."""

    def _call():
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        if response.status_code >= 400:
            raise PeerError(
                f"{url} returned {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )
        return response.json()

    try:
        return await asyncio.to_thread(_call)
    except requests.RequestException as exc:
        raise PeerError(f"Failed to reach {url}: {exc}")


def _lm_studio_host_port() -> Tuple[str, int]:
    """Parse LM_STUDIO_URL ('host:port', optional scheme) into (host, port)."""
    value = LM_STUDIO_URL.split("//", 1)[-1].strip().rstrip("/")
    host, _, port = value.partition(":")
    if not port.isdigit():
        raise PeerError(f"Invalid LM_STUDIO_URL format: {LM_STUDIO_URL!r} (expected 'host:port')")
    return host or "localhost", int(port)


# ---------------------------------------------------------------------------
# Lazy singletons for the Qdrant / LM Studio clients (created on first use so
# gateway startup never depends on the backing infrastructure).
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
_qdrant_manager: Optional[Any] = None
_embedder: Optional[Any] = None


def get_qdrant_manager():
    """Return a shared QdrantManager (created on first use)."""
    global _qdrant_manager
    if _qdrant_manager is None:
        with _state_lock:
            if _qdrant_manager is None:
                from ai_memory_pipeline.qdrant_client_wrapper import QdrantManager
                _qdrant_manager = QdrantManager(url=QDRANT_URL)
                logger.info("Gateway QdrantManager initialized for %s", QDRANT_URL)
    return _qdrant_manager


def get_embedder():
    """Return a shared LMStudioEmbedder (created on first use)."""
    global _embedder
    if _embedder is None:
        with _state_lock:
            if _embedder is None:
                from ai_memory_pipeline.lm_studio_embeddings import LMStudioEmbedder
                host, port = _lm_studio_host_port()
                _embedder = LMStudioEmbedder(host=host, port=port)
                logger.info("Gateway LMStudioEmbedder initialized at %s:%s", host, port)
    return _embedder


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class ProcessRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Document text to process")
    filename: Optional[str] = None
    content_type: Optional[str] = None
    force_type: bool = False
    fuzzy_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query text to embed and search")
    collection: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for container orchestration."""
    return HealthResponse(
        status="healthy",
        service="ai-memory-pipeline-gateway",
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Memory Pipeline",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/api/v1/process": "Process documents (chunk + dedup)",
            "/api/v1/search": "Search memories (embed + Qdrant lookup)",
            "/api/v1/status": "Service status"
        }
    }


@app.post("/api/v1/process")
async def process_document(request: ProcessRequest):
    """Chunk a document, then check every chunk for duplicates.

    Pipeline: chunking (/chunk) -> deduplication (/check) per chunk.
    Chunking is a hard dependency (no chunks, nothing to dedup); a
    deduplication failure degrades gracefully and is reported per chunk.
    """
    # Step 1 — chunking (hard dependency)
    try:
        chunk_response = await _http_post(
            f"{CHUNKING_URL}/chunk",
            {
                "content": request.content,
                "filename": request.filename,
                "content_type": request.content_type,
                "force_type": request.force_type,
            },
        )
    except PeerError as exc:
        if exc.status_code is not None and 400 <= exc.status_code < 500:
            raise HTTPException(status_code=exc.status_code, detail=f"Chunking rejected request: {exc}")
        raise HTTPException(status_code=502, detail=f"Chunking service unavailable: {exc}")

    chunks: List[Dict[str, Any]] = chunk_response.get("chunks", [])
    base_id = (request.filename or "document").rsplit(".", 1)[0] if request.filename else "document"

    # Step 2 — dedup check per chunk (soft dependency)
    results = []
    duplicates_found = 0
    for chunk in chunks:
        doc_id = f"{base_id}#{chunk.get('chunk_index', 0)}"
        try:
            dedup = await _http_post(
                f"{DEDUP_URL}/check",
                {
                    "doc_id": doc_id,
                    "content": chunk["content"],
                    "fuzzy_threshold": request.fuzzy_threshold,
                },
            )
            if dedup.get("is_duplicate"):
                duplicates_found += 1
        except PeerError as exc:
            dedup = {"status": "unavailable", "error": str(exc)}
        results.append({"chunk": chunk, "dedup": dedup})

    return {
        "chunks": results,
        "total_chunks": len(results),
        "duplicates_found": duplicates_found,
        "source_filename": request.filename,
    }


async def _resolve_collection(collection: Optional[str]) -> str:
    """Verify Qdrant reachability and resolve the target collection."""
    try:
        response = requests.get(f"{QDRANT_URL}/collections", timeout=HEALTH_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant unreachable at {QDRANT_URL}: {exc}")

    names = [c.get("name") for c in response.json().get("result", {}).get("collections", [])]
    if collection is None:
        if not names:
            raise HTTPException(status_code=404, detail="No collections found in Qdrant — nothing to search")
        return names[0]
    if collection not in names:
        available = ", ".join(n for n in names if n) if names else "none"
        raise HTTPException(
            status_code=404,
            detail=f"Collection '{collection}' not found. Available: {available}"
        )
    return collection


async def _run_search(query: str, collection: Optional[str], limit: int):
    """Embed the query with LM Studio and search Qdrant for similar memories."""
    target = await _resolve_collection(collection)

    # Embedding via LM Studio's OpenAI-compatible API (raises RuntimeError if down)
    try:
        embedder = get_embedder()
        vector = await asyncio.to_thread(embedder.generate_single_embedding, query)
    except PeerError as exc:
        raise HTTPException(status_code=502, detail=f"LM Studio misconfigured: {exc}")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"LM Studio embedding failed: {exc}")
    if not vector:
        raise HTTPException(status_code=502, detail="LM Studio returned an empty embedding")

    # Similarity search (Qdrant connectivity already verified above)
    manager = get_qdrant_manager()
    hits = await asyncio.to_thread(manager.search_similar, target, vector, limit)

    return {
        "query": query,
        "collection": target,
        "total_results": len(hits),
        "results": [
            {"id": hit["id"], "score": round(hit["score"], 6), "payload": hit["payload"]}
            for hit in hits
        ],
    }


@app.post("/api/v1/search")
async def search_post(request: SearchRequest):
    """Embed the query with LM Studio and search Qdrant for similar memories."""
    return await _run_search(request.query, request.collection, request.limit)


@app.get("/api/v1/search")
async def search_get(
    q: str = Query(..., min_length=1, description="Query text to embed and search"),
    collection: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
):
    """GET variant of /api/v1/search (query text as ?q=...)."""
    return await _run_search(q, collection, limit)


async def _probe_service(name: str, url: str) -> Dict[str, Any]:
    """Probe a peer service's /health endpoint."""

    def _call():
        response = requests.get(f"{url}/health", timeout=HEALTH_TIMEOUT)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {}

    try:
        detail = await asyncio.to_thread(_call)
        return {"service": name, "status": "healthy", "url": url, "detail": detail}
    except requests.RequestException as exc:
        return {"service": name, "status": "unreachable", "url": url, "error": str(exc)}


async def _probe_infrastructure() -> Dict[str, Any]:
    """Check Qdrant and LM Studio directly (not via the peer services)."""

    async def check_qdrant():
        try:
            response = requests.get(f"{QDRANT_URL}/collections", timeout=HEALTH_TIMEOUT)
            response.raise_for_status()
            collections = [c.get("name") for c in response.json().get("result", {}).get("collections", [])]
            return {"status": "healthy", "url": QDRANT_URL, "collections": len(collections)}
        except requests.RequestException as exc:
            return {"status": "unreachable", "url": QDRANT_URL, "error": str(exc)}

    async def check_lm_studio():
        try:
            host, port = _lm_studio_host_port()
        except PeerError as exc:
            return {"status": "misconfigured", "url": LM_STUDIO_URL, "error": str(exc)}
        base = f"http://{host}:{port}"

        def _call():
            response = requests.get(f"{base}/v1/models", timeout=HEALTH_TIMEOUT)
            response.raise_for_status()
            return len(response.json().get("data", []))

        try:
            models = await asyncio.to_thread(_call)
            return {"status": "healthy", "url": base, "models": models}
        except requests.RequestException as exc:
            return {"status": "unreachable", "url": base, "error": str(exc)}

    qdrant, lm_studio = await asyncio.gather(check_qdrant(), check_lm_studio())
    return {"qdrant": qdrant, "lm_studio": lm_studio}


@app.get("/api/v1/status")
async def service_status():
    """Aggregated health of all peer services and backing infrastructure."""
    peers = await asyncio.gather(*[_probe_service(name, url) for name, url in PEER_SERVICES.items()])
    infrastructure = await _probe_infrastructure()

    healthy_peers = [p["service"] for p in peers if p["status"] == "healthy"]
    all_healthy = (
        len(healthy_peers) == len(peers)
        and all(i["status"] == "healthy" for i in infrastructure.values())
    )

    return {
        "status": "healthy" if all_healthy else ("degraded" if healthy_peers else "unhealthy"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "services": peers,
        "infrastructure": infrastructure,
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info(
        "AI Memory Pipeline Gateway starting up (peers: %s)",
        ", ".join(f"{name}={url}" for name, url in PEER_SERVICES.items()),
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("AI Memory Pipeline Gateway shutting down")
