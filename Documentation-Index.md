# Documentation Index

> **Purpose:** Navigation for all documentation across the platform.
> **Last Updated:** 2026-11-09 (documentation refresh)
> **Path note:** `D:\` is an SMB mapping of `\\192.168.0.16\docker\`. In opencode, use UNC paths only (e.g. `\\192.168.0.16\docker\AI-Memory\`).

## AI-Memory (D:\AI-Memory\ = \\192.168.0.16\docker\AI-Memory\)

| File | Description |
|------|-------------|
| `Memory-Index.md` | Entry point, directory map, key rules |
| `Active-Context.md` | Current state, blockers, environment |
| `Session-Handover.md` | Session log, what was done/next |
| `Task-Queue.md` | All work items with status |
| `Decisions.md` | ADRs with rationale |
| `Research-Findings.md` | Technical research |
| `System-Architecture.md` | Platform architecture |
| `Troubleshooting-Knowledgebase.md` | Known issues & fixes |
| `templates/troubleshooting-template.md` | Template for new blocker entries (T-XXX) |
| `templates/decision-template.md` | Template for new ADRs (D-XXX) |
| `templates/research-template.md` | Template for research notes |
| `templates/session-template.md` | Template for session logs |

## AIPlatform (D:\AIPlatform\)

| Directory | Purpose |
|-----------|---------|
| `config/` | Platform configuration files |
| `continue/` | Continue 2.0 configs, prompts, workflows |
| `docs/` | Operational documentation, runbooks |
| `indexers/` | Repository indexing services |
| `ingestion/` | Chunking, redaction, embedding pipeline |
| `lmstudio/` | LM Studio integration configs |
| `memory-sync/` | Memory synchronization services |
| `tests/` | Test suites |

## Docker (C:\docker\)

| Directory | Purpose |
|-----------|---------|
| `qdrant/config/` | Qdrant config.yaml |
| `qdrant/scripts/` | Health check, backup, restore, maintenance |
| `qdrant/backups/` | Qdrant snapshots |
| `qdrant/snapshots/` | Active snapshots |
| `qdrant/logs/` | Qdrant logs |
| `backups/qdrant/` | Qdrant backup copies |

## Backups (D:\backups\)

| Directory | Purpose |
|-----------|---------|
| `ai-memory/` | AI-Memory backups (daily incremental, weekly full) |
| `config/` | Config file backups |
| `qdrant/` | Qdrant snapshot backups |

## External References

| Resource | URL |
|----------|-----|
| Qdrant Docs | https://qdrant.tech/documentation/ |
| Continue 2.0 | https://docs.continue.dev/ |
| LM Studio | https://lmstudio.ai/docs/ |
| Infisical | https://infisical.com/docs |
| Docker Desktop | https://docs.docker.com/desktop/ |
| Synology DSM | https://www.synology.com/en-us/knowledgebase |
