#!/usr/bin/env python3
"""
Dynamic Content-Aware Chunking Service

Automatically adjusts chunk size and strategy based on content type.
Optimizes embedding quality by tailoring chunking to document structure.

Features:
- Content-type detection (code, text, markdown, structured data)
- Adaptive chunk sizing for different content types
- Semantic-aware chunk boundaries
- Recursive chunking with overlap handling
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


# NLTK for sentence boundary detection (optional)
try:
    import nltk
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False

# Web framework for service endpoints (Phase 4 microservice)
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger('DynamicChunkingService')


class ContentType(Enum):
    """Supported content types."""
    CODE = "code"
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    XML = "xml"
    SQL = "sql"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass
class Chunk:
    """Represents a document chunk."""
    content: str
    start_char: int
    end_char: int
    chunk_index: int
    total_chunks: int
    content_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks,
            'content_type': self.content_type,
            'metadata': self.metadata,
        }


class ContentTypeDetector:
    """Detects content type from file extension and content analysis."""
    
    # File extensions mapped to content types
    EXTENSION_MAP = {
        '.py': ContentType.CODE,
        '.js': ContentType.CODE,
        '.ts': ContentType.CODE,
        '.java': ContentType.CODE,
        '.go': ContentType.CODE,
        '.rs': ContentType.CODE,
        '.cpp': ContentType.CODE,
        '.c': ContentType.CODE,
        '.h': ContentType.CODE,
        '.rb': ContentType.CODE,
        '.php': ContentType.CODE,
        '.swift': ContentType.CODE,
        '.kt': ContentType.CODE,
        
        '.md': ContentType.MARKDOWN,
        '.markdown': ContentType.MARKDOWN,
        
        '.json': ContentType.JSON,
        '.yaml': ContentType.CONFIG,
        '.yml': ContentType.CONFIG,
        '.toml': ContentType.CONFIG,
        '.ini': ContentType.CONFIG,
        '.conf': ContentType.CONFIG,
        '.cfg': ContentType.CONFIG,
        '.env': ContentType.CONFIG,
        
        '.html': ContentType.HTML,
        '.htm': ContentType.HTML,
        
        '.xml': ContentType.XML,
        
        '.sql': ContentType.SQL,
        
        '.txt': ContentType.TEXT,
    }
    
    # Code patterns for detection
    CODE_PATTERNS = [
        r'\b(function|def|class|import|from|const|let|var)\b',
        r'\{[^}]*\}',  # Braces
        r'<[a-zA-Z][^>]*>',  # HTML-like tags
        r'[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)',  # Function calls
    ]
    
    def __init__(self):
        self._compiled_patterns = [
            (pattern, re.compile(pattern)) for pattern in self.CODE_PATTERNS
        ]
    
    def detect_from_filename(self, filename: str) -> ContentType:
        """Detect content type from file extension."""
        ext = Path(filename).suffix.lower()
        return self.EXTENSION_MAP.get(ext, ContentType.UNKNOWN)
    
    def detect_from_content(self, content: str) -> ContentType:
        """Detect content type by analyzing content structure."""
        # Empty content
        if not content or len(content.strip()) == 0:
            return ContentType.TEXT
        
        # Try to parse as JSON
        try:
            json.loads(content)
            return ContentType.JSON
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Check for XML
        if re.match(r'^\s*<[^>]+>', content.strip()):
            return ContentType.XML
        
        # Check for HTML
        if re.search(r'<[a-zA-Z][^>]*>[^<]*</[a-zA-Z]+>', content):
            return ContentType.HTML
        
        # Check for SQL
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE']
        if any(kw in content.upper() for kw in sql_keywords):
            return ContentType.SQL
        
        # Check for code patterns
        for _, pattern in self._compiled_patterns:
            if pattern.search(content):
                return ContentType.CODE
        
        # Default to text
        return ContentType.TEXT
    
    def detect(self, filename: str, content: str) -> Tuple[ContentType, Dict[str, Any]]:
        """Detect content type from filename and content."""
        ext_type = self.detect_from_filename(filename)
        
        if ext_type != ContentType.UNKNOWN:
            return ext_type, {'source': 'filename_extension'}
        
        content_type = self.detect_from_content(content)
        
        return content_type, {
            'source': 'content_analysis',
            'detected_type': content_type.value,
        }


class ContentChunker:
    """Chunking strategies for different content types."""
    
    # Chunk sizes by content type (in characters)
    DEFAULT_CHUNK_SIZES = {
        ContentType.CODE: 500,      # Smaller chunks for code precision
        ContentType.TEXT: 1000,     # Standard text size
        ContentType.MARKDOWN: 800,  # Markdown has structure but needs context
        ContentType.JSON: 2000,     # JSON can be large
        ContentType.HTML: 1500,     # HTML tags add overhead
        ContentType.XML: 1500,      # Similar to HTML
        ContentType.SQL: 600,       # SQL statements need to stay intact
        ContentType.CONFIG: 800,    # Config files need structure
    }
    
    def __init__(
        self,
        default_chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 50,
    ):
        self.default_chunk_size = default_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # NLTK resources for sentence boundary detection
        if NLP_AVAILABLE:
            try:
                nltk.data.find('tokenizers/punkt_tab')
            except LookupError:
                try:
                    nltk.download('punkt_tab', quiet=True)
                except Exception:
                    pass
    
    def chunk_code(
        self,
        content: str,
        max_size: int = None,
        min_size: int = None
    ) -> List[Chunk]:
        """Chunk code with function/class boundary awareness."""
        if max_size is None:
            max_size = self.DEFAULT_CHUNK_SIZES[ContentType.CODE]
        if min_size is None:
            min_size = self.min_chunk_size
        
        chunks = []
        
        # Split by newlines first
        lines = content.split('\n')
        
        current_chunk = []
        current_start = 0
        char_count = 0
        
        for i, line in enumerate(lines):
            line_length = len(line) + 1  # +1 for newline
            
            if char_count + line_length > max_size and current_chunk:
                # Finalize current chunk
                chunk_text = '\n'.join(current_chunk)
                
                # Find function/class boundary if possible
                chunk_text, adjusted_end = self._trim_to_boundary(
                    chunk_text,
                    ['def ', 'class ', 'function ', 'const '],
                    ['}', ']', ')']
                )
                
                chunks.append(Chunk(
                    content=chunk_text,
                    start_char=current_start,
                    end_char=current_start + len(chunk_text),
                    chunk_index=len(chunks),
                    total_chunks=0,  # Will be set later
                    content_type='code',
                ))
                
                # Start new chunk with overlap
                overlap_lines = []
                overlap_size = 0
                
                for j in range(len(current_chunk) - 1, -1, -1):
                    line_overlap = len(current_chunk[j]) + 1
                    if overlap_size + line_overlap > self.chunk_overlap:
                        break
                    overlap_lines.insert(0, current_chunk[j])
                    overlap_size += line_overlap
                
                current_chunk = overlap_lines
                current_start += len('\n'.join(current_chunk)) + 1
                char_count = overlap_size
            
            current_chunk.append(line)
            char_count += line_length
        
        # Final chunk
        if current_chunk:
            chunks.append(Chunk(
                content='\n'.join(current_chunk),
                start_char=current_start,
                end_char=current_start + len('\n'.join(current_chunk)),
                chunk_index=len(chunks),
                total_chunks=0,
                content_type='code',
            ))
        
        # Update totals
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        return chunks
    
    def chunk_text(
        self,
        content: str,
        max_size: int = None,
        min_size: int = None
    ) -> List[Chunk]:
        """Chunk text by sentences or paragraphs."""
        if max_size is None:
            max_size = self.DEFAULT_CHUNK_SIZES[ContentType.TEXT]
        if min_size is None:
            min_size = self.min_chunk_size
        
        chunks = []
        
        # Try to split by paragraphs first
        paragraphs = content.split('\n\n')
        
        current_chunk = []
        char_count = 0
        
        for para in paragraphs:
            para_length = len(para) + 2  # +2 for newlines
            
            if char_count + para_length > max_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                
                chunks.append(Chunk(
                    content=chunk_text,
                    start_char=len('\n\n'.join(chunk_text)) - len(chunk_text) if chunks else 0,
                    end_char=0,  # Will be calculated
                    chunk_index=len(chunks),
                    total_chunks=0,
                    content_type='text',
                ))
                
                # Overlap
                overlap_size = 0
                overlap_paragraphs = []
                
                for p in reversed(current_chunk):
                    if overlap_size + len(p) + 2 > self.chunk_overlap:
                        break
                    overlap_paragraphs.insert(0, p)
                    overlap_size += len(p) + 2
                
                current_chunk = overlap_paragraphs
                char_count = overlap_size
            
            current_chunk.append(para)
            char_count += para_length
        
        # Final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            
            chunks.append(Chunk(
                content=chunk_text,
                start_char=len('\n\n'.join(chunk_text)) - len(chunk_text) if chunks else 0,
                end_char=0,
                chunk_index=len(chunks),
                total_chunks=0,
                content_type='text',
            ))
        
        # Calculate actual positions and update totals
        pos = 0
        for i, chunk in enumerate(chunks):
            chunk.start_char = pos
            chunk.end_char = pos + len(chunk.content)
            pos = chunk.end_char
            chunk.total_chunks = len(chunks)
        
        return chunks
    
    def chunk_markdown(
        self,
        content: str,
        max_size: int = None,
        min_size: int = None
    ) -> List[Chunk]:
        """Chunk markdown with header awareness."""
        if max_size is None:
            max_size = self.DEFAULT_CHUNK_SIZES[ContentType.MARKDOWN]
        if min_size is None:
            min_size = self.min_chunk_size
        
        # Split by headers
        sections = re.split(r'(\n#{1,6}\s+.+)', content)
        
        chunks = []
        current_chunk = ""
        
        for section in sections:
            if not section.strip():
                continue
            
            test_chunk = current_chunk + section
            
            if len(test_chunk) > max_size and current_chunk:
                chunks.append(Chunk(
                    content=current_chunk,
                    start_char=0,
                    end_char=len(current_chunk),
                    chunk_index=len(chunks),
                    total_chunks=0,
                    content_type='markdown',
                ))
                
                # Overlap with last header
                overlap_match = re.search(r'(\n#{1,6}\s+.+)$', current_chunk)
                if overlap_match:
                    current_chunk = overlap_match.group(1) + section
                else:
                    current_chunk = section
            else:
                current_chunk = test_chunk
        
        # Final chunk
        if current_chunk:
            chunks.append(Chunk(
                content=current_chunk,
                start_char=0,
                end_char=len(current_chunk),
                chunk_index=len(chunks),
                total_chunks=0,
                content_type='markdown',
            ))
        
        # Update totals
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            if i < len(chunks) - 1:
                next_start = chunks[i + 1].start_char if i + 1 < total else len(content)
                chunk.end_char = min(chunk.start_char + len(chunk.content), next_start)
            chunk.total_chunks = total
        
        return chunks
    
    def _trim_to_boundary(
        self,
        text: str,
        start_patterns: List[str],
        end_patterns: List[str]
    ) -> Tuple[str, int]:
        """Trim text to nearest structural boundary."""
        # Try to find a good ending point
        for pattern in reversed(end_patterns):
            idx = text.rfind(pattern)
            if idx > len(text) * 0.3:  # Only trim from last 70% of chunk
                return text[:idx + 1], idx + 1
        
        # Try to find a good starting point
        for pattern in start_patterns:
            idx = text.find(pattern)
            if idx > 0 and idx < len(text) * 0.7:  # Only trim from first 70%
                return text[idx:], idx
        
        return text, len(text)


class DynamicChunkingService:
    """Main service for dynamic content-aware chunking."""
    
    def __init__(
        self,
        default_chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.default_chunk_size = default_chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.detector = ContentTypeDetector()
        self.chunker = ContentChunker(
            default_chunk_size=default_chunk_size,
            chunk_overlap=chunk_overlap,
        )
        
        # Statistics
        self.stats = {
            'total_chunks': 0,
            'chunks_by_type': {},
            'avg_chunk_size': 0,
        }
    
    def chunk_content(
        self,
        content: str,
        filename: str = None,
        content_type: ContentType = None,
        force_type: bool = False,
    ) -> List[Chunk]:
        """Chunk content using appropriate strategy."""
        # Detect content type
        if not content_type or not force_type:
            detected_type, detection_info = self.detector.detect(
                filename or '', content
            )
            content_type = detected_type
        
        # Select chunking method
        chunk_methods = {
            ContentType.CODE: self.chunker.chunk_code,
            ContentType.TEXT: self.chunker.chunk_text,
            ContentType.MARKDOWN: self.chunker.chunk_markdown,
            ContentType.JSON: lambda c, **kw: [Chunk(
                content=c[:1000], start_char=0, end_char=min(1000, len(c)),
                chunk_index=0, total_chunks=1, content_type='json'
            )],
            ContentType.HTML: self.chunker.chunk_text,
            ContentType.XML: self.chunker.chunk_text,
            ContentType.SQL: lambda c, **kw: [Chunk(
                content=c[:800], start_char=0, end_char=min(800, len(c)),
                chunk_index=0, total_chunks=1, content_type='sql'
            )],
            ContentType.CONFIG: self.chunker.chunk_text,
        }
        
        method = chunk_methods.get(content_type, self.chunker.chunk_text)
        
        # Chunk
        chunks = method(content)
        
        # Update statistics
        type_str = content_type.value if content_type else 'unknown'
        self.stats['total_chunks'] += len(chunks)
        
        if type_str not in self.stats['chunks_by_type']:
            self.stats['chunks_by_type'][type_str] = 0
        self.stats['chunks_by_type'][type_str] += len(chunks)
        
        total_size = sum(len(c.content) for c in chunks)
        self.stats['avg_chunk_size'] = (
            (self.stats['avg_chunk_size'] * (self.stats['total_chunks'] - len(chunks)) + total_size)
            / max(self.stats['total_chunks'], 1)
        )
        
        return chunks
    
    def chunk_file(
        self,
        filepath: str,
        content_type: ContentType = None,
    ) -> List[Chunk]:
        """Read and chunk a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.chunk_content(content, filename=filepath, content_type=content_type)
        
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return []
    
    def chunk_directory(
        self,
        directory: str,
        extensions: List[str] = None,
    ) -> Dict[str, List[Chunk]]:
        """Chunk all files in a directory."""
        results = {}
        
        dir_path = Path(directory)
        
        for filepath in dir_path.rglob('*'):
            if filepath.is_file():
                ext = filepath.suffix.lower()
                
                # Filter by extensions if specified
                if extensions and ext not in extensions:
                    continue
                
                chunks = self.chunk_file(str(filepath))
                
                if chunks:
                    results[str(filepath)] = chunks
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get chunking statistics."""
        total = sum(self.stats['chunks_by_type'].values())
        
        return {
            **self.stats,
            'total_files': len(self.stats['chunks_by_type']),
            'avg_chunk_size_rounded': round(self.stats['avg_chunk_size'], 2),
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health and dependencies."""
        try:
            # Check if required models are available
            detector_available = self.detector is not None
            
            return {
                'status': 'healthy',
                'service': 'DynamicChunkingService',
                'timestamp': datetime.utcnow().isoformat(),
                'dependencies': {
                    'content_detector': {
                        'status': 'available' if detector_available else 'unavailable',
                    },
                },
                'metadata': {
                    'chunk_size': self.default_chunk_size,
                    'chunk_overlap': self.chunk_overlap,
                    'statistics': self.get_statistics(),
                },
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'DynamicChunkingService',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'dependencies': {
                    'content_detector': {
                        'status': 'error',
                        'error': str(e),
                    },
                },
            }


# =============================================================================
# FastAPI application (Phase 4 microservice)
# =============================================================================

service = DynamicChunkingService()

app = FastAPI(
    title="Dynamic Chunking Service",
    description="Content-aware adaptive chunking for the AI Memory Pipeline",
    version="1.0.0"
)


class ChunkRequest(BaseModel):
    content: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    force_type: bool = False


@app.get("/health")
async def health():
    """Health check endpoint for container orchestration."""
    return service.health_check()


@app.post("/chunk")
async def chunk_document(request: ChunkRequest):
    """Chunk a document using the content-aware strategy."""
    ctype = None
    if request.content_type:
        try:
            ctype = ContentType(request.content_type)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Unknown content type: {request.content_type}"},
            )
    chunks = service.chunk_content(
        request.content,
        filename=request.filename,
        content_type=ctype,
        force_type=request.force_type,
    )
    return {
        "chunks": [c.to_dict() for c in chunks],
        "total_chunks": len(chunks),
    }


@app.get("/statistics")
async def statistics():
    """Get chunking statistics."""
    return service.get_statistics()


def main():
    """Main entry point for dynamic chunking."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dynamic Content-Aware Chunking')
    parser.add_argument('--file', type=str, help='File to chunk')
    parser.add_argument('--directory', type=str, help='Directory to chunk recursively')
    parser.add_argument('--extensions', type=str, help='Comma-separated extensions to process')
    parser.add_argument('--output', type=str, help='Output file for chunks (JSON)')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')
    
    args = parser.parse_args()
    
    service = DynamicChunkingService(
        default_chunk_size=1000,
        chunk_overlap=200,
    )
    
    if args.extensions:
        extensions = [ext.strip() for ext in args.extensions.split(',')]
    else:
        extensions = None
    
    if args.file:
        chunks = service.chunk_file(args.file)
        
        print(f"=== Chunking Results for: {args.file} ===")
        print(f"Total chunks: {len(chunks)}")
        
        for i, chunk in enumerate(chunks[:5]):  # Show first 5
            preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
            print(f"\n--- Chunk {i+1} ({chunk.content_type}) ---")
            print(preview)
        
        if args.output:
            output_data = {
                'file': args.file,
                'chunks': [c.to_dict() for c in chunks],
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"\nChunks saved to {args.output}")
    
    elif args.directory:
        results = service.chunk_directory(args.directory, extensions)
        
        total_chunks = sum(len(chunks) for chunks in results.values())
        print(f"=== Chunking Results ===")
        print(f"Directory: {args.directory}")
        print(f"Files processed: {len(results)}")
        print(f"Total chunks: {total_chunks}")
        
        if args.stats:
            stats = service.get_statistics()
            print("\n=== Statistics ===")
            print(json.dumps(stats, indent=2))
    
    else:
        # Demo
        demo_text = """
        This is a demonstration of the dynamic chunking service.
        The service automatically detects content types and applies appropriate chunking strategies.

        For code files, it respects function and class boundaries.
        For text documents, it uses sentence-level chunking.
        For markdown, it preserves header structure.

        You can use this service to preprocess your documents before embedding them.
        """
        
        print("=== Dynamic Chunking Demo ===\n")
        chunks = service.chunk_content(demo_text)
        
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i+1} (type: {chunk.content_type}, size: {len(chunk.content)}):")
            print(f"  {chunk.content[:80]}...")
            print()


if __name__ == '__main__':
    main()