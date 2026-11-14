# =============================================================================
# AI Memory Pipeline - NAS Setup Script (Windows PowerShell)
# =============================================================================
# Run this script on your NAS to prepare the directory structure
# =============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AI Memory Pipeline - NAS Directory Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Directories to create
$dirs = @(
    "\\192.168.0.16\docker\qdrant\storage"
    "\\192.168.0.16\docker\qdrant\config"
    "\\192.168.0.16\docker\qdrant\backups"
    "\\192.168.0.16\docker\ai-memory\logs"
    "\\192.168.0.16\SharedMemory\me"
    "\\192.168.0.16\SharedMemory\wife"
    "\\192.168.0.16\SharedMemory\shared"
)

Write-Host "Creating directory structure..." -ForegroundColor Yellow

foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "[SKIP] $dir" -ForegroundColor Yellow
    } else {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "[CREATE] $dir" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Checking for configuration files..." -ForegroundColor Yellow

# Check for config.yaml
$configPath = "\\192.168.0.16\docker\qdrant\config\config.yaml"
if (Test-Path $configPath) {
    Write-Host "[OK] config.yaml exists" -ForegroundColor Green
} else {
    Write-Host "[WARNING] config.yaml not found at $configPath" -ForegroundColor Yellow
    Write-Host "Creating minimal config.yaml..." -ForegroundColor Yellow

    $configContent = @'
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
'@

    $configContent | Out-File -FilePath $configPath -Encoding ASCII
    Write-Host "[CREATED] $configPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Checking for Dockerfile..." -ForegroundColor Yellow

$dockerfilePath = "\\192.168.0.16\docker\repositories\AI-Memory\Dockerfile.pipeline"
if (Test-Path $dockerfilePath) {
    Write-Host "[OK] Dockerfile.pipeline exists" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Dockerfile.pipeline not found at $dockerfilePath" -ForegroundColor Red
    Write-Host "Please ensure the AI-Memory repository is cloned to \\192.168.0.16\docker\repositories\" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Navigate to \\192.168.0.16\docker\repositories\AI-Memory"
Write-Host "2. Build the custom Qdrant image:"
Write-Host "   docker build -f qdrant\Dockerfile -t qdrant-custom:v1.7.0 ."
Write-Host "3. Deploy all services:"
Write-Host "   docker compose up -d"
Write-Host ""
Write-Host "Directory structure created at:"
foreach ($dir in $dirs) {
    Write-Host "  $dir"
}
