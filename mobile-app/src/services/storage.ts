/**
 * Local persistence for the offline-first note queue.
 *
 * Uses AsyncStorage for the queue (small, structured data). Larger
 * payloads (audio, images) belong in expo-file-system and are handled
 * by the capture flow directly.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import { CapturedNote } from "../types";

const QUEUE_KEY = "ai_memory.note_queue.v1";
const SETTINGS_KEY = "ai_memory.settings.v1";

export async function loadQueue(): Promise<CapturedNote[]> {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    return raw ? (JSON.parse(raw) as CapturedNote[]) : [];
  } catch {
    return [];
  }
}

export async function saveQueue(queue: CapturedNote[]): Promise<void> {
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export async function loadSettings(): Promise<Record<string, unknown> | null> {
  try {
    const raw = await AsyncStorage.getItem(SETTINGS_KEY);
    return raw ? (JSON.parse(raw) as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export async function saveSettings(settings: Record<string, unknown>): Promise<void> {
  await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}
