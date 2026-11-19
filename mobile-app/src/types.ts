/**
 * Shared types for the AI Memory mobile app.
 */

export type CaptureTemplate =
  | "meeting"
  | "idea"
  | "observation"
  | "quote";

export type NoteStatus = "pending" | "syncing" | "synced" | "error";

/** A locally captured note, queued for sync when online. */
export interface CapturedNote {
  id: string;
  template: CaptureTemplate;
  title: string;
  body: string;
  tags: string[];
  createdAt: number; // epoch ms
  status: NoteStatus;
  /** Set after successful sync: stable doc_id from the pipeline. */
  docId?: string;
  /** Relative vault path written by obsidian-sync (e.g. "Inbox/2026-11-19 idea.md"). */
  vaultPath?: string;
  lastError?: string;
}

export interface SyncSummary {
  synced: number;
  failed: number;
  pending: number;
  lastSyncAt?: number;
}

export interface AppSettings {
  /** Base URL of the AI memory ingestion API (Phase 5 service). */
  apiBaseUrl: string;
  /** Qdrant URL for direct status checks. */
  qdrantUrl: string;
  /** LM Studio base URL (used by the backend, shown for diagnostics). */
  lmStudioUrl: string;
  /** Vault subfolder where mobile captures are written. */
  captureFolder: string;
}
