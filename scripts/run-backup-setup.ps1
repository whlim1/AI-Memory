# Quick setup for Windows Task Scheduler backup tasks
# Run this command from any location:
# powershell -ExecutionPolicy Bypass -File "\\192.168.0.16\docker\AI-Memory\scripts\run-backup-setup.ps1"

$ScriptDir = "\\192.168.0.16\docker\AI-Memory\scripts"
$ScriptPath = Join-Path $ScriptDir "auto-backup.ps1"
$VerificationPath = Join-Path $ScriptDir "verify-backup.ps1"

Write-Host "=== AI Memory Pipeline - Automated Backup Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $IsAdmin) {
    Write-Warning "This script must be run as Administrator to create scheduled tasks."
    Write-Host ""
    Write-Host "Please right-click on PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Verify script files exist
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Auto backup script not found: $ScriptPath"
    exit 1
}

Write-Host "[OK] Found auto-backup.ps1" -ForegroundColor Green

if (Test-Path $VerificationPath) {
    Write-Host "[OK] Found verify-backup.ps1" -ForegroundColor Green
} else {
    Write-Host "[WARN] verify-backup.ps1 not found (optional)" -ForegroundColor Yellow
}

# Create scheduled tasks
try {
    # Task 1: Daily LM Studio config backup at 2 AM
    $TaskName_LM = "AI Memory - LM Studio Backup"
    
    $Action_LM = New-ScheduledTaskAction -Execute "PowerShell.exe" `
        -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""
    
    $Trigger_Daily = New-ScheduledTaskTrigger -Daily -At 2:00AM
    
    $Settings_LM = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries -Hidden
    
    $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" `
        -LogonType S4U
    
    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $TaskName_LM -ErrorAction SilentlyContinue
    
    Register-ScheduledTask -TaskName $TaskName_LM `
        -Action $Action_LM `
        -Trigger $Trigger_Daily `
        -Settings $Settings_LM `
        -Principal $Principal `
        -Description "Daily backup of LM Studio configuration at 2 AM"
    
    Write-Host "[1/3] Created task: $TaskName_LM" -ForegroundColor Green
    
    # Task 2: Weekly full Qdrant backup on Sunday at 2 AM
    $TaskName_Qdrant_Full = "AI Memory - Qdrant Full Backup"
    
    $Action_Qdrant = New-ScheduledTaskAction -Execute "PowerShell.exe" `
        -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""
    
    $Trigger_Sunday = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2:00AM
    
    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $TaskName_Qdrant_Full -ErrorAction SilentlyContinue
    
    Register-ScheduledTask -TaskName $TaskName_Qdrant_Full `
        -Action $Action_Qdrant `
        -Trigger $Trigger_Sunday `
        -Settings $Settings_LM `
        -Principal $Principal `
        -Description "Weekly full backup of Qdrant database on Sundays at 2 AM"
    
    Write-Host "[2/3] Created task: $TaskName_Qdrant_Full" -ForegroundColor Green
    
    # Task 3: Verification check (optional, runs daily at 3 AM)
    if (Test-Path $VerificationPath) {
        $TaskName_Verify = "AI Memory - Backup Verification"
        
        $Action_Verify = New-ScheduledTaskAction -Execute "PowerShell.exe" `
            -Argument "-ExecutionPolicy Bypass -File `"$VerificationPath`""
        
        $Trigger_Verify = New-ScheduledTaskTrigger -Daily -At 3:00AM
        
        # Remove existing task if present
        Unregister-ScheduledTask -TaskName $TaskName_Verify -ErrorAction SilentlyContinue
        
        Register-ScheduledTask -TaskName $TaskName_Verify `
            -Action $Action_Verify `
            -Trigger $Trigger_Verify `
            -Settings $Settings_LM `
            -Principal $Principal `
            -Description "Daily verification of backup status at 3 AM"
        
        Write-Host "[3/3] Created task: $TaskName_Verify" -ForegroundColor Green
    } else {
        Write-Host "[3/3] Skipped verification task (script not found)" -ForegroundColor Yellow
    }
    
    # Display created tasks
    Write-Host ""
    Write-Host "=== Scheduled Tasks Created ===" -ForegroundColor Cyan
    Get-ScheduledTask | Where-Object { $_.TaskName -like "*AI Memory*" } | 
        Format-Table TaskName, State, @{Label="Next Run";Expression={$_.Triggers.NextRunTime}}, Description
    
    # Summary
    Write-Host ""
    Write-Host "=== Setup Complete ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Backup Schedule:" -ForegroundColor Yellow
    Write-Host "  [1] LM Studio Config: Daily at 2:00 AM"
    Write-Host "  [2] Qdrant Full Backup: Sunday at 2:00 AM"
    if (Test-Path $VerificationPath) {
        Write-Host "  [3] Backup Verification: Daily at 3:00 AM"
    }
    Write-Host ""
    Write-Host "Backup Location:" -ForegroundColor Yellow
    Write-Host "  \\192.168.0.16\docker\AI-Memory\backups\"
    Write-Host ""
    Write-Host "To test a task manually, run:" -ForegroundColor Cyan
    Write-Host '  Start-ScheduledTask -TaskName "AI Memory - LM Studio Backup"'
    Write-Host ""
    
} catch {
    Write-Error "Failed to create scheduled tasks: $($_.Exception.Message)"
    exit 1
}
