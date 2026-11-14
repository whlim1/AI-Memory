"""
Qdrant client integration for AI Memory Pipeline.

This module provides a wrapper around the Qdrant vector database client
to handle document indexing, retrieval, and management operations.
"""

from typing import List, Dict, Any, Optional, Union
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Filter, FieldCondition, MatchValue, PointStruct
import logging

logger = logging.getLogger(__name__)

class QdrantManager:
    """
    A class for managing interactions with the Qdrant vector database.
    
    Provides methods for indexing documents, searching vectors,
    and managing collections in Qdrant.
    """

    def __init__(self, host: str = None, port: int = 6333, api_key: Optional[str] = None, url: str = None):
        """
        Initialize the Qdrant client manager.

        Args:
            host (str): Qdrant server hostname (deprecated, use url instead)
            port (int): Qdrant server port
            api_key (Optional[str]): API key for authentication (if required)
            url (Optional[str]): Full URL to Qdrant server (e.g., "http://localhost:6333")
        """
        # Support both url parameter and host/port combination
        if url:
            self.url = url
            self.host = None
            self.port = None
            # Initialize the actual Qdrant client with URL
            if api_key:
                self.client = QdrantClient(url=url, api_key=api_key)
            else:
                self.client = QdrantClient(url=url)
        else:
            self.host = host or "localhost"
            self.port = port
            self.api_key = api_key  # Store for tests
            self.url = f"http://{self.host}:{self.port}"
            # Initialize the actual Qdrant client with host/port
            if api_key:
                self.client = QdrantClient(host=self.host, port=self.port, api_key=api_key)
            else:
                self.client = QdrantClient(host=self.host, port=self.port)
            
        logger.info(f"Connected to Qdrant at {self.url}")

    def create_collection(self, collection_name: str, vector_size: int = 1536, distance: str = "Cosine") -> bool:
        """
        Create a new collection in Qdrant.

        Args:
            collection_name (str): Name of the collection to create
            vector_size (int): Size of vectors in the collection (default: 1536 for OpenAI ada-002)
            distance (str): Distance metric for similarity search

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance)
            )
            logger.info(f"Created collection '{collection_name}' with vector size {vector_size}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            return False

    def index_document(self, 
                      collection_name: str, 
                      document_id: str,
                      content_vector: List[float],
                      metadata: Dict[str, Any] = None) -> bool:
        """
        Index a single document in Qdrant.

        Args:
            collection_name (str): Name of the collection
            document_id (str): Unique identifier for the document
            content_vector (List[float]): Vector representation of the document content
            metadata (Dict[str, Any]): Additional metadata to store with the document

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            point = PointStruct(
                id=document_id,
                vector=content_vector,
                payload=metadata or {}
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"Indexed document '{document_id}' in collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to index document '{document_id}': {e}")
            return False

    def search_similar(self, 
                      collection_name: str,
                      query_vector: List[float],
                      limit: int = 10,
                      filter_conditions: Optional[Filter] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents in Qdrant.

        Args:
            collection_name (str): Name of the collection to search
            query_vector (List[float]): Vector representation of the query
            limit (int): Maximum number of results to return
            filter_conditions (Optional[Filter]): Optional filters to apply

        Returns:
            List[Dict[str, Any]]: List of matching documents with scores
        """
        try:
            # Use search which is available in qdrant-client 1.0+
            search_kwargs = {
                "collection_name": collection_name,
                "query_vector": query_vector,
                "limit": limit,
                "with_payload": True,
                "with_vectors": False
            }
            if filter_conditions is not None:
                search_kwargs["filter"] = filter_conditions
            
            results = self.client.search(**search_kwargs)
            
            # Convert Qdrant results to a more usable format
            return [
                {
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload or {}
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def upsert_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> bool:
        """
        Batch upsert multiple documents into Qdrant.

        Args:
            collection_name (str): Name of the collection
            documents (List[Dict[str, Any]]): List of document dictionaries with 'id', 'text', and 'metadata' keys

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Import LM Studio embedder
            from ai_memory_pipeline.lm_studio_embeddings import LMStudioEmbedder
            
            # Initialize LM Studio embedder
            embedder = LMStudioEmbedder(host="localhost", port=1234)
            
            ids = []
            vectors = []
            payloads = []
            
            for doc in documents:
                text = doc.get('text', '')
                metadata = doc.get('metadata', {})
                
                # Generate embedding for the text using LM Studio
                vector = embedder.generate_single_embedding(text)
                
                ids.append(doc['id'])
                vectors.append(vector)
                payloads.append({
                    **metadata,
                    'content': text
                })
            
            # Use Batch model to properly format the data
            from qdrant_client.http.models import Batch
            batch = Batch(ids=ids, vectors=vectors, payloads=payloads)
            
            # Use the public upsert method with Batch object
            self.client.upsert(
                collection_name=collection_name,
                points=batch
            )
            
            logger.info(f"Upserted {len(documents)} documents to collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            return False

    def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by ID.

        Args:
            collection_name (str): Name of the collection
            document_id (str): Unique identifier for the document

        Returns:
            Optional[Dict[str, Any]]: Document payload or None if not found
        """
        try:
            result = self.client.get_points(
                collection_name=collection_name,
                ids=[document_id]
            )
            
            if result and len(result) > 0:
                return {
                    'id': document_id,
                    'payload': result[0].payload or {}
                }
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve document '{document_id}': {e}")
            return None

    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        Delete a document from the collection.

        Args:
            collection_name (str): Name of the collection
            document_id (str): Unique identifier for the document

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=[document_id]
            )
            logger.info(f"Deleted document '{document_id}' from collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document '{document_id}': {e}")
            return False

    def list_collections(self) -> List[str]:
        """
        Get a list of all collections in Qdrant.

        Returns:
            List[str]: Names of all collections
        """
        try:
            collections = self.client.get_collections()
            return [collection.name for collection in collections.collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def health_check(self) -> bool:
        """
        Check if the Qdrant client is healthy and responsive.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Simple check - see if we can get server info
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

# Example usage and testing
if __name__ == "__main__":
    # Initialize Qdrant manager (this would typically be configured via environment variables)
    qdrant = QdrantManager()
    
    print("Qdrant Manager initialized successfully")
    
    # Test health check
    if qdrant.health_check():
        print("Qdrant is healthy and responsive")
    else:
        print("Qdrant connection failed")