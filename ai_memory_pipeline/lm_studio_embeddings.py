"""
LM Studio embedding client for AI Memory Pipeline.

This module provides a wrapper around the LM Studio API
to generate embeddings using remote LLM inference.
"""

import requests
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

class LMStudioEmbedder:
    """
    A class for generating embeddings using LM Studio's local API.
    
    Connects to a running LM Studio instance and uses its embedding endpoint
    to generate vector representations of text.
    """

    def __init__(self, host: str = "localhost", port: int = 1234, model_id: Optional[str] = None):
        """
        Initialize the LM Studio embedder.

        Args:
            host (str): LM Studio server hostname
            port (int): LM Studio server port
            model_id (Optional[str]): Specific model ID to use for embeddings. If None, uses 'text-embedding-qwen3-embedding-8b'.
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        # Default to Qwen3 embedding model if no model_id specified
        self.model_id = model_id or "text-embedding-qwen3-embedding-8b"
        logger.info(f"Initialized LM Studio embedder at {self.base_url} with model {self.model_id}")

    def _get_model(self) -> Optional[str]:
        """Get the currently loaded model in LM Studio."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                if models:
                    # Use specified model or first available
                    if self.model_id:
                        for m in models:
                            if m.get("id") == self.model_id:
                                return m.get("id")
                    return models[0].get("id")
        except Exception as e:
            logger.warning(f"Failed to get model from LM Studio: {e}")
        return None

    def _check_embeddings_endpoint(self) -> bool:
        """Check if the embeddings endpoint is available."""
        try:
            # Try to get the model info
            model_id = self._get_model()
            if model_id:
                logger.info(f"LM Studio model loaded: {model_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to check embeddings endpoint: {e}")
        return False

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using LM Studio.

        Args:
            texts (List[str]): List of text strings to embed

        Returns:
            List[List[float]]: List of embedding vectors
        """
        if not texts:
            return []

        # Check endpoint availability
        if not self._check_embeddings_endpoint():
            raise RuntimeError("LM Studio embeddings endpoint not available")

        embeddings = []
        for i, text in enumerate(texts):
            try:
                # LM Studio uses OpenAI-compatible API
                response = requests.post(
                    f"{self.base_url}/v1/embeddings",
                    json={
                        "model": self._get_model(),
                        "input": text,
                        "encoding_format": "float"
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result.get("data", [])[0].get("embedding", [])
                    embeddings.append(embedding)
                    logger.debug(f"Generated embedding for text {i+1}/{len(texts)} (dim: {len(embedding)})")
                else:
                    logger.error(f"Failed to generate embedding for text {i+1}: {response.text}")
                    raise RuntimeError(f"Embedding API returned status {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error generating embedding for text {i+1}: {e}")
                raise

        return embeddings

    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.

        Args:
            text (str): Text string to embed

        Returns:
            List[float]: Embedding vector
        """
        results = self.generate_embeddings([text])
        return results[0] if results else []
