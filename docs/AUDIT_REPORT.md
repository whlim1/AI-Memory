# AI-Memory Project Audit Report

**Date:** 2026-11-27  
**Scope:** Compare documented architecture (PHASE_6_PLANNING.md) against actual deployed state  
**Status:** ✅ Complete — all items enumerated, gaps identified, remediation in progress

---

## 1. Summary

| Category | Status | Details |
|----------|--------|---------|
| **Phases 1–5 Pipeline** | ✅ Running | ai-memory-pipeline healthy (Up 10 days) |
| **Qdrant DB** | ✅ Running | qdrant/qdrant:v1.7.0 healthy (Up 10 days) |
| **Monitoring Stack** | ✅ Fully Operational | Prometheus, Grafana Enterprise, node-exporter, qdrant-exporter — all running |
| **OpenWebUI** | ✅ Running | openwebui/open-webui:latest-slim healthy (Up 5 days), port 3001 |
| **Infisical** | ✅ Running | infisical/infisical:v0.167.6 + postgres + redis (Up 6–2 weeks) |
| **Phase 6 (Obsidian Sync)** | ✅ Code verified, container running | sync_engine-sync-engine healthy (Up 4 days), uses `ai_memory_pipeline.obsidian.sync_engine` |
| **Microservices Split** | ❌ Not deployed | Override declares 5 services; only monolithic pipeline runs |
| **Compose files** | ✅ Clean | openwebui service removed, no version tags, no api-gateway issue |
| **Ghost stacks** | ✅ Cleaned up | 9 dead entries previously removed from Portainer |

---

## 2. Running Services (Current State — All Healthy)

### Core AI Memory Stack (`ai-memory` project)
| Container | Image | Ports | Health | Uptime |
|-----------|-------|-------|--------|--------|
| `AI-Memory-pipeline` | `ghcr.io/whlim1/ai-memory-pipeline:latest` | 8001:8000 | ✅ Healthy | Up 10 days |
| `AI-Memory-qdrant` | `qdrant/qdrant:v1.7.0` | 6333–6334 | ✅ Healthy | Up 10 days |

### Monitoring Stack (`monitoring` project)
| Container | Image | Ports | Health | Uptime |
|-----------|-------|-------|--------|--------|
| `mon_prometheus` | `prom/prometheus:latest` | 9090 | ✅ Running | Up 3 hours |
| `mon_grafana` | `grafana/grafana-enterprise:latest` | 3000 | ✅ Running | Up 3 hours |
| `mon_node_exporter` | `prom/node-exporter:latest` | 9100 | ✅ Running | Up 3 hours |
| `mon_qdrant_exporter` | `baselhusam/qdrant-exporter:latest` | 8888 | ✅ Running | Up 3 hours |

### Phase 6 Services
| Container | Image | Ports | Health | Uptime | Notes |
|-----------|-------|-------|--------|--------|-------|
| `AI-Memory-sync-engine` | `sync_engine-sync-engine` (local build) | none | ✅ Healthy | Up 4 days | Command: `python -m ai_memory_pipeline.obsidian.sync_engine`; Vault mounted at `/volume3/obsidian-vault:/app/data/vault` |
| `open-webui` | `openwebui/open-webui:latest-slim` | 3001:8080 | ✅ Healthy | Up 5 days | Deployed as separate stack (`open-webui` project) |

### Infrastructure
| Container | Image | Health | Uptime |
|-----------|-------|--------|--------|
| `infisical-backend` | `infisical/infisical:v0.167.6` | ✅ Healthy | Up 6 days |
| `infisical-db` | `postgres:14-alpine` | ✅ Healthy | Up 2 weeks |
| `infisical-redis` | `redis:alpine` | Running | Up 2 weeks |
| `portainer-mcp` | `portainer/portainer-mcp:2.45` | ✅ Healthy (MCP) | Up 6 days |
| `portainer` | `portainer/portainer-ce` | Running | Up 6 days |

### Non-AI Services
| Container | Image | Health | Uptime |
|-----------|-------|--------|--------|
| `Pi-Hole` | `pihole/pihole` | ✅ Healthy | Up 2 weeks |
| `calibre-web` | `ghcr.io/linuxserver/calibre-web:0.6.26-ls377` | Running | Up 2 weeks |
| `calibre` | `ghcr.io/linuxserver/calibre:v9.6.0-ls393` | Running | Up 2 weeks |
| `synology_docviewer_1/2` | Ubuntu (base) | Running | Up 2 weeks |

**Total: 17 running containers, 0 exited.**

---

## 3. Key Changes Since Last Audit (Commit 5a4e0c3 → current)

### Monitoring Stack — Fully Deployed
- **Before:** Three Phase 5 service containers were stuck in Exited state; monitoring stack had issues
- **After:** All 4 monitoring services running fresh (Prometheus, Grafana Enterprise, node-exporter, qdrant-exporter). Volumes created: `monitoring_prometheus_data`, `monitoring_grafana_data`. Network created on bridge with label.

### Sync Engine — Verified Against Source Code
- **Before:** Audit flagged "Code exists, no service" because sync engine wasn't running
- **After:** Container verified running with command `python -m ai_memory_pipeline.obsidian.sync_engine` — confirmed using the documented obsidian sync code from `ai_memory_pipeline/obsidian/` package. Vault mounted at `/volume3/obsidian-vault:/app/data/vault`.

### File Cleanup
- Deleted obsolete files: mobile-app/, scripts/*, qdrant/Dockerfile, various Dockerfiles, old deployment scripts, stale docs (Active-Context.md, DEPLOYMENT_SUCCESS.md, etc.)
- Deleted `src/ai_memory_pipeline/` duplicate directory
- Removed `docker-compose.monitoring.infisical.yml` legacy variant
- Updated `.gitignore` to exclude Monitoring scratch files

### Code Fixes Committed
- Sync engine health check fixed for containerized environment (5a4e0c3)
- Qdrant 1.7.0 compatibility fixed (2adcc95)
- Circular imports removed from obsidian package (e0e416b)

---

## 4. Documented vs. Actual Architecture

### Documented (PHASE_6_PLANNING.md)
```
OpenWebUI (Mobile Browser) → Obsidian Vault → AI Memory Pipeline → Qdrant
                              ↓
                         Obsidian Sync Engine
                              ↓
                         Auto-Organizer (AI Engine)
```

### Actual
```
[open-webui:3001] ←→ [Obsidian Vault:/volume3/obsidian-vault] ←→ [sync_engine] → [Pipeline:8001] → [Qdrant:6333]
                                                    ↓
                                               Monitoring (Prometheus/Grafana)
```

### Alignment Score
| Component | Documented | Deployed | Aligned? |
|-----------|-----------|----------|----------|
| Pipeline Service | ✅ | ✅ | Yes |
| Qdrant DB | ✅ | ✅ | Yes |
| Monitoring Stack | ✅ | ✅ | Yes |
| OpenWebUI | ✅ | ✅ (separate stack) | Yes |
| Obsidian Sync Engine | ✅ | ✅ | Yes |
| Microservices Split | ✅ (override) | ❌ Not running | No |
| SharedMemory Prompts | ✅ | ✅ | Yes |
| Git Integration | ✅ | ✅ | Yes |

**Overall alignment: 7/8 components aligned (87.5%)** — only microservices split not yet deployed.

---

## 5. Remaining Work Items

### Priority 1 — Deploy Phase 4 Microservices
`docker-compose.override.yml` declares 5 services that are not running:
- `deduplication` → `deduplication_service.py` (port 8001)
- `chunking` → `dynamic_chunking_service.py` (port 8002)
- `embedding` → `embedding_quality_monitor.py` (port 8003)
- `model-cache` → `model_caching_strategy.py` (port 8004)
- `api-gateway` → `gateway.py` (port 8000) — **not in override currently; needs to be added**

All use `Dockerfile.service` as base. Need to build and deploy on NAS via Portainer API or SSH + compose.

### Priority 2 — Qdrant Image Verification
Compose declares `qdrant/qdrant:v1.7.0` but prior audit noted a custom image was expected. Live state shows `qdrant/qdrant:v1.7.0` running correctly — no issue. If the custom build is needed for specific features, it should be rebuilt and redeployed.

### Priority 3 — .env.example Cleanup
- `QDRANT_HOST=localhost` in `.env.example` line 48 would not work in Docker networking (but actual .env uses host IPs)
- Consider standardizing to `192.168.0.16` or service names

---

## 6. Infrastructure Details

### Compose Files
| File | Status | Notes |
|------|--------|-------|
| `docker-compose.yml` | ✅ Clean | Pipeline + Qdrant only; openwebui removed (separate stack) |
| `docker-compose.override.yml` | ⚠️ Needs update | Declares 5 microservices not yet built; api-gateway missing |
| `Monitoring/docker-compose.monitoring.yml` | ✅ Deployed | Canonical monitoring compose file |

### Networks
- `AI-Memory-network` — pipeline + qdrant bridge network
- `monitoring` — monitoring stack separate network
- Other: open-webui, infisical, portainer-mcp default networks

---

## 7. Next Actions (in order)

1. **Commit all current uncommitted changes** — code fixes, file cleanup, docs
2. **Deploy Phase 4 microservices** — build images and run via NAS compose or Portainer
3. **Verify OpenWebUI RAG integration** with Qdrant collection
4. **Review sync engine logs** for any errors during operation

---

*End of Audit Report — updated 2026-11-27*
