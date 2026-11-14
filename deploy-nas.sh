#!/bin/bash
# =============================================================================
# Deploy AI Memory Pipeline to Synology NAS
# =============================================================================

set -e

echo "=== AI Memory Pipeline Deployment Script ==="
echo "Target: Synology NAS (192.168.0.16)"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker CLI not found. Please install Docker on your NAS."
    echo "See: https://www.synology.com/directory/docker"
    exit 1
fi

echo "✓ Docker version: $(docker --version)"
echo ""

# Stop existing containers
echo "=== Stopping existing containers ==="
docker compose down || true

# Build images (if not already built on NAS)
echo ""
echo "=== Building pipeline image ==="
docker build -f Dockerfile.pipeline -t ai-memory-pipeline:v1 .
echo "✓ Pipeline image built"

# Start services
echo ""
echo "=== Starting services ==="
docker compose up -d

# Wait for containers to start
sleep 5

# Check status
echo ""
echo "=== Container Status ==="
docker ps --filter "name=ai-memory" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Verify health
echo ""
echo "=== Health Checks ==="
echo "Waiting for containers to become healthy..."

sleep 10

docker ps --filter "name=ai-memory" --format "{{.Names}}" | while read name; do
    status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "unknown")
    echo "- $name: $status"
done

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services running on NAS:"
echo "  - Qdrant (Vector DB): http://localhost:6333"
echo "  - API Gateway:        http://localhost:8000"
echo ""
echo "To access from Windows host:"
echo "  - Qdrant: http://192.168.0.16:6333"
echo "  - API:    http://192.168.0.16:8000"
echo ""
echo "Logs:"
echo "  docker compose logs -f ai-memory-pipeline"
echo "  docker compose logs -f qdrant"
