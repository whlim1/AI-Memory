# AI-Memory Deployment Learnings

## Portainer Stack Deployment: Use Git-Based Deployment for Larger Files

### Problem
When deploying Docker Compose stacks to Portainer v2.45.3 via API, full-size compose files (~3.76 KB) consistently caused timeouts with `Invoke-RestMethod`, `WebClient`, and `curl` POST requests, while minimal test files (~0.08 KB) deployed successfully.

### Root Cause
The `/api/stacks/create/standalone/string` endpoint has issues handling larger payloads over HTTP POST requests. This appears to be a limitation or bug in Portainer's API endpoint for string-based stack creation.

### Solution: Use Git-Based Deployment
Instead of pushing the compose file content in the API request body:

1. **Push the docker-compose file to a Git repository**
   ```powershell
   git add docker-compose.portainer.yml
   git commit -m "Add docker-compose.portainer.yml for Portainer deployment"
   git push origin master
   ```

2. **Deploy using Portainer's Git endpoint** (`/api/stacks/create/git`):
   ```powershell
   $Body = @{
       name = "ai-memory"
       repositoryURL = "https://github.com/whlim1/AIPlatform.git"
       repositoryReference = "master"
       composeFilePath = "docker-compose.portainer.yml"
       endpointId = 3
   } | ConvertTo-Json -Depth 10
   
   Invoke-RestMethod -Uri "$PortainerUrl/api/stacks/create/git?endpointId=3" `
       -Method "POST" -Headers $Headers -Body $Body
   ```

### Benefits of Git-Based Deployment
- No payload size limitations
- Portainer handles pulling the repository internally
- Better reliability and reproducibility
- Version control integration
- Recommended by Portainer documentation

### Key Learning
**Always prefer Git-based deployment for Portainer stacks when possible**, especially for files larger than ~1 KB. Reserve string-based deployments (`/api/stacks/create/standalone/string`) only for very small compose configurations or testing scenarios.

### Related Files
- `deploy-git.ps1` - Git-based deployment script (working)
- `docker-compose.portainer.yml` - Compose file stored in Git
- `deploy-portainer.ps1` - Failed string-based deployment attempt
