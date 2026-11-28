#!/usr/bin/env python3
"""
Model Caching Strategy Service

Optimizes GPU memory usage by implementing smart model switching and caching strategies for LM Studio.

Features:
- Track model usage patterns and hot/cold classification
- Automatic model swapping based on predicted demand
- GPU memory optimization with LRU eviction policy
- REST API integration for LM Studio model management
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import time

# HTTP client for LM Studio API
import requests

# Web framework for service endpoints (Phase 4 microservice)
from fastapi import FastAPI
from pydantic import BaseModel


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('ModelCacheManager')


class ModelStatus(Enum):
    """Model caching status."""
    HOT = "hot"      # Currently loaded in GPU VRAM
    WARM = "warm"    # In system RAM, quick to load
    COLD = "cold"    # Not cached, needs full load
    EVICTED = "evicted"  # Was hot/warm but evicted


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    model_id: str
    model_name: str
    status: ModelStatus = ModelStatus.COLD
    last_used: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0
    estimated_vram_usage: float = 0.0  # GB
    load_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'status': self.status.value,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count,
            'estimated_vram_usage': self.estimated_vram_usage,
            'load_time_seconds': self.load_time_seconds,
        }


class ModelCacheManager:
    """Manages model caching strategy and GPU memory optimization."""
    
    def __init__(
        self,
        lm_studio=None,
        lm_studio_url: str = "http://localhost:1234",
        max_gpu_memory_gb: float = 24.0,  # Default high-end GPU
        hot_model_count: int = 1,         # Number of models to keep in VRAM
        warm_cache_count: int = 3,        # Models to keep in system RAM
        eviction_threshold_minutes: int = 60,
    ):
        # Accept either an LMSmartEmbedder instance or a URL string
        if lm_studio is not None:
            # Check if it's an LMSmartEmbedder instance (has base_url attribute)
            if hasattr(lm_studio, 'base_url'):
                self.lm_studio_url = lm_studio.base_url.rstrip('/')
            elif isinstance(lm_studio, str):
                self.lm_studio_url = lm_studio.rstrip('/')
            else:
                raise ValueError("lm_studio must be an LMSmartEmbedder instance or URL string")
        else:
            self.lm_studio_url = lm_studio_url.rstrip('/')
        
        # Store the lm_studio reference (can be None, instance, or URL string)
        self.lm_studio = lm_studio
        
        self.max_gpu_memory_gb = max_gpu_memory_gb
        self.hot_model_count = hot_model_count
        self.warm_cache_count = warm_cache_count
        self.eviction_threshold_minutes = eviction_threshold_minutes
        
        # Cache storage
        self.cache_dir = Path('data/model_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.models: Dict[str, ModelInfo] = {}
        self.model_order: List[str] = []  # LRU order (most recent first)
        
        # Load persisted state
        self._load_state()
        
        logger.info(f"ModelCacheManager initialized for {lm_studio_url}")
    
    def _get_available_models(self) -> Dict[str, str]:
        """Get list of available models from LM Studio."""
        try:
            response = requests.get(
                f"{self.lm_studio_url}/v1/models",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                models = {}
                for item in data.get('data', []):
                    model_id = item.get('id', '')
                    model_name = item.get('name', item.get('id', ''))
                    # Extract name from full ID if needed
                    if '/' in model_name:
                        model_name = model_name.split('/')[-1]
                    models[model_id] = model_name
                return models
        except Exception as e:
            logger.error(f"Error fetching models from LM Studio: {e}")
        
        return {}
    
    def _probe_lm_studio(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Fast, non-blocking probe of the LM Studio API.

        Returns a small status dict and NEVER raises. Used by the container
        healthcheck so it stays well under the Docker healthcheck timeout even
        when LM Studio is slow or unreachable.
        """
        result: Dict[str, Any] = {
            'reachable': False,
            'model_count': 0,
            'error': None,
        }
        try:
            response = requests.get(
                f"{self.lm_studio_url}/v1/models",
                timeout=timeout,
            )
            if response.status_code == 200:
                data = response.json()
                result['reachable'] = True
                result['model_count'] = len(data.get('data', []))
            else:
                result['error'] = f"HTTP {response.status_code}"
        except Exception as e:
            result['error'] = str(e)
        return result

    def _get_current_model(self) -> Optional[str]:
        """Get currently loaded model."""
        try:
            response = requests.get(
                f"{self.lm_studio_url}/v1/models",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [{}])[0].get('id')
        except Exception as e:
            logger.error(f"Error getting current model: {e}")
        return None
    
    def _load_model(self, model_id: str) -> bool:
        """Load a model into GPU."""
        start_time = time.time()
        
        try:
            # Check if already loaded
            current = self._get_current_model()
            if current == model_id:
                logger.info(f"Model {model_id} already loaded")
                return True
            
            # Load via LM Studio API
            response = requests.post(
                f"{self.lm_studio_url}/v1/models/load",
                json={"model": model_id},
                timeout=300  # 5 minutes for large models
            )
            
            if response.status_code == 200:
                load_time = time.time() - start_time
                logger.info(f"Model {model_id} loaded in {load_time:.2f}s")
                
                # Update model info
                if model_id in self.models:
                    self.models[model_id].status = ModelStatus.HOT
                    self.models[model_id].last_used = datetime.utcnow()
                    self.models[model_id].usage_count += 1
                    self.models[model_id].load_time_seconds = load_time
                
                return True
            
        except Exception as e:
            logger.error(f"Error loading model {model_id}: {e}")
        
        return False
    
    def _unload_model(self, model_id: str) -> bool:
        """Unload a model from GPU."""
        try:
            # Check if this is the current model
            current = self._get_current_model()
            if current != model_id:
                logger.info(f"Model {model_id} not currently loaded")
                return True
            
            # Unload via LM Studio API
            response = requests.post(
                f"{self.lm_studio_url}/v1/models/unload",
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Model {model_id} unloaded")
                
                if model_id in self.models:
                    # Keep warm cache (RAM) but mark as not hot
                    self.models[model_id].status = ModelStatus.WARM
                
                return True
            
        except Exception as e:
            logger.error(f"Error unloading model {model_id}: {e}")
        
        return False
    
    def _evict_cold_models(self, needed_memory_gb: float) -> List[str]:
        """Evict cold/warm models to free memory."""
        evicted = []
        
        # Sort by last used (oldest first)
        sorted_models = sorted(
            self.models.items(),
            key=lambda x: x[1].last_used
        )
        
        for model_id, info in sorted_models:
            if info.status == ModelStatus.COLD or (
                info.status == ModelStatus.WARM and 
                len([m for m in self.models.values() if m.status == ModelStatus.HOT]) > 0
            ):
                logger.info(f"Evicting cold/warm model: {model_id}")
                evicted.append(model_id)
                
                # Mark as evicted
                info.status = ModelStatus.EVICTED
                
                # Free up memory accounting
                if needed_memory_gb >= info.estimated_vram_usage:
                    needed_memory_gb -= info.estimated_vram_usage
                    if needed_memory_gb <= 0:
                        break
        
        return evicted
    
    def ensure_model_loaded(self, model_id: str) -> bool:
        """Ensure a specific model is loaded in GPU."""
        current = self._get_current_model()
        
        # Already loaded
        if current == model_id:
            logger.info(f"Model {model_id} already loaded")
            return True
        
        # Check if we have memory
        available_memory = self.max_gpu_memory_gb - self._get_total_vram_usage()
        
        if available_memory < 1.0:  # Need at least 1GB headroom
            logger.warning("Low GPU memory, attempting eviction")
            self._evict_cold_models(available_memory)
        
        return self._load_model(model_id)
    
    def _get_total_vram_usage(self) -> float:
        """Get total VRAM usage from hot models."""
        total = 0.0
        for info in self.models.values():
            if info.status == ModelStatus.HOT:
                total += info.estimated_vram_usage
        return total
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory and cache status."""
        hot_models = [m for m in self.models.values() if m.status == ModelStatus.HOT]
        warm_models = [m for m in self.models.values() if m.status == ModelStatus.WARM]
        cold_models = [m for m in self.models.values() if m.status == ModelStatus.COLD]
        
        return {
            'lm_studio_url': self.lm_studio_url,
            'max_gpu_memory_gb': self.max_gpu_memory_gb,
            'current_vram_usage_gb': round(self._get_total_vram_usage(), 2),
            'available_gpu_memory_gb': round(
                max(0, self.max_gpu_memory_gb - self._get_total_vram_usage()), 2
            ),
            'hot_models': len(hot_models),
            'warm_models': len(warm_models),
            'cold_models': len(cold_models),
            'total_cached': len(self.models),
        }
    
    def sync_with_lm_studio(self) -> Dict[str, Any]:
        """Sync cache state with LM Studio's actual state."""
        current_model = self._get_current_model()
        
        # Get available models
        available = self._get_available_models()
        
        for model_id in available.keys():
            if model_id not in self.models:
                self.models[model_id] = ModelInfo(
                    model_id=model_id,
                    model_name=available[model_id],
                    status=ModelStatus.COLD,
                )
        
        # Update current model status
        if current_model and current_model in self.models:
            self.models[current_model].status = ModelStatus.HOT
        
        return {
            'synced_models': list(available.keys()),
            'current_model': current_model,
        }
    
    def _save_state(self) -> None:
        """Persist cache state to disk."""
        state = {
            'timestamp': datetime.utcnow().isoformat(),
            'models': {k: v.to_dict() for k, v in self.models.items()},
            'model_order': self.model_order,
        }
        
        filepath = self.cache_dir / 'cache_state.json'
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self) -> None:
        """Load persisted cache state."""
        filepath = self.cache_dir / 'cache_state.json'
        if not filepath.exists():
            return
        
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            for model_id, info_data in state.get('models', {}).items():
                status_str = info_data.get('status', ModelStatus.COLD.value)
                try:
                    status = ModelStatus(status_str)
                except ValueError:
                    status = ModelStatus.COLD
                
                self.models[model_id] = ModelInfo(
                    model_id=info_data['model_id'],
                    model_name=info_data['model_name'],
                    status=status,
                    last_used=datetime.fromisoformat(info_data.get('last_used', datetime.utcnow().isoformat())),
                    usage_count=info_data.get('usage_count', 0),
                    estimated_vram_usage=info_data.get('estimated_vram_usage', 0.0),
                    load_time_seconds=info_data.get('load_time_seconds', 0.0),
                )
        except Exception as e:
            logger.error(f"Error loading cache state: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health and dependencies.

        Fast by design: the container healthcheck runs `curl -f .../health`
        with a 10s timeout, so this must return quickly even when LM Studio
        is slow or unreachable. A bounded 2s probe is used for the LM Studio
        dependency; a missing/down LM Studio is reported as `degraded`, not a
        hard failure, because the service itself is healthy.
        """
        probe = self._probe_lm_studio(timeout=2.0)

        return {
            'status': 'healthy',
            'service': 'ModelCacheManager',
            'timestamp': datetime.utcnow().isoformat(),
            'dependencies': {
                'lm_studio': {
                    'status': 'connected' if probe['reachable'] else 'degraded',
                    'base_url': str(self.lm_studio.base_url) if hasattr(self.lm_studio, 'base_url') else (str(self.lm_studio) if self.lm_studio else self.lm_studio_url),
                    **({'error': probe['error']} if probe['error'] else {}),
                },
            },
            'metadata': {
                'available_models_count': probe['model_count'],
                'total_cached': len(self.models),
                'hot_models': sum(1 for m in self.models.values() if m.status == ModelStatus.HOT),
                'warm_models': sum(1 for m in self.models.values() if m.status == ModelStatus.WARM),
                'cold_models': sum(1 for m in self.models.values() if m.status == ModelStatus.COLD),
            },
        }


class ModelSwitcher:
    """High-level model switching strategy based on usage patterns."""
    
    def __init__(self, cache_manager: ModelCacheManager):
        self.cache_manager = cache_manager
    
    def get_model_suggestion(self) -> Optional[str]:
        """Suggest which model to load based on usage patterns."""
        if not self.cache_manager.models:
            return None
        
        # Get models sorted by usage
        sorted_models = sorted(
            self.cache_manager.models.values(),
            key=lambda x: (x.usage_count, x.last_used.timestamp()),
            reverse=True
        )
        
        # Return most used model that's not already hot
        for info in sorted_models:
            if info.status != ModelStatus.HOT:
                return info.model_id
        
        # If all are hot, return the most recently used
        return sorted_models[0].model_id if sorted_models else None
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Run cache optimization routine."""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'actions': [],
            'memory_before': self.cache_manager.get_memory_status(),
        }
        
        # Check if we need to evict
        vram_usage = self.cache_manager._get_total_vram_usage()
        if vram_usage > self.cache_manager.max_gpu_memory_gb * 0.95:
            results['actions'].append({
                'action': 'eviction_needed',
                'reason': f'VRAM usage {vram_usage:.2f}GB exceeds 95% of max',
            })
            
        # Check for models that should be evicted
        sorted_models = sorted(
            self.cache_manager.models.values(),
            key=lambda x: (x.last_used.timestamp() if x.last_used else 0)
        )
        
        current_hot = [m for m in self.cache_manager.models.values() if m.status == ModelStatus.HOT]
        
        # Keep only N hot models
        if len(current_hot) > self.cache_manager.hot_model_count:
            for info in current_hot[self.cache_manager.hot_model_count:]:
                results['actions'].append({
                    'action': 'evict_hot',
                    'model_id': info.model_id,
                    'reason': f'More than {self.cache_manager.hot_model_count} hot models',
                })
        
        # Mark unused models as cold
        cutoff = datetime.utcnow() - timedelta(minutes=self.cache_manager.eviction_threshold_minutes)
        for model in self.cache_manager.models.values():
            if model.last_used and model.last_used < cutoff:
                results['actions'].append({
                    'action': 'demote_warm',
                    'model_id': model.model_id,
                    'reason': f'Unused for {self.cache_manager.eviction_threshold_minutes} minutes',
                })
        
        results['memory_after'] = self.cache_manager.get_memory_status()
        
        return results
    
    def switch_to_model(self, model_id: str) -> Dict[str, Any]:
        """Switch to a specific model with optimization."""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'requested_model': model_id,
        }
        
        # Ensure model is loaded
        success = self.cache_manager.ensure_model_loaded(model_id)
        
        if success:
            results['status'] = 'success'
            
            # Run optimization after switch
            opt_results = self.optimize_cache()
            results['optimization'] = opt_results
        else:
            results['status'] = 'failed'
        
        return results


# =============================================================================
# FastAPI application (Phase 4 microservice)
# =============================================================================

def _resolve_lm_studio_url() -> str:
    """Resolve the LM Studio URL from the LM_STUDIO_URL env var (scheme optional)."""
    url = os.getenv('LM_STUDIO_URL', 'http://localhost:1234').strip()
    if not url.startswith(('http://', 'https://')):
        url = f'http://{url}'
    return url


cache_manager = ModelCacheManager(lm_studio_url=_resolve_lm_studio_url())
switcher = ModelSwitcher(cache_manager)

app = FastAPI(
    title="Model Caching Strategy Service",
    description="Model caching and GPU memory optimization for LM Studio",
    version="1.0.0"
)


class SwitchRequest(BaseModel):
    model_id: str


@app.get("/health")
async def health():
    """Health check endpoint for container orchestration."""
    return cache_manager.health_check()


@app.get("/status")
async def memory_status():
    """Get GPU memory and cache status."""
    return cache_manager.get_memory_status()


@app.post("/sync")
async def sync_with_lm_studio():
    """Sync the model inventory with LM Studio."""
    return cache_manager.sync_with_lm_studio()


@app.get("/suggest")
async def get_suggestion():
    """Get a model suggestion for loading."""
    return {"suggestion": switcher.get_model_suggestion()}


@app.post("/optimize")
async def optimize_cache():
    """Run cache optimization (evict cold models as needed)."""
    return switcher.optimize_cache()


@app.post("/switch")
async def switch_model(request: SwitchRequest):
    """Switch to a specific model."""
    return switcher.switch_to_model(request.model_id)


def main():
    """Main entry point for model caching strategy."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Model Caching Strategy')
    parser.add_argument('--url', default='http://localhost:1234', help='LM Studio URL')
    parser.add_argument('--sync', action='store_true', help='Sync with LM Studio')
    parser.add_argument('--status', action='store_true', help='Show memory status')
    parser.add_argument('--suggest', action='store_true', help='Get model suggestion')
    parser.add_argument('--optimize', action='store_true', help='Run optimization')
    parser.add_argument('--switch', type=str, help='Switch to specific model')
    
    args = parser.parse_args()
    
    cache_manager = ModelCacheManager(lm_studio_url=args.url)
    switcher = ModelSwitcher(cache_manager)
    
    if args.sync:
        result = cache_manager.sync_with_lm_studio()
        print(json.dumps(result, indent=2))
    
    elif args.status:
        status = cache_manager.get_memory_status()
        print("=== Memory Status ===")
        for key, value in status.items():
            print(f"{key}: {value}")
        
        print("\n=== Cached Models ===")
        for model_id, info in cache_manager.models.items():
            print(f"  [{info.status.value.upper()}] {model_id} (used: {info.usage_count})")
    
    elif args.suggest:
        suggestion = switcher.get_model_suggestion()
        if suggestion:
            print(f"Suggested model: {suggestion}")
        else:
            print("No models available")
    
    elif args.optimize:
        results = switcher.optimize_cache()
        print(json.dumps(results, indent=2))
    
    elif args.switch:
        results = switcher.switch_to_model(args.switch)
        print(json.dumps(results, indent=2))
    
    else:
        # Default: sync and show status
        cache_manager.sync_with_lm_studio()
        status = cache_manager.get_memory_status()
        print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()