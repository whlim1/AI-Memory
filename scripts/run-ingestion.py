#!/usr/bin/env python3
"""
Document Ingestion Pipeline for AI-Memory Project

This script ingests documents from the Bootstrap directory into Qdrant vector database.
It processes Markdown files, chunks them, and stores embeddings for semantic search.
"""

import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_memory_pipeline import QdrantManager, chunk_text, extract_metadata_from_text
from ai_memory_pipeline.lm_studio_smart_embedder import LMSmartEmbedder


def get_file_hash(filepath: str) -> str:
    """Generate a hash for the file content."""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def ingest_document(filepath: Path, qdrant_manager: QdrantManager, collection_name: str) -> dict:
    """
    Ingest a single document into Qdrant.
    
    Args:
        filepath: Path to the document file
        qdrant_manager: QdrantManager instance
        collection_name: Name of the collection to ingest into
        
    Returns:
        dict with ingestion results
    """
    print(f"  Processing: {filepath.name}")
    
    try:
        # Read document content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract metadata
        metadata = extract_metadata_from_text(content)
        
        # Add additional metadata fields
        metadata_dict = {
            **metadata.to_dict(),
            "source_file": filepath.name,
            "source_path": str(filepath),
            "file_hash": get_file_hash(str(filepath)),
            "ingested_at": datetime.now().isoformat(),
            "document_type": "documentation"
        }
        
        # Chunk the document
        chunks = chunk_text(content, max_chunk_size=384)
        
        # Generate embeddings and upsert
        chunk_docs = []
        for i, chunk_content in enumerate(chunks):
            # Create unique integer ID using hash of file hash and chunk index
            combined_hash = hashlib.md5(f"{metadata_dict['file_hash']}_chunk_{i}".encode()).hexdigest()
            chunk_id = int(combined_hash[:8], 16)  # Use first 8 hex chars as int
            
            # Create metadata for this chunk
            chunk_metadata = {
                **metadata_dict,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "content_preview": chunk_content[:100] if chunk_content else "",
                "original_chunk_id": f"{metadata_dict['file_hash']}_chunk_{i}"
            }
            
            chunk_docs.append({
                "id": chunk_id,
                "text": chunk_content,
                "metadata": chunk_metadata
            })
        
        # Upsert all chunks
        qdrant_manager.upsert_documents(collection_name, chunk_docs)
        
        print(f"    ✓ Ingested {len(chunks)} chunks")
        return {
            "status": "success",
            "file": filepath.name,
            "chunks": len(chunks),
            "metadata": metadata_dict
        }
        
    except Exception as e:
        print(f"    ✗ Error: {str(e)}")
        return {
            "status": "error",
            "file": filepath.name,
            "error": str(e)
        }


def main():
    """Main ingestion pipeline."""
    print("=" * 60)
    print("AI-Memory Document Ingestion Pipeline")
    print("=" * 60)
    
    # Configuration
    bootstrap_dir = Path(r"D:\AIPlatform\Bootstrap")
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "aimemory_docs")
    
    print(f"\nConfiguration:")
    print(f"  Bootstrap directory: {bootstrap_dir}")
    print(f"  Collection name: {collection_name}")
    
    # Check if bootstrap directory exists
    if not bootstrap_dir.exists():
        print(f"\n⚠️  Warning: Bootstrap directory not found at {bootstrap_dir}")
        print("Creating a test document for demonstration...")
        
        # Create test document
        test_doc = project_root / "docs" / "test-document.md"
        test_doc.parent.mkdir(exist_ok=True)
        test_doc.write_text("""
# Test Document

This is a test document for the AI-Memory ingestion pipeline.

## Sections

1. Introduction - This document tests chunking functionality
2. Architecture - The system uses Qdrant for vector storage
3. Integration - OpenCode agent retrieves relevant context

## Conclusion

The ingestion pipeline successfully processes markdown documents.
        """)
        bootstrap_dir = test_doc.parent
    
    # Initialize LM Studio smart embedder with automatic model switching
    print("\nVerifying LM Studio connectivity...")
    try:
        lm_embedder = LMSmartEmbedder(host="localhost", port=1234)
        
        # Test the embeddings endpoint - this will automatically switch to embedding model
        test_embedding = lm_embedder.generate_single_embedding("test")
        print(f"✓ LM Studio connected (model: {lm_embedder.embedding_model_id}, dim: {len(test_embedding)})")
    except Exception as e:
        print(f"✗ Failed to connect to LM Studio: {str(e)}")
        print("Please ensure LM Studio is running and the embedding model is loaded.")
        return 1
    
    # Initialize Qdrant manager
    print("\nInitializing Qdrant connection...")
    try:
        qdrant_manager = QdrantManager(
            url=f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', 6333)}"
        )
        print("✓ Connected to Qdrant")
        
        # Ensure collection exists
        collections = qdrant_manager.client.get_collections().collections
        collection_names = [c.name for c in collections]
        if collection_name not in collection_names:
            print(f"Creating collection '{collection_name}'...")
            qdrant_manager.create_collection(collection_name)
        
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {str(e)}")
        return 1
    
    # Find documents to ingest
    print(f"\nSearching for documents in {bootstrap_dir}...")
    md_files = list(bootstrap_dir.glob("*.md"))
    
    if not md_files:
        print("⚠️  No markdown files found. Creating test documents...")
        
        # Create test documentation
        docs_dir = project_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        # Test documentation 1
        (docs_dir / "architecture.md").write_text("""
# AI-Memory Architecture

This document describes the system architecture.

## Components

- Qdrant: Vector database for semantic search
- LM Studio: Local LLM endpoint
- OpenCode: IDE agent integration
- Infisical: Secrets management

## Data Flow

1. Documents are ingested and chunked
2. Embeddings are generated
3. Vectors are stored in Qdrant
4. Agent retrieves relevant context
        """)
        
        # Test documentation 2
        (docs_dir / "ingestion.md").write_text("""
# Document Ingestion Pipeline

This document describes the ingestion process.

## Steps

1. Load documents from source directory
2. Extract metadata
3. Chunk text into manageable pieces
4. Generate embeddings
5. Store in Qdrant vector database

## Configuration

The pipeline reads configuration from environment variables.
        """)
        
        md_files = list(docs_dir.glob("*.md"))
    
    print(f"Found {len(md_files)} markdown files")
    
    # Ingest documents
    results = []
    for filepath in md_files:
        result = ingest_document(filepath, qdrant_manager, collection_name)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("Ingestion Summary")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    
    print(f"\nTotal files processed: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    
    if error_count > 0:
        print("\nFailed files:")
        for r in results:
            if r["status"] == "error":
                print(f"  - {r['file']}: {r.get('error', 'Unknown error')}")
    
    # Verify collection
    print("\nVerifying collection...")
    try:
        collection_info = qdrant_manager.client.get_collection(collection_name)
        print(f"Collection info:")
        print(f"  Name: {collection_name}")
        print(f"  Vectors count: {collection_info.vectors_count}")
        print(f"  Payload schema: {len(collection_info.payload_schema)} fields")
    except Exception as e:
        print(f"Warning: Could not get collection info: {str(e)}")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
