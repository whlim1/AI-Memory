import Constants from "expo-constants";
import { AppSettings } from "./types";

/**
 * Default settings. Values come from app.json `extra` so they can be
 * overridden per-environment without code changes.
 *
 * Local network (default, Android-first):
 *   - Ingestion API:  http://192.168.0.16:9091
 *   - Qdrant:         http://192.168.0.16:6333
 *   - LM Studio:      http://192.168.0.19:1234
 *
 * Remote (Tailscale MagicDNS):
 *   - http://gmktec-hx9.ts-dns.xyz:9091 etc.
 */
const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

export const DEFAULT_SETTINGS: AppSettings = {
  apiBaseUrl: extra.apiBaseUrl ?? "http://192.168.0.16:9091",
  qdrantUrl: extra.qdrantUrl ?? "http://192.168.0.16:6333",
  lmStudioUrl: extra.lmStudioUrl ?? "http://192.168.0.19:1234",
  captureFolder: "Inbox",
};
