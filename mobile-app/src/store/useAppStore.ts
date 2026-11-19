/**
 * Global app state (zustand).
 *
 * Holds the offline note queue, settings, and sync status. All mutations
 * persist to local storage so the queue survives app restarts.
 */
import { create } from "zustand";
import { CapturedNote, AppSettings, SyncSummary } from "../types";
import { DEFAULT_SETTINGS } from "../config";
import { loadQueue, saveQueue, loadSettings, saveSettings } from "../services/storage";
import { enqueueNote, syncPending, summarize } from "../services/syncService";

interface AppState {
  notes: CapturedNote[];
  settings: AppSettings;
  sync: SyncSummary;
  hydrated: boolean;

  hydrate: () => Promise<void>;
  capture: (
    note: Omit<CapturedNote, "status" | "createdAt">
  ) => Promise<void>;
  removeNote: (id: string) => Promise<void>;
  syncNow: () => Promise<void>;
  updateSettings: (patch: Partial<AppSettings>) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  notes: [],
  settings: DEFAULT_SETTINGS,
  sync: { synced: 0, failed: 0, pending: 0 },
  hydrated: false,

  hydrate: async () => {
    const [queue, savedSettings] = await Promise.all([
      loadQueue(),
      loadSettings(),
    ]);
    set({
      notes: queue,
      settings: { ...DEFAULT_SETTINGS, ...(savedSettings ?? {}) },
      sync: summarize(queue),
      hydrated: true,
    });
  },

  capture: async (note) => {
    const captured = await enqueueNote(get().settings, note);
    const notes = [captured, ...get().notes];
    set({ notes, sync: summarize(notes) });
    await saveQueue(notes);
  },

  removeNote: async (id) => {
    const notes = get().notes.filter((n) => n.id !== id);
    set({ notes, sync: summarize(notes) });
    await saveQueue(notes);
  },

  syncNow: async () => {
    const { queue, summary } = await syncPending(get().settings, get().notes);
    set({ notes: queue, sync: summary });
    await saveQueue(queue);
  },

  updateSettings: async (patch) => {
    const settings = { ...get().settings, ...patch };
    set({ settings });
    await saveSettings(settings);
  },
}));
