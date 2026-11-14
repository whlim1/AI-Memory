# LM Studio Deployment Checklist

## Pre-Deployment Verification

- [ ] **System Requirements**
  - [ ] Windows host with sufficient VRAM (minimum 16GB recommended)
  - [ ] Python 3.10+ installed and accessible
  - [ ] Docker Desktop installed and running
  - [ ] At least 56GB free system RAM for model loading

- [ ] **Network Configuration**
  - [ ] LM Studio server configured to listen on localhost:1234
  - [ ] Qdrant accessible at localhost:6333
  - [ ] No firewall rules blocking local connections

## Model Installation

### Required Models
- [ ] **Coding Model**: `qwen3-coder-next` (Q4 quantization recommended)
- [ ] **Embedding Model**: `text-embedding-qwen3-embedding-8b` (Q4 quantization recommended)

### Loading Models in LM Studio
1. Open LM Studio
2. Navigate to "Model Catalog"
3. Search for and download each required model:
   - `qwen3-coder-next`
   - `text-embedding-qwen3-embedding-8b`
4. Load models (one at a time recommended for VRAM management):
   - Click on model card
   - Select quantization (Q4_K_M recommended for balance)
   - Click "Load Model"
5. Verify models are loaded in server view

## Configuration Files

### LM Studio Configuration (`config.yaml`)
```yaml
server:
  host: localhost
  port: 1234
  model: text-embedding-qwen3-embedding-8b
```

### Project Configuration (`.env` file)
```bash
# LM Studio API
LM_STUDIO_HOST=localhost
LM_STUDIO_PORT=1234

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=aimemory_docs

# Embedding Settings
EMBEDDING_MODEL=text-embedding-qwen3-embedding-8b
CODING_MODEL=qwen3-coder-next
```

## Post-Deployment Verification

### Test Connectivity
```bash
python scripts/test-connectivity.py
```
Expected output:
- LM Studio connection: ✓
- Qdrant connection: ✓
- Model list: 13 models available

### Run Validation Suite
```bash
python scripts/validate-lm-studio.py
```
Expected result: **6/6 tests passed**

## Daily Operations Checklist

### Starting Services
- [ ] Start Docker Desktop
- [ ] Start Qdrant container: `docker-compose up -d qdrant`
- [ ] Start LM Studio server
  - Open LM Studio
  - Load required models (coding + embedding)
  - Click "Start Server" button
  - Verify server is running on port 1234

### Monitoring
- [ ] Check VRAM usage in LM Studio server view
- [ ] Verify Qdrant health: `http://localhost:6333/health`
- [ ] Review logs for any errors

### Model Management
- [ ] Monitor loaded models (should be 2: coding + embedding)
- [ ] If VRAM issues occur, unload unused model via LM Studio UI
- [ ] Keep backup of model configurations

## Troubleshooting

### Common Issues

1. **Model Not Loading**
   - Check available VRAM
   - Try lower quantization (Q3_K_M instead of Q5)
   - Load models sequentially with restarts between

2. **API Connection Refused**
   - Verify LM Studio server is running
   - Check port 1234 is not in use: `netstat -ano | findstr :1234`
   - Restart LM Studio server

3. **Embedding Dimension Mismatch**
   - Verify correct embedding model is loaded
   - Check model ID matches configuration
   - Reset model cache if needed

### Emergency Procedures

**VRAM Exhaustion:**
```bash
# Stop all services
docker-compose down

# Unload one model in LM Studio UI
# Restart services
docker-compose up -d qdrant
```

**Service Recovery:**
1. Check logs: `docker-compose logs`
2. Verify ports are free
3. Restart individual containers if needed

## Maintenance Schedule

### Weekly
- [ ] Review Qdrant storage usage
- [ ] Check LM Studio model loading times
- [ ] Backup configuration files

### Monthly
- [ ] Update Docker images
- [ ] Review and clean up old embeddings
- [ ] Test backup/restore procedures

## Contact & Support

For issues:
1. Check logs: `scripts/logs/`
2. Run validation: `python scripts/validate-lm-studio.py`
3. Review documentation in `docs/` folder
4. Contact operations team