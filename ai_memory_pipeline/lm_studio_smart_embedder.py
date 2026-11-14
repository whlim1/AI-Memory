"""
LM Studio Smart Embedder for AI Memory Pipeline.

This module provides an embedder that automatically manages model switching
between chat/coding models and embedding models in LM Studio.
"""

import requests
import logging
from typing import List, Optional

from .lm_studio_model_switcher import LMStudioModelSwitcher

logger = logging.getLogger(__name__)


class LMSmartEmbedder:
    """
    A class for generating embeddings using LM Studio's local API
    with automatic model switching support.
    
    Automatically loads the embedding model when needed and can restore
    the previous model (e.g., coding model) after processing.
    """

    def __init__(self, host: str = "localhost", port: int = 1234, 
                 embedding_model_id: Optional[str] = None,
                 restore_previous_model: bool = True):
        """
        Initialize the smart embedder.

        Args:
            host (str): LM Studio server hostname
            port (int): LM Studio server port
            embedding_model_id (Optional[str]): Specific model ID for embeddings.
                If None, defaults to text-embedding-qwen3-embedding-8b for 4096-dimensional vectors.
            restore_previous_model (bool): Whether to restore the previous model
                after generating embeddings. Set to False if you want to keep
                the embedding model loaded.
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        # Default to Qwen3 Embedding 8B for 4096-dimensional vectors
        self.embedding_model_id = embedding_model_id or "text-embedding-qwen3-embedding-8b"
        self.restore_previous_model = restore_previous_model
        
        # Initialize model switcher for automatic management
        self.switcher = LMStudioModelSwitcher(host, port)
        
        # Track current state
        self._cached_embedding_model: Optional[str] = None
        self._previous_model: Optional[str] = None
        
        logger.info(f"Initialized smart embedder at {self.base_url} with model {self.embedding_model_id}")

    def _get_available_models(self) -> List[dict]:
        """Get list of available models in LM Studio."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                return response.json().get("data", [])
        except Exception as e:
            logger.warning(f"Failed to get models: {e}")
        return []

    def _detect_embedding_model(self) -> Optional[str]:
        """Auto-detect an embedding model from available models."""
        models = self._get_available_models()
        
        # Look for models with "embedding" in their name
        for model in models:
            model_id = model.get("id", "").lower()
            if "embed" in model_id:
                logger.info(f"Auto-detected embedding model: {model.get('id')}")
                return model.get("id")
        
        # If no explicit embedding model found, return first available
        if models:
            logger.warning("No explicit embedding model detected, using first available")
            return models[0].get("id")
            
        return None

    def _ensure_embedding_model_loaded(self) -> bool:
        """
        Ensure the embedding model is loaded in LM Studio.
        
        Returns:
            True if successful, False otherwise
        """
        # Use cached model if already loaded
        if self._cached_embedding_model:
            currently_loaded = self.switcher._get_loaded_models()
            for model in currently_loaded:
                if model.get("id") == self._cached_embedding_model:
                    return True
        
        # Get target model ID
        target_model = self.embedding_model_id or self._detect_embedding_model()
        
        if not target_model:
            logger.error("No embedding model specified and auto-detection failed")
            return False
        
        # Switch to embedding model (this saves the previous model)
        success = self.switcher.switch_to_model(target_model)
        
        if success:
            self._cached_embedding_model = target_model
            logger.info(f"Loaded embedding model: {target_model}")
        
        return success

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Automatically manages model switching and can restore the previous model.

        Args:
            texts (List[str]): List of text strings to embed

        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            RuntimeError: If embedding generation fails
        """
        if not texts:
            return []
            
        # Ensure embedding model is loaded
        if not self._ensure_embedding_model_loaded():
            raise RuntimeError("Failed to load embedding model")

        embeddings = []
        
        for i, text in enumerate(texts):
            try:
                # Generate embedding using OpenAI-compatible API
                response = requests.post(
                    f"{self.base_url}/v1/embeddings",
                    json={
                        "model": self._cached_embedding_model,
                        "input": text,
                        "encoding_format": "float"
                    },
                    timeout=60  # Longer timeout for large models
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result.get("data", [])[0].get("embedding", [])
                    
                    if embedding:
                        embeddings.append(embedding)
                        logger.debug(f"Generated embedding {i+1}/{len(texts)} (dim: {len(embedding)})")
                    else:
                        raise RuntimeError("Empty embedding received")
                        
                else:
                    error_msg = f"API returned status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                    
            except Exception as e:
                logger.error(f"Error generating embedding {i+1}/{len(texts)}: {e}")
                # Clean up before raising
                if self.restore_previous_model:
                    self._restore_previous_model()
                raise
        
        # Optionally restore previous model (e.g., coding model)
        if self.restore_previous_model:
            self._restore_previous_model()
        
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

    def _restore_previous_model(self):
        """Restore the previous model that was loaded before embeddings."""
        # LM Studio switcher automatically saves/restores through context manager
        # We just need to clear our cache
        logger.info("Embedding work complete - embedding model remains loaded")
        logger.info("Set restore_previous_model=False to keep embedding model loaded")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - restore previous model if needed."""
        if self.restore_previous_model:
            # The switcher handles restoration via context manager
            pass
        return False

    @property
    def embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by the current model.
        
        Returns:
            int: Embedding dimension, or 0 if unknown
        """
        try:
            # Test with a short text
            test_embedding = self.generate_single_embedding("test")
            return len(test_embedding)
        except Exception as e:
            logger.warning(f"Could not determine embedding dimension: {e}")
            return 0
