#!/usr/bin/env python3
"""Verify the ingestion results in Qdrant."""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_memory_pipeline import QdrantManager

def main():
    q = QdrantManager()
    
    # Get collection info
    info = q.client.get_collection('aimemory_docs')
    print(f"Collection: aimemory_docs")
    print(f"  Vectors count: {info.vectors_count}")
    print(f"  Indexed vectors count: {info.indexed_vectors_count}")
    print(f"  Payload schema fields: {len(info.payload_schema)}")
    
    # Get sample payloads
    points, next_page = q.client.scroll('aimemory_docs', limit=5, with_payload=True)
    
    print(f"\nSample ingested documents:")
    for p in points:
        print(f"  ID: {p.id}")
        source = p.payload.get('source_file', 'N/A') if hasattr(p, 'payload') and p.payload else 'N/A'
        chunk_idx = p.payload.get('chunk_index', 'N/A') if hasattr(p, 'payload') and p.payload else 'N/A'
        total_chunks = p.payload.get('total_chunks', 'N/A') if hasattr(p, 'payload') and p.payload else 'N/A'
        preview = p.payload.get('content_preview', '')[:80] if hasattr(p, 'payload') and p.payload else ''
        content = p.payload.get('content', '')[:50] if hasattr(p, 'payload') and p.payload else ''
        
        print(f"    Source: {source}")
        print(f"    Chunk: {chunk_idx} / {total_chunks}")
        print(f"    Preview: {preview}...")
        print(f"    Content sample: {content}...")
    
    # Count by source file
    from collections import Counter
    sources = Counter(p.payload.get('source_file', 'unknown') for p in points)
    print(f"\nIngestion breakdown:")
    for source, count in sources.items():
        print(f"  {source}: {count} chunks")

if __name__ == "__main__":
    main()
