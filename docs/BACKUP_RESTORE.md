# Backup and Restore Procedures for LM Studio

## Overview

This guide covers backup and restore procedures for:
- LM Studio model configurations
- Qdrant embeddings database
- Project configuration files

## Backup Strategy

### Frequency Recommendations
- **Configuration**: Daily (automated)
- **Qdrant Database**: Weekly + daily incremental
- **Model Files**: Monthly or when models are updated

### Storage Locations

**Local Backups:**
```
\\192.168.0.16\docker\AI-Memory\backups\
├── config\
│   ├── lm-studio-\[date\].json
│   └── project-\[date\].json
├── qdrant\
│   ├── full-\[date\].dump
│   └── incremental-\[date\].dump
└── models\
    └── \[model-id\]-\[date\].json
```

## Configuration Backup

### Export LM Studio Models

```python
import requests
import json
from datetime import datetime
from pathlib import Path

def backup_lm_studio_models(output_dir="backups/config"):
    """Backup current LM Studio model configuration."""
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Fetch models from LM Studio
        response = requests.get("http://localhost:1234/v1/models", timeout=10)
        
        if response.status_code == 200:
            models_data = response.json()
            
            # Create backup file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = output_path / f"lm-studio-{timestamp}.json"
            
            # Add metadata
            backup_data = {
                "backup_timestamp": timestamp,
                "backup_type": "full",
                "models": models_data['data']
            }
            
            # Save backup
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            print(f"✓ LM Studio models backed up to: {backup_file}")
            return str(backup_file)
            
        else:
            print(f"✗ Failed to fetch models: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Backup failed: {e}")
        return None

# Usage
backup_lm_studio_models()
```

### Export Project Configuration

```python
import json
from datetime import datetime
from pathlib import Path

def backup_project_config(output_dir="backups/config"):
    """Backup project configuration files."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = output_path / f"project-{timestamp}.json"
    
    # Configuration to backup
    config_backup = {
        "backup_timestamp": timestamp,
        "config_files": {
            "docker-compose.yml": {
                "path": "docker-compose.yml",
                "content_hash": ""  # Will be computed
            },
            ".env.example": {
                "path": ".env.example",
                "content_hash": ""
            }
        },
        "models": {
            "coding_model": "qwen3-coder-next",
            "embedding_model": "text-embedding-qwen3-embedding-8b"
        },
        "endpoints": {
            "lm_studio_host": "localhost",
            "lm_studio_port": 1234,
            "qdrant_host": "localhost",
            "qdrant_port": 6333
        }
    }
    
    # Save backup
    with open(backup_file, 'w') as f:
        json.dump(config_backup, f, indent=2)
    
    print(f"✓ Project config backed up to: {backup_file}")
    return str(backup_file)

# Usage
backup_project_config()
```

## Qdrant Database Backup

### Full Database Export

```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import json
from datetime import datetime
from pathlib import Path
import os

def backup_qdrant_database(
    collection_name="aimemory_docs",
    output_dir="backups/qdrant"
):
    """Backup entire Qdrant database to JSON."""
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = output_path / f"full-{timestamp}.json"
    
    try:
        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)
        
        # Get collection info
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.vectors_count
        
        print(f"Found {total_points} points in '{collection_name}'")
        
        # Collect all points (handle pagination)
        all_points = []
        offset = None
        
        batch_size = 100
        while True:
            result, next_offset = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vector=False  # Can enable if needed
            )
            
            all_points.extend(result)
            offset = next_offset
            
            print(f"Retrieved {len(all_points)}/{total_points} points")
            
            if offset is None:
                break
        
        # Create backup data
        backup_data = {
            "backup_timestamp": timestamp,
            "collection_name": collection_name,
            "total_points": len(all_points),
            "points": [
                {
                    "id": point.id,
                    "payload": point.payload,
                    "vector": None  # Not including vectors for size reasons
                }
                for point in all_points
            ]
        }
        
        # Save backup
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"✓ Qdrant backup saved to: {backup_file}")
        return str(backup_file)
        
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# Usage
backup_qdrant_database()
```

### Docker-Based Backup (Recommended for Large Databases)

```bash
#!/bin/bash

# Qdrant Docker Backup Script
# This script creates a backup of the Qdrant data directory

set -e

BACKUP_DIR="\\192.168.0.16\docker\AI-Memory\backups\qdrant"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="full-${DATE}.tar.gz"

echo "Starting Qdrant backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Stop the container temporarily (or use snapshot feature)
docker-compose stop qdrant

# Copy data directory
docker cp ai-memory-qdrant-1:/qdrant/storage "$BACKUP_DIR/${DATE}_storage"

# Restart the container
docker-compose start qdrant

# Create compressed archive
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}" "${DATE}_storage"

# Remove uncompressed directory
rm -rf "${BACKUP_DIR}/${DATE}_storage"

echo "✓ Backup created: ${BACKUP_DIR}/${BACKUP_NAME}"
```

## Restore Procedures

### Restore LM Studio Configuration

```python
import requests
import json
from pathlib import Path

def restore_lm_studio_models(backup_file):
    """Restore LM Studio models from backup."""
    
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)
    
    print(f"Restoring {len(backup_data['models'])} models...")
    
    # Note: LM Studio doesn't have a programmatic restore API
    # This function validates the backup and provides instructions
    
    for model in backup_data['models']:
        model_id = model['id']
        print(f"  - {model_id}")
        
        # In practice, you would manually load these models in LM Studio UI
        # Or use the models.download_model() API if available
    
    print("\nInstructions:")
    print("1. Open LM Studio")
    print("2. Navigate to 'My Models' tab")
    print("3. For each model listed above:")
    print("   a. Click 'Load Model'")
    print("   b. Select the quantization version")
    print("4. Start the server")
    
    return True

# Usage
restore_lm_studio_models("backups/config/lm-studio-20251115_120000.json")
```

### Restore Qdrant Database

```python
from qdrant_client import QdrantClient
import json
from pathlib import Path

def restore_qdrant_database(backup_file, collection_name="aimemory_docs"):
    """Restore Qdrant database from backup."""
    
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)
    
    print(f"Restoring {len(backup_data['points'])} points...")
    
    try:
        client = QdrantClient(host="localhost", port=6333)
        
        # Check if collection exists
        collections = [c.collection_name for c in client.get_collections().collections]
        
        if collection_name not in collections:
            print(f"Creating collection '{collection_name}'...")
            
            # Get dimension from first point
            sample_point = backup_data['points'][0]
            vector_size = 4096  # Default for text-embedding-qwen3
            
            client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": {
                        "size": vector_size,
                        "distance": "Cosine"
                    }
                }
            )
        
        # Restore points in batches
        batch_size = 100
        for i in range(0, len(backup_data['points']), batch_size):
            batch = backup_data['points'][i:i + batch_size]
            
            points = [
                {
                    "id": point['id'],
                    "vector": None,  # Not restoring vectors in this example
                    "payload": point['payload']
                }
                for point in batch
            ]
            
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            print(f"Restored {min(i + len(batch), len(backup_data['points']))}/{len(backup_data['points'])} points")
        
        print("✓ Restore completed!")
        return True
        
    except Exception as e:
        print(f"✗ Restore failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Usage
restore_qdrant_database("backups/qdrant/full-20251115_120000.json")
```

## Automated Backup Scripts

### Windows PowerShell Backup Script

```powershell
<#
.SYNOPSIS
    Automated backup script for AI Memory Pipeline
.DESCRIPTION
    Creates daily backups of LM Studio config and Qdrant database
#>

param(
    [string]$BackupBasePath = "\\\\192.168.0.16\\docker\\AI-Memory\\backups",
    [switch]$Compress = $true
)

$ErrorActionPreference = "Stop"

# Create backup directories
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupPaths = @{
    Config = Join-Path $BackupBasePath "config"
    Qdrant = Join-Path $BackupBasePath "qdrant"
}

foreach ($path in $backupPaths.Values) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

Write-Host "=== Starting Backup ===" -ForegroundColor Green
Write-Host "Timestamp: $timestamp"

# Backup LM Studio Configuration
Write-Host "`n[1/2] Backing up LM Studio configuration..." -ForegroundColor Cyan

try {
    $lmStudioUrl = "http://localhost:1234/v1/models"
    $response = Invoke-RestMethod -Uri $lmStudioUrl -Method Get -TimeoutSec 10
    
    if ($response.data) {
        $configBackup = @{
            backup_timestamp = $timestamp
            models = $response.data
        }
        
        $configFile = Join-Path $backupPaths.Config "lm-studio-${timestamp}.json"
        $configBackup | ConvertTo-Json -Depth 10 | Out-File $configFile
        
        Write-Host "  ✓ Saved to: $configFile" -ForegroundColor Green
    } else {
        Write-Host "  ✗ No models found" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  ✗ Failed: $_" -ForegroundColor Red
}

# Backup Qdrant Database (Docker-based)
Write-Host "`n[2/2] Backing up Qdrant database..." -ForegroundColor Cyan

try {
    # Stop container for consistent backup
    docker-compose stop qdrant
    
    $qdrantBackupPath = Join-Path $backupPaths.Qdrant "${timestamp}_storage"
    
    # Copy data from container
    docker cp ai-memory-qdrant-1:/qdrant/storage $qdrantBackupPath
    
    # Restart container
    docker-compose start qdrant
    
    if ($Compress) {
        Write-Host "  Compressing backup..." -ForegroundColor Cyan
        
        $archiveFile = Join-Path $backupPaths.Qdrant "full-${timestamp}.tar.gz"
        
        # Use PowerShell's compression (Windows 10+)
        Add-Type -Assembly System.IO.Compression.FileSystem
        [IO.Compression.ZipFile]::CreateFromDirectory($qdrantBackupPath, "${archiveFile}.zip")
        
        Remove-Item $qdrantBackupPath -Recurse
        
        Write-Host "  ✓ Saved to: ${archiveFile}.zip" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Backup saved to: $qdrantBackupPath" -ForegroundColor Green
    }
}
catch {
    Write-Host "  ✗ Failed: $_" -ForegroundColor Red
    
    # Try to restart container even if backup failed
    try {
        docker-compose start qdrant
    } catch {}
}

Write-Host "`n=== Backup Complete ===" -ForegroundColor Green
```

### Linux/Mac Backup Script (Bash)

```bash
#!/bin/bash

# Automated Backup Script for AI Memory Pipeline
# Usage: ./backup.sh [daily|weekly|monthly]

set -e

BACKUP_BASE="/mnt/data/ai-memory/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TYPE=${1:-"daily"}

# Create backup directories
mkdir -p "$BACKUP_BASE/config"
mkdir -p "$BACKUP_BASE/qdrant"

echo "=== Starting Backup ==="
echo "Type: $TYPE"
echo "Timestamp: $TIMESTAMP"

# Function to cleanup old backups
cleanup_old_backups() {
    local dir=$1
    local keep_days=$2
    
    echo "Cleaning up backups older than $keep_days days in $dir..."
    find "$dir" -type f -mtime +"$keep_days" -delete 2>/dev/null || true
}

# Backup LM Studio Configuration
echo ""
echo "[1/2] Backing up LM Studio configuration..."

if curl -s http://localhost:1234/v1/models | grep -q '"data"'; then
    curl -s http://localhost:1234/v1/models > "$BACKUP_BASE/config/lm-studio-${TIMESTAMP}.json"
    echo "  ✓ Saved to: $BACKUP_BASE/config/lm-studio-${TIMESTAMP}.json"
else
    echo "  ✗ Failed to connect to LM Studio"
fi

# Backup Qdrant Database
echo ""
echo "[2/2] Backing up Qdrant database..."

# Stop container for consistent backup
docker-compose stop qdrant || true

QDRANT_BACKUP="$BACKUP_BASE/qdrant/${TIMESTAMP}_storage"

if docker cp ai-memory-qdrant-1:/qdrant/storage "$QDRANT_BACKUP" 2>/dev/null; then
    # Compress the backup
    tar -czf "$BACKUP_BASE/qdrant/full-${TIMESTAMP}.tar.gz" -C "$(dirname $QDRANT_BACKUP)" "$(basename $QDRANT_BACKUP)"
    
    # Remove uncompressed backup
    rm -rf "$QDRANT_BACKUP"
    
    echo "  ✓ Saved to: $BACKUP_BASE/qdrant/full-${TIMESTAMP}.tar.gz"
else
    echo "  ✗ Failed to backup Qdrant data"
fi

# Restart container
docker-compose start qdrant || true

# Cleanup old backups (keep 7 days for daily, 30 for weekly)
if [ "$TYPE" = "daily" ]; then
    cleanup_old_backups "$BACKUP_BASE/config" 7
    cleanup_old_backups "$BACKUP_BASE/qdrant" 7
elif [ "$TYPE" = "weekly" ]; then
    cleanup_old_backups "$BACKUP_BASE/config" 30
    cleanup_old_backups "$BACKUP_BASE/qdrant" 30
fi

echo ""
echo "=== Backup Complete ==="
```

## Scheduled Backup Setup

### Windows Task Scheduler

```powershell
# Create scheduled task for daily backup at 2:00 AM

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-File `"`$PSScriptRoot\backup.ps1`""

$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

Register-ScheduledTask -TaskName "AIMemoryDailyBackup" `
    -Description "Daily backup of AI Memory Pipeline data" `
    -Action $action `
    -Trigger $trigger `
    -RunLevel Highest
```

### Linux Cron Job

```bash
# Add to crontab for daily backup at 2:00 AM
0 2 * * * /mnt/data/ai-memory/scripts/backup.sh daily >> /var/log/ai-memory-backup.log 2>&1

# Weekly full backup on Sunday at 3:00 AM
0 3 * * 0 /mnt/data/ai-memory/scripts/backup.sh weekly >> /var/log/ai-memory-backup.log 2>&1
```

## Verification Procedures

After any restore operation:

```bash
# 1. Verify LM Studio models are loaded
curl http://localhost:1234/v1/models | jq '.data | length'

# 2. Check Qdrant collection status
curl http://localhost:6333/collections/aimemory_docs | jq '.'

# 3. Run validation script
python scripts/validate-lm-studio.py

# 4. Test embedding generation
python -c "from ai_memory_pipeline.lm_studio_smart_embedder import LMSmartEmbedder; e = LMSmartEmbedder(); print(e.generate_embeddings(['test']))"
```

## Disaster Recovery

### Full System Recovery Checklist

1. **Stop all services**
   ```bash
   docker-compose down
   ```

2. **Restore Qdrant data**
   ```bash
   # Stop container
   docker-compose stop qdrant
   
   # Restore backup
   tar -xzf backups/qdrant/full-YYYYMMDD_HHMMSS.tar.gz -C /path/to/qdrant/data
   
   # Restart
   docker-compose up -d qdrant
   ```

3. **Restore LM Studio models**
   - Open LM Studio
   - Load models from backup list
   - Start server

4. **Validate restore**
   ```bash
   python scripts/validate-lm-studio.py
   ```

5. **Resume operations**
   - Monitor VRAM usage
   - Verify embedding quality
   - Check ingestion pipeline