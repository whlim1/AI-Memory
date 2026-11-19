/**
 * Offline-first sync service.
 *
 * Captured notes are always written locally first (queue + vault file).
 * When the backend is reachable, pending notes are pushed in FIFO order.
 * A note stays in the queue until the backend confirms it (doc_id).
 */
import { CapturedNote, AppSettings, SyncSummary } from "../types";
import { ingestNote, checkApi } from "./api";
import { writeNoteToVault } from "../obsidian-sync/vaultWriter";

let syncing = false;

export async function enqueueNote(
  settings: AppSettings,
  note: Omit<CapturedNote, "status" | "createdAt">
): Promise<CapturedNote> {
  const captured: CapturedNote = {
    ...note,
    createdAt: Date.now(),
    status: "pending",
  };
  // Write the Markdown file into the local vault mirror immediately so
  // the note survives app restarts and is visible to the vault watcher.
  try {
    captured.vaultPath = await writeNoteToVault(settings, captured);
  } catch (e) {
    captured.lastError = `Vault write failed: ${String(e)}`;
  }
  return captured;
}

/**
 * Push all pending notes to the backend.
 *
 * Returns a summary; never throws (callers may run this on a timer).
 */
export async function syncPending(
  settings: AppSettings,
  queue: CapturedNote[]
): Promise<{ summary: SyncSummary; queue: CapturedNote[] }> {
  if (syncing) {
    return { summary: summarize(queue), queue };
  }
  syncing = true;
  try {
    const online = await checkApi(settings);
    const updated = [...queue];
    let synced = 0;
    let failed = 0;

    if (online) {
      for (let i = 0; i < updated.length; i++) {
        const note = updated[i];
        if (note.status === "synced") continue;
        updated[i] = { ...note, status: "syncing" };
        try {
          const res = await ingestNote(settings, {
            title: note.title,
            body: note.body,
            tags: note.tags,
            template: note.template,
          });
          updated[i] = {
            ...updated[i],
            status: "synced",
            docId: res.doc_id,
            lastError: undefined,
          };
          synced++;
        } catch (e) {
          updated[i] = {
            ...updated[i],
            status: "error",
            lastError: String(e),
          };
          failed++;
        }
      }
    }

    return {
      summary: {
        synced,
        failed,
        pending: updated.filter((n) => n.status !== "synced").length,
        lastSyncAt: Date.now(),
      },
      queue: updated,
    };
  } finally {
    syncing = false;
  }
}

export function summarize(queue: CapturedNote[]): SyncSummary {
  return {
    synced: queue.filter((n) => n.status === "synced").length,
    failed: queue.filter((n) => n.status === "error").length,
    pending: queue.filter((n) => n.status !== "synced").length,
  };
}
