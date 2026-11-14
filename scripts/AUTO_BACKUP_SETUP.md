# Automated Backup Setup for Windows

This guide covers setting up automated backups for the AI Memory Pipeline using Windows Task Scheduler.

## Backup Schedule Recommendations

| Backup Type | Frequency | Storage Location |
|-------------|-----------|------------------|
| LM Studio Config | Daily | `backups/config/` |
| Qdrant Full | Sunday 2 AM | `backups/qdrant/full/` |
| Qdrant Incremental | Mon-Sat 2 AM | `backups/qdrant/incremental/` |

## PowerShell Backup Script

Save this as `scripts\auto-backup.ps1`:

```powershell
# Automated Backup Script for AI Memory Pipeline
# Runs via Windows Task Scheduler

param(
    [string]$BaseDir = "D:\AI-Memory",
    [string]$BackupRoot = "\\192.168.0.16\docker\AI-Memory\backups"
)

Write-Host "=== AI Memory Pipeline Automated Backup ===" -ForegroundColor Cyan
Write-Host "Started: $(Get-Date)" -ForegroundColor Yellow

# Configuration
$ConfigDir = Join-Path $BaseDir "config"
$LmStudioBackupDir = Join-Path $BackupRoot "config"
$QdrantBackupDir = Join-Path $BackupRoot "qdrant"

# Ensure backup directories exist
New-Item -ItemType Directory -Force -Path $LmStudioBackupDir, $QdrantBackupDir | Out-Null

$DateStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DayOfWeek = (Get-Date).DayOfWeek

try {
    # Backup LM Studio Configuration (Daily)
    Write-Host "`n[1/2] Backing up LM Studio configuration..." -ForegroundColor Yellow
    $LmConfigFile = Join-Path $LmStudioBackupDir "lm-studio_$DateStamp.json"
    
    try {
        $Response = Invoke-RestMethod -Uri "http://localhost:1234/v1/models" -ErrorAction Stop
        $ModelList = $Response.data | Select-Object id, type
        
        $ConfigBackup = @{
            timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
            host = "localhost"
            port = 1234
            models = $ModelList
            backup_type = "configuration"
        }
        
        $ConfigBackup | ConvertTo-Json -Depth 10 | Out-File $LmConfigFile -Encoding utf8
        Write-Host "✓ LM Studio configuration backed up to: $LmConfigFile" -ForegroundColor Green
        
        # Keep only last 30 days of config backups
        Get-ChildItem $LmStudioBackupDir -Filter "lm-studio_*.json" | 
            Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
            Remove-Item -Force
        
    } catch {
        Write-Warning "LM Studio not running or unreachable: $($_.Exception.Message)"
    }
    
    # Backup Qdrant Database
    Write-Host "`n[2/2] Backing up Qdrant database..." -ForegroundColor Yellow
    
    if ($DayOfWeek -eq "Sunday") {
        # Full backup on Sunday
        $BackupType = "full"
        $BackupDir = Join-Path $QdrantBackupDir "full"
        New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
        
        $BackupFile = Join-Path $BackupDir "qdrant_full_$DateStamp.dump"
        
        Write-Host "Creating full backup to: $BackupFile" -ForegroundColor Yellow
        # Use Docker to create snapshot
        docker exec qdrant qdrant snapshot save /snapshots/$DateStamp.dump 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            # Copy snapshot from container
            docker cp qdrant:/snapshots/$DateStamp.dump $BackupFile 2>$null
            
            if (Test-Path $BackupFile) {
                Write-Host "✓ Full backup completed: $BackupFile" -ForegroundColor Green
                
                # Clean up snapshots older than 90 days
                Get-ChildItem $QdrantBackupDir\full -Filter "*.dump" | 
                    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
                    Remove-Item -Force
                
                # Clean up old snapshots in container
                docker exec qdrant qdrant snapshot delete /snapshots/*.dump 2>$null
            }
        }
    } else {
        # Incremental backup on other days
        $BackupType = "incremental"
        $BackupDir = Join-Path $QdrantBackupDir "incremental"
        New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
        
        $BackupFile = Join-Path $BackupDir "qdrant_incremental_$DateStamp.dump"
        
        Write-Host "Creating incremental backup to: $BackupFile" -ForegroundColor Yellow
        # Use Docker to create snapshot
        docker exec qdrant qdrant snapshot save /snapshots/inc_$DateStamp.dump 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            docker cp qdrant:/snapshots/inc_$DateStamp.dump $BackupFile 2>$null
            
            if (Test-Path $BackupFile) {
                Write-Host "✓ Incremental backup completed: $BackupFile" -ForegroundColor Green
                
                # Keep only last 14 days of incremental backups
                Get-ChildItem $BackupDir -Filter "*.dump" | 
                    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } |
                    Remove-Item -Force
            }
        }
    }
    
    Write-Host "`n=== Backup Complete ===" -ForegroundColor Cyan
    Write-Host "Finished: $(Get-Date)" -ForegroundColor Yellow
    
} catch {
    Write-Error "Backup failed: $($_.Exception.Message)"
    exit 1
}
```

## Windows Task Scheduler Setup

### Step 1: Create the Scheduled Tasks

Open PowerShell as Administrator and run:

```powershell
# Define paths
$ScriptPath = "D:\AI-Memory\scripts\auto-backup.ps1"
$TaskName_LM = "AI Memory - LM Studio Backup"
$TaskName_Qdrant = "AI Memory - Qdrant Backup"

# Create scheduled task for daily backup (2 AM)
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""
$Trigger_Daily = New-ScheduledTaskTrigger -Daily -At 2:00AM
$Trigger_Sunday = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2:00AM

# Task settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RunLevel Normal -Hidden

# Create tasks (run as current user)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Password

# LM Studio config backup (daily at 2 AM)
Register-ScheduledTask -TaskName $TaskName_LM `
    -Action $Action `
    -Trigger $Trigger_Daily `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Daily backup of LM Studio configuration"

# Qdrant full backup (Sunday at 2 AM)
Register-ScheduledTask -TaskName "$TaskName_Qdrant-Full" `
    -Action $Action `
    -Trigger $Trigger_Sunday `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Weekly full backup of Qdrant database"

Write-Host "Scheduled tasks created successfully!" -ForegroundColor Green
Write-Host "`nTasks created:" -ForegroundColor Yellow
Write-Host "  - $TaskName_LM (Daily at 2 AM)"
Write-Host "  - $TaskName_Qdrant-Full (Sunday at 2 AM)"
```

### Step 2: Verify Task Schedule

```powershell
# List all AI Memory tasks
Get-ScheduledTask | Where-Object { $_.TaskName -like "*AI Memory*" } | 
    Format-Table TaskName, State, NextRunTime

# Test a task (optional)
Start-ScheduledTask -TaskName "AI Memory - LM Studio Backup"
```

## Alternative: Python-Based Backup Script

For environments where PowerShell is restricted, use `scripts\auto-backup.py`:

```python
#!/usr/bin/env python3
"""Automated backup script for AI Memory Pipeline."""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import requests

def backup_lm_studio(base_dir: str = r"D:\AI-Memory", output_dir: str = None):
    """Backup LM Studio configuration."""
    if output_dir is None:
        output_dir = os.path.join(base_dir, "backups", "config")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        models = response.json().get("data", [])
        
        backup_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "host": "localhost",
            "port": 1234,
            "models": [{"id": m["id"], "type": m.get("type", "unknown")} for m in models],
            "backup_type": "configuration"
        }
        
        date_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(output_dir, f"lm-studio_{date_stamp}.json")
        
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"✓ LM Studio config backed up: {backup_file}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"⚠ LM Studio not accessible: {e}")
        return False

def backup_qdrant(base_dir: str = r"D:\AI-Memory"):
    """Backup Qdrant database using Docker snapshot."""
    date_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Determine backup type
    day_of_week = datetime.now().weekday()  # 0=Monday, 6=Sunday
    is_full_backup = day_of_week == 6  # Sunday
    
    if is_full_backup:
        backup_dir = os.path.join(base_dir, "backups", "qdrant", "full")
        snapshot_name = f"{date_stamp}.dump"
    else:
        backup_dir = os.path.join(base_dir, "backups", "qdrant", "incremental")
        snapshot_name = f"inc_{date_stamp}.dump"
    
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    backup_file = os.path.join(backup_dir, f"qdrant_backup_{date_stamp}.dump")
    
    try:
        # Create snapshot in container
        subprocess.run([
            "docker", "exec", "qdrant",
            "qdrant", "snapshot", "save", "/snapshots/" + snapshot_name
        ], check=True)
        
        # Copy from container
        subprocess.run([
            "docker", "cp",
            f"qdrant:/snapshots/{snapshot_name}",
            backup_file
        ], check=True)
        
        print(f"✓ Qdrant {'full' if is_full_backup else 'incremental'} backup: {backup_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"⚠ Backup failed: {e}")
        return False

def cleanup_old_backups(base_dir: str = r"D:\AI-Memory", days_to_keep: int = 30):
    """Remove backups older than specified days."""
    config_dir = os.path.join(base_dir, "backups", "config")
    
    for backup_file in Path(config_dir).glob("*.json"):
        if (datetime.now() - datetime.fromtimestamp(backup_file.stat().st_mtime)).days > days_to_keep:
            backup_file.unlink()
            print(f"  Removed old config: {backup_file.name}")

if __name__ == "__main__":
    print("=== AI Memory Pipeline Automated Backup ===")
    print(f"Started: {datetime.now()}")
    
    base_dir = r"D:\AI-Memory"
    
    # Run backups
    backup_lm_studio(base_dir)
    backup_qdrant(base_dir)
    
    # Cleanup old backups
    cleanup_old_backups(base_dir, days_to_keep=30)
    
    print(f"\nFinished: {datetime.now()}")
```

## Monitoring Backup Success

Create a monitoring task that runs after backups:

```powershell
# scripts\verify-backup.ps1
param(
    [string]$BackupRoot = "\\192.168.0.16\docker\AI-Memory\backups"
)

Write-Host "=== Backup Verification ===" -ForegroundColor Cyan

# Check config backups
$ConfigBackups = Get-ChildItem (Join-Path $BackupRoot "config") -Filter "*.json" | 
    Sort-Object LastWriteTime -Descending

if ($ConfigBackups.Count -gt 0) {
    Write-Host "✓ Latest config backup: $($ConfigBackups[0].Name)" -ForegroundColor Green
} else {
    Write-Warning "No config backups found"
}

# Check qdrant backups
$QdrantFull = Get-ChildItem (Join-Path $BackupRoot "qdrant" "full") -Filter "*.dump"
$QdrantInc = Get-ChildItem (Join-Path $BackupRoot "qdrant" "incremental") -Filter "*.dump"

Write-Host "  Full backups: $($QdrantFull.Count)" -ForegroundColor Yellow
Write-Host "  Incremental backups: $($QdrantInc.Count)" -ForegroundColor Yellow

# Verify recent backup exists (within last 24 hours)
$Recent = $ConfigBackups | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-1) }
if ($Recent.Count -gt 0) {
    Write-Host "✓ Recent backup found" -ForegroundColor Green
} else {
    Write-Error "No recent backups found in last 24 hours!" -ErrorAction Stop
}
```

## Troubleshooting

### Task Won't Run
- Check Task Scheduler → Properties → "Run whether user is logged on or not"
- Ensure the task has correct permissions
- Verify script path exists and is accessible

### Permission Denied
```powershell
# Set execution policy (run as Admin)
Set-ExecutionPolicy Bypass -Scope CurrentUser
```

### Backup Location Unavailable
- Use UNC paths that are always accessible when network is available
- Consider local backup as fallback with sync to network storage

---

**Next Step**: After setting up automated backups, configure the monitoring alerting system described in `docs/MONITORING_GUIDE.md`.
