# System Architecture

> **Purpose:** High-level architecture of the AI Memory & Retrieval Platform.

## Overview

```
+------------------------------------------------------------------+
|                        USER (VS Code + Continue 2.0)              |
+------------------------------------------------------------------+
         |                              |
         | (retrieval queries)          | (LLM inference)
         v                              v
+------------------+          +------------------+
|   QDRANT         |          |   LM STUDIO      |
|   (Vector DB)    |          |   (Local LLM)    |
|   Port: 6333     |          |   Port: 1234     |
|   Docker         |          |   Qwen3.8-27B    |
+------------------+          +------------------+
         ^                              ^
         |                              |
         | (ingest: chunk, embed, store)| (embeddings, summaries)
         |                              |
+------------------------------------------------------------------+
|                    INGESTION PIPELINE (Python)                    |
|  +----------+  +----------+  +----------+  +----------+         |
|  | Redactor |->| Chunker  |->| Embedder |->| Qdrant   |         |
|  +----------+  +----------+  +----------+  | Client   |         |
|                                               +----------+         |
+------------------------------------------------------------------+
         ^
         | (source content)
         |
+------------------------------------------------------------------+
|                    AI-MEMORY (D:\AI-Memory\)                      |
|  Authoritative knowledge: decisions, architecture, research,      |
|  sessions, troubleshooting, project summaries                     |
+------------------------------------------------------------------+
         ^
         | (sync)
         |
+------------------------------------------------------------------+
|                    MEMORY SYNC SERVICE                            |
|  Watches AI-Memory, re-indexes changed files into Qdrant         |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    BACKUP LAYER                                   |
|  D:\backups\ai-memory\    (daily incremental, weekly full)        |
|  C:\docker\qdrant\backups\ (snapshots)                            |
|  Synology NAS 192.168.0.16 (secondary)                            |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    MONITORING                                     |
|  Health checks, log rotation, disk usage, Qdrant metrics          |
+------------------------------------------------------------------+
```

## Component Details

### 1. Qdrant (Vector Database)
- **Deployment:** Docker container
- **Port:** 6333 (HTTP), 6334 (gRPC)
- **Storage:** `C:\docker\qdrant\` (volumes)
- **Collections:** 8 (project-memory, architecture, decisions, research, documentation, sessions, source-code, troubleshooting)
- **Index:** HNSW (m=16, ef_construct=100)
- **Distance:** Cosine
- **Snapshots:** Daily, retained 7 days
- **Config:** `C:\docker\qdrant\config\config.yaml`

### 2. LM Studio (Local LLM)
- **Endpoint:** `http://0.0.0.0:1234/v1`
- **Model:** Qwen3.8-27B
- **Auth:** Bearer token (Infisical-managed)
- **Use:** Embeddings, semantic summaries, chat
- **API:** OpenAI-compatible

### 3. Ingestion Pipeline (Python)
- **Location:** `D:\AI-Memory\ai_memory_pipeline\`
- **Modules:**
  - `chunking.py` — sentence/word/paragraph splitting, `chunk_text`, `chunk_generator`
  - `redaction.py` — `Redactor` class + `redact_pii` (regex-based PII redaction)
  - `semantic_summary.py` — `SemanticSummarizer` class + `summarize_text`
  - `metadata.py` — `DocumentMetadata`, `extract_metadata_from_text`, `merge_metadata`
  - `qdrant_client.py` — `QdrantManager` (upsert/query)
- **Packaging:** `pyproject.toml` + `requirements.txt` at repo root (recreated 2026-11-11); only external dependency is `qdrant-client>=1.7`

### 4. Memory Sync Service
- **Location:** `D:\AIPlatform\memory-sync\`
- **Function:** Watches `D:\AI-Memory\` for changes, re-indexes into Qdrant
- **Trigger:** File system events (watchdog) or scheduled (Task Scheduler)
- **Conflict resolution:** AI-Memory is authoritative. Qdrant is derived.

### 5. Continue 2.0 (IDE Agent)
- **Location:** `D:\AIPlatform\continue\`
- **Config:** `.continuerc` (YAML)
- **Context providers:** Qdrant (custom), codebase, docs
- **Rules:** Project rules, memory rules
- **Models:** LM Studio (Qwen3.8-27B)

### 6. Backup Layer
- **AI-Memory:** `D:\backups\ai-memory\` (daily incremental, weekly full)
- **Qdrant:** `C:\docker\qdrant\backups\` (snapshots, 7-day retention)
- **Secondary:** Synology NAS `192.168.0.16`
- **Scheduler:** Windows Task Scheduler

### 7. Monitoring
- **Health checks:** Qdrant `/healthz`, LM Studio `/v1/models`
- **Logs:** `C:\docker\qdrant\logs\`, `D:\AIPlatform\logs\`
- **Alerts:** Disk usage >80%, Qdrant down, LM Studio unreachable

## Data Flow

### Ingestion Flow
```
Source File (AI-Memory / Repo / Docs)
    |
    v
[Redactor] -- strips secrets, PII --> [REDACTED]
    |
    v
[Chunker] -- 1000 tokens, 150 overlap
    |
    v
[Embedder] -- LM Studio /v1/embeddings
    |
    v
[Qdrant Client] -- upsert with metadata
    |
    v
Qdrant Collection (indexed, searchable)
```

### Retrieval Flow
```
User Query (Continue 2.0)
    |
    v
[Qdrant Query] -- semantic search + metadata filter
    |
    v
[Ranked Results] -- priority: memory > decisions > arch > docs > code
    |
    v
[Context Assembly] -- top N chunks + summaries
    |
    v
[LM Studio] -- generate response with context
    |
    v
Response to User
```

## Security Model

| Layer | Mechanism |
|-------|-----------|
| Secrets | Infisical (env vars), never in code/memory |
| Redaction | Pre-embedding pipeline (API keys, passwords, PII) |
| Network | Local only (no cloud). Tailscale for remote access. |
| Docker | Non-root (PUID=1030, PGID=100) |
| Backups | Encrypted at rest (BitLocker on D:), SMB to NAS |
| Access | Local machine only. Tailscale for authorized peers. |

## Scalability Considerations

- **Single node** is sufficient for <10M vectors
- **Qdrant** can scale to cluster mode if needed (add nodes)
- **LM Studio** is the bottleneck for embeddings (CPU inference)
- **AI-Memory** is markdown - scales indefinitely
- **Backups** grow linearly with content size
- **5+ year lifespan:** Qdrant snapshots + AI-Memory markdown = durable
