#!/usr/bin/env python3
"""
Embedding Quality Monitoring Service

Tracks embedding drift, quality metrics, and triggers re-ingestion when thresholds are exceeded.

Features:
- Embedding distance monitoring (cosine similarity)
- Vector norm analysis for degenerate embeddings
- Collection-level quality scoring
- Automated re-ingestion triggers
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Qdrant client
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('EmbeddingQualityMonitor')


class EmbeddingQualityMetrics:
    """Tracks and calculates embedding quality metrics."""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.metrics_history: List[Dict[str, Any]] = []
        
    def calculate_vector_norm_stats(self, vectors: np.ndarray) -> Dict[str, float]:
        """Calculate statistics on vector norms."""
        norms = np.linalg.norm(vectors, axis=1)
        return {
            'mean_norm': float(np.mean(norms)),
            'std_norm': float(np.std(norms)),
            'min_norm': float(np.min(norms)),
            'max_norm': float(np.max(norms)),
            'median_norm': float(np.median(norms)),
        }
    
    def calculate_cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return float(dot_product / (norm_v1 * norm_v2))
    
    def calculate_embedding_drift(
        self, 
        current_vectors: np.ndarray,
        baseline_vectors: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Calculate embedding drift compared to baseline."""
        if baseline_vectors is None:
            return {'drift_detected': False, 'metrics': {}}
        
        # Calculate mean cosine similarity between all pairs
        similarities = []
        for i, curr_vec in enumerate(current_vectors):
            if i < len(baseline_vectors):
                sim = self.calculate_cosine_similarity(curr_vec, baseline_vectors[i])
                similarities.append(sim)
        
        avg_similarity = np.mean(similarities) if similarities else 0.0
        
        return {
            'drift_detected': avg_similarity < 0.85,  # Threshold
            'average_cosine_similarity': float(avg_similarity),
            'similarity_count': len(similarities),
        }


class EmbeddingQualityMonitor:
    """Main monitoring service for embedding quality."""
    
    def __init__(
        self,
        qdrant_client=None,
        qdrant_host: str = os.getenv('QDRANT_HOST', 'localhost'),
        qdrant_port: int = int(os.getenv('QDRANT_PORT', 6333)),
        metrics_retention_days: int = 30,
        drift_threshold: float = 0.85,
        norm_std_threshold: float = 0.1,
    ):
        # Accept either a QdrantManager instance or connection parameters
        if qdrant_client is not None:
            # Check if it's a QdrantManager instance (has client attribute)
            if hasattr(qdrant_client, 'client'):
                self.qdrant_client = qdrant_client.client
            elif isinstance(qdrant_client, QdrantClient):
                self.qdrant_client = qdrant_client
            else:
                raise ValueError("qdrant_client must be a QdrantManager instance or QdrantClient")
        else:
            # Use connection parameters to create client
            self.qdrant_client = QdrantClient(
                host=qdrant_host,
                port=qdrant_port,
                timeout=30,
            )
        self.metrics_retention_days = metrics_retention_days
        self.drift_threshold = drift_threshold
        self.norm_std_threshold = norm_std_threshold
        
        # Metrics storage
        self.metrics_dir = Path('data/embedding_metrics')
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"EmbeddingQualityMonitor initialized for {qdrant_host}:{qdrant_port}")
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get basic statistics about a collection."""
        try:
            collection_info = self.qdrant_client.get_collection(collection_name)
            return {
                'collection_name': collection_name,
                'vectors_count': collection_info.vectors_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count,
                'points_count': collection_info.points_count,
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
    
    def sample_vectors(
        self, 
        collection_name: str, 
        sample_size: int = 1000
    ) -> Tuple[Optional[np.ndarray], List[str]]:
        """Sample vectors from a collection for analysis."""
        try:
            points = []
            point_ids = []
            
            # Scroll through points
            scroll_result = self.qdrant_client.scroll(
                collection_name=collection_name,
                limit=min(sample_size, 10000),
                with_vectors=True,
                with_payload=False,
            )
            
            for point in scroll_result[0]:
                if point.vector is not None:
                    points.append(point.vector)
                    point_ids.append(str(point.id))
            
            if not points:
                return None, []
                
            vectors_array = np.array(points)
            return vectors_array, point_ids
            
        except Exception as e:
            logger.error(f"Error sampling vectors: {e}")
            return None, []
    
    def analyze_embedding_quality(
        self,
        collection_name: str,
        sample_size: int = 1000
    ) -> Dict[str, Any]:
        """Comprehensive quality analysis of embeddings in a collection."""
        
        # Sample vectors
        vectors, point_ids = self.sample_vectors(collection_name, sample_size)
        if vectors is None:
            return {
                'collection': collection_name,
                'status': 'error',
                'message': 'No vectors found',
            }
        
        metrics = EmbeddingQualityMetrics(collection_name)
        
        # Calculate norm statistics
        norm_stats = metrics.calculate_vector_norm_stats(vectors)
        
        # Check for degenerate embeddings (near-zero vectors)
        zero_vectors = np.sum(np.linalg.norm(vectors, axis=1) < 0.001)
        
        # Analyze drift against baseline (if exists)
        drift_analysis = metrics.calculate_embedding_drift(vectors)
        
        # Calculate overall quality score
        quality_score = self._calculate_quality_score(
            norm_stats,
            zero_vectors,
            len(point_ids),
            drift_analysis['average_cosine_similarity'] if not drift_analysis['drift_detected'] else 0.0
        )
        
        result = {
            'collection': collection_name,
            'status': 'analyzed',
            'timestamp': datetime.utcnow().isoformat(),
            'sample_size': len(point_ids),
            'quality_score': quality_score,
            'norm_statistics': norm_stats,
            'zero_vector_count': int(zero_vectors),
            'drift_analysis': drift_analysis,
        }
        
        # Save metrics
        self._save_metrics(collection_name, result)
        
        return result
    
    def _calculate_quality_score(
        self,
        norm_stats: Dict[str, float],
        zero_vector_count: int,
        total_vectors: int,
        avg_similarity: float = 1.0
    ) -> float:
        """Calculate overall quality score (0-100)."""
        
        # Norm stability score (0-40 points)
        norm_std_ratio = norm_stats['std_norm'] / max(norm_stats['mean_norm'], 0.001)
        norm_score = max(0, 40 - (norm_std_ratio * 20))
        
        # Zero vector penalty (up to -30 points)
        zero_ratio = zero_vector_count / max(total_vectors, 1)
        zero_penalty = min(30, zero_ratio * 100)
        
        # Drift score (0-30 points)
        drift_score = avg_similarity * 30
        
        final_score = max(0, min(100, norm_score - zero_penalty + drift_score))
        return round(final_score, 2)
    
    def _save_metrics(self, collection_name: str, metrics: Dict[str, Any]) -> None:
        """Save metrics to disk."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{collection_name}_{timestamp}.json"
        filepath = self.metrics_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")
    
    def check_thresholds(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Check if any thresholds are exceeded."""
        alerts = []
        
        norm_stats = metrics.get('norm_statistics', {})
        
        # Check norm std threshold
        mean_norm = norm_stats.get('mean_norm', 1.0)
        std_norm = norm_stats.get('std_norm', 0)
        if mean_norm > 0 and (std_norm / mean_norm) > self.norm_std_threshold:
            alerts.append({
                'type': 'high_norm_variance',
                'severity': 'warning',
                'message': f"High norm variance detected: {std_norm/mean_norm:.4f}",
                'collection': metrics['collection'],
            })
        
        # Check zero vector ratio
        total = metrics.get('sample_size', 1)
        zeros = metrics.get('zero_vector_count', 0)
        if total > 0 and (zeros / total) > 0.05:
            alerts.append({
                'type': 'high_zero_vectors',
                'severity': 'warning',
                'message': f"High zero vector ratio: {zeros}/{total}",
                'collection': metrics['collection'],
            })
        
        # Check drift
        if metrics.get('drift_analysis', {}).get('drift_detected', False):
            alerts.append({
                'type': 'embedding_drift',
                'severity': 'critical',
                'message': f"Embedding drift detected: similarity {metrics['drift_analysis'].get('average_cosine_similarity', 0):.4f}",
                'collection': metrics['collection'],
            })
        
        return alerts
    
    def get_all_collections(self) -> List[str]:
        """Get list of all collections."""
        try:
            collections = self.qdrant_client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    def monitor_all_collections(self) -> Dict[str, Any]:
        """Monitor all collections and return summary."""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'collections_analyzed': 0,
            'alerts': [],
            'summary': {},
        }
        
        collections = self.get_all_collections()
        
        for collection in collections:
            try:
                metrics = self.analyze_embedding_quality(collection)
                
                if metrics['status'] == 'analyzed':
                    results['collections_analyzed'] += 1
                    
                    # Check thresholds
                    alerts = self.check_thresholds(metrics)
                    results['alerts'].extend(alerts)
                    
                    # Store summary
                    results['summary'][collection] = {
                        'quality_score': metrics['quality_score'],
                        'vectors_count': metrics.get('sample_size', 0),
                        'needs_review': metrics['quality_score'] < 70 or len(alerts) > 0,
                    }
                    
            except Exception as e:
                logger.error(f"Error analyzing {collection}: {e}")
                results['summary'][collection] = {
                    'error': str(e),
                    'needs_review': True,
                }
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """Check service health and dependencies."""
        try:
            # Check Qdrant connection
            collections = self.get_all_collections()
            
            return {
                'status': 'healthy',
                'service': 'EmbeddingQualityMonitor',
                'timestamp': datetime.utcnow().isoformat(),
                'dependencies': {
                    'qdrant': {
                        'status': 'connected',
                        'collections_count': len(collections),
                    },
                },
                'metadata': {
                    'collection_names': collections,
                },
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': 'EmbeddingQualityMonitor',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'dependencies': {
                    'qdrant': {
                        'status': 'disconnected',
                        'error': str(e),
                    },
                },
            }
    
    def trigger_reingestion(self, collection_name: str) -> Dict[str, Any]:
        """Trigger re-ingestion for a collection."""
        # This would integrate with your ingestion pipeline
        logger.info(f"Re-ingestion triggered for collection: {collection_name}")
        
        return {
            'status': 'triggered',
            'collection': collection_name,
            'timestamp': datetime.utcnow().isoformat(),
            'actions': [
                f'Set reingest flag in metadata for all documents in {collection_name}',
                'Run ingestion pipeline to refresh embeddings',
                'Update metrics after completion',
            ],
        }


def main():
    """Main entry point for monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Embedding Quality Monitor')
    parser.add_argument('--collection', type=str, help='Specific collection to monitor')
    parser.add_argument('--all-collections', action='store_true', help='Monitor all collections')
    parser.add_argument('--thresholds', action='store_true', help='Check threshold violations')
    parser.add_argument('--reingest', type=str, help='Trigger re-ingestion for collection')
    
    args = parser.parse_args()
    
    monitor = EmbeddingQualityMonitor()
    
    if args.reingest:
        result = monitor.trigger_reingestion(args.reingest)
        print(json.dumps(result, indent=2))
        return
    
    if args.all_collections:
        results = monitor.monitor_all_collections()
        print("\n=== Collection Summary ===")
        for collection, summary in results['summary'].items():
            status = "⚠️ NEEDS REVIEW" if summary.get('needs_review', False) else "✅ OK"
            score = summary.get('quality_score', 'N/A')
            print(f"{collection}: {score} - {status}")
        
        if results['alerts']:
            print("\n=== Alerts ===")
            for alert in results['alerts']:
                print(f"[{alert['severity'].upper()}] {alert['message']}")
    
    elif args.collection:
        metrics = monitor.analyze_embedding_quality(args.collection)
        print(json.dumps(metrics, indent=2))
        
        alerts = monitor.check_thresholds(metrics)
        if alerts:
            print("\n=== Alerts ===")
            for alert in alerts:
                print(f"[{alert['severity'].upper()}] {alert['message']}")
    else:
        # Default: monitor all
        results = monitor.monitor_all_collections()
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
