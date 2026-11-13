#!/usr/bin/env powershell
# Test Infisical connection and secret retrieval

Write-Host "=== Infisical Connection Test ===" -ForegroundColor Cyan
Write-Host ""

# Configuration
$infisicalUrl = "http://192.168.0.16:8081"
$projectId = "b245c33e-7702-475c-b4f4-dbb4741d21b1"
$client_id = "bc0119a6-066f-42a2-8a06-746f97e1ddb8"
$secret_key = "fe182e0168b91de74f6cb643c1634e532a91c8eb9e2c8cf60941ade7039b9d4a"

# Test 1: Check Infisical server connectivity (try multiple endpoints)
Write-Host "[Test 1] Checking Infisical server connectivity..." -ForegroundColor Yellow

$endpoints = @("/api/v1/auth/health", "/api/healthz", "/", "/api/v1/projects")

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-RestMethod -Uri "$infisicalUrl$endpoint" -Method Get -TimeoutSec 5
        Write-Host "  [OK] Endpoint $endpoint is reachable" -ForegroundColor Green
        if ($response) {
            Write-Host "  Response: $($response | ConvertTo-Json)" -ForegroundColor Cyan
        }
    } catch {
        # Silently try next endpoint
    }
}

# Test 2: Direct API call to list projects
Write-Host ""
Write-Host "[Test 2] Testing direct API access..." -ForegroundColor Yellow

try {
    $authBody = @{
        apiKey = $secret_key
    } | ConvertTo-Json -Compress
    
    $response = Invoke-RestMethod -Uri "$infisicalUrl/api/v1/auth/service-token/authenticate" -Method Post `
        -Headers @{ "Content-Type" = "application/json" } `
        -Body $authBody `
        -TimeoutSec 10
    
    Write-Host "  [OK] Authentication successful!" -ForegroundColor Green
    Write-Host "  Response: $($response | ConvertTo-Json)" -ForegroundColor Cyan
    
} catch {
    Write-Host "  [INFO] Auth endpoint not accessible: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Infisical Test Complete ===" -ForegroundColor Green
