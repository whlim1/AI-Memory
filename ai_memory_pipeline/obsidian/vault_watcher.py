"""
Obsidian vault file system watcher for AI Memory Pipeline Phase 6.

Monitors an Obsidian vault directory for Markdown file changes
(created, modified, deleted) and emits events for the sync engine.

Uses the `watchdog` library when available for real-time monitoring,
and falls back to a polling-based watcher (md5 + mtime) otherwise.
"""

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class VaultEvent(Enum):
    """Types of file system events emitted by the vault watcher."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class VaultFileEvent:
    """A single file system event for a vault file."""

    event: VaultEvent
    filepath: str
    timestamp: float = field(default_factory=time.time)
    file_hash: Optional[str] = None

    @property
    def relative_path(self) -> str:
        """File path relative to the vault root (set by the watcher)."""
        return getattr(self, "_relative_path", "") or ""


def compute_file_hash(filepath: str) -> Optional[str]:
    """
    Compute the MD5 hash of a file.

    Args:
        filepath (str): Path to the file.

    Returns:
        Optional[str]: Hex digest, or None if the file cannot be read.
    """
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except (OSError, IOError) as e:
        logger.warning(f"Could not hash file '{filepath}': {e}")
        return None


class VaultWatcher:
    """
    Watches an Obsidian vault directory for Markdown file changes.

    Prefers watchdog-based real-time monitoring; falls back to polling
    when watchdog is not installed.

    Example:
        >>> watcher = VaultWatcher("/path/to/vault")
        >>> watcher.on_change(lambda ev: print(ev.event, ev.filepath))
        >>> watcher.start()
        ...
        >>> watcher.stop()
    """

    # Files/directories Obsidian uses internally — never indexed
    IGNORED_DIRS = {".obsidian", ".trash", ".git", ".DS_Store"}
    WATCHED_EXTENSIONS = {".md"}

    def __init__(
        self,
        vault_path: Optional[str] = None,
        poll_interval: int = None,
        debounce_seconds: float = 1.0,
    ):
        """
        Initialize the vault watcher.

        Args:
            vault_path (Optional[str]): Path to the Obsidian vault root.
                Defaults to the OBSIDIAN_VAULT_PATH environment variable.
            poll_interval (Optional[int]): Polling interval in seconds for
                the fallback watcher. Defaults to OBSIDIAN_SYNC_INTERVAL
                (or 60 seconds).
            debounce_seconds (float): Minimum seconds between events for
                the same file (avoids duplicate events during saves).
        """
        self.vault_path = Path(
            vault_path or os.environ.get("OBSIDIAN_VAULT_PATH", "")
        ).expanduser()

        if not self.vault_path.is_dir():
            raise ValueError(
                f"Vault path does not exist or is not a directory: {self.vault_path}"
            )

        self.poll_interval = poll_interval or int(
            os.environ.get("OBSIDIAN_SYNC_INTERVAL", 60)
        )
        self.debounce_seconds = debounce_seconds

        self._callbacks: List[Callable[[VaultFileEvent], None]] = []
        self._running = False
        self._stop_requested = False

        # File state for polling mode: path -> (md5, mtime)
        self._file_state: Dict[str, tuple] = {}

        # Debounce: path -> last event timestamp
        self._last_event: Dict[str, float] = {}

        # watchdog observer (only set when watchdog is available)
        self._observer = None
        self._use_watchdog = self._init_watchdog()

    def _init_watchdog(self) -> bool:
        """Try to set up a watchdog observer. Returns True on success."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            logger.info("watchdog not installed; using polling-based vault watcher")
            return False

        watcher = self

        class _Handler(FileSystemEventHandler):
            def on_created(self, event):
                watcher._handle_fs_event(VaultEvent.CREATED, event)

            def on_modified(self, event):
                watcher._handle_fs_event(VaultEvent.MODIFIED, event)

            def on_deleted(self, event):
                watcher._handle_fs_event(VaultEvent.DELETED, event)

        self._handler = _Handler()
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.vault_path), recursive=True)
        logger.info(f"watchdog observer scheduled for {self.vault_path}")
        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_change(self, callback: Callable[[VaultFileEvent], None]) -> None:
        """Register a callback invoked for each vault file event."""
        self._callbacks.append(callback)

    def start(self) -> None:
        """Start watching the vault (non-blocking)."""
        if self._running:
            logger.warning("Vault watcher is already running")
            return

        self._stop_requested = False
        self._running = True

        if self._use_watchdog:
            self._observer.start()
            logger.info(f"Vault watcher started (watchdog) on {self.vault_path}")
        else:
            import threading

            self._scan_vault()  # baseline snapshot
            self._poll_thread = threading.Thread(
                target=self._poll_loop, daemon=True, name="vault-watcher-poll"
            )
            self._poll_thread.start()
            logger.info(
                f"Vault watcher started (polling every {self.poll_interval}s) on {self.vault_path}"
            )

    def stop(self) -> None:
        """Stop watching the vault."""
        self._stop_requested = True
        self._running = False

        if self._observer is not None:
            self._observer.stop()
            self._observer = None

        logger.info("Vault watcher stopped")

    @property
    def is_running(self) -> bool:
        """Whether the watcher is currently active."""
        return self._running

    def scan_vault(self) -> List[str]:
        """
        List all watchable Markdown files in the vault.

        Returns:
            List[str]: Absolute paths of Markdown files (excluding ignored dirs).
        """
        return [str(p) for p in self._iter_markdown_files()]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _iter_markdown_files(self):
        """Yield Markdown files in the vault, skipping ignored directories."""
        for path in self.vault_path.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.WATCHED_EXTENSIONS:
                continue
            # Skip anything under an ignored directory
            parts = path.relative_to(self.vault_path).parts
            if any(part in self.IGNORED_DIRS for part in parts):
                continue
            yield path

    def _handle_fs_event(self, event: VaultEvent, fs_event) -> None:
        """Process a raw watchdog event (file or directory)."""
        if getattr(fs_event, "is_directory", False):
            return

        filepath = fs_event.src_path
        if Path(filepath).suffix.lower() not in self.WATCHED_EXTENSIONS:
            return

        self._emit(event, filepath)

    def _poll_loop(self) -> None:
        """Background loop for the polling fallback watcher."""
        while not self._stop_requested:
            try:
                self._scan_vault()
            except Exception as e:
                logger.error(f"Vault scan failed: {e}")
            time.sleep(self.poll_interval)

    def _scan_vault(self) -> None:
        """Compare current vault state against the last snapshot and emit events."""
        current: Dict[str, tuple] = {}

        for path in self._iter_markdown_files():
            filepath = str(path)
            file_hash = compute_file_hash(filepath)
            if file_hash is None:
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            current[filepath] = (file_hash, mtime)

        # New or modified files
        for filepath, (file_hash, _mtime) in current.items():
            prev = self._file_state.get(filepath)
            if prev is None:
                self._emit(VaultEvent.CREATED, filepath, file_hash)
            elif prev[0] != file_hash:
                self._emit(VaultEvent.MODIFIED, filepath, file_hash)

        # Deleted files
        for filepath in list(self._file_state.keys()):
            if filepath not in current:
                self._emit(VaultEvent.DELETED, filepath)

        self._file_state = current

    def _emit(
        self,
        event: VaultEvent,
        filepath: str,
        file_hash: Optional[str] = None,
    ) -> None:
        """Apply debounce, then dispatch the event to all registered callbacks."""
        now = time.time()
        last = self._last_event.get(filepath)
        if last is not None and (now - last) < self.debounce_seconds:
            return
        self._last_event[filepath] = now

        vault_event = VaultFileEvent(
            event=event, filepath=filepath, file_hash=file_hash
        )
        try:
            vault_event._relative_path = str(
                Path(filepath).relative_to(self.vault_path)
            )
        except ValueError:
            vault_event._relative_path = Path(filepath).name

        logger.debug(f"Vault event: {event.value} {filepath}")

        for callback in self._callbacks:
            try:
                callback(vault_event)
            except Exception as e:
                logger.error(f"Vault event callback failed for {filepath}: {e}")
