/**
 * HTTP client for the AI memory backend (Phase 5 ingestion service)
 * and Qdrant health checks.
 */
import { AppSettings } from "../types";

export interface IngestResponse {
  status: string;
  doc_id?: string;
  chunks?: number;
}

/**
 * POST a captured note to the ingestion API.
 *
 * The Phase 5 ingestion service accepts Markdown notes and returns the
 * assigned doc_id. Adjust the endpoint path if the service exposes a
 * different route.
 */
export async function ingestNote(
  settings: AppSettings,
  note: { title: string; body: string; tags: string[]; template: string }
): Promise<IngestResponse> {
  const res = await fetch(`${settings.apiBaseUrl}/api/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: note.title,
      content: note.body,
      tags: note.tags,
      source_type: "mobile_capture",
      template: note.template,
    }),
  });
  if (!res.ok) {
    throw new Error(`Ingest failed: HTTP ${res.status}`);
  }
  return (await res.json()) as IngestResponse;
}

/** Lightweight connectivity probe against Qdrant. */
export async function checkQdrant(settings: AppSettings): Promise<boolean> {
  try {
    const res = await fetch(`${settings.qdrantUrl}/healthz`, {
      method: "GET",
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** Lightweight connectivity probe against the ingestion API. */
export async function checkApi(settings: AppSettings): Promise<boolean> {
  try {
    const res = await fetch(`${settings.apiBaseUrl}/health`, {
      method: "GET",
    });
    return res.ok;
  } catch {
    return false;
  }
}
