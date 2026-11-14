#!/bin/bash
# =============================================================================
# AI Memory Pipeline - NAS Setup Script
# =============================================================================
# Run this script on your NAS to prepare the directory structure
# =============================================================================

set -e  # Exit on error

echo "=========================================="
echo "AI Memory Pipeline - NAS Directory Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directories to create
declare -a DIRS=(
    "/docker/qdrant/storage"
    "/docker/qdrant/config"
    "/docker/qdrant/backups"
    "/docker/ai-memory/logs"
    "/SharedMemory/me"
    "/SharedMemory/wife"
    "/SharedMemory/shared"
)

echo ""
echo "Creating directory structure..."

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}[SKIP]${NC} $dir (already exists)"
    else
        mkdir -p "$dir"
        echo -e "${GREEN}[CREATE]${NC} $dir"
    fi
done

echo ""
echo "Checking for configuration files..."

# Check for config.yaml
if [ -f "/docker/qdrant/config/config.yaml" ]; then
    echo -e "${GREEN}[OK]${NC} config.yaml exists"
else
    echo -e "${YELLOW}[WARNING]${NC} config.yaml not found at /docker/qdrant/config/config.yaml"
    echo "Creating minimal config.yaml..."

    cat > /docker/qdrant/config/config.yaml << 'EOF'
# Minimal Qdrant configuration
log_level: info
service:
  http_port: 6333
  grpc_port: 6334
cluster:
  enabled: false
storage:
  storage_type: file
  path: /qdrant/storage
EOF

    echo -e "${GREEN}[CREATED]${NC} /docker/qdrant/config/config.yaml"
fi

echo ""
echo "Checking for Dockerfile..."
if [ -f "/docker/repositories/AI-Memory/Dockerfile.pipeline" ]; then
    echo -e "${GREEN}[OK]${NC} Dockerfile.pipeline exists"
else
    echo -e "${RED}[ERROR]${NC} Dockerfile.pipeline not found at /docker/repositories/AI-Memory/"
    echo "Please ensure the AI-Memory repository is cloned to /docker/repositories/"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Navigate to /docker/repositories/AI-Memory"
echo "2. Build the custom Qdrant image:"
echo "   docker build -f qdrant/Dockerfile -t qdrant-custom:v1.7.0 ."
echo "3. Deploy all services:"
echo "   docker compose up -d"
echo ""
echo "Directory structure created at:"
for dir in "${DIRS[@]}"; do
    echo "  $dir"
done
