import fs from "node:fs";
import path from "node:path";
import { getSettings } from "@/server/services/settings";
import { decryptSecret } from "@/server/lib/crypto";
import { logger } from "@/server/lib/logger";

/**
 * Suno API istemcisi — kie.ai / sunoapi.org uyumlu REST katmani.
 * Resmi Suno API degil; ucretli ucuncu parti saglayici uzerinden calisir.
 */

export interface SunoGenerateOptions {
  title: string;
  style: string;
  lyrics?: string;
  instrumental?: boolean;
  model?: string;
  callBackUrl?: string;
}

export interface SunoTrackResult {
  id: string;
  title?: string;
  audioUrl?: string;
  imageUrl?: string;
  duration?: number;
  prompt?: string;
  tags?: string;
}

export type SunoTaskStatus = "pending" | "generating" | "ready" | "failed";

export interface SunoPollResult {
  status: SunoTaskStatus;
  tracks: SunoTrackResult[];
  error?: string;
  rawStatus?: string;
}

interface SunoApiConfig {
  baseUrl: string;
  apiKey: string;
}

async function resolveSunoConfig(): Promise<SunoApiConfig> {
  const settings = await getSettings();
  const row = settings as unknown as {
    sunoApiKeyEncrypted?: string | null;
    sunoApiBaseUrl?: string;
  };
  const baseUrl = (row.sunoApiBaseUrl?.trim() || process.env.SUNO_API_BASE_URL?.trim() || "https://api.kie.ai").replace(
    /\/$/,
    ""
  );
  const fromEnv = process.env.SUNO_API_KEY?.trim();
  if (fromEnv) return { baseUrl, apiKey: fromEnv };
  if (row.sunoApiKeyEncrypted) {
    try {
      return { baseUrl, apiKey: decryptSecret(row.sunoApiKeyEncrypted) };
    } catch (err) {
      logger.error({ err }, "Suno API anahtari cozulemedi");
    }
  }
  throw new Error("Suno API anahtari ayarlanmamis. Ayarlar > Suno API bolumunden ekleyin.");
}

async function sunoFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { baseUrl, apiKey } = await resolveSunoConfig();
  const res = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const text = await res.text();
  let json: { code?: number; msg?: string; data?: T } = {};
  try {
    json = JSON.parse(text) as typeof json;
  } catch {
    throw new Error(`Suno API gecersiz yanit: ${text.slice(0, 200)}`);
  }
  if (!res.ok || (json.code != null && json.code !== 200)) {
    throw new Error(json.msg || `Suno API hatasi (${res.status})`);
  }
  return (json.data ?? json) as T;
}

/** Muzik uretim isi baslatir. */
export async function generateMusic(options: SunoGenerateOptions): Promise<{ taskId: string }> {
  const settings = await getSettings();
  const row = settings as unknown as { sunoDefaultModel?: string };
  const model = options.model || row.sunoDefaultModel || "V4_5";
  const instrumental = options.instrumental ?? false;
  const customMode = true;
  const body: Record<string, unknown> = {
    customMode,
    instrumental,
    model,
    title: options.title.slice(0, 80),
    style: options.style.slice(0, 1000),
    callBackUrl: options.callBackUrl || "https://localhost/suno-callback",
  };
  if (!instrumental) {
    body.prompt = (options.lyrics || options.title).slice(0, 5000);
  }
  const data = await sunoFetch<{ taskId?: string; task_id?: string }>("/api/v1/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
  const taskId = data.taskId || data.task_id;
  if (!taskId) throw new Error("Suno taskId donmedi");
  return { taskId };
}

function mapTrack(raw: Record<string, unknown>): SunoTrackResult {
  return {
    id: String(raw.id ?? raw.clip_id ?? ""),
    title: typeof raw.title === "string" ? raw.title : undefined,
    audioUrl:
      typeof raw.audio_url === "string"
        ? raw.audio_url
        : typeof raw.source_audio_url === "string"
          ? raw.source_audio_url
          : undefined,
    imageUrl: typeof raw.image_url === "string" ? raw.image_url : undefined,
    duration: typeof raw.duration === "number" ? raw.duration : Number(raw.duration) || undefined,
    prompt: typeof raw.prompt === "string" ? raw.prompt : undefined,
    tags: typeof raw.tags === "string" ? raw.tags : undefined,
  };
}

function statusFromRecord(raw: Record<string, unknown>): SunoPollResult {
  const statusRaw = String(raw.status ?? raw.state ?? raw.callbackType ?? "").toLowerCase();
  const failMsg = typeof raw.error === "string" ? raw.error : typeof raw.msg === "string" ? raw.msg : undefined;
  const nested = (raw.response ?? raw.data ?? raw.result ?? raw) as Record<string, unknown>;
  const trackList = Array.isArray(nested)
    ? nested
    : Array.isArray(nested.data)
      ? nested.data
      : Array.isArray(nested.sunoData)
        ? nested.sunoData
        : [];
  const tracks = trackList.map((t) => mapTrack(t as Record<string, unknown>)).filter((t) => t.id || t.audioUrl);
  const hasAudio = tracks.some((t) => t.audioUrl);
  let status: SunoTaskStatus = "generating";
  if (/fail|error|400|451|500/.test(statusRaw) || (failMsg && /fail|error/i.test(failMsg))) {
    status = "failed";
  } else if (hasAudio || /complete|success|done|first/.test(statusRaw)) {
    status = "ready";
  } else if (/pending|queue|wait|text/.test(statusRaw)) {
    status = "generating";
  }
  return { status, tracks, error: status === "failed" ? failMsg || "Suno uretimi basarisiz" : undefined, rawStatus: statusRaw };
}

/** Uretim durumunu sorgular ve hazir parcalari dondurur. */
export async function pollMusicTask(taskId: string): Promise<SunoPollResult> {
  const data = await sunoFetch<Record<string, unknown>>(
    `/api/v1/generate/record-info?taskId=${encodeURIComponent(taskId)}`
  );
  return statusFromRecord(data);
}

/** Uzak MP3 dosyasini yerel diske indirir. */
export async function downloadTrack(url: string, destPath: string): Promise<string> {
  fs.mkdirSync(path.dirname(destPath), { recursive: true });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Suno parca indirilemedi (${res.status})`);
  const buf = Buffer.from(await res.arrayBuffer());
  if (buf.length < 10_000) throw new Error("Indirilen parca cok kucuk — eksik dosya olabilir");
  fs.writeFileSync(destPath, buf);
  return destPath;
}

export async function describeSunoKey(): Promise<{ present: boolean; baseUrl: string }> {
  const settings = await getSettings();
  const row = settings as unknown as {
    sunoApiKeyEncrypted?: string | null;
    sunoApiBaseUrl?: string;
  };
  const baseUrl = row.sunoApiBaseUrl?.trim() || process.env.SUNO_API_BASE_URL?.trim() || "https://api.kie.ai";
  const present = !!(process.env.SUNO_API_KEY?.trim() || row.sunoApiKeyEncrypted);
  return { present, baseUrl };
}
