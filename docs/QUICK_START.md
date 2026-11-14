# AI Memory Pipeline - Quick Start Guide

This guide will help you get the AI Memory Pipeline up and running quickly with LM Studio model switching and Qdrant integration.

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **System Requirements**
  - Windows host with sufficient VRAM (minimum 16GB recommended)
  - Python 3.15+ installed
  - Docker Desktop installed and running
  - At least 56GB free system RAM for model loading

- [ ] **Network Configuration**
  - LM Studio server configured to listen on localhost:1234
  - Qdrant accessible at localhost:6333
  - No firewall rules blocking local connections

## Quick Setup (15 minutes)

### Step 1: Start Qdrant Database

```bash
# Navigate to project directory
cd D:/AI-Memory

# Start Qdrant service
docker-compose up -d

# Verify it's running
docker-compose ps
```

Expected output shows `qdrant` container as "healthy".

### Step 2: Load Models in LM Studio

1. Open **LM Studio**
2. Navigate to **Model Catalog**
3. Download and load the following models:

| Model Name | Purpose | Quantization |
|------------|---------|--------------|
| `qwen3-coder-next` | Coding/Chat operations | Q4_K_M recommended |
| `text-embedding-qwen3-embedding-8b` | Embedding generation | Q4_K_M recommended |

**Important**: Load models sequentially (one at a time) to manage VRAM effectively.

### Step 3: Verify LM Studio API

Open PowerShell and run:

```powershell
# Test LM Studio connectivity
curl http://localhost:1234/v1/models
```

You should see both models listed in the response.

### Step 4: Run Ingestion Pipeline Test

```bash
# Ensure virtual environment is activated
.venv\Scripts\activate

# Run ingestion on sample documents
python -m ai_memory_pipeline.run_ingestion
```

## Daily Operations

### Starting the System (2 minutes)

1. **Start Qdrant**:
   ```bash
   docker-compose up -d
   ```

2. **Verify Services**:
   ```powershell
   # Check Qdrant health
   curl http://localhost:6333/readyz
   
   # Check LM Studio
   curl http://localhost:1234/v1/models
   ```

3. **Check VRAM Usage** (if concerned):
   - Open LM Studio → Server tab
   - Monitor "GPU Memory Used" metric
   - Should be <70% under normal operation

### Running Ingestion Tasks

```bash
# Full pipeline run
python scripts/run-ingestion.py

# With custom directory
python scripts/run-ingestion.py --input-dir "D:\Documents\ToProcess"
```

The smart embedder will automatically switch between models as needed.

### Monitoring System Health

#### VRAM Monitoring
- **Warning**: >70% VRAM usage
- **Critical**: >85% VRAM usage  
- **Action Required**: >90% VRAM usage

If VRAM becomes an issue:
1. Unload unused models in LM Studio
2. Reduce batch size in `config.yaml`
3. Consider using lower quantization (Q3 instead of Q4)

#### Log Monitoring
```bash
# View Qdrant logs
docker-compose logs -f qdrant

# Check system health
python scripts/health-check.py
```

## Common Tasks

### Adding New Documents

1. Place documents in your input directory (PDF, DOCX, TXT)
2. Run ingestion:
   ```bash
   python scripts/run-ingestion.py --input-dir "D:\Your\Documents"
   ```

### Backing Up Data (Weekly)

```powershell
# Full backup of Qdrant database
.\scripts\backup-qdrant.ps1 -Destination "\\192.168.0.16\docker\AI-Memory\backups\qdrant"

# Backup LM Studio configuration
python scripts/backup-lm-studio.py --output-dir "D:\AI-Memory\backups\config"
```

See `docs/BACKUP_RESTORE.md` for complete backup procedures.

### Restoring from Backup

```powershell
# Restore Qdrant database
.\scripts\restore-qdrant.ps1 -Source "path\to\backup.dump"

# Restore LM Studio configuration
python scripts/restore-lm-studio.py --config-file "config.json"
```

## Troubleshooting

### Issue: VRAM Exhaustion

**Symptoms**: Model fails to load, OOM errors in LM Studio

**Solutions**:
1. Unload models not currently in use
2. Restart LM Studio to clear memory
3. Consider using Q3 quantization for embedding model

### Issue: Connection Refused

**Check**:
```powershell
# Is Qdrant running?
docker-compose ps

# Can you reach LM Studio?
curl http://localhost:1234/v1/models
```

### Issue: Slow Embedding Generation

**Solutions**:
1. Ensure embedding model is loaded in LM Studio
2. Check VRAM usage - high usage slows inference
3. Reduce batch size in `config.yaml`

## Next Steps

After completing this quick start:

1. **Read Detailed Documentation**
   - `docs/DEPLOYMENT_CHECKLIST.md` - Comprehensive deployment verification
   - `docs/MONITORING_GUIDE.md` - Advanced monitoring and alerting
   - `docs/BACKUP_RESTORE.md` - Complete backup and restore procedures

2. **Configure Automated Backup**
   - Set up Windows Task Scheduler for daily backups
   - See `docs/BACKUP_RESTORE.md` for scheduled task instructions

3. **Customize Configuration**
   - Edit `config.yaml` for your specific needs
   - Adjust chunking parameters, batch sizes, and thresholds

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review detailed documentation in `docs/`
3. Run health check: `python scripts/health-check.py`

---

**Estimated Setup Time**: 15 minutes  
**Daily Operation Time**: 2-5 minutes  
**Weekly Maintenance**: 10 minutes (backup verification)
