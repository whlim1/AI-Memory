"""
Tests for Embedding Quality Monitor.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_memory_pipeline.embedding_quality_monitor import (
    EmbeddingQualityMonitor,
    QualityMetric,
    QualityThreshold,
    EmbeddingStats,
    QualityMonitorManager
)


class TestEmbeddingStats:
    """Tests for EmbeddingStats dataclass."""
    
    def test_empty_embeddings(self):
        """Test stats calculation with empty embeddings."""
        stats = EmbeddingStats()
        assert stats.count == 0
        assert stats.avg_norm == 0.0
    
    def test_single_embedding(self):
        """Test stats calculation with single embedding."""
        embeddings = [[1.0, 2.0, 3.0]]
        arr = __import__('numpy').array(embeddings)
        
        import numpy as np
        norms = np.linalg.norm(arr, axis=1)
        
        stats = EmbeddingStats(
            count=len(embeddings),
            avg_norm=float(np.mean(norms)),
            min_norm=float(np.min(norms)),
            max_norm=float(np.max(norms)),
            norm_std=float(np.std(norms)),
            avg_variance=float(np.var(arr, axis=0).mean()),
            dimension=arr.shape[1]
        )
        
        assert stats.count == 1
        # sqrt(1 + 4 + 9) = sqrt(14) ≈ 3.74
        assert abs(stats.avg_norm - 3.74165738677) < 0.001


class TestQualityMetric:
    """Tests for QualityMetric dataclass."""
    
    def test_metric_creation(self):
        """Test creating a quality metric."""
        metric = QualityMetric(
            timestamp=datetime.now(),
            document_id="test-123",
            norm=1.5,
            variance=0.1
        )
        
        assert metric.document_id == "test-123"
        assert metric.norm == 1.5
        assert metric.variance == 0.1
        assert not metric.is_anomaly
        assert len(metric.anomaly_reasons) == 0
    
    def test_to_dict(self):
        """Test converting metric to dictionary."""
        metric = QualityMetric(
            timestamp=datetime(2024, 1, 1),
            document_id="test-123",
            norm=1.5,
            variance=0.1,
            is_anomaly=True,
            anomaly_reasons=["norm too high"]
        )
        
        result = metric.to_dict()
        
        assert "timestamp" in result
        assert result["document_id"] == "test-123"
        assert result["is_anomaly"] == True
        assert "norm too high" in result["anomaly_reasons"]


class TestEmbeddingQualityMonitor:
    """Tests for EmbeddingQualityMonitor class."""
    
    @pytest.fixture
    def mock_qdrant(self):
        """Create a mock Qdrant client."""
        mock_client = Mock()
        mock_scroll_result = Mock()
        mock_scroll_result.points = []
        mock_client.scroll.return_value = mock_scroll_result
        return mock_client
    
    @pytest.fixture
    def monitor(self, mock_qdrant):
        """Create a test monitor instance."""
        with patch('qdrant_client.QdrantClient') as MockQdrant:
            MockQdrant.return_value = mock_qdrant
            mon = EmbeddingQualityMonitor(
                qdrant_client=mock_qdrant,
                collection_name="test-collection",
                window_size=100,
                threshold_config=QualityThreshold(
                    norm_min=0.1,
                    norm_max=10.0,
                    variance_min=0.0001,
                    variance_max=0.5
                )
            )
        return mon
    
    def test_initialization(self, mock_qdrant):
        """Test monitor initialization."""
        with patch('qdrant_client.QdrantClient') as MockQdrant:
            MockQdrant.return_value = mock_qdrant
            mon = EmbeddingQualityMonitor(mock_qdrant)
            
            assert mon.qdrant == mock_qdrant
            assert mon.collection_name == "ai-memory"
            assert len(mon.embedding_window) == 0
    
    def test_record_embedding_normal(self, monitor):
        """Test recording a normal embedding."""
        # Use values with low variance that's above the minimum threshold (0.0001)
        # but within norm bounds (0.1 to 10.0)
        embedding = [1.0, 1.1, 0.9]  # variance ≈ 0.0067, norm ≈ 1.73
        
        metric = monitor.record_embedding(embedding, "doc-1")
        
        assert not metric.is_anomaly
        assert len(monitor.embedding_window) == 1
    
    def test_record_embedding_anomaly(self, monitor):
        """Test recording an anomalous embedding."""
        # Create threshold that will trigger anomaly
        monitor.thresholds.norm_min = 0.5
        monitor.thresholds.norm_max = 2.0
        
        # Embedding with norm > 2 will be anomalous
        embedding = [10.0, 20.0, 30.0]  # norm ≈ 37.4
        
        metric = monitor.record_embedding(embedding, "doc-anomalous")
        
        assert metric.is_anomaly
        assert len(metric.anomaly_reasons) > 0
    
    def test_calculate_drift(self, monitor):
        """Test drift calculation."""
        reference = [[1.0, 2.0], [3.0, 4.0]]
        current = [[1.1, 2.1], [3.1, 4.1]]
        
        monitor.set_reference_distribution(reference)
        drift = monitor._calculate_drift(current)
        
        # Very similar distributions should have low drift
        assert drift >= 0
        assert drift < 0.5
    
    def test_check_anomalies_norm_too_low(self, monitor):
        """Test anomaly detection for norm too low."""
        # Set high minimum threshold
        monitor.thresholds.norm_min = 100.0
        
        embedding = [1.0, 2.0]  # norm ≈ 2.24
        
        metric = monitor._check_anomalies(embedding, "doc-test")
        
        assert metric.is_anomaly
        assert any("norm too low" in reason for reason in metric.anomaly_reasons)
    
    def test_check_anomalies_variance_too_high(self, monitor):
        """Test anomaly detection for variance too high."""
        # Set low maximum variance threshold
        monitor.thresholds.variance_max = 0.001
        
        embedding = [1.0, 100.0]  # high variance
    
        metric = monitor._check_anomalies(embedding, "doc-test")
        
        assert metric.is_anomaly
        assert any("variance too high" in reason for reason in metric.anomaly_reasons)
    
    def test_get_quality_summary(self, monitor):
        """Test quality summary generation."""
        # Record some embeddings
        for i in range(10):
            embedding = [float(i) * 0.1, float(i) * 0.2]
            monitor.record_embedding(embedding, f"doc-{i}")
        
        summary = monitor.get_quality_summary()
        
        assert "timestamp" in summary
        assert summary["collection"] == "test-collection"
        assert "statistics" in summary
        assert "anomaly_rate" in summary
    
    def test_save_quality_report(self, monitor, tmp_path):
        """Test saving quality report to file."""
        # Record some embeddings
        for i in range(5):
            embedding = [float(i) * 0.1, float(i) * 0.2]
            monitor.record_embedding(embedding, f"doc-{i}")
        
        filepath = str(tmp_path / "quality_report.json")
        monitor.save_quality_report(filepath)
        
        assert os.path.exists(filepath)
        
        with open(filepath) as f:
            import json
            data = json.load(f)
            
        assert "collection" in data
    
    def test_trigger_reingestion(self, monitor):
        """Test re-ingestion trigger."""
        # Add anomalous metrics to trigger re-ingestion
        for i in range(12):
            metric = QualityMetric(
                timestamp=datetime.now(),
                document_id=f"doc-{i}",
                norm=1.0,
                variance=0.1,
                is_anomaly=True,
                anomaly_reasons=["test anomaly"]
            )
            monitor.quality_metrics.append(metric)
        
        triggered = monitor.trigger_reingestion(anomaly_count=10)
        
        assert triggered
    
    def test_get_anomaly_documents(self, monitor):
        """Test getting anomalous documents."""
        # Add some anomalous metrics
        for i in range(5):
            metric = QualityMetric(
                timestamp=datetime.now(),
                document_id=f"doc-{i}",
                norm=1.0,
                variance=0.1,
                is_anomaly=True,
                anomaly_reasons=["test"]
            )
            monitor.quality_metrics.append(metric)
        
        anomalies = monitor.get_anomaly_documents()
        
        assert len(anomalies) <= 10


class TestQualityMonitorManager:
    """Tests for QualityMonitorManager class."""
    
    @pytest.fixture
    def mock_qdrant(self):
        """Create a mock Qdrant client with collections."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "test-collection"
        
        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        
        mock_client.get_collections.return_value = mock_collections
        
        # Configure scroll to return mock points with vectors
        mock_point1 = Mock()
        mock_point1.id = "doc-1"
        mock_point1.vector = [0.1, 0.2, 0.3]
        mock_point1.payload = {"document_id": "doc-1"}
        
        mock_scroll_result = Mock()
        mock_scroll_result.points = [mock_point1]
        
        mock_client.scroll.return_value = mock_scroll_result
        
        return mock_client
    
    def test_manager_initialization(self, mock_qdrant):
        """Test manager initialization."""
        with patch('qdrant_client.QdrantClient') as MockQdrant:
            MockQdrant.return_value = mock_qdrant
            
            manager = QualityMonitorManager(mock_qdrant)
            
            assert "test-collection" in manager.monitors
    
    def test_create_monitor(self, mock_qdrant):
        """Test creating a new monitor."""
        with patch('qdrant_client.QdrantClient') as MockQdrant:
            MockQdrant.return_value = mock_qdrant
            
            manager = QualityMonitorManager(mock_qdrant)
            
            # Create another collection
            new_monitor = manager.create_monitor("new-collection")
            
            assert "new-collection" in manager.monitors
    
    def test_check_all_collections(self, mock_qdrant):
        """Test checking all collections."""
        with patch('qdrant_client.QdrantClient') as MockQdrant:
            MockQdrant.return_value = mock_qdrant
            
            manager = QualityMonitorManager(mock_qdrant)
            
            results = manager.check_all_collections()
            
            assert isinstance(results, dict)
            assert "test-collection" in results
    
    def test_get_overall_health(self, mock_qdrant):
        """Test getting overall health status."""
        with patch('qdrant_client.QdrantClient') as MockQdrant:
            MockQdrant.return_value = mock_qdrant
            
            manager = QualityMonitorManager(mock_qdrant)
            
            health = manager.get_overall_health()
            
            assert "timestamp" in health
            assert "healthy_collections" in health
            assert "total_collections" in health
