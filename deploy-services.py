#!/usr/bin/env python3
"""
Step-by-step Service Deployment Script

Deploys AI Memory Pipeline services in dependency order:
1. Qdrant (already running)
2. Deduplication Service
3. Dynamic Chunking Service  
4. Embedding Quality Monitor
5. Model Cache Manager
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.deduplication_service import DeduplicationService
from services.dynamic_chunking_service import DynamicChunkingService
from services.embedding_quality_monitor import EmbeddingQualityMonitor
from services.model_caching_strategy import ModelCacheManager
from services.qdrant_manager import QdrantManager


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def deploy_deduplication():
    """Deploy Deduplication Service."""
    print_header("DEPLOYING DEDUPLICATION SERVICE")
    
    try:
        service = DeduplicationService(
            exact_threshold=1.0,
            fuzzy_threshold=0.85,
            hash_types=None  # Use defaults
        )
        
        health = service.health_check()
        
        if health:
            print("✅ Deduplication Service deployed successfully!")
            print(f"   Health: {health}")
            return True, service
        else:
            print("❌ Deduplication Service health check failed!")
            return False, None
            
    except Exception as e:
        print(f"❌ Failed to deploy Deduplication Service: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def deploy_chunking():
    """Deploy Dynamic Chunking Service."""
    print_header("DEPLOYING DYNAMIC CHUNKING SERVICE")
    
    try:
        service = DynamicChunkingService(
            default_chunk_size=512,
            chunk_overlap=64
        )
        
        health = service.health_check()
        
        if health.get('status') == 'healthy':
            print("✅ Dynamic Chunking Service deployed successfully!")
            print(f"   Health: {json.dumps(health, indent=2, default=str)}")
            return True, service
        else:
            print("❌ Dynamic Chunking Service health check failed!")
            return False, None
            
    except Exception as e:
        print(f"❌ Failed to deploy Dynamic Chunking Service: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def deploy_embedding(qdrant_client):
    """Deploy Embedding Quality Monitor."""
    print_header("DEPLOYING EMBEDDING QUALITY MONITOR")
    
    try:
        service = EmbeddingQualityMonitor(
            qdrant_client=qdrant_client
        )
        
        health = service.health_check()
        
        if health.get('status') == 'healthy':
            print("✅ Embedding Quality Monitor deployed successfully!")
            print(f"   Health: {json.dumps(health, indent=2, default=str)}")
            return True, service
        else:
            print("❌ Embedding Quality Monitor health check failed!")
            return False, None
            
    except Exception as e:
        print(f"❌ Failed to deploy Embedding Quality Monitor: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def deploy_model_cache():
    """Deploy Model Cache Manager."""
    print_header("DEPLOYING MODEL CACHE MANAGER")
    
    try:
        service = ModelCacheManager(
            lm_studio_url="http://localhost:1234",
            max_gpu_memory_gb=24.0,
            hot_model_count=1,
            warm_cache_count=3,
            eviction_threshold_minutes=60
        )
        
        health = service.health_check()
        
        if health.get('status') == 'healthy':
            print("✅ Model Cache Manager deployed successfully!")
            print(f"   Health: {json.dumps(health, indent=2, default=str)}")
            return True, service
        else:
            print("❌ Model Cache Manager health check failed!")
            return False, None
            
    except Exception as e:
        print(f"❌ Failed to deploy Model Cache Manager: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    """Main deployment function."""
    print_header("AI MEMORY PIPELINE - STEP-BY-STEP DEPLOYMENT")
    print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    
    results = {}
    
    # Step 1: Qdrant (already running)
    print_header("STEP 1: VERIFY QRANT STATUS")
    try:
        import requests
        response = requests.get("http://localhost:6333/readyz", timeout=5)
        if response.status_code == 200:
            print("✅ Qdrant is running and healthy!")
            results['qdrant'] = {'status': 'healthy'}
        else:
            print(f"❌ Qdrant health check failed with status: {response.status_code}")
            results['qdrant'] = {'status': 'unhealthy', 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        results['qdrant'] = {'status': 'unreachable', 'error': str(e)}
    
    # Step 2: Deduplication Service
    success, _ = deploy_deduplication()
    results['deduplication'] = {'status': 'healthy' if success else 'failed'}
    
    # Step 3: Dynamic Chunking Service
    success, _ = deploy_chunking()
    results['chunking'] = {'status': 'healthy' if success else 'failed'}
    
    # Step 4: Embedding Quality Monitor (requires Qdrant client)
    print_header("STEP 4: CONNECT TO QRANT FOR EMBEDDING MONITOR")
    qdrant_client = None
    try:
        from services.qdrant_manager import QdrantManager
        qmgr = QdrantManager(host="localhost", port=6333, api_key=None)
        # Use the client attribute directly
        qdrant_client = qmgr.client
        print("✅ Connected to Qdrant successfully!")
        
        success, _ = deploy_embedding(qdrant_client)
        results['embedding_monitor'] = {'status': 'healthy' if success else 'failed'}
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        import traceback
        traceback.print_exc()
        results['embedding_monitor'] = {'status': 'failed', 'error': str(e)}
    
    # Step 5: Model Cache Manager
    success, _ = deploy_model_cache()
    results['model_cache'] = {'status': 'healthy' if success else 'failed'}
    
    # Summary
    print_header("DEPLOYMENT SUMMARY")
    print(json.dumps(results, indent=2))
    
    total = len(results)
    successful = sum(1 for r in results.values() if r.get('status') == 'healthy')
    
    print(f"\nTotal Services: {total}")
    print(f"Successful: {successful}")
    print(f"Failed/Unhealthy: {total - successful}")
    
    if successful == total:
        print("\n🎉 ALL SERVICES DEPLOYED SUCCESSFULLY!")
        return 0
    else:
        print("\n⚠️  Some services failed to deploy. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
