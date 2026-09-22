import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs";
import path from "node:path";
import { getSettings } from "@/server/services/settings";

const execFileAsync = promisify(execFile);

export interface CheckResult {
  ok: boolean;
  label: string;
  detail: string;
}

/**
 * ffmpeg/ffprobe kurulum ve surum kontrolu.
 * Her cagri iki alt surec baslatir; dashboard bu ucu her olayda yokladigi
 * icin sonuc 5 dk onbellekte tutulur (kurulum degisince en gec 5 dk'da gorunur).
 */
const FFMPEG_CHECK_TTL_MS = 5 * 60_000;
let ffmpegCheckCache: { at: number; value: { ffmpeg: CheckResult; ffprobe: CheckResult } } | null = null;

export async function checkFfmpeg(): Promise<{ ffmpeg: CheckResult; ffprobe: CheckResult }> {
  if (ffmpegCheckCache && Date.now() - ffmpegCheckCache.at < FFMPEG_CHECK_TTL_MS) return ffmpegCheckCache.value;
  const settings = await getSettings();
  const ffmpeg = await checkBinary(settings.ffmpegPath || "ffmpeg", "FFmpeg");
  const ffprobe = await checkBinary(settings.ffprobePath || "ffprobe", "ffprobe");
  const value = { ffmpeg, ffprobe };
  // Basarisiz sonucu kisa sure sakla: kullanici ffmpeg kurup hemen kontrol edebilir
  if (ffmpeg.ok && ffprobe.ok) ffmpegCheckCache = { at: Date.now(), value };
  return value;
}

async function checkBinary(bin: string, label: string): Promise<CheckResult> {
  try {
    const { stdout } = await execFileAsync(bin, ["-version"], { timeout: 10_000, windowsHide: true });
    const firstLine = stdout.split(/\r?\n/)[0] ?? "";
    return { ok: true, label, detail: firstLine.trim() };
  } catch {
    return {
      ok: false,
      label,
      detail: `${label} bulunamadi. Kurulum icin: winget install Gyan.FFmpeg (kurulumdan sonra terminali yeniden acin)`,
    };
  }
}

/** Node surumu kontrolu (>=22 onerilir). */
export function checkNode(): CheckResult {
  const version = process.versions.node;
  const major = Number(version.split(".")[0]);
  return {
    ok: major >= 22,
    label: "Node.js",
    detail: major >= 22 ? `v${version}` : `v${version} — Node 22 veya ustu onerilir`,
  };
}

/** Chrome kurulum kontrolu (bilinen kurulum yollari). */
export function checkChrome(): CheckResult {
  const candidates = [
    path.join(process.env.ProgramFiles ?? "C:\\Program Files", "Google", "Chrome", "Application", "chrome.exe"),
    path.join(process.env["ProgramFiles(x86)"] ?? "C:\\Program Files (x86)", "Google", "Chrome", "Application", "chrome.exe"),
    path.join(process.env.LOCALAPPDATA ?? "", "Google", "Chrome", "Application", "chrome.exe"),
  ];
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return { ok: true, label: "Google Chrome", detail: candidate };
    }
  }
  return { ok: false, label: "Google Chrome", detail: "Chrome bulunamadi. https://www.google.com/chrome/ adresinden kurun." };
}

/** Playwright paketinin kurulu olup olmadigini kontrol eder. */
export async function checkPlaywright(): Promise<CheckResult> {
  try {
    const { chromium } = await import("playwright");
    return {
      ok: true,
      label: "Playwright",
      detail: `Kurulu (sistem Chrome'u "channel: chrome" ile kullanilacak). Executable: ${chromium.name()}`,
    };
  } catch {
    return { ok: false, label: "Playwright", detail: "playwright paketi yuklenemedi. npm install calistirin." };
  }
}

/** Kalici Chrome profil klasoru mevcut mu / olusturulabilir mi? */
export async function checkChromeProfile(): Promise<CheckResult> {
  const settings = await getSettings();
  const dir = settings.chromeProfileDir;
  if (!dir) return { ok: false, label: "Chrome Profili", detail: "Profil klasoru ayarlanmamis" };
  const exists = fs.existsSync(dir);
  return {
    ok: true,
    label: "Chrome Profili",
    detail: exists ? `${dir} (mevcut${fs.existsSync(path.join(dir, "Default")) ? ", oturum verisi var" : ""})` : `${dir} (ilk acilista olusturulacak)`,
  };
}
