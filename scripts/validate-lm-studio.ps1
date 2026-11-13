#!/usr/bin/env powershell
# Validate LM Studio API connectivity

$ErrorActionPreference = "Continue"

Write-Host "=== LM Studio Validation Script ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$baseUrl = "http://localhost:1234/v1"
$apiKey = if ($env:INFISICAL_API_KEY) { $env:INFISICAL_API_KEY } else { "test-key" }

# Test 1: Check if server is reachable
Write-Host "[Test 1] Checking server connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/models" -Method Get `
        -Headers @{ "Authorization" = "Bearer $apiKey" } -TimeoutSec 5
    
    Write-Host "  [OK] Server is reachable" -ForegroundColor Green
    
    # Display available models
    if ($response.data) {
        Write-Host "  Available models:" -ForegroundColor Cyan
        foreach ($model in $response.data) {
            Write-Host "    - $($model.id)" -ForegroundColor White
        }
    } else {
        Write-Host "  [WARN] No models found. Load a model via LM Studio UI." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  [FAIL] Connection failed: $($_.Exception.Message)" -ForegroundColor Red
    
    $statusCode = if ($_.Exception.InnerException) { $_.Exception.InnerException.StatusCode } else { $null }
    
    if ($statusCode -eq 404) {
        Write-Host "  [INFO] Server responded with 404. Check if API path is correct." -ForegroundColor Yellow
    } elseif ($_.Exception.Message -like "*Could not connect*") {
        Write-Host "  [INFO] LM Studio server may not be running on port 1234." -ForegroundColor Yellow
        Write-Host "  [INFO] Start LM Studio and click the server icon to enable API." -ForegroundColor Yellow
    }
    
    exit 1
}

Write-Host ""
Write-Host "[Test 2] Testing model generation (sample)..." -ForegroundColor Yellow

# Test generation with a simple prompt
$generationBody = @{
    model = "lmstudio-qwen3-27b"
    messages = @(
        @{role = "system"; content = "You are a helpful assistant."}
        @{role = "user"; content = "Say 'test' in one word"}
    )
    temperature = 0.7
    max_tokens = 10
} | ConvertTo-Json -Compress

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/chat/completions" -Method Post `
        -Headers @{ 
            "Authorization" = "Bearer $apiKey"
            "Content-Type" = "application/json"
        } `
        -Body $generationBody `
        -TimeoutSec 30
    
    Write-Host "  [OK] Generation successful!" -ForegroundColor Green
    if ($response.choices) {
        Write-Host "  Response: $($response.choices[0].message.content)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  [SKIP] Generation test skipped (model may not be loaded): $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Validation Complete ===" -ForegroundColor Green
