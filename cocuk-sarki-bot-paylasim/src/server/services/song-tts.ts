import fs from "node:fs";
import path from "node:path";
import type { Project } from "@prisma/client";
import { synthesizeSpeech } from "@/server/services/openai";
import { getSettings } from "@/server/services/settings";
import { runFfmpeg, concatAudioFiles, probeDurationSeconds } from "@/server/services/ffmpeg";
import { ensureProjectDirs, safeProjectPath } from "@/server/lib/paths";
import { saveSongMasterAudio } from "@/server/services/song-audio";
import type { SongSettings } from "@/lib/song-settings";
import { recordEvent } from "@/server/lib/logger";

/**
 * Suno API anahtari yoksa (ve kullanici manuel ses yuklemediyse) "sarki sesi"
 * icin tek gercekci yol budur: OpenAI TTS ile lyrics'i SESLENDIRME (melodi
 * degil, ritmik okuma). Tekerleme / saymaca gibi konusma-agirlikli turlerde
 * dogal durur. `[Verse]`, `[Chorus]` gibi Suno bicimi basliklar sese
 * DOKULMEZ; sadece bolum sinirini belirtir (aralarina kisa sessizlik girer).
 */

function resolveFfmpegPath(ffmpegPath?: string): string {
  return ffmpegPath || "ffmpeg";
}

/** [Intro], [Verse 1] gibi basliklara gore metni bolumlere ayirir; basliklari sese dokmez. */
function splitLyricsIntoSections(formattedLyrics: string): string[] {
  const lines = formattedLyrics.split(/\r?\n/);
  const sections: string[] = [];
  let current: string[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (/^\[[^\]]+\]$/.test(trimmed)) {
      if (current.some((l) => l.trim())) sections.push(current.join("\n").trim());
      current = [];
      continue;
    }
    current.push(line);
  }
  if (current.some((l) => l.trim())) sections.push(current.join("\n").trim());
  return sections.filter((s) => s.length > 0);
}

/** TTS'e gonderilmeden once temizler: fazla noktalama TTS'i tuhaf duraklatabilir. */
function cleanForSpeech(section: string): string {
  return section
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .join(",\n");
}

async function generateSilence(durationSeconds: number, outputPath: string, ffmpegBin: string): Promise<void> {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  await runFfmpeg(
    [
      "-y",
      "-f",
      "lavfi",
      "-i",
      `anullsrc=r=44100:cl=mono`,
      "-t",
      durationSeconds.toFixed(2),
      "-q:a",
      "9",
      outputPath,
    ],
    30_000,
    ffmpegBin
  );
}

export interface SynthesizeSongOptions {
  voice?: string;
  speed?: number;
}

/**
 * Verilen (Suno bicimi basliklu) sozlerden tam bir "sarki sesi" mp3'u
 * uretir: her bolum ayri TTS cagrisiyla seslendirilir, bolumler arasina
 * kisa sessizlik konur, sonra tek dosyada birlestirilir ve proje master
 * parcasi olarak kaydedilir (saveSongMasterAudio ile ayni yol — sure
 * ffprobe ile olculur, DB guncellenir).
 */
export async function generateOpenAiSongAudio(
  project: Project,
  formattedLyrics: string,
  opts?: SynthesizeSongOptions
): Promise<SongSettings> {
  const sections = splitLyricsIntoSections(formattedLyrics);
  if (sections.length === 0) throw new Error("Seslendirilecek soz bulunamadi (bolum basliklari [Verse]/[Chorus] vb. bekleniyor)");

  const settings = await getSettings();
  const ffmpegBin = resolveFfmpegPath(settings.ffmpegPath);

  ensureProjectDirs(project.slug);
  const tmpDir = safeProjectPath(project.slug, "song", "tts-tmp");
  fs.mkdirSync(tmpDir, { recursive: true });

  await recordEvent({
    projectId: project.id,
    step: "song",
    message: `OpenAI TTS ile sarki sesi uretiliyor (${sections.length} bolum)...`,
  });

  const silencePath = path.join(tmpDir, "gap.mp3");
  await generateSilence(0.55, silencePath, ffmpegBin);

  const parts: string[] = [];
  for (let i = 0; i < sections.length; i++) {
    const text = cleanForSpeech(sections[i]);
    if (!text.trim()) continue;
    // 4096 karakter siniri: bolumler zaten kucuk ama guvenlik icin kes.
    const safeText = text.slice(0, 3800);
    const buffer = await synthesizeSpeech(safeText, {
      voice: opts?.voice ?? "shimmer",
      speed: opts?.speed ?? 0.92,
    });
    const sectionPath = path.join(tmpDir, `section-${i}.mp3`);
    fs.writeFileSync(sectionPath, buffer);
    parts.push(sectionPath);
    if (i < sections.length - 1) parts.push(silencePath);
  }

  if (parts.length === 0) throw new Error("Hicbir bolum seslendirilemedi");

  const concatPath = path.join(tmpDir, "concat.mp3");
  await concatAudioFiles(parts, concatPath);
  const duration = await probeDurationSeconds(concatPath);
  if (duration <= 1) throw new Error("Uretilen ses suresi okunamadi / cok kisa");

  const finalBuffer = fs.readFileSync(concatPath);

  const result = await saveSongMasterAudio(project, finalBuffer, "master.mp3", {
    musicSource: "manual_upload",
    sunoStatus: "ready",
    formattedLyrics,
    lyricsSource: "manual",
    vocalStyle: "openai-tts-narration",
  });

  // Temizlik: gecici bolum/sessizlik dosyalari artik gerekmiyor.
  try {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  } catch {
    /* onemsiz */
  }

  await recordEvent({
    projectId: project.id,
    step: "song",
    message: `OpenAI TTS sarki sesi hazir (${duration.toFixed(1)} sn, ${sections.length} bolum) — Suno yok, seslendirme kullanildi`,
  });

  return result;
}
