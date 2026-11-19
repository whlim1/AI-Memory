"""
Obsidian integration package for AI Memory Pipeline Phase 6.

Provides vault monitoring, content extraction, knowledge graph building,
and two-way synchronization between an Obsidian vault and the AI memory
pipeline (Qdrant + LM Studio).
"""

from . import vault_watcher
from . import content_processor
from . import graph_builder
from . import sync_engine

from .vault_watcher import VaultWatcher, VaultEvent
from .content_processor import ContentProcessor, NoteContent
from .graph_builder import KnowledgeGraphBuilder
from .sync_engine import ObsidianSyncEngine

__all__ = [
    'vault_watcher',
    'content_processor',
    'graph_builder',
    'sync_engine',
    'VaultWatcher',
    'VaultEvent',
    'ContentProcessor',
    'NoteContent',
    'KnowledgeGraphBuilder',
    'ObsidianSyncEngine',
]
