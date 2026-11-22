"""
Obsidian integration package for AI Memory Pipeline Phase 6.

Provides vault monitoring, content extraction, knowledge graph building,
and two-way synchronization between an Obsidian vault and the AI memory
pipeline (Qdrant + LM Studio).

NOTE: Submodules are NOT imported here to avoid circular import issues
when running ``python -m ai_memory_pipeline.obsidian.sync_engine``.
Import submodules explicitly when needed.
"""

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
