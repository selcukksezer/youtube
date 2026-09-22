import { execFile, spawn, type ChildProcess } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs";
import path from "node:path";
import { getSettings } from "@/server/services/settings";
import { recordEvent } from "@/server/lib/logger";
import {
  assertRenderJobContinuing,
  attachRenderChild,
  clearRenderChild,
} from "@/server/services/render-jobs";

export class FfmpegCancelledError extends Error {
  constructor() {
    super("FFmpeg kullanici tarafindan iptal edildi");
    this.name = "FfmpegCancelledError";
  }
}

export type RunFfmpegOptions = {
  signal?: AbortSignal;
  renderJobId?: string;
};

const execFileAsync = promisify(execFile);

/**
 * FFmpeg / ffprobe servis katmani.
 * - Video analizi (ffprobe)
 * - Son kare cikarma
 * - Concat demuxer ile dogrudan birlestirme
 * - Filter graph ile guvenli yeniden kodlama (fade, kirpma secenekleri)
 */

export interface VideoInfo {
  path: string;
  durationSeconds: number;
  width: number;
  height: number;
  fps: number;
  videoCodec: string;
  audioCodec: string | null;
  audioSampleRate: number | null;
  pixelFormat: string;
  sizeBytes: number;
}

/** Sarki mux: kayipsiz master (WAV/FLAC) tek sefer 320k AAC'ye iner — 192k MP3 neslinden daha temiz. */
const SONG_AAC_ENCODE = ["-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2"] as const;

async function binPaths(): Promise<{ ffmpeg: string; ffprobe: string }> {
  const settings = await getSettings();
  return { ffmpeg: settings.ffmpegPath || "ffmpeg", ffprobe: settings.ffprobePath || "ffprobe" };
}

/** ffprobe JSON ciktisini VideoInfo'ya donusturur. */
export function parseProbeOutput(filePath: string, probeJson: string): VideoInfo {
  const data = JSON.parse(probeJson) as {
    format?: { duration?: string; size?: string };
    streams?: Array<{
      codec_type?: string;
      codec_name?: string;
      width?: number;
      height?: number;
      pix_fmt?: string;
      sample_rate?: string;
      avg_frame_rate?: string;
      r_frame_rate?: string;
    }>;
  };
  const videoStream = data.streams?.find((s) => s.codec_type === "video");
  const audioStream = data.streams?.find((s) => s.codec_type === "audio");
  if (!videoStream) throw new Error(`Video akisi bulunamadi: ${filePath}`);

  const rate = videoStream.avg_frame_rate && videoStream.avg_frame_rate !== "0/0" ? videoStream.avg_frame_rate : videoStream.r_frame_rate ?? "0/1";
  const [num, den] = rate.split("/").map(Number);
  const fps = den > 0 ? num / den : 0;

  return {
    path: filePath,
    durationSeconds: Number(data.format?.duration ?? 0),
    width: videoStream.width ?? 0,
    height: videoStream.height ?? 0,
    fps: Number(fps.toFixed(3)),
    videoCodec: videoStream.codec_name ?? "unknown",
    audioCodec: audioStream?.codec_name ?? null,
    audioSampleRate: audioStream?.sample_rate ? Number(audioStream.sample_rate) : null,
    pixelFormat: videoStream.pix_fmt ?? "unknown",
    sizeBytes: Number(data.format?.size ?? 0),
  };
}

/** Videoyu ffprobe ile analiz eder. */
export async function probeVideo(filePath: string): Promise<VideoInfo> {
  const { ffprobe } = await binPaths();
  const { stdout } = await execFileAsync(
    ffprobe,
    ["-v", "error", "-print_format", "json", "-show_format", "-show_streams", filePath],
    { timeout: 30_000, windowsHide: true, maxBuffer: 10 * 1024 * 1024 }
  );
  return parseProbeOutput(filePath, stdout);
}

/** Dosya var mi, acilabiliyor mu, minimum boyutta mi? */
export async function validateVideoFile(filePath: string, minBytes = 50_000): Promise<{ ok: boolean; info?: VideoInfo; error?: string }> {
  if (!fs.existsSync(filePath)) return { ok: false, error: "Dosya bulunamadi" };
  const stat = fs.statSync(filePath);
  if (stat.size < minBytes) return { ok: false, error: `Dosya cok kucuk (${stat.size} bayt) — yarim indirme olabilir` };
  try {
    const info = await probeVideo(filePath);
    if (info.durationSeconds <= 0.2) return { ok: false, error: "Video suresi gecersiz" };
    return { ok: true, info };
  } catch (err) {
    return { ok: false, error: `Video acilamadi: ${err instanceof Error ? err.message : String(err)}` };
  }
}

/** Videonun son temiz karesini PNG olarak cikarir (ffmpeg -sseof). */
export async function extractLastFrame(videoPath: string, outputPath: string): Promise<string> {
  const { ffmpeg } = await binPaths();
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  await execFileAsync(
    ffmpeg,
    ["-y", "-sseof", "-0.2", "-i", videoPath, "-frames:v", "1", "-update", "1", "-q:v", "2", outputPath],
    { timeout: 60_000, windowsHide: true }
  );
  if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size < 1000) {
    throw new Error("Son kare cikartilamadi");
  }
  return outputPath;
}

/** Videonun belirli bir saniyesinden tek kare cikarir (referans gorsel icin). */
export async function extractFrameAt(videoPath: string, seconds: number, outputPath: string): Promise<string> {
  const { ffmpeg } = await binPaths();
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  await execFileAsync(
    ffmpeg,
    ["-y", "-ss", String(Math.max(0, seconds)), "-i", videoPath, "-frames:v", "1", "-update", "1", "-q:v", "2", outputPath],
    { timeout: 60_000, windowsHide: true }
  );
  if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size < 1000) {
    throw new Error(`${seconds}. saniyeden kare cikartilamadi`);
  }
  return outputPath;
}

/** Windows'ta kalin, okunakli bir TrueType font yolu bulur. */
export function resolveThumbnailFontPath(): string | null {
  const candidates = [
    "C:/Windows/Fonts/seguibl.ttf", // Segoe UI Black — Turkce + kalin
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/impact.ttf",
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function escapeDrawtextValue(value: string): string {
  return value
    .replace(/\\/g, "\\\\")
    .replace(/:/g, "\\:")
    .replace(/'/g, "\\'")
    .replace(/%/g, "\\%")
    .replace(/\n/g, "\\n");
}

/**
 * Kalin sans-serif (Segoe UI Black / Arial Bold) icin kaba karakter genisligi (em).
 * ffmpeg drawtext'in gercek metrigini bilmedigimiz icin taşmayı onleyecek sekilde
 * biraz genis tahmin edilir.
 */
function charWidthEm(ch: string): number {
  if (/[ıiIlj!.,:;'’`|\-]/.test(ch)) return 0.34;
  if (ch === " ") return 0.3;
  if (/[mwMWĞ]/.test(ch)) return 0.94;
  if (/[frtszçş]/.test(ch)) return 0.52;
  if (/[A-ZÇĞİÖŞÜ0-9]/.test(ch)) return 0.7;
  return 0.6;
}

/** Metnin em cinsinden tahmini genisligi (fontSize ile carpilir). */
export function estimateTextWidthEm(text: string): number {
  let sum = 0;
  for (const ch of text) sum += charWidthEm(ch);
  return sum;
}

/**
 * Kelimeleri istenen satir sayisina DENGELI boler: en uzun satirin genisligini
 * en kucuk yapan bolunmeyi arar. (Acgozlu bolme "kisa satir + cok uzun satir"
 * gibi dengesiz sonuc verip puntoyu gereksiz kucultuyordu.)
 */
function wrapIntoLines(words: string[], lineCount: number): string[] {
  if (lineCount <= 1 || words.length <= 1) return [words.join(" ")];

  const memo = new Map<string, { maxEm: number; splits: number[] }>();
  const search = (start: number, linesLeft: number): { maxEm: number; splits: number[] } => {
    const key = `${start}|${linesLeft}`;
    const cached = memo.get(key);
    if (cached) return cached;

    // Son satir: kalan tum kelimeler
    if (linesLeft === 1) {
      const result = { maxEm: estimateTextWidthEm(words.slice(start).join(" ")), splits: [] as number[] };
      memo.set(key, result);
      return result;
    }

    let best: { maxEm: number; splits: number[] } | null = null;
    // Bu satirda en az 1, kalan satirlara en az 1 kelime kalacak sekilde dene
    for (let end = start + 1; end <= words.length - (linesLeft - 1); end++) {
      const lineEm = estimateTextWidthEm(words.slice(start, end).join(" "));
      const rest = search(end, linesLeft - 1);
      const maxEm = Math.max(lineEm, rest.maxEm);
      if (!best || maxEm < best.maxEm) best = { maxEm, splits: [end, ...rest.splits] };
    }
    const result = best ?? { maxEm: estimateTextWidthEm(words.slice(start).join(" ")), splits: [] };
    memo.set(key, result);
    return result;
  };

  const { splits } = search(0, Math.min(lineCount, words.length));
  const lines: string[] = [];
  let cursor = 0;
  for (const split of splits) {
    lines.push(words.slice(cursor, split).join(" "));
    cursor = split;
  }
  lines.push(words.slice(cursor).join(" "));
  return lines.filter(Boolean);
}

export interface ThumbnailTextLayout {
  lines: string[];
  fontSize: number;
  lineSpacing: number;
  borderWidth: number;
  boxBorderWidth: number;
}

/**
 * Kapak yazisini gorsele SIGDIRAN oranli yerlesim hesabi.
 *
 * Once punto sabit (h/7) verildigi icin uzun yazilar gorselin dısına taşiyordu.
 * Burada punto; metnin tahmini genisligine, guvenli kenar bosluguna ve dikey paya
 * gore hesaplanir, gerekirse yazi 2-3 satira bolunur. Kontur/kutu boslugu da
 * puntoyla oranli buyur — kucuk puntoda kalin cerceve metni yutmaz.
 */
export function computeThumbnailTextLayout(options: {
  text: string;
  width: number;
  height: number;
  maxLines?: number;
}): ThumbnailTextLayout {
  const width = options.width > 0 ? options.width : 1280;
  const height = options.height > 0 ? options.height : 720;
  const words = options.text.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);

  const safeWidth = width * 0.8; // iki yandan ~%10 guvenli bosluk
  const heightBudget = height * 0.26; // kutu dahil dikey pay
  const BOX_PAD_EM = 0.18; // kutu boslugu (punto orani, iki yan icin 2x)
  const LINE_EM = 1.18; // satir yuksekligi + satir araligi
  const maxFont = height * 0.105; // "cok buyuk olmasin" ust sinir (eski sabit deger h/7 idi)
  const maxLines = Math.max(1, Math.min(3, options.maxLines ?? (words.length > 1 ? 2 : 1)));

  let best: { lines: string[]; fontSize: number } | null = null;
  for (let lineCount = 1; lineCount <= maxLines; lineCount++) {
    if (lineCount > words.length) break;
    const lines = wrapIntoLines(words, lineCount);
    const longestEm = Math.max(...lines.map((line) => estimateTextWidthEm(line)));
    const byWidth = safeWidth / (longestEm + BOX_PAD_EM * 2);
    const byHeight = heightBudget / (lines.length * LINE_EM + BOX_PAD_EM * 2);
    const fontSize = Math.min(byWidth, byHeight, maxFont);
    // Esitlikte AZ satirli olan kazanir; cok satir ancak belirgin buyume saglarsa secilir
    if (!best || fontSize > best.fontSize + 1) best = { lines, fontSize };
  }

  const chosen = best ?? { lines: [options.text.trim()], fontSize: maxFont };
  const fontSize = Math.max(12, Math.floor(chosen.fontSize));
  return {
    lines: chosen.lines,
    fontSize,
    lineSpacing: Math.max(2, Math.round(fontSize * 0.12)),
    borderWidth: Math.max(2, Math.round(fontSize * 0.07)),
    boxBorderWidth: Math.max(6, Math.round(fontSize * BOX_PAD_EM)),
  };
}

/**
 * PNG/JPG uzerine YouTube kapak tarzi kalin yazi bindirir (beyaz + siyah kontur + kutu).
 * Punto gorselin olculerine ve yazinin uzunluguna gore hesaplanir; yazi gorsele
 * daima sigar (gerekirse satira bolunur). Font yoksa veya ffmpeg basarisizsa hata
 * firlatir — cagiran yedekleyebilir.
 */
export async function burnTextOntoImage(
  inputPath: string,
  outputPath: string,
  text: string,
  options?: { position?: "bottom" | "top" }
): Promise<string> {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (!cleaned) throw new Error("Bindirme yazisi bos");
  if (!fs.existsSync(inputPath)) throw new Error("Kaynak gorsel yok");

  const font = resolveThumbnailFontPath();
  if (!font) throw new Error("Sistemde kalin font bulunamadi (Impact/Arial Bold)");

  const { ffmpeg } = await binPaths();
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  // Gorsel olculeri: punto bunlara gore oranlanir (probe basarisizsa 16:9 varsayilan)
  let imageWidth = 1280;
  let imageHeight = 720;
  try {
    const info = await probeVideo(inputPath);
    if (info.width > 0 && info.height > 0) {
      imageWidth = info.width;
      imageHeight = info.height;
    }
  } catch {
    // olcu okunamadi: varsayilan 1280x720 oranlari kullanilir
  }

  const layout = computeThumbnailTextLayout({ text: cleaned, width: imageWidth, height: imageHeight });

  // Gecici UTF-8 text dosyasi — Turkce karakter ve ozel isaretler icin guvenli
  const textFile = path.join(path.dirname(outputPath), `thumb-text-${Date.now()}.txt`);
  fs.writeFileSync(textFile, layout.lines.join("\n"), "utf8");

  const fontEsc = escapeDrawtextValue(font.replace(/\\/g, "/"));
  const textEsc = escapeDrawtextValue(textFile.replace(/\\/g, "/"));
  const margin = Math.round(imageHeight * 0.06);
  const yExpr =
    options?.position === "bottom" ? `h-text_h-${margin + layout.boxBorderWidth * 2}` : String(margin);

  // YouTube mobil CTR: kalin yazi + kontur; olculer puntoyla oranli, ust safe-zone
  const filter = [
    `drawtext=fontfile='${fontEsc}'`,
    `textfile='${textEsc}'`,
    `fontsize=${layout.fontSize}`,
    "fontcolor=white",
    `borderw=${layout.borderWidth}`,
    "bordercolor=black",
    `line_spacing=${layout.lineSpacing}`,
    "box=1",
    "boxcolor=black@0.48",
    `boxborderw=${layout.boxBorderWidth}`,
    "x=(w-text_w)/2",
    `y=${yExpr}`,
  ].join(":");

  try {
    await runFfmpeg(["-y", "-i", inputPath, "-vf", filter, "-frames:v", "1", "-update", "1", "-q:v", "2", outputPath], 60_000, ffmpeg);
  } finally {
    try {
      fs.unlinkSync(textFile);
    } catch {
      // ignore
    }
  }

  if (!fs.existsSync(outputPath) || fs.statSync(outputPath).size < 800) {
    throw new Error("Yazili thumbnail yazilamadi");
  }
  return outputPath;
}

/** Concat demuxer liste dosyasi icerigini uretir (tek tirnak kacisli). */
export function buildConcatListContent(filePaths: string[]): string {
  return filePaths
    .map((p) => {
      // ffmpeg concat demuxer: yol tek tirnak icinde; icteki tek tirnak '\'' ile kacilir.
      // Windows ters bolu yerine bolu kullanmak guvenlidir.
      const normalized = p.replace(/\\/g, "/").replace(/'/g, "'\\''");
      return `file '${normalized}'`;
    })
    .join("\n");
}

/** Kliplerin teknik ozellikleri concat demuxer icin yeterince ayni mi? */
export function clipsAreUniform(infos: VideoInfo[]): boolean {
  if (infos.length <= 1) return true;
  const first = infos[0];
  return infos.every(
    (i) =>
      i.width === first.width &&
      i.height === first.height &&
      Math.abs(i.fps - first.fps) < 0.5 &&
      i.videoCodec === first.videoCodec &&
      i.audioCodec === first.audioCodec &&
      i.audioSampleRate === first.audioSampleRate &&
      i.pixelFormat === first.pixelFormat
  );
}

export function runFfmpeg(
  args: string[],
  timeoutMs: number,
  ffmpegBin: string,
  opts?: RunFfmpegOptions
): Promise<{ stderr: string }> {
  return new Promise((resolve, reject) => {
    if (opts?.signal?.aborted) {
      reject(new FfmpegCancelledError());
      return;
    }
    if (opts?.renderJobId) {
      try {
        assertRenderJobContinuing(opts.renderJobId);
      } catch (err) {
        reject(err);
        return;
      }
    }

    const child: ChildProcess = spawn(ffmpegBin, args, { windowsHide: true });
    if (opts?.renderJobId) attachRenderChild(opts.renderJobId, child);

    let stderr = "";
    let settled = false;
    const cleanup = () => {
      if (opts?.renderJobId) clearRenderChild(opts.renderJobId);
      opts?.signal?.removeEventListener("abort", onAbort);
    };
    const settleReject = (err: Error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      cleanup();
      reject(err);
    };
    const settleResolve = (value: { stderr: string }) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      cleanup();
      resolve(value);
    };

    const onAbort = () => {
      try {
        if (!child.killed) child.kill("SIGKILL");
      } catch {
        /* ignore */
      }
      settleReject(new FfmpegCancelledError());
    };
    opts?.signal?.addEventListener("abort", onAbort);

    const timer = setTimeout(() => {
      try {
        if (!child.killed) child.kill("SIGKILL");
      } catch {
        /* ignore */
      }
      settleReject(new Error(`FFmpeg zaman asimina ugradi (${Math.round(timeoutMs / 1000)} sn)`));
    }, timeoutMs);

    child.stderr?.on("data", (d: Buffer) => {
      stderr += d.toString();
      if (stderr.length > 4 * 1024 * 1024) stderr = stderr.slice(-2 * 1024 * 1024);
    });
    child.on("error", (err) => {
      settleReject(err);
    });
    child.on("close", (code) => {
      if (opts?.signal?.aborted) {
        settleReject(new FfmpegCancelledError());
        return;
      }
      if (code === 0) settleResolve({ stderr });
      else settleReject(new Error(`FFmpeg hata koduyla bitti (${code}): ${stderr.slice(-800)}`));
    });
  });
}

/** Baslangic/bitis siyah kare araligini tespit eder (saniye cinsinden kirpma onerisi). */
export async function detectBlackBounds(
  videoPath: string,
  durationSeconds: number,
  opts?: RunFfmpegOptions
): Promise<{ trimStart: number; trimEnd: number }> {
  const { ffmpeg } = await binPaths();
  const { stderr } = await runFfmpeg(
    ["-i", videoPath, "-vf", "blackdetect=d=0.05:pix_th=0.10", "-an", "-f", "null", "-"],
    120_000,
    ffmpeg,
    opts
  );
  let trimStart = 0;
  let trimEnd = 0;
  const regex = /black_start:(\d+(?:\.\d+)?)\s+black_end:(\d+(?:\.\d+)?)/g;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(stderr)) !== null) {
    const start = Number(match[1]);
    const end = Number(match[2]);
    if (start <= 0.05) trimStart = Math.max(trimStart, Math.min(end, 1.5));
    if (end >= durationSeconds - 0.05) trimEnd = Math.max(trimEnd, Math.min(durationSeconds - start, 1.5));
  }
  return { trimStart, trimEnd };
}

/** Baslangic/bitis sessizligini tespit eder. */
export async function detectSilenceBounds(
  videoPath: string,
  durationSeconds: number,
  opts?: RunFfmpegOptions
): Promise<{ trimStart: number; trimEnd: number }> {
  const { ffmpeg } = await binPaths();
  try {
    const { stderr } = await runFfmpeg(
      ["-i", videoPath, "-af", "silencedetect=noise=-45dB:d=0.25", "-vn", "-f", "null", "-"],
      120_000,
      ffmpeg,
      opts
    );
    let trimStart = 0;
    let trimEnd = 0;
    const startRegex = /silence_start:\s*(-?\d+(?:\.\d+)?)/g;
    const endRegex = /silence_end:\s*(\d+(?:\.\d+)?)/g;
    const starts: number[] = [];
    const ends: number[] = [];
    let m: RegExpExecArray | null;
    while ((m = startRegex.exec(stderr)) !== null) starts.push(Number(m[1]));
    while ((m = endRegex.exec(stderr)) !== null) ends.push(Number(m[1]));
    for (let i = 0; i < starts.length; i++) {
      const start = starts[i];
      const end = ends[i] ?? durationSeconds;
      if (start <= 0.05) trimStart = Math.max(trimStart, Math.min(end, 1.0));
      if (end >= durationSeconds - 0.05) trimEnd = Math.max(trimEnd, Math.min(durationSeconds - start, 1.0));
    }
    return { trimStart, trimEnd };
  } catch {
    // Ses akisi olmayan videoda silencedetect hata verebilir
    return { trimStart: 0, trimEnd: 0 };
  }
}

export type OutputResolution = "source" | "1080" | "1440" | "2160";

export interface MergeOptions {
  /** direct: concat demuxer (ayni ozellikte klipler) — reencode: guvenli yeniden kodlama */
  mode: "direct" | "reencode" | "auto";
  /** Klip birlesim noktalarinda ses gecis suresi (ms). 0 = kapali. 50-150 onerilir. */
  audioFadeMs: number;
  /** Baslangic/bitis sessizligini kirp */
  trimSilence: boolean;
  /** Baslangic/bitis siyah karelerini kirp */
  trimBlack: boolean;
  /**
   * Cikti cozunurlugu. source = kaynak klip boyutu (en dogru).
   * 1080/1440/2160 = yeniden kodlayip hedefe olcekle (kaynak daha dusukse upscale; detay sihirli eklenmez).
   */
  outputResolution?: OutputResolution;
}

/** En-boy oranina gore hedef genislik/yukseklik. */
export function resolveOutputSize(
  sourceWidth: number,
  sourceHeight: number,
  resolution: OutputResolution
): { width: number; height: number; upscaled: boolean } {
  if (resolution === "source" || sourceWidth <= 0 || sourceHeight <= 0) {
    return { width: sourceWidth, height: sourceHeight, upscaled: false };
  }
  const portrait = sourceHeight > sourceWidth;
  const targetShort = resolution === "1080" ? 1080 : resolution === "1440" ? 1440 : 2160;
  // 16:9 / 9:16 klasik: kisa kenar = 1080/1440/2160
  let width: number;
  let height: number;
  if (portrait) {
    width = targetShort;
    height = Math.round((targetShort * sourceHeight) / sourceWidth / 2) * 2;
  } else {
    height = targetShort;
    width = Math.round((targetShort * sourceWidth) / sourceHeight / 2) * 2;
  }
  // Klasik 16:9 / 9:16 sabitleri (yuvarlama sapmasini duzelt)
  if (!portrait && Math.abs(sourceWidth / sourceHeight - 16 / 9) < 0.05) {
    if (resolution === "1080") {
      width = 1920;
      height = 1080;
    } else if (resolution === "1440") {
      width = 2560;
      height = 1440;
    } else {
      width = 3840;
      height = 2160;
    }
  }
  if (portrait && Math.abs(sourceHeight / sourceWidth - 16 / 9) < 0.05) {
    if (resolution === "1080") {
      width = 1080;
      height = 1920;
    } else if (resolution === "1440") {
      width = 1440;
      height = 2560;
    } else {
      width = 2160;
      height = 3840;
    }
  }
  const upscaled = width > sourceWidth + 8 || height > sourceHeight + 8;
  return { width, height, upscaled };
}

export interface MergeResult {
  outputPath: string;
  mode: "direct" | "reencode";
  info: VideoInfo;
  clipCount: number;
  warnings: string[];
}

/**
 * Klipleri tek MP4'e birlestirir.
 * Cikti: H.264 + AAC 48kHz, yuv420p, +faststart.
 */
export async function mergeClips(
  clipPaths: string[],
  outputPath: string,
  options: MergeOptions,
  projectId?: string,
  runOpts?: RunFfmpegOptions
): Promise<MergeResult> {
  if (clipPaths.length === 0) throw new Error("Birlestirilecek klip yok");
  const { ffmpeg } = await binPaths();
  const warnings: string[] = [];
  const checkCancel = () => {
    if (runOpts?.signal?.aborted) throw new FfmpegCancelledError();
    if (runOpts?.renderJobId) assertRenderJobContinuing(runOpts.renderJobId);
  };

  const infos: VideoInfo[] = [];
  for (const clipPath of clipPaths) {
    checkCancel();
    // Indirme aninda 50KB esigi zaten uygulandi; burada yalnizca dosyanin
    // hala mevcut/acilabilir oldugunu dogruluyoruz.
    const validation = await validateVideoFile(clipPath, 10_000);
    if (!validation.ok || !validation.info) throw new Error(`Klip dogrulanamadi (${path.basename(clipPath)}): ${validation.error}`);
    infos.push(validation.info);
  }

  const uniform = clipsAreUniform(infos);
  const resolution: OutputResolution = options.outputResolution ?? "source";
  const needsScale = resolution !== "source";
  let mode: "direct" | "reencode";
  if (options.mode === "auto") {
    mode =
      uniform && options.audioFadeMs === 0 && !options.trimSilence && !options.trimBlack && !needsScale
        ? "direct"
        : "reencode";
  } else {
    mode = options.mode;
  }
  if (mode === "direct" && !uniform) {
    warnings.push("Klipler ayni teknik ozellikte degil; guvenli yeniden kodlamaya gecildi.");
    mode = "reencode";
  }
  if (mode === "direct" && (options.audioFadeMs > 0 || options.trimSilence || options.trimBlack || needsScale)) {
    warnings.push(
      needsScale
        ? "Hedef cozunurluk yeniden kodlama gerektirir; yeniden kodlamaya gecildi."
        : "Ses gecisi/kirpma secenekleri yeniden kodlama gerektirir; yeniden kodlamaya gecildi."
    );
    mode = "reencode";
  }

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const totalDuration = infos.reduce((sum, i) => sum + i.durationSeconds, 0);
  const timeout = Math.max(300_000, totalDuration * 20_000);

  if (mode === "direct") {
    const listPath = path.join(path.dirname(outputPath), "concat-list.txt");
    fs.writeFileSync(listPath, buildConcatListContent(clipPaths), "utf8");
    await recordEvent({ projectId, step: "render", message: `Dogrudan birlestirme basladi (${clipPaths.length} klip)` });
    checkCancel();
    await runFfmpeg(
      ["-y", "-f", "concat", "-safe", "0", "-i", listPath, "-c", "copy", "-movflags", "+faststart", outputPath],
      timeout,
      ffmpeg,
      runOpts
    );
  } else {
    // Kirpma analizleri
    const trims: Array<{ start: number; end: number }> = [];
    for (let i = 0; i < clipPaths.length; i++) {
      checkCancel();
      let trimStart = 0;
      let trimEnd = 0;
      if (options.trimBlack) {
        const black = await detectBlackBounds(clipPaths[i], infos[i].durationSeconds, runOpts);
        trimStart = Math.max(trimStart, black.trimStart);
        trimEnd = Math.max(trimEnd, black.trimEnd);
      }
      if (options.trimSilence) {
        const silence = await detectSilenceBounds(clipPaths[i], infos[i].durationSeconds, runOpts);
        trimStart = Math.max(trimStart, silence.trimStart);
        trimEnd = Math.max(trimEnd, silence.trimEnd);
      }
      // Klibin en az %60'i kalmali; asiri kirpmayi engelle
      const maxTrimTotal = infos[i].durationSeconds * 0.4;
      if (trimStart + trimEnd > maxTrimTotal) {
        const scale = maxTrimTotal / (trimStart + trimEnd);
        trimStart *= scale;
        trimEnd *= scale;
        warnings.push(`${path.basename(clipPaths[i])}: kirpma miktari guvenlik icin sinirlandi`);
      }
      trims.push({ start: trimStart, end: trimEnd });
    }

    // Hedef cozunurluk/fps: en buyuk kaynak klip + kullanici hedefi
    const bestSource = infos.reduce((best, i) => (i.width * i.height > best.width * best.height ? i : best), infos[0]);
    const sized = resolveOutputSize(bestSource.width, bestSource.height, resolution);
    const target = { width: sized.width, height: sized.height, fps: bestSource.fps || 24 };
    if (sized.upscaled) {
      warnings.push(
        `Cikti ${target.width}x${target.height} (kaynak ~${bestSource.width}x${bestSource.height}). Upscale detay eklemez; YouTube/paylasim icin kullanisli olabilir.`
      );
    }
    const fadeSec = Math.min(Math.max(options.audioFadeMs, 0), 300) / 1000;
    // YouTube/paylasim icin yuksek kalite: QHD/4K'da dusuk CRF + slow preset
    const crf =
      resolution === "2160" ? "14" : resolution === "1440" ? "15" : resolution === "1080" ? "17" : "18";
    const preset = resolution === "2160" || resolution === "1440" ? "slow" : "medium";
    const audioBitrate = resolution === "2160" || resolution === "1440" ? "320k" : "192k";
    const highResTimeout = resolution === "2160" || resolution === "1440";

    const inputArgs: string[] = [];
    for (const clipPath of clipPaths) inputArgs.push("-i", clipPath);

    const filterParts: string[] = [];
    const concatInputs: string[] = [];
    for (let i = 0; i < clipPaths.length; i++) {
      const info = infos[i];
      const trim = trims[i];
      const effectiveDuration = info.durationSeconds - trim.start - trim.end;
      const vTrim = `trim=start=${trim.start.toFixed(3)}:end=${(info.durationSeconds - trim.end).toFixed(3)},setpts=PTS-STARTPTS`;
      // lanczos + accurate_rnd: QHD/4K upscale'te daha temiz kenarlar
      const vScale = `scale=${target.width}:${target.height}:flags=lanczos+accurate_rnd+full_chroma_int:force_original_aspect_ratio=decrease,pad=${target.width}:${target.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=${target.fps || 24},format=yuv420p`;
      filterParts.push(`[${i}:v]${vTrim},${vScale}[v${i}]`);

      const hasAudio = info.audioCodec !== null;
      if (hasAudio) {
        const aTrim = `atrim=start=${trim.start.toFixed(3)}:end=${(info.durationSeconds - trim.end).toFixed(3)},asetpts=PTS-STARTPTS`;
        let aChain = `[${i}:a]${aTrim},aresample=48000`;
        if (fadeSec > 0 && effectiveDuration > fadeSec * 3) {
          const fadeOutStart = Math.max(0, effectiveDuration - fadeSec);
          if (i > 0) aChain += `,afade=t=in:st=0:d=${fadeSec.toFixed(3)}`;
          if (i < clipPaths.length - 1) aChain += `,afade=t=out:st=${fadeOutStart.toFixed(3)}:d=${fadeSec.toFixed(3)}`;
        }
        filterParts.push(`${aChain}[a${i}]`);
      } else {
        // Ses akisi olmayan klip icin sessiz ses uret
        filterParts.push(
          `anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration=${Math.max(effectiveDuration, 0.1).toFixed(3)}[a${i}]`
        );
        warnings.push(`${path.basename(clipPaths[i])}: ses akisi yok, sessiz ses eklendi`);
      }
      concatInputs.push(`[v${i}][a${i}]`);
    }
    filterParts.push(`${concatInputs.join("")}concat=n=${clipPaths.length}:v=1:a=1[outv][outa]`);

    await recordEvent({
      projectId,
      step: "render",
      message: `Yeniden kodlayarak birlestirme basladi (${clipPaths.length} klip, ${target.width}x${target.height}, CRF ${crf}, preset ${preset}${fadeSec > 0 ? `, ${options.audioFadeMs}ms ses gecisi` : ""})`,
    });

    const encodeTimeout = highResTimeout
      ? Math.max(600_000, totalDuration * 45_000)
      : Math.max(300_000, totalDuration * 20_000);

    const x264Args =
      resolution === "2160"
        ? ["-profile:v", "high", "-level", "5.1"]
        : resolution === "1440"
          ? ["-profile:v", "high", "-level", "5.0"]
          : ["-profile:v", "high"];

    checkCancel();
    await runFfmpeg(
      [
        "-y",
        ...inputArgs,
        "-filter_complex",
        filterParts.join(";"),
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        crf,
        ...x264Args,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        audioBitrate,
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        outputPath,
      ],
      encodeTimeout,
      ffmpeg,
      runOpts
    );
  }

  const finalValidation = await validateVideoFile(outputPath, 10_000);
  if (!finalValidation.ok || !finalValidation.info) {
    throw new Error(`Final video dogrulanamadi: ${finalValidation.error}`);
  }
  await recordEvent({
    projectId,
    step: "render",
    message: `Birlestirme tamamlandi: ${path.basename(outputPath)} (${Math.round(finalValidation.info.durationSeconds)} sn, ${(finalValidation.info.sizeBytes / (1024 * 1024)).toFixed(1)} MB)`,
  });

  return { outputPath, mode, info: finalValidation.info, clipCount: clipPaths.length, warnings };
}

/** Ses veya video dosyasinin format suresini okur (WAV/FLAC dahil — video akisi gerekmez). */
export async function probeDurationSeconds(filePath: string): Promise<number> {
  const { ffprobe } = await binPaths();
  const { stdout } = await execFileAsync(
    ffprobe,
    ["-v", "error", "-print_format", "json", "-show_format", "-show_streams", filePath],
    { timeout: 30_000, windowsHide: true, maxBuffer: 10 * 1024 * 1024 }
  );
  const data = JSON.parse(String(stdout || "{}")) as {
    format?: { duration?: string };
    streams?: Array<{ duration?: string; codec_type?: string }>;
  };
  const candidates = [
    Number(data.format?.duration ?? 0),
    ...((data.streams ?? []).map((s) => Number(s.duration ?? 0))),
  ].filter((n) => Number.isFinite(n) && n > 0);
  const n = candidates[0];
  if (!n) throw new Error(`Sure okunamadi: ${path.basename(filePath)}`);
  return n;
}

/** Perde (semiton) kaydirir; sureyi atempo ile korur. 0 ise bos filtre. */
export function buildPitchFilter(pitchSemitones: number, sampleRate = 24000): string {
  if (!pitchSemitones) return "";
  const ratio = 2 ** (pitchSemitones / 12);
  const parts = [`asetrate=${Math.round(sampleRate * ratio)}`, `aresample=${sampleRate}`];
  let remaining = 1 / ratio;
  while (remaining < 0.5 - 1e-6 || remaining > 2 + 1e-6) {
    if (remaining < 0.5) {
      parts.push("atempo=0.5");
      remaining /= 0.5;
    } else {
      parts.push("atempo=2.0");
      remaining /= 2;
    }
  }
  parts.push(`atempo=${remaining.toFixed(5)}`);
  return parts.join(",");
}

export async function applyAudioFilter(
  inputPath: string,
  outputPath: string,
  filter: string,
  opts?: RunFfmpegOptions
): Promise<void> {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  if (!filter.trim()) {
    if (path.resolve(inputPath) !== path.resolve(outputPath)) fs.copyFileSync(inputPath, outputPath);
    return;
  }
  const { ffmpeg } = await binPaths();
  await runFfmpeg(["-y", "-i", inputPath, "-af", filter, outputPath], 300_000, ffmpeg, opts);
}

export async function concatAudioFiles(
  inputPaths: string[],
  outputPath: string,
  opts?: RunFfmpegOptions
): Promise<void> {
  if (inputPaths.length === 0) throw new Error("Birlestirilecek ses yok");
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  if (inputPaths.length === 1) {
    fs.copyFileSync(inputPaths[0], outputPath);
    return;
  }
  const { ffmpeg } = await binPaths();
  const listPath = `${outputPath}.concat.txt`;
  fs.writeFileSync(listPath, buildConcatListContent(inputPaths), "utf8");
  try {
    await runFfmpeg(["-y", "-f", "concat", "-safe", "0", "-i", listPath, "-c", "copy", outputPath], 300_000, ffmpeg, opts);
  } catch {
    await runFfmpeg(
      ["-y", "-f", "concat", "-safe", "0", "-i", listPath, "-c:a", "pcm_s16le", outputPath],
      300_000,
      ffmpeg,
      opts
    );
  }
}

/**
 * Herhangi bir ses dosyasini 24 kHz mono WAV'a cevirir.
 *
 * Saglayicilar farkli bicimler donuyor (Google/Azure WAV, ElevenLabs mp3);
 * birlestirme ve sure olcumu tek bicimde yapilsin diye normalize edilir.
 */
export async function convertToWav(inputPath: string, outputPath: string, opts?: RunFfmpegOptions): Promise<void> {
  const { ffmpeg } = await binPaths();
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  await runFfmpeg(
    ["-y", "-i", inputPath, "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", outputPath],
    180_000,
    ffmpeg,
    opts
  );
}

/**
 * Konusma hizi filtresi (perdeyi bozmaz). atempo 0.5-2 araligini kabul
 * ettigi icin gerekirse zincirlenir.
 */
export function buildTempoFilter(speed: number): string {
  const target = Number(speed);
  if (!Number.isFinite(target) || Math.abs(target - 1) < 1e-3) return "";
  const parts: string[] = [];
  let remaining = Math.min(3, Math.max(0.34, target));
  while (remaining < 0.5 - 1e-6 || remaining > 2 + 1e-6) {
    if (remaining < 0.5) {
      parts.push("atempo=0.5");
      remaining /= 0.5;
    } else {
      parts.push("atempo=2.0");
      remaining /= 2;
    }
  }
  parts.push(`atempo=${remaining.toFixed(5)}`);
  return parts.join(",");
}

export interface AssembleLongformInput {
  segmentPaths: string[];
  voicePath: string;
  musicPath?: string | null;
  outputPath: string;
  projectId?: string;
  runOpts?: RunFfmpegOptions;
}

/** Ken Burns segmentlerini birlestirir, ses + muzik ducking + loudnorm uygular. */
export async function assembleLongform(input: AssembleLongformInput): Promise<VideoInfo> {
  if (input.segmentPaths.length === 0) throw new Error("Montaj icin gorsel segment yok");
  if (!fs.existsSync(input.voicePath)) throw new Error("Ses dosyasi bulunamadi");
  const { ffmpeg } = await binPaths();
  fs.mkdirSync(path.dirname(input.outputPath), { recursive: true });
  const workDir = path.dirname(input.outputPath);
  const silentPath = path.join(workDir, "longform-silent.mp4");
  const listPath = path.join(workDir, "longform-concat.txt");
  fs.writeFileSync(listPath, buildConcatListContent(input.segmentPaths), "utf8");

  const concatTimeout = Math.max(180_000, input.segmentPaths.length * 8_000);
  try {
    await runFfmpeg(
      ["-y", "-f", "concat", "-safe", "0", "-i", listPath, "-c", "copy", silentPath],
      concatTimeout,
      ffmpeg,
      input.runOpts
    );
  } catch {
    await runFfmpeg(
      [
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        listPath,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-an",
        silentPath,
      ],
      concatTimeout * 2,
      ffmpeg,
      input.runOpts
    );
  }

  const args = ["-y", "-i", silentPath, "-i", input.voicePath];
  const hasMusic = !!(input.musicPath && fs.existsSync(input.musicPath));
  if (hasMusic) {
    args.push("-stream_loop", "-1", "-i", input.musicPath!);
    args.push(
      "-filter_complex",
      "[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume=1.0[voice];[2:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume=0.13[bg];[voice][bg]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[a]",
      "-map",
      "0:v",
      "-map",
      "[a]"
    );
  } else {
    args.push("-filter_complex", "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]", "-map", "0:v", "-map", "[a]");
  }
  args.push(
    "-c:v",
    "libx264",
    "-preset",
    "veryfast",
    "-crf",
    "20",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-b:a",
    "192k",
    "-ar",
    "48000",
    "-shortest",
    "-movflags",
    "+faststart",
    input.outputPath
  );

  const mixTimeout = Math.max(300_000, input.segmentPaths.length * 12_000);
  await runFfmpeg(args, mixTimeout, ffmpeg, input.runOpts);

  const finalValidation = await validateVideoFile(input.outputPath, 10_000);
  if (!finalValidation.ok || !finalValidation.info) {
    throw new Error(`Uzun form final dogrulanamadi: ${finalValidation.error}`);
  }
  await recordEvent({
    projectId: input.projectId,
    step: "longform",
    message: `Uzun form montaj tamamlandi: ${path.basename(input.outputPath)} (${Math.round(finalValidation.info.durationSeconds)} sn)`,
  });
  return finalValidation.info;
}

export interface MergeSongFinalInput {
  clipPaths: string[];
  masterAudioPath: string;
  outputPath: string;
  options?: MergeOptions;
  projectId?: string;
  runOpts?: RunFfmpegOptions;
}

/** Cocuk sarki: sessiz/goruntu klipleri birlestirip Suno master parcasini mux eder. */
export async function mergeSongFinal(input: MergeSongFinalInput): Promise<MergeResult> {
  if (input.clipPaths.length === 0) throw new Error("Birlestirilecek klip yok");
  if (!fs.existsSync(input.masterAudioPath)) throw new Error("Master parca bulunamadi");
  const { ffmpeg } = await binPaths();
  const warnings: string[] = [];
  const workDir = path.dirname(input.outputPath);
  const silentPath = path.join(workDir, "song-silent.mp4");
  const listPath = path.join(workDir, "song-concat.txt");
  fs.mkdirSync(workDir, { recursive: true });
  fs.writeFileSync(listPath, buildConcatListContent(input.clipPaths), "utf8");

  const checkCancel = () => {
    if (input.runOpts?.signal?.aborted) throw new FfmpegCancelledError();
    if (input.runOpts?.renderJobId) assertRenderJobContinuing(input.runOpts.renderJobId);
  };

  checkCancel();
  const concatTimeout = Math.max(180_000, input.clipPaths.length * 10_000);
  try {
    await runFfmpeg(
      ["-y", "-f", "concat", "-safe", "0", "-i", listPath, "-c", "copy", "-an", silentPath],
      concatTimeout,
      ffmpeg,
      input.runOpts
    );
  } catch {
    await runFfmpeg(
      [
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        listPath,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-an",
        silentPath,
      ],
      concatTimeout * 2,
      ffmpeg,
      input.runOpts
    );
  }

  const videoInfo = await probeVideo(silentPath);
  const audioDuration = await probeDurationSeconds(input.masterAudioPath);
  const drift = Math.abs(videoInfo.durationSeconds - audioDuration);
  if (drift > 1.5) {
    warnings.push(
      `Video (${videoInfo.durationSeconds.toFixed(1)} sn) ile parca (${audioDuration.toFixed(1)} sn) arasinda ${drift.toFixed(1)} sn fark — -shortest ile kesilecek`
    );
  }

  checkCancel();
  await runFfmpeg(
    [
      "-y",
      "-i",
      silentPath,
      "-i",
      input.masterAudioPath,
      "-map",
      "0:v",
      "-map",
      "1:a",
      "-c:v",
      "copy",
      ...SONG_AAC_ENCODE,
      "-shortest",
      "-movflags",
      "+faststart",
      input.outputPath,
    ],
    Math.max(300_000, videoInfo.durationSeconds * 15_000),
    ffmpeg,
    input.runOpts
  );

  const finalInfo = await probeVideo(input.outputPath);
  await recordEvent({
    projectId: input.projectId,
    step: "render",
    message: `Sarki final mux tamamlandi (${finalInfo.durationSeconds.toFixed(1)} sn)`,
  });

  return {
    outputPath: input.outputPath,
    mode: "reencode",
    clipCount: input.clipPaths.length,
    warnings,
    info: finalInfo,
  };
}

/**
 * Flow klibindeki uretilmis sesi siler; master parçadan start..start+duration dilimini
 * video uzerine basar. Video kisa ise son kare dondurulur, uzun ise kesilir.
 */
export async function muxMasterSliceOntoClip(input: {
  videoPath: string;
  masterAudioPath: string;
  startSeconds: number;
  durationSeconds: number;
}): Promise<VideoInfo> {
  if (!fs.existsSync(input.videoPath)) throw new Error("Klip videosu bulunamadi");
  if (!fs.existsSync(input.masterAudioPath)) throw new Error("Master parca bulunamadi");
  const duration = Math.max(0.2, input.durationSeconds);
  const start = Math.max(0, input.startSeconds);
  const { ffmpeg } = await binPaths();
  const dir = path.dirname(input.videoPath);
  const ext = path.extname(input.videoPath) || ".mp4";
  const tmpPath = path.join(dir, `${path.basename(input.videoPath, ext)}.mp3mux${ext}`);
  const rawBackup = path.join(dir, `${path.basename(input.videoPath, ext)}.flow-audio${ext}`);

  await runFfmpeg(
    [
      "-y",
      "-i",
      input.videoPath,
      "-ss",
      start.toFixed(3),
      "-t",
      duration.toFixed(3),
      "-i",
      input.masterAudioPath,
      "-filter_complex",
      "[0:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration=30[v]",
      "-map",
      "[v]",
      "-map",
      "1:a:0",
      "-c:v",
      "libx264",
      "-preset",
      "veryfast",
      "-crf",
      "18",
      "-pix_fmt",
      "yuv420p",
      ...SONG_AAC_ENCODE,
      "-t",
      duration.toFixed(3),
      "-movflags",
      "+faststart",
      tmpPath,
    ],
    Math.max(120_000, duration * 20_000),
    ffmpeg
  );

  const info = await probeVideo(tmpPath);
  if (info.durationSeconds < 0.2) {
    fs.rmSync(tmpPath, { force: true });
    throw new Error("Master dilimi videoya basilemedi (cikti suresi gecersiz)");
  }
  try {
    if (fs.existsSync(rawBackup)) fs.rmSync(rawBackup, { force: true });
    fs.renameSync(input.videoPath, rawBackup);
    fs.renameSync(tmpPath, input.videoPath);
    fs.rmSync(rawBackup, { force: true });
  } catch {
    fs.copyFileSync(tmpPath, input.videoPath);
    fs.rmSync(tmpPath, { force: true });
    fs.rmSync(rawBackup, { force: true });
  }
  return probeVideo(input.videoPath);
}

export function masterSliceMarkerPath(videoPath: string): string {
  return `${videoPath}.from-master`;
}

export function markClipHasMasterSlice(videoPath: string, startSeconds: number, durationSeconds: number): void {
  fs.writeFileSync(
    masterSliceMarkerPath(videoPath),
    JSON.stringify({ startSeconds, durationSeconds, at: Date.now() }),
    "utf8"
  );
}

export function clipHasMasterSlice(videoPath: string): boolean {
  return fs.existsSync(masterSliceMarkerPath(videoPath));
}
