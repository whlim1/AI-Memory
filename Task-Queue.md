# Task Queue

> **Purpose:** Ordered work items. Status: [ ] pending, [~] in progress, [x] done, [!] blocked

## Phase 1: Foundation (No Docker Required)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Environment discovery & verification | [x] | Done 2026-11-08 |
| 1.2 | Directory skeleton creation | [x] | Done 2026-11-08 |
| 1.3 | Document findings (AI-Memory core files) | [x] | Done 2026-11-08 — all 9 core docs + 4 templates created |
| 1.4 | AI-Memory: Decisions.md | [x] | Done 2026-11-08 |
| 1.5 | AI-Memory: Research-Findings.md | [x] | Done 2026-11-08 |
| 1.6 | AI-Memory: Documentation-Index.md | [x] | Done 2026-11-08 |
| 1.7 | AI-Memory: System-Architecture.md | [x] | Done 2026-11-08 |
| 1.8 | AI-Memory: Troubleshooting-Knowledgebase.md | [x] | Done 2026-11-08 |
| 1.9 | AI-Memory: Templates (session, decision, research) | [x] | Done 2026-11-08 — 4 templates incl. troubleshooting |
| 1.17 | AI-Memory: Documentation refresh (all core docs + templates) | [x] | Done 2026-11-09 — Memory-Index, Documentation-Index, Troubleshooting-KB (T-001 resolved, T-011 added), UNC-path rule documented |
| 1.10 | Python: Project structure (pyproject.toml, requirements) | [x] | Created pyproject.toml, requirements.txt, and directory structure — files were missing; recreated 2026-11-11 (qdrant-client>=1.7 is the only external dep) |
| 1.11 | Python: Chunking service (1000 tokens, 150 overlap) | [x] | Done — `ai_memory_pipeline/chunking.py`; verified by unit tests (2026-11-12) |
| 1.12 | Python: Redaction service (secrets, keys, PII) | [x] | Done — `ai_memory_pipeline/redaction.py`; verified by unit tests (2026-11-12) |
| 1.13 | Python: Semantic summary generator | [x] | Done — `ai_memory_pipeline/semantic_summary.py`; verified by unit tests (2026-11-12) |
| 1.14 | Python: Metadata generator | [x] | Done — `ai_memory_pipeline/metadata.py`; verified by unit tests (2026-11-12) |
| 1.15 | Python: Qdrant client wrapper | [x] | Done — `ai_memory_pipeline/qdrant_client.py`; verified by unit tests with stubbed client (no live server needed, 2026-11-12) |
| 1.16 | Python: Unit tests for pipeline | [x] | Done 2026-11-12 — pytest suite in `tests/` (conftest + 5 test modules; qdrant stubbed via sys.modules); **116 passed**; no code bugs found (2 initial failures were wrong test expectations, fixed tests only) |

## Phase 2: Qdrant Deployment (Requires Docker)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | Install Docker Desktop + WSL 2 | [x] | Done — Docker Desktop 29.9.2, WSL 2 (docker-desktop distro Running), Compose v5.6.1; daemon verified 2026-11-09 |
| 2.2 | docker-compose.yml for Qdrant | [x] | Done 2026-11-09 — telemetry off, 1GB upload, on_disk:false, 2CPU/2GB limits, log rotation; local C: paths (SMB unreliable for bind mounts) |
| 2.3 | Qdrant config (config.yaml) | [x] | Done 2026-11-09 — `C:\docker\qdrant\config\config.yaml`; telemetry off, ports 6333/6334, 1GB upload, on_disk:false, WAL 32MB; committed to `C:\docker\qdrant` repo (first commit) |
| 2.4 | Health check script | [x] | Done 2026-11-09 — `C:\docker\qdrant\scripts\health-check.ps1`; checks container + `/healthz` + `/readyz` + collections; exit 0/1 for schedulers; logs to `logs\health-check.log` |
| 2.5 | Startup script (auto-restart) | [x] | Done 2026-11-09 — `C:\docker\qdrant\scripts\start-qdrant.ps1`; idempotent `compose up -d` + `/readyz` wait, up to 3 restarts on failure; exit 0/1 for schedulers; logs to `logs\start-qdrant.log` |
| 2.6 | Backup script (snapshot) | [x] | Done 2026-11-09 — `C:\docker\qdrant\scripts\backup-qdrant.ps1`; snapshots all collections to `backups\`, 7-day retention, exit 0/1 for schedulers; logs to `logs\backup-qdrant.log` |
| 2.7 | Restore script | [x] | Done 2026-11-09 — `C:\docker\qdrant\scripts\restore-qdrant.ps1`; restores from `backups\` via `POST /collections/{name}/snapshots/upload`; modes `-List`/`-Collection`/`-SnapshotFile`/default-all; type-`YES` confirmation unless `-Force`; verifies restored collection + vector count; exit 0/1; logs to `logs\restore-qdrant.log`; committed `bc68b0c` |
| 2.8 | Maintenance script (optimize, vacuum) | [ ] | |
| 2.9 | Create all 8 collections | [ ] | |
| 2.10 | Collection metadata schema | [ ] | |
| 2.11 | Snapshot rotation policy | [ ] | |
| 2.12 | Recovery documentation | [ ] | |

## Phase 3: Integration

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Continue 2.0: .continuerc config | [ ] | |
| 3.2 | Continue 2.0: Agent settings | [ ] | |
| 3.3 | Continue 2.0: Retrieval workflows | [ ] | |
| 3.4 | Continue 2.0: Custom system prompts | [ ] | |
| 3.5 | Continue 2.0: Project manager config | [ ] | |
| 3.6 | Continue 2.0: Memory workflows | [ ] | |
| 3.7 | Continue 2.0: Repository indexing pipeline | [ ] | |
| 3.8 | LM Studio: Config files | [ ] | |
| 3.9 | LM Studio: Connection examples | [ ] | |
| 3.10 | LM Studio: Continue config | [ ] | |
| 3.11 | LM Studio: Endpoint validation | [ ] | |
| 3.12 | LM Studio: Connectivity tests | [ ] | |

## Phase 4: Operations

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Backup: Daily incremental (AI-Memory) | [ ] | Windows Task Scheduler |
| 4.2 | Backup: Weekly full (AI-Memory) | [ ] | |
| 4.3 | Backup: Qdrant snapshots (daily) | [ ] | |
| 4.4 | Backup: Config backup | [ ] | |
| 4.5 | Backup: Collection definitions backup | [ ] | |
| 4.6 | Restore: Full restore procedure | [ ] | |
| 4.7 | Restore: Fresh agent reconstruction test | [ ] | |
| 4.8 | Monitoring: Health checks | [ ] | |
| 4.9 | Monitoring: Log rotation | [ ] | |
| 4.10 | Monitoring: Disk usage alerts | [ ] | |
| 4.11 | Docs: Runbooks | [ ] | |
| 4.12 | Docs: Troubleshooting guide | [ ] | |
| 4.13 | Docs: Security validation | [ ] | |
| 4.14 | Docs: Runtime maintenance | [ ] | |
| 4.15 | Windows: Installation scripts | [ ] | |

## Legend
- [ ] = Pending
- [~] = In Progress
- [x] = Done
- [!] = Blocked (external dependency)
