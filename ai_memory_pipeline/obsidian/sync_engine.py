"""
Obsidian sync engine for AI Memory Pipeline Phase 6.1.

Wires the pieces together:

    VaultWatcher  ->  ContentProcessor  ->  LMSmartEmbedder
        (fs events)      (parse + chunk)       (embeddings)
                                        ->  QdrantManager  (indexing)
                                        ->  KnowledgeGraphBuilder (graph)

Environment variables:
    OBSIDIAN_VAULT_PATH      Vault directory (required unless passed in)
    OBSIDIAN_COLLECTION      Qdrant collection (default: ai_memory_documents)
    OBSIDIAN_SYNC_INTERVAL   Poll fallback interval seconds (default: 60)
    OBSIDIAN_AUTO_CATEGORIZE "true"/"false" (default: true)
    OBSIDIAN_EMBEDDING_MODEL LM Studio embedding model id (default: auto)
    QDRANT_URL               Full Qdrant URL (preferred)
    QDRANT_HOST / QDRANT_PORT Qdrant host/port (fallback)
    LM_STUDIO_URL            LM Studio base URL (default: http://localhost:1234)
"""

import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ..metadata import DocumentMetadata
from ..qdrant_client_wrapper import QdrantManager
from .content_processor import ContentProcessor, NoteContent
from .graph_builder import KnowledgeGraphBuilder
from .vault_watcher import VaultEvent, VaultFileEvent, VaultWatcher, compute_file_hash

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "ai_memory_documents"
DEFAULT_SYNC_INTERVAL = 60
DEFAULT_LM_STUDIO_URL = "http://localhost:1234"


def _chunk_point_id(doc_id: str, chunk_index: int) -> int:
    """
    Deterministic uint64 Qdrant point id for a note chunk.

    Qdrant point ids must be a UUID or an unsigned 64-bit integer, so we
    derive a stable integer from the note doc_id + chunk index.
    """
    digest = hashlib.md5(
        f"{doc_id}_chunk_{chunk_index}".encode("utf-8")
    ).hexdigest()
    return int(digest[:15], 16)  # 60 bits, safely within uint64


def _parse_lm_studio_url(url: str) -> tuple:
    """Parse an LM Studio base URL into (host, port)."""
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = parsed.hostname or "localhost"
    port = parsed.port or 1234
    return host, port


class ObsidianSyncEngine:
    """
    Keeps an Obsidian vault in sync with the AI memory pipeline.

    - Watches the vault for .md changes (watchdog or polling fallback)
    - Parses, chunks, embeds, and indexes note content into Qdrant
    - Removes stale chunks when notes are deleted or re-chunked
    - Maintains a JSON knowledge graph alongside the vault

    Usage:
        engine = ObsidianSyncEngine(vault_path="/path/to/vault")
        engine.start()          # starts watcher + initial full sync
        ...
        engine.stop()
    """

    def __init__(
        self,
        vault_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        qdrant: Optional[QdrantManager] = None,
        embedder=None,
        processor: Optional[ContentProcessor] = None,
        watcher: Optional[VaultWatcher] = None,
        graph_builder: Optional[KnowledgeGraphBuilder] = None,
        auto_categorize: Optional[bool] = None,
        sync_interval: Optional[int] = None,
        embedder_model_id: Optional[str] = None,
    ):
        """
        Args:
            vault_path: Vault directory. Falls back to OBSIDIAN_VAULT_PATH.
            collection_name: Qdrant collection. Falls back to
                OBSIDIAN_COLLECTION, then "ai_memory_documents".
            qdrant: Pre-built QdrantManager (built from env if omitted).
            embedder: Pre-built LMSmartEmbedder (built from env if omitted).
            processor: Pre-built ContentProcessor.
            watcher: Pre-built VaultWatcher.
            graph_builder: Pre-built KnowledgeGraphBuilder.
            auto_categorize: Derive a category tag for uncategorized notes.
                Falls back to OBSIDIAN_AUTO_CATEGORIZE, then True.
            sync_interval: Poll fallback interval. Falls back to
                OBSIDIAN_SYNC_INTERVAL, then 60.
            embedder_model_id: LM Studio embedding model id. Falls back to
                OBSIDIAN_EMBEDDING_MODEL.
        """
        self.vault_path = Path(
            vault_path or os.getenv("OBSIDIAN_VAULT_PATH", "")
        ).expanduser()
        if not self.vault_path or not self.vault_path.is_dir():
            raise ValueError(
                f"Obsidian vault path not found: {self.vault_path!r}. "
                "Set OBSIDIAN_VAULT_PATH or pass vault_path."
            )

        self.collection_name = (
            collection_name
            or os.getenv("OBSIDIAN_COLLECTION", DEFAULT_COLLECTION)
        )

        if auto_categorize is None:
            auto_categorize = os.getenv(
                "OBSIDIAN_AUTO_CATEGORIZE", "true"
            ).lower() in ("1", "true", "yes")
        self.auto_categorize = auto_categorize

        if sync_interval is None:
            sync_interval = int(
                os.getenv("OBSIDIAN_SYNC_INTERVAL", str(DEFAULT_SYNC_INTERVAL))
            )
        self.sync_interval = sync_interval

        # Knowledge graph persisted alongside the vault
        graph_path = self.vault_path / ".ai-memory" / "graph.json"
        self.graph_builder = graph_builder or KnowledgeGraphBuilder(
            graph_path=str(graph_path)
        )
        self.graph_builder.load()

        self.processor = processor or ContentProcessor()
        self.watcher = watcher or VaultWatcher(
            vault_path=str(self.vault_path),
            poll_interval=self.sync_interval,
        )
        self._qdrant = qdrant
        self._embedder = embedder
        self._embedder_model_id = embedder_model_id or os.getenv(
            "OBSIDIAN_EMBEDDING_MODEL"
        )

        # doc_id -> file_hash of last successful sync (skip no-op re-syncs)
        self._synced_hashes: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._started = False
        self._sync_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, initial_sync: bool = True) -> None:
        """
        Start watching the vault.

        Args:
            initial_sync: Run a full vault sync in a background thread
                before event-driven updates begin.
        """
        if self._started:
            logger.warning("ObsidianSyncEngine already started")
            return

        self._ensure_collection()
        self.watcher.on_change(self._on_vault_event)
        self.watcher.start()
        self._started = True
        logger.info(
            "Obsidian sync engine started (vault=%s, collection=%s)",
            self.vault_path, self.collection_name,
        )

        if initial_sync:
            self._sync_thread = threading.Thread(
                target=self._safe_full_sync,
                name="obsidian-initial-sync",
                daemon=True,
            )
            self._sync_thread.start()

    def stop(self) -> None:
        """Stop the watcher and background sync."""
        if not self._started:
            return
        self.watcher.stop()
        self._started = False
        if self._sync_thread is not None:
            self._sync_thread.join(timeout=30)
            self._sync_thread = None
        logger.info("Obsidian sync engine stopped")

    @property
    def is_running(self) -> bool:
        return self._started

    def _safe_full_sync(self) -> None:
        try:
            self.full_sync()
        except Exception as e:
            logger.error(f"Initial full sync failed: {e}")

    # ------------------------------------------------------------------
    # Sync operations
    # ------------------------------------------------------------------

    def full_sync(self) -> Dict[str, Any]:
        """
        Sync every Markdown file in the vault and prune orphans.

        Returns:
            dict: Summary with synced/removed/skipped/error counts.
        """
        summary = {"synced": 0, "skipped": 0, "removed": 0, "errors": 0}
        current_doc_ids = set()

        for filepath in self.watcher.scan_vault():
            try:
                result = self.sync_file(filepath)
                if result["status"] == "synced":
                    summary["synced"] += 1
                    current_doc_ids.add(result["doc_id"])
                elif result["status"] == "skipped":
                    summary["skipped"] += 1
                    current_doc_ids.add(result["doc_id"])
                else:
                    summary["errors"] += 1
            except Exception as e:
                summary["errors"] += 1
                logger.error(f"Full sync failed for {filepath}: {e}")

        # Prune indexed notes that no longer exist in the vault
        for doc_id in list(self._synced_hashes.keys()):
            if doc_id not in current_doc_ids:
                if self._delete_note_chunks(doc_id):
                    summary["removed"] += 1
                    del self._synced_hashes[doc_id]

        self.graph_builder.save()
        logger.info("Full sync complete: %s", summary)
        return summary

    def sync_file(self, filepath: str,
                  file_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse, embed, and index a single vault file.

        Args:
            filepath (str): Absolute path to a Markdown file.
            file_hash (Optional[str]): Pre-computed md5 (computed if omitted).

        Returns:
            dict: {"status": "synced"|"skipped"|"error", "doc_id", ...}
        """
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "error": f"File not found: {filepath}"}

        if file_hash is None:
            file_hash = compute_file_hash(str(path))
        if file_hash is None:
            return {"status": "error", "error": f"Could not read {filepath}"}

        # Skip if content unchanged since last successful sync
        note = self.processor.process_file(
            str(path), vault_path=str(self.vault_path), file_hash=file_hash
        )
        if not note.doc_id:
            self.processor.build_metadata(note)
        if self._synced_hashes.get(note.doc_id) == file_hash:
            logger.debug("Skipping unchanged note '%s'", note.relative_path)
            return {"status": "skipped", "doc_id": note.doc_id}

        with self._lock:
            # Remove stale chunks from a previous version of this note
            self._delete_note_chunks(note.doc_id)

            self.processor.chunk_note(note)
            self._auto_categorize(note)
            metadata = self.processor.build_metadata(note)

            if not note.chunks:
                # Empty note: just record the hash so we don't retry forever
                self._synced_hashes[note.doc_id] = file_hash
                self.graph_builder.add_note(note)
                self.graph_builder.save()
                return {"status": "synced", "doc_id": note.doc_id,
                        "chunks": 0}

            vectors = self._embed_chunks(note)
            payload_base = metadata.to_dict()
            payload_base["doc_id"] = note.doc_id
            payload_base["file_hash"] = file_hash

            indexed = 0
            for i, chunk in enumerate(note.chunks):
                point_id = _chunk_point_id(note.doc_id, i)
                chunk_payload = {
                    **payload_base,
                    "chunk_index": i,
                    "total_chunks": len(note.chunks),
                    "content": chunk.content,
                }
                if self.qdrant.index_document(
                    self.collection_name, str(point_id),
                    vectors[i], chunk_payload,
                ):
                    indexed += 1

            if indexed == 0:
                return {"status": "error", "doc_id": note.doc_id,
                        "error": "No chunks were indexed"}

            self._synced_hashes[note.doc_id] = file_hash
            self.graph_builder.add_note(note)
            self.graph_builder.save()

        logger.info(
            "Synced note '%s' (%d chunks) -> %s",
            note.relative_path, indexed, self.collection_name,
        )
        return {"status": "synced", "doc_id": note.doc_id, "chunks": indexed}

    def remove_file(self, filepath: str) -> bool:
        """
        Remove a note's chunks from Qdrant and the knowledge graph.

        Args:
            filepath (str): Absolute path of the deleted vault file.

        Returns:
            bool: True if anything was removed.
        """
        try:
            relative_path = str(Path(filepath).relative_to(self.vault_path))
        except ValueError:
            relative_path = Path(filepath).name

        doc_id = hashlib.md5(
            relative_path.encode("utf-8")
        ).hexdigest()[:16]

        removed = self._delete_note_chunks(doc_id)
        self.graph_builder.remove_note(doc_id=doc_id, relative_path=relative_path)
        self.graph_builder.save()
        self._synced_hashes.pop(doc_id, None)
        if removed:
            logger.info("Removed note '%s' from index", relative_path)
        return removed

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def _on_vault_event(self, event: VaultFileEvent) -> None:
        """Callback registered with the VaultWatcher."""
        if event.event == VaultEvent.DELETED:
            try:
                self.remove_file(event.filepath)
            except Exception as e:
                logger.error(
                    f"Failed to remove {event.filepath} from index: {e}"
                )
            return

        # CREATED / MODIFIED
        try:
            self.sync_file(event.filepath, file_hash=event.file_hash)
        except Exception as e:
            logger.error(f"Failed to sync {event.filepath}: {e}")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def qdrant(self) -> QdrantManager:
        """Lazily build the Qdrant client from environment variables."""
        if self._qdrant is None:
            url = os.getenv("QDRANT_URL")
            if url:
                self._qdrant = QdrantManager(url=url)
            else:
                host = os.getenv("QDRANT_HOST", "localhost")
                port = int(os.getenv("QDRANT_PORT", "6333"))
                self._qdrant = QdrantManager(host=host, port=port)
        return self._qdrant

    @property
    def embedder(self):
        """Lazily build the LM Studio smart embedder from environment."""
        if self._embedder is None:
            from ..lm_studio_smart_embedder import LMSmartEmbedder

            lm_url = os.getenv("LM_STUDIO_URL", DEFAULT_LM_STUDIO_URL)
            host, port = _parse_lm_studio_url(lm_url)
            self._embedder = LMSmartEmbedder(
                host=host, port=port,
                embedding_model_id=self._embedder_model_id,
            )
        return self._embedder

    def _ensure_collection(self) -> None:
        """Create the target collection if it does not exist yet."""
        if self.collection_name in self.qdrant.list_collections():
            return
        try:
            vector_size = self.embedder.embedding_dimension
        except Exception as e:
            logger.warning(
                f"Could not probe embedding dimension ({e}); "
                f"falling back to 1536"
            )
            vector_size = 1536
        if not self.qdrant.create_collection(
            self.collection_name, vector_size=vector_size
        ):
            raise RuntimeError(
                f"Failed to create Qdrant collection '{self.collection_name}'"
            )

    def _embed_chunks(self, note: NoteContent) -> List[List[float]]:
        """Generate embeddings for all chunks of a note."""
        texts = [chunk.content for chunk in note.chunks]
        return self.embedder.generate_embeddings(texts)

    def _auto_categorize(self, note: NoteContent) -> None:
        """
        Assign a category to notes that lack one.

        Priority: frontmatter 'category' > first tag > top-level vault
        folder > "uncategorized".
        """
        if not self.auto_categorize:
            return

        category = note.frontmatter.get("category")
        if not category:
            if note.tags:
                category = note.tags[0]
            elif "/" in note.relative_path:
                category = note.relative_path.split("/", 1)[0]
            else:
                category = "uncategorized"

        if category not in note.tags:
            note.tags.append(category)
        note.frontmatter.setdefault("category", category)

    def _delete_note_chunks(self, doc_id: str) -> bool:
        """
        Delete all indexed chunks belonging to a note doc_id.

        Uses a payload filter on the 'doc_id' field so it works even
        when the chunk count changed between syncs.

        Returns:
            bool: True if the delete call succeeded.
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            self.qdrant.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=doc_id),
                        )
                    ]
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete chunks for doc_id {doc_id}: {e}")
            return False


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    import signal
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "/app/data/vault")
    engine = ObsidianSyncEngine(vault_path=vault_path)

    stop_event = threading.Event()

    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down…")
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    engine.start()
    logger.info("Sync engine started — waiting for changes")

    # Block until a shutdown signal arrives
    while not stop_event.is_set():
        stop_event.wait(timeout=5)

    engine.stop()
    logger.info("Sync engine stopped")
    sys.exit(0)
