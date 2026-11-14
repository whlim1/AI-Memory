# Automated Backup Script for AI Memory Pipeline
# Runs via Windows Task Scheduler
# Handles both LM Studio config and Qdrant backups

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
if (-not (Test-Path $LmStudioBackupDir)) {
    New-Item -ItemType Directory -Path $LmStudioBackupDir | Out-Null
}
if (-not (Test-Path $QdrantBackupDir)) {
    New-Item -ItemType Directory -Path $QdrantBackupDir | Out-Null
}

$ErrorCount = 0

# ============================================
# Backup 1: LM Studio Configuration
# ============================================
Write-Host "`n[1/2] Backing up LM Studio configuration..." -ForegroundColor Cyan

try {
    # Get LM Studio config directory (standard location)
    $LmStudioConfigPath = Join-Path $env:APPDATA "LM Studio"
    
    if (Test-Path $LmStudioConfigPath) {
        $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $BackupSubDir = Join-Path $LmStudioBackupDir $Timestamp
        
        Write-Host "  Source: $LmStudioConfigPath" -ForegroundColor Gray
        Write-Host "  Target: $BackupSubDir" -ForegroundColor Gray
        
        # Copy entire config directory
        Copy-Item -Path $LmStudioConfigPath -Destination $BackupSubDir -Recurse -Force
        Write-Host "  [OK] LM Studio configuration backed up successfully" -ForegroundColor Green
        
        # Keep only last 7 days of backups
        $RetentionDays = 7
        Get-ChildItem -Path $LmStudioBackupDir | Where-Object { 
            $_.PSIsContainer -and ($_.CreationTime -lt (Get-Date).AddDays(-$RetentionDays))
        } | Remove-Item -Recurse -Force
        
    } else {
        Write-Host "  [WARN] LM Studio config directory not found: $LmStudioConfigPath" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Error backing up LM Studio configuration: $($_.Exception.Message)" -ForegroundColor Red
    $ErrorCount++
}

# ============================================
# Backup 2: Qdrant Database
# ============================================
Write-Host "`n[2/2] Backing up Qdrant database..." -ForegroundColor Cyan

try {
    # Check if Docker is running
    $DockerStatus = docker info 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $IsSunday = (Get-Date).DayOfWeek -eq "Sunday"
        
        if ($IsSunday) {
            # Full backup on Sundays
            $BackupSubDir = Join-Path $QdrantBackupDir "full_$Timestamp"
            
            Write-Host "  Performing full Qdrant backup..." -ForegroundColor Cyan
            
            # Create backup directory
            New-Item -ItemType Directory -Path $BackupSubDir | Out-Null
            
            # Execute backup using Docker
            $ContainerId = docker ps --filter "name=qdrant" --format "{{.ID}}"
            
            if ($ContainerId) {
                # Copy qdrant_data from container
                docker cp "${ContainerId}:/qdrant/storage" "$BackupSubDir\" 2>$null
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  [OK] Full Qdrant backup completed: $BackupSubDir" -ForegroundColor Green
                    
                    # Compress the backup
                    $ZipPath = "$BackupSubDir.zip"
                    try {
                        Compress-Archive -Path "$BackupSubDir\storage\*" -DestinationPath $ZipPath -CompressionLevel Optimal
                        Remove-Item -Path $BackupSubDir -Recurse -Force
                        Write-Host "  [OK] Backup compressed: $ZipPath" -ForegroundColor Green
                    } catch {
                        Write-Host "  [WARN] Backup created but compression failed: $($_.Exception.Message)" -ForegroundColor Yellow
                    }
                } else {
                    # Fallback to API backup if container copy fails
                    Write-Host "  [WARN] Container copy failed, attempting API backup..." -ForegroundColor Yellow
                    Invoke-QdrantApiBackup -Timestamp $Timestamp
                }
            } else {
                Write-Host "  [WARN] Qdrant container not running" -ForegroundColor Yellow
                # Create placeholder for manual backup
                $PlaceholderFile = Join-Path $QdrantBackupDir "manual_backup_needed_$Timestamp.txt"
                Set-Content -Path $PlaceholderFile -Value "Qdrant container not found. Please start container and run backup manually."
            }
        } else {
            # Incremental backup (monitored via storage directory modification times)
            $IncrementalDir = Join-Path $QdrantBackupDir "incremental_$Timestamp"
            New-Item -ItemType Directory -Path $IncrementalDir | Out-Null
            
            # Copy only recently modified files
            try {
                $StorageDir = "$BaseDir\qdrant_storage"
                if (Test-Path $StorageDir) {
                    Write-Host "  Performing incremental backup..." -ForegroundColor Cyan
                    
                    # Get list of changed files in last 24 hours
                    $ChangedFiles = Get-ChildItem -Path $StorageDir -Recurse | Where-Object { 
                        $_.LastWriteTime -gt (Get-Date).AddHours(-24)
                    }
                    
                    if ($ChangedFiles.Count -gt 0) {
                        Write-Host "  Found $($ChangedFiles.Count) modified files" -ForegroundColor Cyan
                        
                        # Copy to backup
                        foreach ($File in $ChangedFiles) {
                            $RelativePath = $File.FullName.Substring($StorageDir.Length + 1)
                            $TargetPath = Join-Path $IncrementalDir $RelativePath
                            $TargetDir = Split-Path $TargetPath -Parent
                            
                            if (-not (Test-Path $TargetDir)) {
                                New-Item -ItemType Directory -Path $TargetDir | Out-Null
                            }
                            Copy-Item -Path $File.FullName -Destination $TargetPath -Force
                        }
                        
                        Write-Host "  [OK] Incremental backup completed: $IncrementalDir" -ForegroundColor Green
                        
                        # Compress incremental backup
                        try {
                            $ZipPath = "$IncrementalDir.zip"
                            Compress-Archive -Path "$IncrementalDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal
                            Remove-Item -Path $IncrementalDir -Recurse -Force
                            Write-Host "  [OK] Incremental backup compressed: $ZipPath" -ForegroundColor Green
                        } catch {
                            Write-Host "  [WARN] Incremental backup created but compression failed: $($_.Exception.Message)" -ForegroundColor Yellow
                        }
                    } else {
                        Write-Host "  [INFO] No changes detected since last backup" -ForegroundColor Gray
                        Remove-Item -Path $IncrementalDir -Force
                    }
                } else {
                    Write-Host "  [WARN] Qdrant storage directory not found: $StorageDir" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "  [ERROR] Error creating incremental backup: $($_.Exception.Message)" -ForegroundColor Red
                $ErrorCount++
            }
        }
        
        # Keep only last 30 days of backups (full) and 7 days (incremental)
        Get-ChildItem -Path $QdrantBackupDir | Where-Object { 
            $_.PSIsContainer -and ($_.CreationTime -lt (Get-Date).AddDays(-30))
        } | Remove-Item -Recurse -Force
        
    } else {
        Write-Host "  [WARN] Docker is not running - skipping Qdrant backup" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Error backing up Qdrant database: $($_.Exception.Message)" -ForegroundColor Red
    $ErrorCount++
}

# ============================================
# Summary
# ============================================
Write-Host "`n=== Backup Summary ===" -ForegroundColor Cyan
Write-Host "Completed: $(Get-Date)" -ForegroundColor Yellow

if ($ErrorCount -eq 0) {
    Write-Host "Status: All backups completed successfully [OK]" -ForegroundColor Green
} elseif ($ErrorCount -eq 1) {
    Write-Host "Status: Some backups failed ($ErrorCount error) [ERROR]" -ForegroundColor Red
} else {
    Write-Host "Status: Some backups failed ($ErrorCount errors) [ERROR]" -ForegroundColor Red
}

Write-Host "`nBackup Location:" -ForegroundColor Yellow
Write-Host "  LM Studio Config: $LmStudioBackupDir"
Write-Host "  Qdrant Database: $QdrantBackupDir"

exit $ErrorCount
