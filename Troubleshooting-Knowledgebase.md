# Troubleshooting Knowledge Base

> **Purpose:** Known issues, fixes, workarounds. Search here before debugging.
> **Last Updated:** 2026-11-09 (documentation refresh)

---

## T-001: Docker Desktop Not Found
- **Status:** ✅ RESOLVED (2026-11-08) — Docker Desktop 29.9.2 installed, daemon running, WSL 2 `docker-desktop` distro Running, Compose v5.6.1.
- **Symptom:** `docker` command not recognized. Qdrant cannot start.
- **Cause:** Docker Desktop not installed. WSL 2 not enabled.
- **Fix:**
  1. Open PowerShell as Admin: `wsl --install`
  2. Reboot
  3. Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
  4. In Docker Desktop settings: Enable "Use WSL 2 based engine"
  5. Verify: `docker --version` and `docker compose version`
- **Prevention:** Check `docker --version` at session start.

## T-002: LM Studio Returns 401
- **Symptom:** `curl http://localhost:1234/v1/models` returns 401 Unauthorized.
- **Cause:** API key not provided or incorrect.
- **Fix:**
  1. Get key from Infisical: `infisical get <secret-path>`
  2. Set env var: `$env:LMSTUDIO_API_KEY = "..."`
  3. Retry: `curl -H "Authorization: Bearer $env:LMSTUDIO_API_KEY" http://localhost:1234/v1/models`
- **Prevention:** Always source key from Infisical. Never hardcode.

## T-003: Qdrant Port Conflict
- **Symptom:** Qdrant fails to start. "Address already in use" on port 6333.
- **Cause:** Another process using port 6333.
- **Fix:**
  1. Find process: `netstat -ano | findstr :6333`
  2. Kill process or change Qdrant port in docker-compose.yml
- **Prevention:** Document port assignments. Check before starting.

## T-004: Disk Space Running Low
- **Symptom:** Backups failing. Qdrant write errors.
- **Cause:** D: drive filling up (backups, snapshots).
- **Fix:**
  1. Check: `Get-PSDrive D | Select-Object Used, Free`
  2. Clean old backups: `Remove-Item D:\backups\ai-memory\*.zip -Filter "*-old*"`
  3. Rotate Qdrant snapshots: keep last 7, delete older
- **Prevention:** Monitoring alert at 80% disk usage.

## T-005: Continue 2.0 Cannot Reach Qdrant
- **Symptom:** Retrieval returns empty results. "Connection refused" in logs.
- **Cause:** Qdrant not running. Wrong port. Firewall blocking.
- **Fix:**
  1. Check Qdrant: `curl http://localhost:6333/healthz`
  2. Check Docker: `docker ps | findstr qdrant`
  3. Check firewall: `New-NetFirewallRule -DisplayName "Qdrant" -Direction Inbound -LocalPort 6333 -Protocol TCP -Action Allow`
- **Prevention:** Health check script runs before Continue starts.

## T-006: Embedding Dimension Mismatch
- **Symptom:** Qdrant rejects upsert. "Vector size mismatch".
- **Cause:** Collection created with wrong vector size. Model changed.
- **Fix:**
  1. Check collection: `curl http://localhost:6333/collections/{name}`
  2. If wrong: Delete and recreate collection with correct size
  3. Re-embed all content
- **Prevention:** Document vector size per collection. Validate before upsert.

## T-007: Python Module Not Found
- **Symptom:** `ModuleNotFoundError: No module named 'qdrant_client'`
- **Cause:** Dependencies not installed.
- **Fix:**
  1. `pip install -r D:\AI-Memory\requirements.txt`
  2. Or: `pip install qdrant-client` (only external dependency)
- **Prevention:** Use virtual environment. `python -m venv venv`

## T-008: Synology NAS Unreachable
- **Symptom:** SMB backup fails. "Network path not found".
- **Cause:** NAS offline. Wrong share name. Firewall.
- **Fix:**
  1. Ping: `ping 192.168.0.16`
  2. Check share: `net view \\192.168.0.16`
  3. Check DSM: `http://192.168.0.16:5001`
- **Prevention:** NAS health check in monitoring.

## T-009: WSL2 Not Running
- **Symptom:** Docker Desktop won't start. "WSL not found".
- **Cause:** WSL 2 not installed or disabled.
- **Fix:**
  1. `wsl --install` (admin)
  2. Reboot
  3. `wsl --list --verbose` (verify WSL 2)
- **Prevention:** Check `wsl --list` at session start.

## T-010: Qdrant Snapshot Restore Fails
- **Symptom:** Restore returns error. Collection not found.
- **Cause:** Snapshot corrupted. Collection name mismatch.
- **Fix:**
  1. List snapshots: `curl http://localhost:6333/collections/{name}/snapshots`
  2. Try older snapshot
  3. If all fail: Restore from D:\backups\qdrant\
- **Prevention:** Test restore procedure monthly.

## T-011: Docker Daemon Stopped / WSL Distro Stopped
- **Status:** ⚠️ KNOWN (2026-11-09) — daemon verified running this session; entry added as a known failure mode.
- **Symptom:** `docker` command exists but fails: "Cannot connect to the Docker daemon at unix:///var/run/docker.sock" or "WSL distro 'docker-desktop' is not running". `docker ps` hangs or errors.
- **Cause:** Docker Desktop daemon exited (crash, update, sleep/hibernate) or the `docker-desktop` WSL distro was stopped (`wsl --shutdown` kills it).
- **Fix:**
  1. Check state: `wsl --list --verbose` (docker-desktop should be `Running`)
  2. Start daemon: `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"` (or launch from Start menu)
  3. Wait for whale icon to be stable, then verify: `docker info` and `docker compose version`
  4. If still failing: `wsl --shutdown` then relaunch Docker Desktop (full reset)
- **Prevention:** Run `docker info` before any deployment task (e.g. task 2.2). If daemon is down, start it before `docker compose up`.
- **Related:** T-001 (not installed), T-009 (WSL2 not installed)
