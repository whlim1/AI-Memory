# Phase 5 Services Deployment Guide

This guide explains how to deploy the three Phase 5 services (Embedding Quality Monitor, Model Caching Strategy, Dynamic Chunking Service) using Portainer v2 API.

## Overview

The Phase 5 deployment includes:

| Service | Port | Description |
|---------|------|-------------|
| embedding-quality-monitor | 9091 | Monitors embedding quality and drift |
| model-caching-strategy | 9092 | Manages model caching for LM Studio |
| dynamic-chunking-service | 9093 | Dynamically adjusts text chunk sizes |

## Image Source

All Phase 5 services are deployed from GitHub Container Registry (GHCR):
- Repository: `ghcr.io/whlim1/aiplatform`
- Images: `embedding-quality-monitor`, `model-caching-strategy`, `dynamic-chunking-service`

## Prerequisites

- Portainer v2.45+ running at `http://192.168.0.16:9000`
- Docker endpoint configured in Portainer (Endpoint ID: 3)
- Access to the docker-compose.monitoring.yml file
- Python 3.11-slim image available

## Deployment Methods

### Method 1: PowerShell Script (Recommended for Windows)

```powershell
# Navigate to the Monitoring directory
cd \\192.168.0.16\docker\AI-Memory\Monitoring

# Run the deployment script
.\deploy-phase5.ps1
```

### Method 2: Python Script

```bash
# Using the simple API deployment script
python deploy_phase5_simple.py

# Or using the full-featured script
python deploy_portainer_v2_correct.py
```

## What Gets Deployed

The deployment creates a Docker Compose stack named `phase5-services` with three containers:

### 1. Embedding Quality Monitor
```yaml
image: python:3.11-slim
ports:
  - "9091:9091"
environment:
  - EQM_QUALITY_THRESHOLD=0.85
  - EQM_DRIFT_THRESHOLD=0.10
  - QDRANT_URL=http://192.168.0.16:6333
```

### 2. Model Caching Strategy
```yaml
image: python:3.11-slim
ports:
  - "9092:9092"
environment:
  - MCM_MAX_CACHE_SIZE=2
  - LM_STUDIO_URL=http://host.docker.internal:1234
```

### 3. Dynamic Chunking Service
```yaml
image: python:3.11-slim
ports:
  - "9093:9093"
environment:
  - DCS_DEFAULT_CHUNK_SIZE=500
  - DCS_OVERLAP_RATIO=0.1
```

## Verification

### Via Portainer UI

1. Open Portainer at `http://192.168.0.16:9000`
2. Navigate to **Stacks** -> **phase5-services**
3. Verify all 3 containers are shown as "Running"

### Via Command Line (after connecting to NAS)

```bash
# Check container status via Docker CLI
docker ps --filter "name=mon_"
```

### Via Metrics Endpoints

```bash
# Test each service is responding
curl http://192.168.0.16:9091/metrics
curl http://192.168.0.16:9092/metrics
curl http://192.168.0.16:9093/metrics
```

## Configuration

### Environment Variables

#### Embedding Quality Monitor
- `EQM_QUALITY_THRESHOLD=0.85` - Minimum quality score threshold
- `EQM_DRIFT_THRESHOLD=0.10` - Maximum allowed drift before alerting
- `EQM_CHECK_INTERVAL=3600` - Check frequency in seconds (default: 1 hour)
- `EQM_HISTORY_SIZE=1000` - Number of embeddings to track for baseline
- `QDRANT_URL=http://192.168.0.16:6333` - Qdrant database URL

#### Model Caching Strategy
- `MCM_MAX_CACHE_SIZE=2` - Maximum number of models to cache
- `MCM_EVICTION_POLICY=lru` - Cache eviction policy (lru, fifo)
- `MCM_PERSIST_CACHE=true` - Persist cache between restarts
- `LM_STUDIO_URL=http://host.docker.internal:1234` - LM Studio API URL

#### Dynamic Chunking Service
- `DCS_DEFAULT_CHUNK_SIZE=500` - Default chunk size in tokens
- `DCS_OVERLAP_RATIO=0.1` - Overlap between chunks (10%)
- `DCS_CODE_CHUNK_SIZE=300` - Chunk size for code content
- `DCS_PROSE_CHUNK_SIZE=600` - Chunk size for prose content

### Modifying Configuration

To change environment variables:

1. Edit the `docker-compose.monitoring.yml` file
2. Re-run the deployment script:
   ```powershell
   .\deploy-phase5.ps1
   ```

## Monitoring

### Prometheus Integration

The services expose metrics at their respective ports:
- Embedding Quality Monitor: `http://192.168.0.16:9091/metrics`
- Model Caching Strategy: `http://192.168.0.16:9092/metrics`
- Dynamic Chunking Service: `http://192.168.0.16:9093/metrics`

These are automatically scraped by the existing Prometheus instance.

### Grafana Dashboards

Create custom dashboards in Grafana at `http://192.168.0.16:3000` using:
- Data source: Prometheus
- Metrics prefix: `eqm_`, `mcm_`, `dcs_`

## Troubleshooting

### Container Won't Start

Check logs in Portainer UI or via Docker CLI:
```bash
docker logs mon_embedding_quality_monitor
docker logs mon_model_caching_strategy
docker logs mon_dynamic_chunking_service
```

### Connection Issues

Verify network connectivity:
```bash
# Test Qdrant connection
curl http://192.168.0.16:6333

# Test LM Studio connection (from within container)
docker exec -it mon_model_caching_strategy curl http://host.docker.internal:1234
```

### Configuration Errors

1. Verify environment variables in docker-compose.yml
2. Check that all required services are running:
   ```bash
   docker ps --filter "name=mon_"
   ```
3. Restart the stack via Portainer UI

## Update Process

To update the Phase 5 services:

```powershell
# 1. Pull latest changes
cd \\192.168.0.16\docker\AI-Memory
git pull

# 2. Navigate to Monitoring directory
cd Monitoring

# 3. Re-deploy
.\deploy-phase5.ps1
```

## Uninstall

To remove the Phase 5 services:

```powershell
# Option 1: Via Portainer UI
# Navigate to Stacks -> phase5-services -> Remove

# Option 2: Via Docker CLI
docker stack rm phase5-services

# Option 3: Via API (requires additional script)
```

## Support

For issues or questions:
- Check the main [PHASE5_SERVICES_GUIDE.md](../docs/PHASE5_SERVICES_GUIDE.md)
- Review service logs in Portainer
- Verify network connectivity between containers
