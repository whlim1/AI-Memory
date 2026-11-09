# Research Findings

> **Purpose:** Technical research, benchmarks, comparisons, and verified facts.

---

## R-001: Qdrant Performance Characteristics
- **Date:** 2025-01-01
- **Source:** Qdrant documentation + community benchmarks
- **Findings:**
  - Written in Rust. Single-node can handle millions of vectors.
  - Snapshot: `PUT /collections/{name}/snapshots` creates a full snapshot.
  - Restore: `PUT /collections/{name}/snapshots/upload?wait=true`
  - Config via `config.yaml` (graceful_shutdown, temp_dir, storage).
  - Default port: 6333 (HTTP), 6334 (gRPC).
  - Supports HNSW index (default) with configurable `m`, `ef_construct`.
  - Payload indexing for metadata filtering.
- **Implication:** Single Docker container is sufficient. No cluster needed.

## R-002: LM Studio API Compatibility
- **Date:** 2025-01-01
- **Source:** Direct API test
- **Findings:**
  - Endpoint: `http://0.0.0.0:1234/v1`
  - OpenAI-compatible: `/v1/chat/completions`, `/v1/embeddings`, `/v1/models`
  - Auth: Bearer token required (401 without)
  - Model: Qwen3.8-27B (confirmed by user)
  - GPU: Intel Iris Xe (integrated) - likely CPU inference
- **Implication:** Use OpenAI SDK or raw HTTP. Key from Infisical.

## R-003: Continue 2.0 Configuration
- **Date:** 2025-01-01
- **Source:** Continue documentation
- **Findings:**
  - Config file: `.continuerc` (YAML) in project root or `~/.continue/config.yaml`
  - Supports: custom models, rules, MCP servers, context providers
  - Context providers: codebase, web, docs, custom
  - Rules: project rules, user rules, inline rules
  - Supports local models via Ollama/LM Studio (OpenAI-compatible)
- **Implication:** Can configure Qdrant as custom context provider via API.

## R-004: Token Counting for Chunking
- **Date:** 2025-01-01
- **Source:** tiktoken library
- **Findings:**
  - `tiktoken` supports cl100k_base (GPT-4), o200k_base (GPT-4o)
  - For Qwen models, use `o200k_base` as approximation (close enough for chunking)
  - 1000 tokens ~= 750 English words ~= 4000-5000 characters
  - 150 token overlap ~= 112 words
- **Implication:** Use tiktoken with o200k_base for chunk size calculation.

## R-005: Windows Docker Desktop Requirements
- **Date:** 2025-01-01
- **Source:** Docker documentation
- **Findings:**
  - Requires WSL 2 backend (recommended) or Hyper-V
  - `wsl --install` enables WSL 2 (admin terminal, reboot required)
  - Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
  - Minimum: Windows 10 21H2 (Build 19044+) or Windows 11
  - This machine: Windows 11 - compatible
  - After install: `docker compose up -d` to start Qdrant
- **Implication:** User needs to: (1) `wsl --install` as admin, (2) reboot, (3) install Docker Desktop, (4) enable WSL 2 backend in Docker settings.

## R-006: Synology NAS Backup Options
- **Date:** 2025-01-01
- **Source:** DSM 7.4 documentation
- **Findings:**
  - SMB/CIFS: `\\192.168.0.16\sharename`
  - rsync: Available via SSH (port 22)
  - Hyper Backup: Synology's native backup tool
  - File Station: Web-based file management
  - PUID/PGID: 1030/100 (user-specified)
- **Implication:** Use SMB for simple file backup. rsync for incremental.

## R-007: Qdrant Collection Design
- **Date:** 2025-01-01
- **Source:** Qdrant documentation + project requirements
- **Findings:**
  - 8 collections planned (see Memory-Index.md)
  - Metadata schema: repository, path, filename, language, last_modified, summary, tags
  - Vector size: depends on embedding model (Qwen3.8-27B embeddings = 4096 dims typically)
  - Distance: Cosine (best for semantic search)
  - HNSW params: m=16, ef_construct=100 (defaults are fine for <1M vectors)
- **Implication:** Create collections with appropriate metadata payload schema.
