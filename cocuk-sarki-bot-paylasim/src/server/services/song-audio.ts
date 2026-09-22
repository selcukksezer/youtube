import fs from "node:fs";
import path from "node:path";
import type { Project } from "@prisma/client";
import { prisma } from "@/server/db";
import { ensureProjectDirs, nextAvailablePath, safeProjectPath } from "@/server/lib/paths";
import { muxMasterSliceOntoClip, probeDurationSeconds, clipHasMasterSlice, markClipHasMasterSlice } from "@/server/services/ffmpeg";
import { downloadTrack } from "@/server/services/suno";
import { recordEvent } from "@/server/lib/logger";
import { loadSongSettings, updateSongSettings } from "@/server/services/song-settings-store";
import { songHasMasterAudio, type SongSettings } from "@/lib/song-settings";
import { songClipAudioWindow } from "@/lib/song-clip-timeline";
import { SONG_AUDIO_EXTS } from "@/lib/song-audio-formats";

export function isAllowedSongAudio(name: string): boolean {
  return SONG_AUDIO_EXTS.has(path.extname(name).toLowerCase());
}

export async function saveSongMasterAudio(
  project: Project,
  buffer: Buffer,
  fileName: string,
  patch: Partial<SongSettings>
): Promise<SongSettings> {
  if (!isAllowedSongAudio(fileName)) {
    throw new Error("Desteklenen formatlar: wav, flac, aiff, mp3, m4a, aac, ogg");
  }
  ensureProjectDirs(project.slug);
  const ext = path.extname(fileName) || ".mp3";
  const dest = nextAvailablePath(safeProjectPath(project.slug, "song", `master${ext}`));
  fs.writeFileSync(dest, buffer);
  const duration = await probeDurationSeconds(dest);
  if (duration <= 0.5) throw new Error("Ses dosyasi suresi okunamadi");

  await prisma.generatedAsset.create({
    data: {
      projectId: project.id,
      kind: "song_audio",
      path: dest,
      bytes: buffer.length,
      meta: JSON.stringify({ durationSeconds: duration, fileName }),
    },
  });

  await prisma.project.update({
    where: { id: project.id },
    data: {
      targetDurationSeconds: Math.max(20, Math.round(duration)),
      audioEnabled: false,
    },
  });

  const settings = await updateSongSettings(project.id, {
    ...patch,
    audioPath: dest,
    audioDurationSeconds: duration,
    audioFileName: path.basename(dest),
  });

  await recordEvent({
    projectId: project.id,
    step: "song",
    message: `Master parca kaydedildi (${duration.toFixed(1)} sn) — ${path.basename(dest)}`,
  });

  return settings;
}

/** Uzak Suno MP3 URL'sini proje klasorune indirip kaydeder. */
export async function importSongFromUrl(
  project: Project,
  url: string,
  patch: Partial<SongSettings>
): Promise<SongSettings> {
  ensureProjectDirs(project.slug);
  const dest = nextAvailablePath(safeProjectPath(project.slug, "song", "master.mp3"));
  await downloadTrack(url, dest);
  const stat = fs.statSync(dest);
  const duration = await probeDurationSeconds(dest);
  if (duration <= 0.5) throw new Error("Ses dosyasi suresi okunamadi");

  await prisma.generatedAsset.create({
    data: {
      projectId: project.id,
      kind: "song_audio",
      path: dest,
      bytes: stat.size,
      meta: JSON.stringify({ durationSeconds: duration, sourceUrl: url }),
    },
  });

  await prisma.project.update({
    where: { id: project.id },
    data: {
      targetDurationSeconds: Math.max(20, Math.round(duration)),
      audioEnabled: false,
    },
  });

  const settings = await updateSongSettings(project.id, {
    ...patch,
    audioPath: dest,
    audioDurationSeconds: duration,
    audioFileName: path.basename(dest),
  });

  await recordEvent({
    projectId: project.id,
    step: "song",
    message: `Master parca indirildi (${duration.toFixed(1)} sn)`,
  });

  return settings;
}

/** Flow klibindeki uretilmis sesi atar; o saniye araligindaki master MP3'u basar. */
export async function stampClipWithMasterSlice(opts: {
  projectId: string;
  clipIndex: number;
  clipCount: number;
  clipSeconds: number;
  videoPath: string;
}): Promise<{ startSeconds: number; endSeconds: number; durationSeconds: number } | null> {
  const settings = await loadSongSettings(opts.projectId);
  if (!songHasMasterAudio(settings) || !settings.audioPath) return null;
  const window = songClipAudioWindow({
    index: opts.clipIndex,
    clipCount: opts.clipCount,
    clipSeconds: opts.clipSeconds,
    audioDurationSeconds: settings.audioDurationSeconds ?? 0,
  });
  await muxMasterSliceOntoClip({
    videoPath: opts.videoPath,
    masterAudioPath: settings.audioPath,
    startSeconds: window.startSeconds,
    durationSeconds: window.durationSeconds,
  });
  markClipHasMasterSlice(opts.videoPath, window.startSeconds, window.durationSeconds);
  await recordEvent({
    projectId: opts.projectId,
    step: "song",
    message: `Klip ${opts.clipIndex}: Flow sesi silindi, master parca ${window.startSeconds.toFixed(1)}–${window.endSeconds.toFixed(1)} sn basildi`,
  });
  return window;
}

/** Daha once Flow sesiyle inmis kliplere master MP3 dilimlerini basar. */
export async function remuxExistingSongClipVideos(projectId: string, clipSeconds: number): Promise<number> {
  const settings = await loadSongSettings(projectId);
  if (!songHasMasterAudio(settings)) return 0;
  const clips = await prisma.clip.findMany({
    where: { projectId, languageVariant: "primary" },
    orderBy: { index: "asc" },
  });
  const clipCount = clips.length;
  if (clipCount === 0) return 0;
  let stamped = 0;
  for (const clip of clips) {
    if (!clip.videoPath || !fs.existsSync(clip.videoPath)) continue;
    if (clipHasMasterSlice(clip.videoPath)) continue;
    const window = await stampClipWithMasterSlice({
      projectId,
      clipIndex: clip.index,
      clipCount,
      clipSeconds,
      videoPath: clip.videoPath,
    });
    if (!window) continue;
    await prisma.clip.update({
      where: { id: clip.id },
      data: { actualDurationSeconds: window.durationSeconds },
    });
    stamped += 1;
  }
  return stamped;
}
