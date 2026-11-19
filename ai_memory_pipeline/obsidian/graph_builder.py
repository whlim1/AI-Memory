"""
Knowledge graph builder for Obsidian vaults (Phase 6.1).

Builds and maintains an in-memory knowledge graph from parsed Obsidian
notes (NoteContent). The graph captures:

- Note nodes (one per Markdown file, keyed by stable doc_id)
- Tag nodes (one per unique tag)
- "links_to" edges between notes (from [[wikilinks]])
- "tagged" edges from notes to their tags

The graph is serializable to/from JSON so it can be persisted alongside
the vault and inspected by other tools (e.g. a future mobile app or
OpenWebUI integration).
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .content_processor import NoteContent

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """A single node in the knowledge graph."""

    id: str
    type: str  # "note" | "tag"
    title: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "attributes": self.attributes,
        }


@dataclass
class GraphEdge:
    """A directed edge between two graph nodes."""

    source: str
    target: str
    type: str  # "links_to" | "tagged"
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "attributes": self.attributes,
        }


class KnowledgeGraphBuilder:
    """
    Builds and maintains a knowledge graph from Obsidian notes.

    Usage:
        builder = KnowledgeGraphBuilder()
        builder.add_note(note)          # incremental update
        builder.remove_note(doc_id)     # remove a note and its edges
        builder.save("graph.json")      # persist
        builder.load("graph.json")      # restore
    """

    def __init__(self, graph_path: Optional[str] = None):
        """
        Args:
            graph_path (Optional[str]): Default path for save()/load().
                Defaults to <vault>/.ai-memory/graph.json when the sync
                engine configures it.
        """
        self.graph_path = Path(graph_path) if graph_path else None
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        # Adjacency indexes for fast lookups
        self._outgoing: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._incoming: Dict[str, List[GraphEdge]] = defaultdict(list)
        # doc_id -> relative vault path (for note lookup by path)
        self._doc_by_path: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_note(self, note: NoteContent) -> GraphNode:
        """
        Add or update a note in the graph.

        Replaces any existing node/edges for this note's doc_id, so the
        method is idempotent for re-syncs.

        Args:
            note (NoteContent): Parsed note (doc_id must be set).

        Returns:
            GraphNode: The note node.
        """
        if not note.doc_id:
            raise ValueError(
                f"Note '{note.relative_path}' has no doc_id; "
                "call ContentProcessor.build_metadata() first"
            )

        # Remove stale edges for this note before re-adding
        self._remove_note_edges(note.doc_id)

        node = GraphNode(
            id=note.doc_id,
            type="note",
            title=note.title or note.relative_path,
            attributes={
                "path": note.relative_path,
                "tags": list(note.tags),
                "aliases": list(note.aliases),
                "word_count": note.word_count,
                "headings": list(note.headings),
            },
        )
        self.nodes[note.doc_id] = node
        self._doc_by_path[note.relative_path] = note.doc_id

        # Tag nodes + "tagged" edges
        for tag in note.tags:
            tag_id = f"tag:{tag}"
            if tag_id not in self.nodes:
                self.nodes[tag_id] = GraphNode(
                    id=tag_id, type="tag", title=tag
                )
            self._add_edge(GraphEdge(note.doc_id, tag_id, type="tagged"))

        # Wikilink edges: resolve targets to known doc_ids when possible,
        # otherwise create a "dangling" note node so the link is visible.
        for target in note.wikilinks:
            target_doc_id = self._resolve_wikilink(target)
            if target_doc_id is None:
                # Dangling link: create a placeholder note node
                target_doc_id = f"missing:{target}"
                if target_doc_id not in self.nodes:
                    self.nodes[target_doc_id] = GraphNode(
                        id=target_doc_id,
                        type="note",
                        title=target,
                        attributes={"path": None, "status": "unresolved"},
                    )
            if target_doc_id != note.doc_id:
                self._add_edge(GraphEdge(
                    note.doc_id, target_doc_id, type="links_to"
                ))

        # This note may now satisfy earlier "missing:" placeholders
        self._reconcile_placeholders(note)

        logger.debug(
            "Graph updated with note '%s' (%d nodes, %d edges)",
            note.relative_path, len(self.nodes), len(self.edges),
        )
        return node

    def remove_note(self, doc_id: Optional[str] = None,
                    relative_path: Optional[str] = None) -> bool:
        """
        Remove a note (and its edges) from the graph.

        Args:
            doc_id (Optional[str]): Note doc_id to remove.
            relative_path (Optional[str]): Alternative lookup by vault path.

        Returns:
            bool: True if a note was removed.
        """
        if doc_id is None and relative_path is not None:
            doc_id = self._doc_by_path.get(relative_path)
        if doc_id is None or doc_id not in self.nodes:
            return False

        self._remove_note_edges(doc_id)
        del self.nodes[doc_id]
        # Clean up path index
        for path, did in list(self._doc_by_path.items()):
            if did == doc_id:
                del self._doc_by_path[path]

        # Drop tag nodes that are no longer referenced
        referenced_tags = {
            e.target for e in self.edges if e.type == "tagged"
        }
        for tag_id in list(self.nodes.keys()):
            if (
                self.nodes[tag_id].type == "tag"
                and tag_id not in referenced_tags
            ):
                del self.nodes[tag_id]

        logger.debug("Graph note removed: %s", doc_id)
        return True

    def add_notes(self, notes: List[NoteContent]) -> None:
        """Add multiple notes in one call."""
        for note in notes:
            self.add_note(note)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def neighbors(self, doc_id: str,
                  edge_type: Optional[str] = None) -> List[str]:
        """Return ids of nodes directly connected to doc_id."""
        result = []
        for edge in self._outgoing.get(doc_id, []):
            if edge_type is None or edge.type == edge_type:
                if edge.target not in result:
                    result.append(edge.target)
        for edge in self._incoming.get(doc_id, []):
            if edge_type is None or edge.type == edge_type:
                if edge.source not in result:
                    result.append(edge.source)
        return result

    def notes_for_tag(self, tag: str) -> List[str]:
        """Return doc_ids of all notes carrying the given tag."""
        tag_id = f"tag:{tag}"
        return [
            e.source for e in self._incoming.get(tag_id, [])
            if e.type == "tagged"
        ]

    @property
    def stats(self) -> Dict[str, int]:
        """Summary counts for logging / status endpoints."""
        note_nodes = [n for n in self.nodes.values() if n.type == "note"]
        return {
            "notes": len(note_nodes),
            "tags": len(self.nodes) - len(note_nodes),
            "edges": len(self.edges),
            "links": sum(1 for e in self.edges if e.type == "links_to"),
            "tagged": sum(1 for e in self.edges if e.type == "tagged"),
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    def save(self, path: Optional[str] = None) -> bool:
        """
        Persist the graph as JSON.

        Args:
            path (Optional[str]): Destination file. Defaults to graph_path.

        Returns:
            bool: True on success.
        """
        target = Path(path) if path else self.graph_path
        if target is None:
            logger.warning("No graph path configured; skipping save")
            return False
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Knowledge graph saved to %s", target)
            return True
        except (OSError, IOError) as e:
            logger.error(f"Failed to save knowledge graph to {target}: {e}")
            return False

    def load(self, path: Optional[str] = None) -> bool:
        """
        Restore the graph from a JSON file.

        Args:
            path (Optional[str]): Source file. Defaults to graph_path.

        Returns:
            bool: True on success.
        """
        source = Path(path) if path else self.graph_path
        if source is None or not source.exists():
            return False
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
            self.nodes = {}
            self.edges = []
            self._outgoing = defaultdict(list)
            self._incoming = defaultdict(list)
            self._doc_by_path = {}

            for n in data.get("nodes", []):
                node = GraphNode(
                    id=n["id"], type=n["type"],
                    title=n.get("title", ""),
                    attributes=n.get("attributes", {}),
                )
                self.nodes[node.id] = node
                if node.type == "note" and node.attributes.get("path"):
                    self._doc_by_path[node.attributes["path"]] = node.id

            for e in data.get("edges", []):
                edge = GraphEdge(
                    source=e["source"], target=e["target"],
                    type=e.get("type", "links_to"),
                    attributes=e.get("attributes", {}),
                )
                self._add_edge(edge)

            logger.info(
                "Knowledge graph loaded from %s (%d nodes, %d edges)",
                source, len(self.nodes), len(self.edges),
            )
            return True
        except (OSError, IOError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load knowledge graph from {source}: {e}")
            return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)
        self._outgoing[edge.source].append(edge)
        self._incoming[edge.target].append(edge)

    def _remove_note_edges(self, doc_id: str) -> None:
        """Remove every edge touching the given note doc_id."""
        self.edges = [
            e for e in self.edges
            if e.source != doc_id and e.target != doc_id
        ]
        self._outgoing[doc_id] = []
        self._incoming[doc_id] = []
        # Rebuild the other side's indexes (cheap for vault-sized graphs)
        self._outgoing = defaultdict(list)
        self._incoming = defaultdict(list)
        for e in self.edges:
            self._outgoing[e.source].append(e)
            self._incoming[e.target].append(e)

    def _reconcile_placeholders(self, note: NoteContent) -> None:
        """
        Replace "missing:" placeholder nodes that this note now satisfies.

        When a note is added out of order, earlier wikilinks to it may have
        created placeholder nodes. Rewire their edges to the real note and
        drop the placeholders.
        """
        candidates = {note.title, note.relative_path}
        if note.relative_path.endswith(".md"):
            candidates.add(note.relative_path[:-3])
        # Obsidian resolves wikilinks by filename stem
        candidates.add(Path(note.relative_path).stem)
        candidates.update(note.aliases)
        candidates.discard("")

        for node_id in list(self.nodes.keys()):
            if not node_id.startswith("missing:"):
                continue
            if node_id[len("missing:"):] not in candidates:
                continue

            placeholder_edges = [
                e for e in self.edges
                if e.source == node_id or e.target == node_id
            ]
            self._remove_note_edges(node_id)
            for e in placeholder_edges:
                new_edge = GraphEdge(
                    source=note.doc_id if e.source == node_id else e.source,
                    target=note.doc_id if e.target == node_id else e.target,
                    type=e.type,
                    attributes=e.attributes,
                )
                if (
                    new_edge.source != new_edge.target
                    and not self._edge_exists(new_edge)
                ):
                    self._add_edge(new_edge)
            del self.nodes[node_id]
            logger.debug(
                "Reconciled placeholder %s -> %s", node_id, note.doc_id
            )

    def _edge_exists(self, edge: GraphEdge) -> bool:
        return any(
            e.source == edge.source
            and e.target == edge.target
            and e.type == edge.type
            for e in self.edges
        )

    def _resolve_wikilink(self, target: str) -> Optional[str]:
        """
        Resolve a wikilink target to a known note doc_id.

        Matches against relative paths (with or without .md) and note
        titles / aliases.
        """
        # 1. Direct path match (with or without .md extension)
        for candidate in (target, f"{target}.md"):
            if candidate in self._doc_by_path:
                return self._doc_by_path[candidate]

        # 1b. Filename-stem match (Obsidian's primary resolution rule)
        for path, doc_id in self._doc_by_path.items():
            if Path(path).stem == target:
                return doc_id

        # 2. Existing placeholder for this target (reconciled later)
        if f"missing:{target}" in self.nodes:
            return f"missing:{target}"

        # 3. Title / alias match
        for node in self.nodes.values():
            if node.type != "note":
                continue
            if node.title == target:
                return node.id
            if target in node.attributes.get("aliases", []):
                return node.id

        return None
