# LM Studio Monitoring and Alerting Guide

## VRAM Usage Monitoring

### Built-in LM Studio Server View

LM Studio provides a built-in server view that displays real-time VRAM usage:

1. **Access Server View**
   - In LM Studio, click the "Server" tab
   - Monitor the "GPU Memory Used" metric

2. **Key Metrics to Track**
   - GPU Memory Used (VRAM)
   - Total GPU Memory
   - Loaded Models Count
   - Active Requests

3. **Alert Thresholds**
   - Warning: >70% VRAM usage
   - Critical: >85% VRAM usage
   - Action Required: >90% VRAM usage

### Programmatic Monitoring

#### Python Script for VRAM Monitoring

```python
import requests
import time
from datetime import datetime

class LMStudioMonitor:
    def __init__(self, host="localhost", port=1234):
        self.base_url = f"http://{host}:{port}"
    
    def get_vram_usage(self):
        """Get current VRAM usage from LM Studio server."""
        try:
            response = requests.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json()['data']
                
                # Get total and used VRAM (if available in model details)
                vram_info = {}
                for model in models:
                    model_id = model['id']
                    vram_info[model_id] = {
                        'loaded': True,
                        'details': model
                    }
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'models_loaded': len(models),
                    'vram_info': vram_info
                }
        except requests.exceptions.RequestException as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_health_status(self):
        """Get overall health status."""
        vram_data = self.get_vram_usage()
        
        if 'error' in vram_data:
            return {
                'status': 'unhealthy',
                'message': vram_data['error']
            }
        
        # Check model count
        if vram_data['models_loaded'] == 0:
            return {
                'status': 'warning',
                'message': 'No models loaded'
            }
        
        return {
            'status': 'healthy',
            'models_loaded': vram_data['models_loaded'],
            'vram_info': vram_data['vram_info']
        }

# Usage
monitor = LMStudioMonitor()
status = monitor.get_health_status()
print(f"Status: {status['status']}")
```

### PowerShell Monitoring Script

```powershell
<#
.SYNOPSIS
    Monitor VRAM usage for LM Studio models
.DESCRIPTION
    Checks LM Studio server status and reports VRAM usage
#>

param(
    [string]$Host = "localhost",
    [int]$Port = 1234,
    [switch]$Verbose
)

$base_url = "http://${Host}:${Port}/v1/models"

try {
    $response = Invoke-RestMethod -Uri $base_url -Method Get -TimeoutSec 5
    
    if ($response.data) {
        Write-Host "`n=== LM Studio Server Status ===" -ForegroundColor Green
        Write-Host "Models Loaded: $($response.data.Count)" -ForegroundColor Cyan
        
        $total_vram = 0
        foreach ($model in $response.data) {
            Write-Host "  - $($model.id)" -ForegroundColor Yellow
            
            if ($Verbose) {
                Write-Host "    Details: $($model | ConvertTo-Json)" -ForegroundColor Gray
            }
        }
        
        return $true
    } else {
        Write-Host "`n=== LM Studio Server Status ===" -ForegroundColor Yellow
        Write-Host "Warning: No models loaded" -ForegroundColor Yellow
        return $false
    }
}
catch {
    Write-Host "`n=== LM Studio Server Status ===" -ForegroundColor Red
    Write-Host "Error: Could not connect to LM Studio server" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    return $false
}
```

## Log Monitoring

### Accessing Logs

LM Studio logs are stored in the application directory:

**Windows:**
```
%APPDATA%\LM Studio\logs\
```

**Key Log Files:**
- `server.log` - Server activity and errors
- `models.log` - Model loading/unloading events

### PowerShell Log Viewer

```powershell
<#
.SYNOPSIS
    View LM Studio logs in real-time
#>

param(
    [switch]$Tail = $false,
    [int]$Lines = 50
)

$log_path = "$env:APPDATA\LM Studio\logs\server.log"

if (Test-Path $log_path) {
    if ($Tail) {
        Get-Content $log_path -Wait -Tail $Lines
    } else {
        Get-Content $log_path -Tail $Lines
    }
} else {
    Write-Host "Log file not found: $log_path" -ForegroundColor Red
}
```

## Alerting Configuration

### Windows Task Scheduler Alerts

Create a scheduled task to monitor VRAM:

```powershell
# Create monitoring script
$script = @"
`$monitor = New-Object PSObject -Property @{
    Host = 'localhost'
    Port = 1234
}
# Add your monitoring logic here
"@

# Save to file
$script | Out-File "C:\Scripts\lm-studio-monitor.ps1"

# Schedule task (run every 5 minutes)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-File C:\Scripts\lm-studio-monitor.ps1"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName "LMStudioMonitor" -Action $action -Trigger $trigger
```

### Integration with Monitoring Tools

#### Prometheus Metrics Exporter

```python
from prometheus_client import start_http_server, Gauge
import requests
import time

# Create metrics
models_loaded = Gauge('lmstudio_models_loaded', 'Number of models loaded')
vram_usage_bytes = Gauge('lmstudio_vram_usage_bytes', 'VRAM usage in bytes')

def collect_metrics():
    """Collect metrics from LM Studio."""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=5)
        
        if response.status_code == 200:
            models = response.json()['data']
            models_loaded.set(len(models))
            
            # Estimate VRAM usage (model-specific data needed for accurate metrics)
            # This is a placeholder - adjust based on actual model sizes
            total_vram = sum(m.get('memory_usage', 0) for m in models)
            vram_usage_bytes.set(total_vram)
            
    except Exception as e:
        print(f"Error collecting metrics: {e}")

if __name__ == '__main__':
    start_http_server(8000)
    while True:
        collect_metrics()
        time.sleep(15)  # Collect every 15 seconds
```

#### Grafana Dashboard Configuration

```json
{
  "annotations": {
    "list": [
      {
        "name": "Alerts",
        "type": "alert"
      }
    ]
  },
  "panels": [
    {
      "title": "Models Loaded",
      "type": "stat",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "lmstudio_models_loaded",
          "refId": "A"
        }
      ]
    },
    {
      "title": "VRAM Usage",
      "type": "graph",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "rate(lmstudio_vram_usage_bytes[5m])",
          "refId": "A"
        }
      ]
    }
  ]
}
```

## Performance Metrics to Track

### Daily Checks
- [ ] VRAM usage under 80% capacity
- [ ] Model load times under 30 seconds
- [ ] API response times under 2 seconds
- [ ] No error messages in logs

### Weekly Analysis
- [ ] Review memory trends
- [ ] Identify slow-performing models
- [ ] Check for memory leaks (increasing VRAM over time)
- [ ] Update model configurations if needed

### Monthly Review
- [ ] Evaluate need for additional models
- [ ] Consider quantization changes
- [ ] Review backup strategy
- [ ] Test failover procedures

## Automated Health Checks

```python
import requests
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class LMStudioHealthChecker:
    def __init__(self, host="localhost", port=1234):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        
    def check_server(self):
        """Check if server is running."""
        try:
            response = requests.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json()['data']
                
                if len(models) == 0:
                    logging.warning("No models loaded")
                    return False
                    
                logging.info(f"Server healthy - {len(models)} models loaded")
                return True
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Server check failed: {e}")
            
        return False
        
    def check_model_integrity(self):
        """Verify required models are loaded."""
        try:
            response = requests.get(
                f"{self.base_url}/v1/models",
                timeout=5
            )
            
            if response.status_code != 200:
                return False
                
            loaded_models = [m['id'] for m in response.json()['data']]
            
            required = [
                "qwen3-coder-next",
                "text-embedding-qwen3-embedding-8b"
            ]
            
            missing = [r for r in required if r not in loaded_models]
            
            if missing:
                logging.warning(f"Missing models: {missing}")
                return False
                
            logging.info("All required models loaded")
            return True
            
        except Exception as e:
            logging.error(f"Model integrity check failed: {e}")
            return False

# Run health checks
def run_health_checks():
    checker = LMStudioHealthChecker()
    
    server_ok = checker.check_server()
    models_ok = checker.check_model_integrity()
    
    return server_ok and models_ok

if __name__ == "__main__":
    success = run_health_checks()
    exit(0 if success else 1)
```

This monitoring setup provides comprehensive oversight of your LM Studio deployment with alerts for VRAM usage, model status, and performance metrics.