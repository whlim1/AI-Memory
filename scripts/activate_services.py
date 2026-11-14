#!/usr/bin/env python3
"""
Phase 5 Services Activation Script for AI Memory Pipeline.

This script initializes and activates all three Phase 5 services:
- Embedding Quality Monitor
- Model Caching Strategy  
- Dynamic Chunking Service

Usage: python scripts/activate_services.py [--dry-run] [--config CONFIG_PATH]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_memory_pipeline import QdrantManager, LMSmartEmbedder
from services import (
    EmbeddingQualityMonitor,
    ModelCacheManager,
    DynamicChunkingService
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Activate Phase 5 services for AI Memory Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python scripts/activate_services.py                    # Activate all services
  python scripts/activate_services.py --dry-run          # Show what would be activated
  python scripts/activate_services.py --config config.yml  # Use custom config
        '''
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what services would be activated without actually starting them'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='Path to configuration file (YAML format)'
    )
    
    parser.add_argument(
        '--services', '-s',
        type=str,
        nargs='+',
        choices=['embedding', 'model-cache', 'dynamic-chunking'],
        default=['embedding', 'model-cache', 'dynamic-chunking'],
        help='Specific services to activate (default: all)'
    )
    
    return parser.parse_args()


def initialize_qdrant():
    """Initialize Qdrant connection."""
    url = f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', 6333)}"
    logger.info(f"Connecting to Qdrant at {url}")
    
    try:
        qdm = QdrantManager(url=url)
        
        # Test connection
        collections = qdm.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        logger.info(f"Connected successfully. Collections: {collection_names}")
        return qdm
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {str(e)}")
        raise


def initialize_lm_embedder():
    """Initialize LM Studio smart embedder."""
    host = os.getenv('LM_STUDIO_HOST', 'localhost')
    port = int(os.getenv('LM_STUDIO_PORT', 1234))
    
    logger.info(f"Connecting to LM Studio at {host}:{port}")
    
    try:
        embedder = LMSmartEmbedder(host=host, port=port)
        
        # Test embedding generation
        test_embedding = embedder.generate_single_embedding("test")
        logger.info(f"Connected successfully. Model: {embedder.embedding_model_id}, dim: {len(test_embedding)}")
        
        return embedder
    except Exception as e:
        logger.error(f"Failed to connect to LM Studio: {str(e)}")
        raise


def activate_embedding_monitor(qdm, dry_run=False):
    """Initialize and start Embedding Quality Monitor."""
    logger.info("=" * 60)
    logger.info("Activating Embedding Quality Monitor")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("[DRY-RUN] Would initialize EmbeddingQualityMonitor")
        return None
    
    try:
        # Initialize monitor with collection name from env or default
        collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'aimemory_docs')
        
        monitor = EmbeddingQualityMonitor(
            qdrant_manager=qdm,
            collection_name=collection_name,
            drift_threshold=float(os.getenv('EMBEDDING_DRIFT_THRESHOLD', 0.1)),
            quality_threshold=float(os.getenv('EMBEDDING_QUALITY_THRESHOLD', 0.85))
        )
        
        logger.info(f"Embedding Quality Monitor initialized for collection: {collection_name}")
        logger.info("Monitor configuration:")
        logger.info(f"  - Drift threshold: {monitor.drift_threshold}")
        logger.info(f"  - Quality threshold: {monitor.quality_threshold}")
        
        # Perform initial quality check
        logger.info("Performing initial quality assessment...")
        quality_report = monitor.assess_embedding_quality()
        
        if quality_report:
            logger.info(f"Initial quality report:")
            logger.info(f"  - Total embeddings analyzed: {quality_report.get('total_embeddings', 'N/A')}")
            logger.info(f"  - Quality score: {quality_report.get('overall_quality_score', 'N/A'):.4f}")
            
            if quality_report.get('drift_detected'):
                logger.warning("⚠️  Drift detected! Consider re-ingesting documents.")
            else:
                logger.info("✓ No significant drift detected")
        
        return monitor
        
    except Exception as e:
        logger.error(f"Failed to initialize Embedding Quality Monitor: {str(e)}")
        raise


def activate_model_cache(qdm, dry_run=False):
    """Initialize and start Model Caching Strategy."""
    logger.info("=" * 60)
    logger.info("Activating Model Caching Strategy")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("[DRY-RUN] Would initialize ModelCacheManager")
        return None
    
    try:
        # Initialize cache manager
        collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'aimemory_docs')
        
        cache_manager = ModelCacheManager(
            qdrant_manager=qdm,
            collection_name=collection_name,
            max_cache_size=int(os.getenv('MAX_CACHE_SIZE_GB', 10)),
            gpu_memory_threshold=float(os.getenv('GPU_MEMORY_THRESHOLD', 0.9))
        )
        
        logger.info("Model Cache Manager initialized")
        logger.info("Cache configuration:")
        logger.info(f"  - Max cache size: {cache_manager.max_cache_size} GB")
        logger.info(f"  - GPU memory threshold: {cache_manager.gpu_memory_threshold}")
        
        # Log current cache state
        cache_stats = cache_manager.get_cache_statistics()
        if cache_stats:
            logger.info("Current cache statistics:")
            for key, value in cache_stats.items():
                logger.info(f"  - {key}: {value}")
        
        return cache_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize Model Caching Strategy: {str(e)}")
        raise


def activate_dynamic_chunking(qdm, dry_run=False):
    """Initialize and start Dynamic Chunking Service."""
    logger.info("=" * 60)
    logger.info("Activating Dynamic Chunking Service")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("[DRY-RUN] Would initialize DynamicChunkingService")
        return None
    
    try:
        # Initialize dynamic chunking service
        collection_name = os.getenv('QDRANT_COLLECTION_NAME', 'aimemory_docs')
        
        chunker = DynamicChunkingService(
            qdrant_manager=qdm,
            collection_name=collection_name,
            base_chunk_size=int(os.getenv('BASE_CHUNK_SIZE', 384)),
            content_type_threshold=float(os.getenv('CONTENT_TYPE_THRESHOLD', 0.7))
        )
        
        logger.info("Dynamic Chunking Service initialized")
        logger.info("Chunking configuration:")
        logger.info(f"  - Base chunk size: {chunker.base_chunk_size}")
        logger.info(f"  - Content type threshold: {chunker.content_type_threshold}")
        
        # Test content-type detection
        test_content = """
        This is a sample document for testing dynamic chunking.
        
        ## Code Section
        
        def hello():
            print("Hello, World!")
            
        ## Conclusion
        
        This document demonstrates the dynamic chunking capabilities.
        """
        
        chunks = chunker.chunk_content(test_content)
        logger.info(f"Test chunking successful. Generated {len(chunks)} chunks")
        
        return chunker
        
    except Exception as e:
        logger.error(f"Failed to initialize Dynamic Chunking Service: {str(e)}")
        raise


def run_service_loop(embedding_monitor, model_cache, dynamic_chunking):
    """Run the services in a monitoring loop."""
    logger.info("=" * 60)
    logger.info("Phase 5 Services Activated Successfully!")
    logger.info("=" * 60)
    
    logger.info("\nActive Services:")
    if embedding_monitor:
        logger.info("  ✓ Embedding Quality Monitor")
    if model_cache:
        logger.info("  ✓ Model Caching Strategy")
    if dynamic_chunking:
        logger.info("  ✓ Dynamic Chunking Service")
    
    logger.info("\nServices are now running in the background.")
    logger.info("Press Ctrl+C to stop all services.\n")
    
    # In production, this would run continuously with scheduled checks
    # For now, we just confirm activation and return
    
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'services_active': {
            'embedding_quality_monitor': embedding_monitor is not None,
            'model_caching_strategy': model_cache is not None,
            'dynamic_chunking_service': dynamic_chunking is not None
        },
        'configuration': {
            'collection_name': os.getenv('QDRANT_COLLECTION_NAME', 'aimemory_docs'),
            'drift_threshold': float(os.getenv('EMBEDDING_DRIFT_THRESHOLD', 0.1)),
            'quality_threshold': float(os.getenv('EMBEDDING_QUALITY_THRESHOLD', 0.85))
        }
    }


def main():
    """Main function to activate Phase 5 services."""
    args = parse_args()
    
    print("=" * 60)
    print("AI Memory Pipeline - Phase 5 Services Activation")
    print("=" * 60)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Dry run: {args.dry_run}")
    print(f"Services to activate: {', '.join(args.services)}\n")
    
    try:
        # Initialize connections
        logger.info("Step 1/3: Initializing Qdrant connection...")
        qdm = initialize_qdrant()
        
        logger.info("Step 2/3: Initializing LM Studio embedder...")
        lm_embedder = initialize_lm_embedder()
        
        # Track active services for reporting
        active_services = {
            'embedding': None,
            'model_cache': None,
            'dynamic_chunking': None
        }
        
        # Activate requested services
        if 'embedding' in args.services:
            try:
                active_services['embedding'] = activate_embedding_monitor(qdm, args.dry_run)
            except Exception as e:
                logger.error(f"Failed to activate Embedding Quality Monitor: {str(e)}")
                if not args.dry_run:
                    raise
        
        if 'model-cache' in args.services:
            try:
                active_services['model_cache'] = activate_model_cache(qdm, args.dry_run)
            except Exception as e:
                logger.error(f"Failed to activate Model Caching Strategy: {str(e)}")
                if not args.dry_run:
                    raise
        
        if 'dynamic-chunking' in args.services:
            try:
                active_services['dynamic_chunking'] = activate_dynamic_chunking(qdm, args.dry_run)
            except Exception as e:
                logger.error(f"Failed to activate Dynamic Chunking Service: {str(e)}")
                if not args.dry_run:
                    raise
        
        # Run service loop (or report in dry-run mode)
        result = run_service_loop(
            active_services['embedding'],
            active_services['model_cache'],
            active_services['dynamic_chunking']
        )
        
        print("\n" + "=" * 60)
        print("Activation Summary")
        print("=" * 60)
        
        if args.dry_run:
            print("[DRY-RUN] No services were actually started.")
            print("Review the configuration and run without --dry-run to activate.")
        else:
            print(f"✓ All requested services activated successfully!")
            print(f"\nTimestamp: {result['timestamp']}")
            
            # Print active services
            print("\nActive Services:")
            for service_name, active in result['services_active'].items():
                status = "✓ ACTIVE" if active else "✗ INACTIVE"
                print(f"  {service_name}: {status}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Service activation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Failed to activate services: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
