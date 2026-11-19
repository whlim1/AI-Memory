"""
Obsidian content processor for AI Memory Pipeline Phase 6.

Parses Obsidian Markdown notes into structured content:
- YAML frontmatter (title, tags, aliases, dates, custom fields)
- Wikilinks ([[Note Name]] / [[Note Name|alias]])
- Inline tags (#tag)
- Headings and body text

Chunks the note body using the existing DynamicChunkingService so that
Obsidian notes are indexed with the same chunking strategy as the rest
of the pipeline.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..metadata import DocumentMetadata
from ..services.dynamic_chunking_service import (
    Chunk,
    ContentType,
    DynamicChunkingService,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for Obsidian-specific syntax
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]")
INLINE_TAG_RE = re.compile(r"(?<!\S)#([A-Za-z0-9_\-/]+)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class NoteContent:
    """Structured representation of a single Obsidian note."""

    # Identity
    file_path: str
    relative_path: str
    title: str = ""
    doc_id: str = ""

    # Parsed structure
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    headings: List[str] = field(default_factory=list)
    wikilinks: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    # File stats
    file_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Chunking output
    chunks: List[Chunk] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.body.split())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'relative_path': self.relative_path,
            'title': self.title,
            'doc_id': self.doc_id,
            'frontmatter': self.frontmatter,
            'headings': self.headings,
            'wikilinks': self.wikilinks,
            'tags': self.tags,
            'aliases': self.aliases,
            'word_count': self.word_count,
            'chunk_count': len(self.chunks),
        }


class ContentProcessor:
    """
    Parses Obsidian Markdown notes into NoteContent objects and chunks
    their body text with the pipeline's DynamicChunkingService.
    """

    def __init__(self,
                 default_chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 chunker: Optional[DynamicChunkingService] = None):
        """
        Initialize the content processor.

        Args:
            default_chunk_size (int): Default chunk size in characters.
            chunk_overlap (int): Overlap between chunks in characters.
            chunker (Optional[DynamicChunkingService]): Pre-configured
                chunker. One is created if not supplied.
        """
        self.chunker = chunker or DynamicChunkingService(
            default_chunk_size=default_chunk_size,
            chunk_overlap=chunk_overlap,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_file(self,
                     file_path: str,
                     vault_path: Optional[str] = None,
                     file_hash: Optional[str] = None) -> NoteContent:
        """
        Read and parse a single Obsidian note.

        Args:
            file_path (str): Absolute path to the .md file.
            vault_path (Optional[str]): Vault root, used to compute the
                relative path. Defaults to the file's own directory.
            file_hash (Optional[str]): Pre-computed md5 hash of the file.

        Returns:
            NoteContent: Parsed note content (not yet chunked).
        """
        path = Path(file_path)
        text = path.read_text(encoding='utf-8', errors='replace')

        if vault_path:
            try:
                relative = path.resolve().relative_to(Path(vault_path).resolve())
                relative_path = str(relative).replace('\\', '/')
            except ValueError:
                relative_path = path.name
        else:
            relative_path = path.name

        frontmatter, body = self._split_frontmatter(text)
        title = self._resolve_title(frontmatter, body, path.name)
        tags = self._collect_tags(frontmatter, body)
        wikilinks = self._extract_wikilinks(body)
        headings = self._extract_headings(body)
        aliases = self._extract_aliases(frontmatter)

        note = NoteContent(
            file_path=str(path),
            relative_path=relative_path,
            title=title,
            frontmatter=frontmatter,
            body=body.strip(),
            headings=headings,
            wikilinks=wikilinks,
            tags=tags,
            aliases=aliases,
            file_hash=file_hash,
            created_at=self._frontmatter_datetime(frontmatter, 'created')
                or self._frontmatter_datetime(frontmatter, 'date'),
            updated_at=self._frontmatter_datetime(frontmatter, 'updated')
                or self._frontmatter_datetime(frontmatter, 'modified'),
        )
        return note

    def chunk_note(self, note: NoteContent) -> NoteContent:
        """
        Chunk the note body using DynamicChunkingService (Markdown mode).

        Args:
            note (NoteContent): Parsed note to chunk.

        Returns:
            NoteContent: Same note with `chunks` populated.
        """
        if not note.body.strip():
            note.chunks = []
            return note

        note.chunks = self.chunker.chunk_content(
            note.body,
            filename=note.relative_path,
            content_type=ContentType.MARKDOWN,
            force_type=True,
        )
        logger.debug(
            "Chunked note '%s' into %d chunks",
            note.relative_path, len(note.chunks),
        )
        return note

    def process_and_chunk(self,
                          file_path: str,
                          vault_path: Optional[str] = None,
                          file_hash: Optional[str] = None) -> NoteContent:
        """Convenience: parse and chunk in one call."""
        note = self.process_file(file_path, vault_path=vault_path, file_hash=file_hash)
        return self.chunk_note(note)

    def build_metadata(self, note: NoteContent) -> DocumentMetadata:
        """
        Build a DocumentMetadata object from a parsed note.

        The doc_id is derived from the note's relative vault path so it is
        stable across re-syncs (unlike the timestamp-based default).

        Args:
            note (NoteContent): Parsed note.

        Returns:
            DocumentMetadata: Metadata ready for Qdrant indexing.
        """
        import hashlib

        if not note.doc_id:
            note.doc_id = hashlib.md5(
                note.relative_path.encode('utf-8')
            ).hexdigest()[:16]

        custom_fields = {
            'vault_path': note.relative_path,
            'wikilinks': note.wikilinks,
            'aliases': note.aliases,
            'headings': note.headings,
            'word_count': note.word_count,
            'chunk_count': len(note.chunks),
            'source_type': 'obsidian',
        }
        # Surface common frontmatter fields without clobbering the above.
        for key in ('category', 'status', 'project', 'type'):
            if key in note.frontmatter:
                custom_fields[key] = note.frontmatter[key]

        return DocumentMetadata(
            doc_id=note.doc_id,
            title=note.title,
            author=str(note.frontmatter.get('author', '')),
            created_at=note.created_at or datetime.now(),
            updated_at=note.updated_at or datetime.now(),
            source=f"obsidian://{note.relative_path}",
            tags=note.tags,
            custom_fields=custom_fields,
        )

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_frontmatter(text: str) -> tuple:
        """Split YAML frontmatter from the note body."""
        match = FRONTMATTER_RE.match(text)
        if not match:
            return {}, text

        raw = match.group(1)
        body = text[match.end():]
        return ContentProcessor._parse_simple_yaml(raw), body

    @staticmethod
    def _parse_simple_yaml(raw: str) -> Dict[str, Any]:
        """
        Minimal YAML frontmatter parser (no external dependency).

        Supports:
        - key: value scalars (strings, numbers, booleans)
        - key: [a, b, c] inline lists
        - key: followed by "- item" block lists
        - ISO date/datetime strings kept as strings
        """
        data: Dict[str, Any] = {}
        current_list_key: Optional[str] = None

        for line in raw.splitlines():
            if not line.strip() or line.strip().startswith('#'):
                continue

            # Block list item
            stripped = line.strip()
            if stripped.startswith('- ') and current_list_key is not None:
                data.setdefault(current_list_key, [])
                if isinstance(data[current_list_key], list):
                    data[current_list_key].append(
                        ContentProcessor._coerce_scalar(stripped[2:].strip())
                    )
                continue

            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()

                if not value:
                    # Possibly the start of a block list
                    current_list_key = key
                    data[key] = []
                    continue

                current_list_key = None
                data[key] = ContentProcessor._parse_value(value)

        return data

    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse a single YAML scalar or inline list."""
        if value.startswith('[') and value.endswith(']'):
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [
                ContentProcessor._coerce_scalar(item.strip())
                for item in inner.split(',')
            ]
        return ContentProcessor._coerce_scalar(value)

    @staticmethod
    def _coerce_scalar(value: str) -> Any:
        """Coerce a YAML scalar string to a Python value."""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            return value[1:-1]
        lowered = value.lower()
        if lowered in ('true', 'yes'):
            return True
        if lowered in ('false', 'no'):
            return False
        if lowered in ('null', 'none', '~'):
            return None
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    @staticmethod
    def _resolve_title(frontmatter: Dict[str, Any], body: str, filename: str) -> str:
        """Resolve the note title: frontmatter > first H1 > filename."""
        if frontmatter.get('title'):
            return str(frontmatter['title'])
        h1 = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
        if h1:
            return h1.group(1)
        return Path(filename).stem

    @staticmethod
    def _collect_tags(frontmatter: Dict[str, Any], body: str) -> List[str]:
        """Collect tags from frontmatter and inline #tags in the body."""
        tags: List[str] = []

        fm_tags = frontmatter.get('tags', [])
        if isinstance(fm_tags, list):
            tags.extend(str(t) for t in fm_tags)
        elif isinstance(fm_tags, str):
            tags.append(fm_tags)

        for tag in INLINE_TAG_RE.findall(body):
            # Skip heading markers and Obsidian embeds
            if tag not in tags:
                tags.append(tag)

        return tags

    @staticmethod
    def _extract_wikilinks(body: str) -> List[str]:
        """Extract unique wikilink targets (without alias or heading part)."""
        seen: List[str] = []
        for target, _alias in WIKILINK_RE.findall(body):
            target = target.strip()
            if target and target not in seen:
                seen.append(target)
        return seen

    @staticmethod
    def _extract_headings(body: str) -> List[str]:
        """Extract heading text in document order."""
        return [m.group(2) for m in HEADING_RE.finditer(body)]

    @staticmethod
    def _extract_aliases(frontmatter: Dict[str, Any]) -> List[str]:
        """Extract aliases from frontmatter."""
        aliases = frontmatter.get('aliases', [])
        if isinstance(aliases, list):
            return [str(a) for a in aliases]
        if isinstance(aliases, str):
            return [aliases]
        return []

    @staticmethod
    def _frontmatter_datetime(frontmatter: Dict[str, Any], key: str) -> Optional[datetime]:
        """Parse a frontmatter date/datetime value if present."""
        value = frontmatter.get(key)
        if not value or not isinstance(value, str):
            return None
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
