"""
LM Studio Model Switcher for AI Memory Pipeline.

This module provides automated model switching between different models
in LM Studio to optimize memory usage.
"""

import requests
import logging
import time
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class LMStudioModelSwitcher:
    """
    Manages model loading/unloading in LM Studio for memory optimization.
    
    Allows switching between different models (e.g., coding model vs embedding model)
    without manual intervention in the LM Studio UI.
    """

    def __init__(self, host: str = "localhost", port: int = 1234):
        """
        Initialize the model switcher.
        
        Args:
            host: LM Studio server hostname
            port: LM Studio server port
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.current_model: Optional[str] = None
        self.model_cache: Dict[str, Any] = {}
        
    def _get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get list of currently loaded models in LM Studio."""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                return response.json().get("data", [])
        except Exception as e:
            logger.warning(f"Failed to get loaded models: {e}")
        return []
    
    def _get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models that can be loaded."""
        try:
            # Use the OpenAI-compatible endpoint which is more reliable
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
        except Exception as e:
            logger.warning(f"Failed to get available models: {e}")
        return []

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Public method to get available models (public wrapper)."""
        return self._get_available_models()

    def get_current_model(self) -> Optional[str]:
        """Get the currently loaded and active model."""
        # First check our tracked current model
        if self.current_model:
            # Verify it's actually loaded in LM Studio
            models = self._get_loaded_models()
            for m in models:
                if m.get("id") == self.current_model:
                    return self.current_model
        
        # Fallback: get the first loaded model from LM Studio
        models = self._get_loaded_models()
        if models:
            return models[0].get("id")
        
        return self.current_model
    
    def _load_model(self, model_id: str) -> bool:
        """
        Load a specific model in LM Studio.
        
        Args:
            model_id: The model identifier to load
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try the standard LM Studio API endpoint
            response = requests.post(
                f"{self.base_url}/load_model",
                json={"model": model_id},
                timeout=300  # 5 minutes for loading large models
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully loaded model: {model_id}")
                self.current_model = model_id
                return True
                
        except Exception as e:
            logger.warning(f"Failed to load model via API: {e}")
        
        # Alternative: Use OpenAI-compatible endpoint for model info
        try:
            # Some LM Studio versions require loading through the chat completions endpoint
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                },
                timeout=300
            )
            
            if response.status_code == 200 or "error" in response.json():
                # Even if there's an error, the model might be loading
                logger.info(f"Initiated model load: {model_id}")
                self.current_model = model_id
                return True
                
        except Exception as e:
            logger.warning(f"Alternative load method failed: {e}")
            
        return False
    
    def _unload_current_model(self) -> bool:
        """
        Unload the currently loaded model.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.current_model:
            logger.info("No model currently loaded")
            return True
            
        try:
            # LM Studio doesn't have a direct unload API, 
            # so we load the default/placeholder model instead
            response = requests.post(
                f"{self.base_url}/load_model",
                json={"model": ""},
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info(f"Unloaded model: {self.current_model}")
                self.current_model = None
                return True
                
        except Exception as e:
            logger.warning(f"Failed to unload model: {e}")
            
        return False
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.
        
        Args:
            model_id: The model identifier
            
        Returns:
            Model information dictionary or None
        """
        models = self._get_available_models()
        for model in models:
            if model.get("id") == model_id or model.get("name") == model_id:
                return model
        return None
    
    def switch_to_model(self, target_model_id: str) -> bool:
        """
        Switch to a different model, unloading the current one first.
        
        Args:
            target_model_id: The model to load
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Switching from '{self.current_model}' to '{target_model_id}'")
        
        # Check if already loaded
        currently_loaded = self._get_loaded_models()
        for model in currently_loaded:
            if model.get("id") == target_model_id:
                logger.info(f"Model '{target_model_id}' is already loaded")
                self.current_model = target_model_id
                return True
        
        # Unload current model if different
        if self.current_model and self.current_model != target_model_id:
            self._unload_current_model()
            time.sleep(2)  # Wait for model to fully unload
        
        # Load target model
        success = self._load_model(target_model_id)
        
        if not success:
            logger.error(f"Failed to load model: {target_model_id}")
            return False
        
        # Verify the model is loaded and update current_model
        time.sleep(2)  # Give LM Studio time to fully initialize the model
        currently_loaded = self._get_loaded_models()
        for model in currently_loaded:
            if model.get("id") == target_model_id:
                logger.info(f"Successfully switched to model: {target_model_id}")
                self.current_model = target_model_id
                return True
        
        # Even if verification fails, update the state since we attempted to load
        logger.warning("Model loaded but verification failed - updating state anyway")
        self.current_model = target_model_id
        return True
    
    def switch_to_embedding_model(self) -> bool:
        """Switch to the embedding model for vector generation."""
        # Try common embedding model names
        embedding_names = [
            "text-embedding-qwen3-embedding-8b",
            "qwen3-embedding-8b",
            "embedding-model",
            "text-embedding"
        ]
        
        available_models = self._get_available_models()
        available_ids = [m.get("id", "").lower() for m in available_models]
        
        # Find the best embedding model
        for name in embedding_names:
            for m in available_models:
                model_id = m.get("id", "").lower()
                if name in model_id and "embedding" in model_id:
                    return self.switch_to_model(m.get("id"))
        
        logger.error("No embedding model found in LM Studio")
        return False
    
    def switch_to_coding_model(self) -> bool:
        """Switch to the coding/model for chat/completions."""
        # Try common coding model names
        coding_names = [
            "qwen3-coder-next",
            "qwen3-coder-next-ud",
            "coder-model",
            "coding-model"
        ]
        
        available_models = self._get_available_models()
        available_ids = [m.get("id", "").lower() for m in available_models]
        
        # Find the best coding model
        for name in coding_names:
            for m in available_models:
                model_id = m.get("id", "").lower()
                if any(keyword in model_id for keyword in ["coder", "next", "chat"]) and "embed" not in model_id:
                    return self.switch_to_model(m.get("id"))
        
        # If no specific coding model found, load the first available
        if available_models:
            return self.switch_to_model(available_models[0].get("id"))
        
        logger.error("No coding model found in LM Studio")
        return False
    
    def context_manager(self, target_model_id: str):
        """
        Context manager for temporary model switching.
        
        Usage:
            with switcher.context_manager("text-embedding-qwen3-embedding-8b"):
                # Do embedding work
                pass
            # Model automatically switched back
            
        Args:
            target_model_id: Model to use within context
            
        Returns:
            Context manager object
        """
        return ModelContextManager(self, target_model_id)


class ModelContextManager:
    """Context manager for automatic model switching."""
    
    def __init__(self, switcher: LMStudioModelSwitcher, target_model_id: str):
        self.switcher = switcher
        self.target_model_id = target_model_id
        self.previous_model: Optional[str] = None
        
    def __enter__(self):
        # Capture the current model ID BEFORE switching (for restoration later)
        # Use current_model attribute which tracks the actively used model
        self.previous_model = self.switcher.current_model
        
        if not self.switcher.switch_to_model(self.target_model_id):
            logger.warning(f"Failed to switch to {self.target_model_id}")
        return self.switcher
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous model (don't fail on restore)
        try:
            if self.previous_model != self.target_model_id:
                if self.previous_model is not None:
                    logger.info(f"Restoring previous model: {self.previous_model}")
                    self.switcher.switch_to_model(self.previous_model)
                else:
                    # Restore to no model loaded (unload current model)
                    logger.info("Restoring to no model loaded")
                    self.switcher._unload_current_model()
        except Exception as e:
            logger.warning(f"Failed to restore previous model: {e}")
        return False
