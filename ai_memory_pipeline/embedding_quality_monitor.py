"""
Embedding Quality Monitoring Service for AI Memory Pipeline.

This module provides real-time monitoring of embedding quality, tracking:
- Embedding drift and distribution shifts
- Quality metrics (norms, sparsity, variance)
- Anomaly detection for embedding outliers
- Automatic re-ingestion triggers when quality thresholds are breached
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
import hashlib

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, ScoredPoint, PointStruct

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingStats:
    """Statistics for a set of embeddings."""
    count: int = 0
    avg_norm: float = 0.0
    min_norm: float = float('inf')
    max_norm: float = 0.0
    norm_std: float = 0.0
    avg_variance: float = 0.0
    dimension: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class QualityMetric:
    """Quality metric for a single embedding."""
    timestamp: datetime
    document_id: str
    norm: float
    variance: float
    is_anomaly: bool = False
    anomaly_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "document_id": self.document_id,
            "norm": self.norm,
            "variance": self.variance,
            "is_anomaly": self.is_anomaly,
            "anomaly_reasons": self.anomaly_reasons
        }


@dataclass 
class QualityThreshold:
    """Quality thresholds for anomaly detection."""
    norm_min: float = 0.1
    norm_max: float = 10.0
    variance_min: float = 0.0001
    variance_max: float = 0.5
    anomaly_threshold_percent: float = 2.0  # Standard deviations
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EmbeddingQualityMonitor:
    """
    Monitor embedding quality and detect anomalies in real-time.
    
    Tracks embedding statistics over time and can trigger re-ingestion
    when quality thresholds are breached or drift is detected.
    """
    
    def __init__(self, 
                 qdrant_client: QdrantClient,
                 collection_name: str = "ai-memory",
                 window_size: int = 1000,
                 threshold_config: Optional[QualityThreshold] = None):
        """
        Initialize the embedding quality monitor.
        
        Args:
            qdrant_client: Active Qdrant client connection
            collection_name: Name of the collection to monitor
            window_size: Number of recent embeddings to track for statistics
            threshold_config: Quality thresholds for anomaly detection
        """
        self.qdrant = qdrant_client
        self.collection_name = collection_name
        self.window_size = window_size
        self.thresholds = threshold_config or QualityThreshold()
        
        # Statistics tracking with sliding window
        self.embedding_window = deque(maxlen=window_size)
        self.quality_metrics: List[QualityMetric] = []
        
        # Drift detection
        self.reference_distribution: Optional[np.ndarray] = None
        self.drift_history: List[Tuple[datetime, float]] = []
        
        logger.info(f"EmbeddingQualityMonitor initialized for collection '{collection_name}'")
    
    def _calculate_embedding_stats(self, embeddings: List[List[float]]) -> EmbeddingStats:
        """Calculate statistics for a set of embeddings."""
        if not embeddings:
            return EmbeddingStats()
            
        arr = np.array(embeddings)
        norms = np.linalg.norm(arr, axis=1)
        
        stats = EmbeddingStats(
            count=len(embeddings),
            avg_norm=float(np.mean(norms)),
            min_norm=float(np.min(norms)),
            max_norm=float(np.max(norms)),
            norm_std=float(np.std(norms)),
            avg_variance=float(np.var(arr, axis=0).mean()),
            dimension=arr.shape[1] if len(arr.shape) > 1 else 0
        )
        
        return stats
    
    def _calculate_drift(self, current_embeddings: List[List[float]]) -> float:
        """Calculate drift between current and reference distribution."""
        if not current_embeddings or self.reference_distribution is None:
            return 0.0
            
        current_arr = np.array(current_embeddings)
        current_mean = np.mean(current_arr, axis=0)
        
        # Cosine similarity between means
        dot_product = np.dot(self.reference_distribution, current_mean)
        norms = np.linalg.norm(self.reference_distribution) * np.linalg.norm(current_mean)
        
        if norms > 0:
            drift = float(1 - (dot_product / norms))
        else:
            drift = 0.0
            
        return drift
    
    def _check_anomalies(self, embedding: List[float], doc_id: str) -> QualityMetric:
        """Check if an embedding is anomalous based on current statistics."""
        metric = QualityMetric(
            timestamp=datetime.now(),
            document_id=doc_id,
            norm=float(np.linalg.norm(embedding)),
            variance=float(np.var(embedding))
        )
        
        # Check norms
        if metric.norm < self.thresholds.norm_min:
            metric.anomaly_reasons.append(f"norm too low: {metric.norm:.4f} < {self.thresholds.norm_min}")
            
        if metric.norm > self.thresholds.norm_max:
            metric.anomaly_reasons.append(f"norm too high: {metric.norm:.4f} > {self.thresholds.norm_max}")
        
        # Check variance
        if metric.variance < self.thresholds.variance_min:
            metric.anomaly_reasons.append(f"variance too low: {metric.variance:.6f} < {self.thresholds.variance_min}")
            
        if metric.variance > self.thresholds.variance_max:
            metric.anomaly_reasons.append(f"variance too high: {metric.variance:.6f} > {self.thresholds.variance_max}")
        
        # Check against window statistics
        if len(self.embedding_window) >= 10:
            arr = np.array(list(self.embedding_window))
            means = np.mean(arr, axis=0)
            stds = np.std(arr, axis=0) + 1e-8
            
            z_scores = np.abs((np.array(embedding) - means) / stds)
            max_z_score = float(np.max(z_scores))
            
            if max_z_score > self.thresholds.anomaly_threshold_percent:
                metric.anomaly_reasons.append(f"z-score too high: {max_z_score:.2f} > {self.thresholds.anomaly_threshold_percent}")
        
        metric.is_anomaly = len(metric.anomaly_reasons) > 0
        return metric
    
    def record_embedding(self, embedding: List[float], doc_id: str) -> QualityMetric:
        """
        Record a new embedding and check for anomalies.
        
        Args:
            embedding: The embedding vector to record
            doc_id: Document ID for tracking
            
        Returns:
            QualityMetric with anomaly information
        """
        self.embedding_window.append(embedding)
        
        metric = self._check_anomalies(embedding, doc_id)
        self.quality_metrics.append(metric)
        
        # Keep only recent metrics (last 10000)
        if len(self.quality_metrics) > 10000:
            self.quality_metrics = self.quality_metrics[-10000:]
            
        return metric
    
    def set_reference_distribution(self, embeddings: List[List[float]]):
        """Set the reference distribution for drift detection."""
        arr = np.array(embeddings)
        self.reference_distribution = np.mean(arr, axis=0)
        logger.info(f"Reference distribution set with {len(embeddings)} embeddings")
    
    def check_drift(self) -> Tuple[bool, float]:
        """
        Check if drift has exceeded acceptable thresholds.
        
        Returns:
            Tuple of (is_drift_detected, drift_score)
        """
        # Get recent embeddings from Qdrant
        results = self.qdrant.scroll(
            collection_name=self.collection_name,
            limit=100,
            with_vectors=True
        )
        
        if not results.points:
            return False, 0.0
            
        current_embeddings = [p.vector for p in results.points]
        drift_score = self._calculate_drift(current_embeddings)
        
        self.drift_history.append((datetime.now(), drift_score))
        
        is_drift = drift_score > 0.1  # 10% drift threshold
        if is_drift:
            logger.warning(f"Drift detected: {drift_score:.4f}")
            
        return is_drift, drift_score
    
    def get_quality_summary(self) -> Dict:
        """Get a summary of embedding quality metrics."""
        stats = self._calculate_embedding_stats(list(self.embedding_window))
        
        anomalies = [m for m in self.quality_metrics if m.is_anomaly]
        anomaly_rate = len(anomalies) / max(len(self.quality_metrics), 1)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "collection": self.collection_name,
            "statistics": stats.to_dict(),
            "anomaly_rate": anomaly_rate,
            "total_metrics": len(self.quality_metrics),
            "drift_history_count": len(self.drift_history),
            "thresholds": self.thresholds.to_dict()
        }
    
    def save_quality_report(self, filepath: str):
        """Save quality report to file."""
        summary = self.get_quality_summary()
        
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
            
        logger.info(f"Quality report saved to {filepath}")
    
    def get_anomaly_documents(self, limit: int = 10) -> List[QualityMetric]:
        """Get documents with anomalous embeddings."""
        anomalies = [m for m in self.quality_metrics if m.is_anomaly]
        return sorted(anomalies, key=lambda x: len(x.anomaly_reasons), reverse=True)[:limit]
    
    def trigger_reingestion(self, anomaly_count: int = 10) -> bool:
        """
        Trigger re-ingestion for documents with anomalous embeddings.
        
        Args:
            anomaly_count: Number of anomalies needed to trigger re-ingestion
            
        Returns:
            True if re-ingestion was triggered
        """
        current_anomalies = [m for m in self.quality_metrics[-100:] if m.is_anomaly]
        
        if len(current_anomalies) >= anomaly_count:
            logger.warning(f"Re-ingestion triggered: {len(current_anomalies)} anomalies detected")
            
            # Log document IDs that need re-ingestion
            doc_ids = [m.document_id for m in current_anomalies[:10]]
            logger.info(f"Documents requiring re-ingestion: {doc_ids}")
            
            return True
            
        return False


class QualityMonitorManager:
    """
    Manages multiple embedding quality monitors for different collections.
    """
    
    def __init__(self, qdrant_client: QdrantClient):
        self.qdrant = qdrant_client
        self.monitors: Dict[str, EmbeddingQualityMonitor] = {}
        
        # Get all collections
        collections = self.qdrant.get_collections().collections
        for collection in collections:
            self.create_monitor(collection.name)
    
    def create_monitor(self, collection_name: str) -> EmbeddingQualityMonitor:
        """Create a new monitor for a collection."""
        if collection_name not in self.monitors:
            self.monitors[collection_name] = EmbeddingQualityMonitor(
                self.qdrant,
                collection_name=collection_name
            )
        return self.monitors[collection_name]
    
    def get_monitor(self, collection_name: str) -> Optional[EmbeddingQualityMonitor]:
        """Get monitor for a collection."""
        return self.monitors.get(collection_name)
    
    def check_all_collections(self) -> Dict[str, bool]:
        """Check all collections for drift or anomalies."""
        results = {}
        for name, monitor in self.monitors.items():
            is_drift, _ = monitor.check_drift()
            summary = monitor.get_quality_summary()
            
            # Check if anomaly rate exceeds threshold
            is_healthy = not is_drift and (summary["anomaly_rate"] < 0.1)
            results[name] = is_healthy
            
        return results
    
    def get_overall_health(self) -> Dict:
        """Get overall health status of all monitored collections."""
        health_checks = self.check_all_collections()
        
        healthy_count = sum(1 for v in health_checks.values() if v)
        total_count = len(health_checks)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "healthy_collections": healthy_count,
            "total_collections": total_count,
            "collection_status": health_checks
        }
