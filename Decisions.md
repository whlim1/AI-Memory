# Decisions

> **Purpose:** Record of all architectural and operational decisions with rationale.
> **Format:** ADR-lite (Context, Decision, Consequences)

---

## D-001: Local-First Architecture
- **Date:** 2025-01-01
- **Context:** User requires a private homelab AI platform. No cloud services.
- **Decision:** All components run locally. Qdrant via Docker, LM Studio for inference, Continue 2.0 as IDE agent.
- **Consequences:** Full data sovereignty. Limited by local hardware. No latency to cloud.

## D-002: Qdrant for Vector Search
- **Date:** 2025-01-01
- **Context:** Need semantic search over AI-Memory, code, docs. Must support metadata filtering, snapshots, local deployment.
- **Decision:** Qdrant (Rust-based, high-performance, Docker-native, snapshot support).
- **Alternatives considered:** Chroma (simpler but less performant), Weaviate (heavier), Milvus (overkill for single-node).
- **Consequences:** Requires Docker. Excellent performance. Native snapshot/restore.

## D-003: LM Studio for Local Inference
- **Date:** 2025-01-01
- **Context:** Need local LLM for embeddings and summarization. Already running.
- **Decision:** Use LM Studio (OpenAI-compatible API at `0.0.0.0:1234`). Model: Qwen3.8-27B.
- **Consequences:** No cloud API costs. Auth required (Infisical-managed key). GPU: Intel Iris Xe (CPU inference likely).

## D-004: Continue 2.0 as IDE Agent
- **Date:** 2025-01-01
- **Context:** Need VS Code integration for retrieval-augmented coding.
- **Decision:** Continue 2.0 with custom config, system prompts, and retrieval workflows.
- **Consequences:** Extensible. Supports custom rules, MCP, local models.

## D-005: AI-Memory as Authoritative Knowledge Base
- **Date:** 2025-01-01
- **Context:** Conversation context is ephemeral. Need durable, retrievable knowledge.
- **Decision:** `D:\AI-Memory\` is the single source of truth. Markdown files + Qdrant vectors.
- **Consequences:** Agents MUST load AI-Memory at session start. Reduces context consumption by 75%+.

## D-006: Python for Ingestion Pipeline
- **Date:** 2025-01-01
- **Context:** Need chunking, redaction, embedding, Qdrant interaction.
- **Decision:** Python 3.15 (available). Libraries: qdrant-client, tiktoken (or similar), regex for redaction.
- **Consequences:** No Node.js dependency. Rich ecosystem. Type-hinted.

## D-007: Secrets via Infisical
- **Date:** 2025-01-01
- **Context:** LM Studio API key, any future credentials.
- **Decision:** Use Infisical (already deployed). Inject via environment variables. NEVER hardcode.
- **Consequences:** Centralized secrets. Audit trail. No secrets in code or memory files.

## D-008: Retrieval Priority Order
- **Date:** 2025-01-01
- **Context:** Reduce context consumption. Avoid loading source code unnecessarily.
- **Decision:** project-memory > decisions > architecture > documentation > source-code (last resort).
- **Consequences:** 75%+ context reduction. Source code only when summaries insufficient.

## D-009: Chunking Strategy
- **Date:** 2025-01-01
- **Context:** Need consistent chunk sizes for embedding.
- **Decision:** 1000 tokens per chunk, 150 token overlap. Semantic boundaries preferred (functions, sections).
- **Consequences:** Good balance of context and granularity. Overlap prevents context loss at boundaries.

## D-010: Redaction Before Embedding
- **Date:** 2025-01-01
- **Context:** Security requirement. No secrets in vector store.
- **Decision:** All content passes through redaction service BEFORE chunking/embedding. Patterns: API keys, passwords, private keys, connection strings, PII.
- **Consequences:** Safe to store. `[REDACTED]` placeholder. Audit log of redactions.

## D-011: Directory Layout (C: vs D:)
- **Date:** 2025-01-01
- **Context:** User preference. C: for Docker (performance), D: for data.
- **Decision:**
  - `C:\docker\` - Docker root (Qdrant volumes, images)
  - `D:\AI-Memory\` - Knowledge base
  - `D:\AIPlatform\` - Platform services, configs, code
  - `D:\backups\` - Backup target
  - `D:\repositories\` - Git repos
- **Consequences:** Clear separation. Docker on C: for I/O performance. Data on D: for capacity.

## D-012: Synology NAS for Secondary Backup
- **Date:** 2025-01-01
- **Context:** Need off-machine backup.
- **Decision:** Synology DS420+ at `192.168.0.16` (ToolRoom). PUID=1030, PGID=100.
- **Consequences:** Network backup. Redundancy. Not primary (local D: is primary).

## D-013: Do NOT Redesign Infisical
- **Date:** 2025-01-01
- **Context:** Infisical already deployed and working.
- **Decision:** Use as-is. Reference secrets via env vars. Do not modify its architecture.
- **Consequences:** Stability. No migration risk.
