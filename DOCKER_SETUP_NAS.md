# =============================================================================
# AI Memory Pipeline - Docker Setup Guide
# =============================================================================
# This guide covers deployment on the NAS (192.168.0.16)
#
# Directory Structure:
#   /docker/              - All Docker containers and configurations
#   /docker/repositories/ - Git repositories
#   /SharedMemory/        - Shared documents (you + wife)
#   /docker/qdrant/       - Qdrant storage, config, backups
#   /docker/ai-memory/    - AI Memory Pipeline data and logs
#
# =============================================================================

## Prerequisites

1. **Docker installed on NAS**
   ```bash
   docker --version
   ```

2. **Directory structure created on NAS**
   ```bash
   mkdir -p /docker/qdrant/{storage,config,backups}
   mkdir -p /docker/ai-memory/logs
   mkdir -p /SharedMemory/{me,wife,shared}
   ```

3. **Configuration files**
   - Copy `config.yaml` to `/docker/qdrant/config/`
   - Ensure `config.yaml` exists (do not leave empty)

## Quick Start

```bash
# Navigate to AI Memory directory
cd /docker/repositories/AI-Memory

# Build the custom Qdrant image (with curl for healthcheck)
docker build -f qdrant/Dockerfile -t qdrant-custom:v1.7.0 .

# Deploy all services
docker compose up -d

# Check status
docker compose ps
```

## Monitoring

```bash
# View logs
docker compose logs -f qdrant
docker compose logs -f ai-memory-pipeline

# Health checks
curl http://localhost:6333/readyz  # Qdrant
curl http://localhost:8000/health   # API Gateway

# Check container status
docker inspect --format='{{.State.Health.Status}}' ai-memory-qdrant
docker inspect --format='{{.State.Health.Status}}' ai-memory-pipeline
```

## Directory Mounts Explained

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `/docker/qdrant/storage` | `/qdrant/storage` | Vector storage, WAL, snapshots |
| `/docker/qdrant/config` | `/qdrant/config:ro` | Qdrant configuration (read-only) |
| `/docker/qdrant/backups` | `/qdrant/backups` | Backup snapshots |
| `/SharedMemory` | `/shared_memory:rw` | Shared documents (you + wife) |
| `/SharedMemory/me` | `/shared_memory/me` | Your personal documents |
| `/SharedMemory/wife` | `/shared_memory/wife` | Your wife's documents |
| `/SharedMemory/shared` | `/shared_memory/shared` | Shared family documents |
| `/docker/ai-memory/logs` | `/app/logs:rw` | Application logs |

## Configuration

### Environment Variables (in docker-compose.yml)

```yaml
environment:
  - QDRANT_URL=http://qdrant:6333           # Qdrant connection
  - SHARED_MEMORY_PATH=/shared_memory        # Shared memory root
  - MY_DOCUMENTS=/shared_memory/me          # Your docs path
  - WIFE_DOCUMENTS=/shared_memory/wife      # Wife's docs path
  - LM_STUDIO_URL=http://localhost:1234     # Local LLM API
  - CHUNK_SIZE=500                          # Text chunk size
  - CHUNK_OVERLAP=50                        # Chunk overlap tokens
  - VECTOR_SIZE=768                         # Embedding dimension
  - EXACT_THRESHOLD=0.95                    # Exact match threshold
  - FUZZY_THRESHOLD=0.85                    # Fuzzy match threshold
```

## Data Persistence

All critical data is stored on the NAS:

- **Vectors**: `/docker/qdrant/storage/`
- **Backups**: `/docker/qdrant/backups/`
- **Logs**: `/docker/ai-memory/logs/`
- **Documents**: `/SharedMemory/*` (me, wife, shared)

## Backup Strategy

```bash
# Create snapshot backup
curl -X POST http://localhost:6333/snapshots/share

# List backups
curl http://localhost:6333/snapshots

# Restore from backup
curl -X POST http://localhost:6333/snapshots/restore \
  -H "Content-Type: application/json" \
  -d '{"snapshot": "/qdrant/backups/snapshot-name"}'
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker compose logs <service_name>

# Verify directories exist and have correct permissions
ls -la /docker/qdrant/
ls -la /SharedMemory/
```

### Qdrant health check failing
```bash
# Test curl inside container
docker exec ai-memory-qdrant curl http://localhost:6333/readyz

# Restart with verbose logging
docker compose down
docker compose up qdrant
```

### Can't access SharedMemory
```bash
# Verify mount works
docker exec ai-memory-pipeline ls -la /shared_memory/

# Check SMB connection (if applicable)
df -h | grep SharedMemory
```

## Updating

```bash
# Pull latest code
cd /docker/repositories/AI-Memory
git pull origin master

# Rebuild and restart
docker compose down
docker build -f Dockerfile.pipeline -t ai-memory-pipeline:latest .
docker compose up -d
```

## Next Steps

1. **Configure LM Studio** on the NAS (if not already)
2. **Upload test documents** to `/SharedMemory/me/`
3. **Run ingestion pipeline** via API or scripts
4. **Verify embeddings** in Qdrant dashboard
5. **Set up scheduled backups**

## Support

For issues, check:
- Logs: `docker compose logs -f ai-memory-pipeline`
- Qdrant docs: https://qdrant.tech/documentation/
- Project README: `/docker/repositories/AI-Memory/README.md`
