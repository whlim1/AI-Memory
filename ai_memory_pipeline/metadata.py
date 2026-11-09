"""
Metadata handling functionality for AI Memory Pipeline.

This module provides functions and classes for managing document metadata,
including extraction, storage, and retrieval operations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

class DocumentMetadata:
    """
    Class to represent document metadata.
    
    Stores information about documents including source, creation time,
    processing status, and custom attributes.
    """

    def __init__(self, 
                 doc_id: str = None,
                 title: str = '',
                 author: str = '',
                 created_at: datetime = None,
                 updated_at: datetime = None,
                 source: str = '',
                 tags: List[str] = None,
                 custom_fields: Dict[str, Any] = None):
        """
        Initialize document metadata.

        Args:
            doc_id (str): Unique identifier for the document
            title (str): Document title
            author (str): Author of the document
            created_at (datetime): Creation timestamp
            updated_at (datetime): Last update timestamp
            source (str): Source or origin of the document
            tags (List[str]): List of tags associated with the document
            custom_fields (Dict[str, Any]): Custom metadata fields
        """
        self.doc_id = doc_id or self._generate_id()
        self.title = title
        self.author = author
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.source = source
        self.tags = tags or []
        self.custom_fields = custom_fields or {}

    def _generate_id(self) -> str:
        """
        Generate a unique ID for the document.

        Returns:
            str: Generated document ID
        """
        timestamp = str(datetime.now().timestamp())
        return hashlib.md5(timestamp.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata object to dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of metadata
        """
        return {
            'doc_id': self.doc_id,
            'title': self.title,
            'author': self.author,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'source': self.source,
            'tags': self.tags,
            'custom_fields': self.custom_fields
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """
        Create metadata object from dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing metadata

        Returns:
            DocumentMetadata: New metadata object
        """
        # Convert ISO format strings back to datetime objects
        created_at = datetime.fromisoformat(data['created_at']) if 'created_at' in data else None
        updated_at = datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else None
        
        return cls(
            doc_id=data.get('doc_id'),
            title=data.get('title', ''),
            author=data.get('author', ''),
            created_at=created_at,
            updated_at=updated_at,
            source=data.get('source', ''),
            tags=data.get('tags', []),
            custom_fields=data.get('custom_fields', {})
        )

    def update(self, **kwargs) -> None:
        """
        Update metadata fields.

        Args:
            **kwargs: Fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the document.

        Args:
            tag (str): Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """
        Remove a tag from the document.

        Args:
            tag (str): Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)

    def add_custom_field(self, key: str, value: Any) -> None:
        """
        Add a custom field.

        Args:
            key (str): Field name
            value (Any): Field value
        """
        self.custom_fields[key] = value

    def remove_custom_field(self, key: str) -> None:
        """
        Remove a custom field.

        Args:
            key (str): Field name to remove
        """
        if key in self.custom_fields:
            del self.custom_fields[key]


def extract_metadata_from_text(text: str, doc_id: str = None) -> DocumentMetadata:
    """
    Extract basic metadata from text content.

    Args:
        text (str): Text to analyze for metadata
        doc_id (str): Optional document ID

    Returns:
        DocumentMetadata: Extracted metadata object
    """
    # Simple extraction - in a real implementation, this would be more sophisticated
    title = "Untitled Document"
    author = "Unknown Author"
    
    # Try to extract basic information from text (this is simplified)
    if text:
        lines = text.split('\n')
        if len(lines) > 0 and not lines[0].strip().startswith('#'):
            title = lines[0][:50] + '...' if len(lines[0]) > 50 else lines[0]
            
    return DocumentMetadata(
        doc_id=doc_id,
        title=title,
        author=author
    )


def merge_metadata(base: DocumentMetadata, additional: Dict[str, Any]) -> DocumentMetadata:
    """
    Merge additional metadata with base metadata.

    Args:
        base (DocumentMetadata): Base metadata object
        additional (Dict[str, Any]): Additional metadata to merge

    Returns:
        DocumentMetadata: Merged metadata object
    """
    # Create a copy of the base metadata
    merged = DocumentMetadata(
        doc_id=base.doc_id,
        title=base.title,
        author=base.author,
        created_at=base.created_at,
        updated_at=base.updated_at,
        source=base.source,
        tags=base.tags.copy(),
        custom_fields=base.custom_fields.copy()
    )
    
    # Update with additional fields
    for key, value in additional.items():
        if hasattr(merged, key):
            setattr(merged, key, value)
    
    return merged

# Example usage and testing
if __name__ == "__main__":
    # Create a sample metadata object
    meta = DocumentMetadata(
        title="Test Document",
        author="John Doe",
        source="test-source"
    )
    
    print("Document Metadata:")
    print(f"ID: {meta.doc_id}")
    print(f"Title: {meta.title}")
    print(f"Author: {meta.author}")
    print(f"Created: {meta.created_at}")
    print(f"Source: {meta.source}")
    
    # Test conversion to dict
    meta_dict = meta.to_dict()
    print("\nAs dictionary:")
    for key, value in meta_dict.items():
        print(f"  {key}: {value}")
    
    # Test creation from dict
    new_meta = DocumentMetadata.from_dict(meta_dict)
    print(f"\nCreated from dict - ID: {new_meta.doc_id}")
    
    # Test adding tags and custom fields
    meta.add_tag("important")
    meta.add_tag("test")
    meta.add_custom_field("category", "documentation")
    meta.add_custom_field("priority", "high")
    
    print(f"\nAfter updates:")
    print(f"Tags: {meta.tags}")
    print(f"Custom Fields: {meta.custom_fields}")