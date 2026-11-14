# Backup Verification Script for AI Memory Pipeline
# Verifies integrity of automated backups

param(
    [string]$BaseDir = "D:\AI-Memory",
    [string]$BackupRoot = "\\192.168.0.16\docker\AI-Memory\backups"
)

Write-Host "=== AI Memory Pipeline Backup Verification ===" -ForegroundColor Cyan
Write-Host "Started: $(Get-Date)" -ForegroundColor Yellow

$ErrorCount = 0
$WarningCount = 0
$BackupStatus = @{}

# ============================================
# Verify LM Studio Configuration Backups
# ============================================
Write-Host "`n[1/2] Verifying LM Studio configuration backups..." -ForegroundColor Cyan

$LmStudioBackupDir = Join-Path $BackupRoot "config"

if (Test-Path $LmStudioBackupDir) {
    $Backups = Get-ChildItem -Path $LmStudioBackupDir -Directory | Sort-Object CreationTime -Descending
    
    if ($Backups.Count -gt 0) {
        Write-Host "  Found $($Backups.Count) backup(s)" -ForegroundColor Green
        
        # Check most recent backup
        $LatestBackup = $Backups[0]
        $BackupAge = (Get-Date) - $LatestBackup.CreationTime
        
        Write-Host "  Latest: $($LatestBackup.Name)" -ForegroundColor Cyan
        Write-Host "  Age: $($BackupAge.TotalHours.ToString('0.0')) hours ago" -ForegroundColor Cyan
        
        # Verify backup contains expected files
        $ExpectedFiles = @("config", "logs")
        $MissingFiles = @()
        
        foreach ($Dir in $ExpectedFiles) {
            if (-not (Test-Path (Join-Path $LatestBackup.FullName $Dir))) {
                $MissingFiles += $Dir
            }
        }
        
        if ($MissingFiles.Count -eq 0) {
            Write-Host "  ✓ All expected files present" -ForegroundColor Green
            $BackupStatus["LM Studio"] = @{
                Status = "OK"
                Latest = $LatestBackup.Name
                AgeHours = [math]::Round($BackupAge.TotalHours, 1)
            }
        } else {
            Write-Host "  ⚠ Missing directories: $($MissingFiles -join ', ')" -ForegroundColor Yellow
            $WarningCount++
            $BackupStatus["LM Studio"] = @{
                Status = "WARNING"
                Latest = $LatestBackup.Name
                AgeHours = [math]::Round($BackupAge.TotalHours, 1)
                Missing = $MissingFiles
            }
        }
    } else {
        Write-Host "  ⚠ No LM Studio backups found" -ForegroundColor Yellow
        $WarningCount++
        $BackupStatus["LM Studio"] = @{
            Status = "NO_BACKUPS"
            Latest = $null
            AgeHours = $null
        }
    }
} else {
    Write-Host "  ✗ Backup directory not found: $LmStudioBackupDir" -ForegroundColor Red
    $ErrorCount++
    $BackupStatus["LM Studio"] = @{
        Status = "ERROR"
        Latest = $null
        AgeHours = $null
        Error = "Directory not found"
    }
}

# ============================================
# Verify Qdrant Database Backups
# ============================================
Write-Host "`n[2/2] Verifying Qdrant database backups..." -ForegroundColor Cyan

$QdrantBackupDir = Join-Path $BackupRoot "qdrant"

if (Test-Path $QdrantBackupDir) {
    # Check for full backups (Sundays)
    $FullBackups = Get-ChildItem -Path $QdrantBackupDir -Directory | 
        Where-Object { $_.Name.StartsWith("full_") } | Sort-Object CreationTime -Descending
    
    # Check for incremental backups
    $IncrementalBackups = Get-ChildItem -Path $QdrantBackupDir -Directory | 
        Where-Object { $_.Name.StartsWith("incremental_") } | Sort-Object CreationTime -Descending
    
    Write-Host "  Full backups: $($FullBackups.Count)" -ForegroundColor Cyan
    Write-Host "  Incremental backups: $($IncrementalBackups.Count)" -ForegroundColor Cyan
    
    # Verify full backup if exists
    if ($FullBackups.Count -gt 0) {
        $LatestFull = $FullBackups[0]
        $BackupAge = (Get-Date) - $LatestFull.CreationTime
        
        Write-Host "  Latest Full: $($LatestFull.Name)" -ForegroundColor Cyan
        
        # Check for zip file
        $ZipFile = "$($LatestFull.FullName).zip"
        if (Test-Path $ZipFile) {
            try {
                # Verify archive integrity
                Add-Type -Assembly System.IO.Compression
                [IO.Compression.ZipFile]::OpenRead($ZipFile).Dispose()
                Write-Host "  ✓ Full backup archive valid" -ForegroundColor Green
                
                $FullStatus = @{
                    Status = "OK"
                    Name = $LatestFull.Name
                    AgeHours = [math]::Round($BackupAge.TotalHours, 1)
                    Compressed = $true
                    ZipPath = $ZipFile
                }
            } catch {
                Write-Host "  ✗ Full backup archive corrupted" -ForegroundColor Red
                $ErrorCount++
                $FullStatus.Status = "CORRUPTED"
            }
        } else {
            # Check uncompressed directory
            if (Test-Path "$($LatestFull.FullName)\storage") {
                Write-Host "  ✓ Full backup directory exists" -ForegroundColor Green
                $FullStatus = @{
                    Status = "OK"
                    Name = $LatestFull.Name
                    AgeHours = [math]::Round($BackupAge.TotalHours, 1)
                    Compressed = $false
                }
            } else {
                Write-Host "  ⚠ Full backup directory incomplete" -ForegroundColor Yellow
                $WarningCount++
                $FullStatus.Status = "INCOMPLETE"
            }
        }
    } else {
        $FullStatus = @{
            Status = "NO_BACKUPS"
        }
    }
    
    # Verify incremental backups if no full backup exists
    if ($IncrementalBackups.Count -gt 0) {
        $LatestInc = $IncrementalBackups[0]
        $BackupAge = (Get-Date) - $LatestInc.CreationTime
        
        Write-Host "  Latest Incremental: $($LatestInc.Name)" -ForegroundColor Cyan
        Write-Host "  Age: $($BackupAge.TotalHours.ToString('0.0')) hours ago" -ForegroundColor Cyan
        
        # Check for zip file
        $ZipFile = "$($LatestInc.FullName).zip"
        if (Test-Path $ZipFile) {
            try {
                Add-Type -Assembly System.IO.Compression
                [IO.Compression.ZipFile]::OpenRead($ZipFile).Dispose()
                Write-Host "  ✓ Incremental backup archive valid" -ForegroundColor Green
                
                $IncStatus = @{
                    Status = "OK"
                    Name = $LatestInc.Name
                    AgeHours = [math]::Round($BackupAge.TotalHours, 1)
                    Compressed = $true
                }
            } catch {
                Write-Host "  ✗ Incremental backup archive corrupted" -ForegroundColor Red
                $ErrorCount++
                $IncStatus.Status = "CORRUPTED"
            }
        } else {
            if (Test-Path "$($LatestInc.FullName)") {
                Write-Host "  ✓ Incremental backup directory exists" -ForegroundColor Green
                $IncStatus = @{
                    Status = "OK"
                    Name = $LatestInc.Name
                    AgeHours = [math]::Round($BackupAge.TotalHours, 1)
                    Compressed = $false
                }
            } else {
                Write-Host "  ⚠ Incremental backup incomplete" -ForegroundColor Yellow
                $WarningCount++
                $IncStatus.Status = "INCOMPLETE"
            }
        }
    } else {
        $IncStatus = @{
            Status = "NO_BACKUPS"
        }
    }
    
    # Store Qdrant status
    $BackupStatus["Qdrant"] = @{
        FullBackup = $FullStatus
        IncrementalBackup = $IncStatus
    }
} else {
    Write-Host "  ✗ Backup directory not found: $QdrantBackupDir" -ForegroundColor Red
    $ErrorCount++
    $BackupStatus["Qdrant"] = @{
        Status = "ERROR"
        Error = "Directory not found"
    }
}

# ============================================
# Summary Report
# ============================================
Write-Host "`n=== Verification Summary ===" -ForegroundColor Cyan

if ($ErrorCount -eq 0) {
    Write-Host "Overall Status: VERIFIED ✓" -ForegroundColor Green
} elseif ($WarningCount -eq 0) {
    Write-Host "Overall Status: FAILED ✗" -ForegroundColor Red
} else {
    Write-Host "Overall Status: DEGRADED (with warnings)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Backup Details:" -ForegroundColor Cyan

foreach ($BackupType in $BackupStatus.Keys) {
    Write-Host "  $BackupType:" -ForegroundColor Gray
    
    if ($BackupType -eq "LM Studio") {
        $Status = $BackupStatus[$BackupType]
        if ($Status.Status -eq "OK") {
            Write-Host "    Status: OK" -ForegroundColor Green
            Write-Host "    Latest: $($Status.Latest)" -ForegroundColor Gray
            Write-Host "    Age: $($Status.AgeHours) hours" -ForegroundColor Gray
        } else {
            Write-Host "    Status: $($Status.Status)" -ForegroundColor Yellow
        }
    } elseif ($BackupType -eq "Qdrant") {
        $Status = $BackupStatus[$BackupType]
        
        if ($Status.FullBackup.Status -ne "NO_BACKUPS") {
            $Full = $Status.FullBackup
            Write-Host "    Full Backup:" -ForegroundColor Gray
            
            switch ($Full.Status) {
                "OK" { Write-Host "      Status: OK" -ForegroundColor Green }
                "WARNING" { Write-Host "      Status: WARNING" -ForegroundColor Yellow }
                default { Write-Host "      Status: $($Full.Status)" -ForegroundColor Red }
            }
            
            if ($Full.Name) {
                Write-Host "      Latest: $($Full.Name)" -ForegroundColor Gray
                Write-Host "      Age: $($Full.AgeHours) hours" -ForegroundColor Gray
                if ($Full.Compressed) {
                    Write-Host "      Compressed: Yes" -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "    Full Backup: None found" -ForegroundColor Yellow
        }
        
        if ($Status.IncrementalBackup.Status -ne "NO_BACKUPS") {
            $Inc = $Status.IncrementalBackup
            Write-Host "    Incremental Backup:" -ForegroundColor Gray
            
            switch ($Inc.Status) {
                "OK" { Write-Host "      Status: OK" -ForegroundColor Green }
                default { Write-Host "      Status: $($Inc.Status)" -ForegroundColor Red }
            }
            
            if ($Inc.Name) {
                Write-Host "      Latest: $($Inc.Name)" -ForegroundColor Gray
                Write-Host "      Age: $($Inc.AgeHours) hours" -ForegroundColor Gray
            }
        } else {
            Write-Host "    Incremental Backup: None found" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Completed: $(Get-Date)" -ForegroundColor Cyan

# Exit with appropriate code
if ($ErrorCount -gt 0) {
    exit 1
} else {
    exit 0
}
