# Memory Index

> **Purpose:** Entry point for any agent session. Read this file FIRST.
> **Rule:** This index is authoritative. If it conflicts with conversation context, this file wins.

## Last Updated
- **Date:** 2026-11-11 (packaging recreation + pipeline import fixes)
- **Agent:** AI Infrastructure Architect
- **Status:** Phase 2 — tasks 2.2–2.7 done, next 2.8; packaging recreated + imports fixed 2026-11-11 (Phase 3 install unblocked)

## Authoritative Files (Load at Every Session Start)

| File | Purpose | Priority |
|------|---------|----------|
| `Memory-Index.md` | This file - navigation & state | 1 |
| `Active-Context.md` | Current task, blockers, decisions in flight | 2 |
| `Session-Handover.md` | What was done, what's next, gotchas | 3 |
| `Task-Queue.md` | Ordered work items with status | 4 |
| `Decisions.md` | All architectural & operational decisions | 5 |

## Directory Map

```
D:\AI-Memory\
+-- Memory-Index.md              <- YOU ARE HERE
+-- Active-Context.md            <- Current working state
+-- Session-Handover.md          <- Session continuity log
+-- Task-Queue.md                <- Work items
+-- Decisions.md                 <- Decision records
+-- Research-Findings.md         <- Technical research
+-- Documentation-Index.md       <- Doc navigation
+-- System-Architecture.md       <- Platform architecture
+-- Troubleshooting-Knowledgebase.md <- Known issues & fixes
|
+-- architecture/                <- Deep architecture docs
+-- decisions/                   <- Individual decision records (ADR format)
+-- research/                    <- Research notes, benchmarks, comparisons
+-- sessions/                    <- Archived session logs
+-- troubleshooting/             <- Detailed troubleshooting guides
+-- project-summaries/           <- Per-project state summaries
+-- archives/                    <- Superseded / historical content
+-- templates/                   <- Templates for new docs
```

## Platform Components

| Component | Location | Status |
|-----------|----------|--------|
| AI-Memory (knowledge base) | `D:\AI-Memory\` (= `\\192.168.0.16\docker\AI-Memory\`) | 9 docs + 4 templates, refreshed 2026-11-09 |
| Qdrant (vector DB) | `C:\docker\qdrant\` | Docker 29.9.2 ready; deployment pending (task 2.2) |
| Ingestion pipeline | `D:\AI-Memory\ai_memory_pipeline\` | Code exists (chunking, redaction, semantic summary, metadata, Qdrant client); packaging recreated + imports fixed 2026-11-11; unit tests pending (task 1.16) |
| Indexers | `D:\AIPlatform\indexers\` | Not started |
| Memory sync | `D:\AIPlatform\memory-sync\` | Not started |
| Continue 2.0 config | `D:\AIPlatform\continue\` | Not started |
| LM Studio integration | `D:\AIPlatform\lmstudio\` | Not started |
| Backups | `D:\backups\` | Not started |
| Monitoring | `D:\AIPlatform\monitoring\` | Not started |
| Documentation | `D:\AIPlatform\docs\` | Not started |

## Qdrant Collections (Planned)

| Collection | Purpose |
|------------|---------|
| `project-memory` | Project state, summaries, context |
| `architecture` | System design, component relationships |
| `decisions` | ADRs, rationale, trade-offs |
| `research` | Technical findings, benchmarks |
| `documentation` | API docs, guides, references |
| `sessions` | Session history, handovers |
| `source-code` | Code chunks (last retrieval priority) |
| `troubleshooting` | Known issues, fixes, workarounds |

## Retrieval Priority Order

```
1. project-memory     -> "What are we building / what's the state?"
2. decisions          -> "Why did we choose X over Y?"
3. architecture       -> "How does the system work?"
4. documentation      -> "How do I use / configure X?"
5. source-code        -> "Show me the implementation" (LAST RESORT)
```

## Key Rules

1. **Never assume conversation context persists.** Load authoritative files at session start.
2. **Search Qdrant before reading source code.**
3. **Summaries over files. Memory over conversation. Evidence over assumptions.**
4. **Redact secrets before chunking.** Never embed API keys, passwords, private keys.
5. **Repository source code is NOT long-term memory.** Durable knowledge lives in AI-Memory.
6. **After every task:** Update Active-Context, Task-Queue, Decisions (if applicable), Session-Handover.
7. **opencode uses UNC paths only, NOT SMB drive letters.** `D:\AI-Memory\` will NOT work in opencode — use `\\192.168.0.16\docker\AI-Memory\`. (`D:\` is an SMB mapping of `\\192.168.0.16\docker`; `C:\docker\qdrant\` is local and stays as-is.)
