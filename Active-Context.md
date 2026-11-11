# Active Context

> **Purpose:** Snapshot of the current working state. Updated at the end of every task/session.
> **Rule:** If this file says "X is done" but you're not sure, verify before proceeding.

## Last Updated
- **Date:** 2026-11-11
- **Session:** Pipeline Packaging & Import Fixes (Phase 2 — tasks 2.2–2.7 still done, next 2.8; packaging recreated + `__init__.py` imports fixed)
- **Agent:** AI Infrastructure Architect

## Current Phase
**Phase 2: Qdrant Deployment** (Docker Compose + Qdrant container)

## Current Task
- [x] Environment discovery & verification
- [x] Directory skeleton creation (C:\docker, D:\AI-Memory, D:\AIPlatform, D:\backups, D:\repositories)
- [x] Document findings for post-reboot continuity
- [x] Docker Desktop 29.9.2 installed + WSL 2 running (verified 2026-11-09)
- [x] Docker Compose v5.6.1 installed
- [x] AI-Memory core files (9 docs + 4 templates)
- [x] AI-Memory documentation refresh (2026-11-09)
- [x] Python: Project structure (pyproject.toml, requirements) 
- [x] Qdrant docker-compose.yml (task 2.2) — committed to AI-Memory repo
- [x] Qdrant config.yaml (task 2.3) — committed to `C:\docker\qdrant` repo (first commit)
- [x] Health check script (task 2.4) — `C:\docker\qdrant\scripts\health-check.ps1` (container + /healthz + /readyz + collections; exit 0/1)
- [x] Startup script (task 2.5) — `C:\docker\qdrant\scripts\start-qdrant.ps1` (idempotent compose up + /readyz wait, up to 3 restarts; exit 0/1)
- [x] Backup script (task 2.6) — `C:\docker\qdrant\scripts\backup-qdrant.ps1` (snapshots all collections to `backups\`, 7-day retention; exit 0/1)
- [x] Restore script (task 2.7) — `C:\docker\qdrant\scripts\restore-qdrant.ps1` (restores from `backups\` via snapshot upload API; `-List`/`-Collection`/`-SnapshotFile`/default-all; type-`YES` confirmation unless `-Force`; verifies + reports vector count; exit 0/1)
- [ ] **NEXT:** Maintenance script (optimize, vacuum) — task 2.8

## Blockers

| Blocker | Owner | Status | Workaround |
|---------|-------|--------|------------|
| (none) | — | — | — |

## Environment State (Verified)

### Hardware
- **Machine:** GMKtec X1 Pro (Windows 11)
- **CPU:** Intel Core i5-13420H (8 cores, 12 threads)
- **RAM:** 32 GB
- **GPU:** Intel Iris Xe (integrated)
- **Disk C:** 476 GB total, ~699 GB free (after cleanup)
- **Disk D:** 476 GB total, ~475 GB free

### Software (Installed)
| Software | Version | Notes |
|----------|---------|-------|
| Python | 3.15.2 | `python` on PATH |
| pip | 26.2.2 | |
| Tailscale | Active | Peers: inference-server (100.107.178.74), husband-phone (100.93.101.103), synology-nas (100.68.127.11) |
| LM Studio | Running | `0.0.0.0:1234`, OpenAI-compatible API, auth required (401 without key) |
| Synology NAS | DS420+, DSM 7.4.1-90080 | `192.168.0.16`, hostname `ToolRoom`, port 5001 open |
| Infisical | Deployed | Secrets management (do NOT redesign) |
| VS Code | Installed | Continue 2.0 extension target |
| Docker Desktop | 29.9.2 | WSL 2 backend (`docker-desktop` distro Running), daemon verified 2026-11-09 |
| Docker Compose | v5.6.1 | Standalone plugin |
| WSL 2 | Enabled | `docker-desktop` distro Running |

### Software (NOT Installed)
| Software | Impact |
|----------|--------|
| Node.js | Not needed for core pipeline (Python-based) |

### Network
- **LAN:** 192.168.0.10 (this machine)
- **Tailscale:** 100.68.127.11 (synology-nas), 100.107.178.74 (inference-server)
- **LM Studio:** `http://0.0.0.0:1234/v1` (OpenAI-compatible)
- **Synology:** `http://192.168.0.16:5001` (DSM web)

## Key Decisions (Summary)
- Local-first, no cloud
- Qdrant for vector search (Docker)
- LM Studio for local LLM inference (Qwen3.8-27B)
- Continue 2.0 as IDE agent
- AI-Memory as authoritative long-term knowledge
- Python 3.15 for ingestion/indexing pipeline
- Secrets via Infisical (env vars), never hardcoded
- PUID=1030, PGID=100 for Synology containers

## Next Actions (Ordered)
1. ~~Document findings~~ (this file)
2. ~~User installs Docker Desktop + WSL 2~~ (done 2026-11-09)
3. ~~User reboots~~ (done 2026-11-09)
4. ~~Agent resumes: create remaining AI-Memory core files~~ (done)
5. ~~AI-Memory documentation refresh~~ (done 2026-11-09)
6. ~~Deploy Qdrant (docker compose)~~ — tasks 2.2/2.3 done (compose + config.yaml)
7. **Qdrant ops scripts** — ~~health check (2.4)~~ done; ~~startup (2.5)~~ done; ~~backup (2.6)~~ done; restore (2.7), maintenance (2.8)
8. **Create 8 collections** with HNSW params (2.9) + metadata schema (2.10)
9. **Snapshot rotation (2.11) + recovery docs (2.12)**
10. Build Python ingestion pipeline (Phase 1 tasks 1.10–1.16)
11. Configure Continue 2.0
12. Integrate LM Studio
13. Backup automation
14. Monitoring
15. Documentation
