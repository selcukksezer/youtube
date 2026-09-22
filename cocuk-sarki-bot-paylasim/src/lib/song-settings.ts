import { z } from "zod";

/** Kelime bazli zaman damgasi (Suno aligned lyrics). */
export const alignedWordSchema = z.object({
  word: z.string(),
  start: z.number(),
  end: z.number(),
});

export const sunoTrackSchema = z.object({
  id: z.string(),
  title: z.string().optional(),
  audioUrl: z.string().optional(),
  imageUrl: z.string().optional(),
  duration: z.number().optional(),
  prompt: z.string().optional(),
  tags: z.string().optional(),
});

export const songSettingsSchema = z.object({
  musicSource: z.enum(["suno_api", "manual_upload"]).optional(),
  sunoTaskId: z.string().optional(),
  sunoClipId: z.string().optional(),
  sunoModel: z.string().optional(),
  sunoStatus: z.enum(["pending", "generating", "ready", "failed"]).optional(),
  sunoError: z.string().optional(),
  sunoTracks: z.array(sunoTrackSchema).optional(),
  selectedTrackIndex: z.number().int().min(0).default(0),
  audioPath: z.string().optional(),
  audioDurationSeconds: z.number().optional(),
  audioFileName: z.string().optional(),
  lyricsSource: z.enum(["suno_prompt", "manual", "aligned"]).optional(),
  formattedLyrics: z.string().optional(),
  alignedLyrics: z.array(alignedWordSchema).optional(),
  bpm: z.number().optional(),
  musicalKey: z.string().optional(),
  mood: z.string().optional(),
  vocalStyle: z.string().optional(),
  /** Proje bazli gorsel cesitlilik tohumu — ayni proje yeniden uretilince ayni kalir. */
  varietySeed: z.number().int().nonnegative().optional(),
});

export type SongSettings = z.infer<typeof songSettingsSchema>;
export type SunoTrack = z.infer<typeof sunoTrackSchema>;
export type AlignedWord = z.infer<typeof alignedWordSchema>;

const EMPTY_SONG_SETTINGS: SongSettings = { selectedTrackIndex: 0 };

export function parseSongSettings(raw: string | null | undefined): SongSettings {
  if (!raw?.trim()) return { ...EMPTY_SONG_SETTINGS };
  try {
    const parsed = JSON.parse(raw) as unknown;
    const result = songSettingsSchema.safeParse(parsed);
    return result.success ? result.data : { ...EMPTY_SONG_SETTINGS };
  } catch {
    return { ...EMPTY_SONG_SETTINGS };
  }
}

export function serializeSongSettings(settings: SongSettings): string {
  return JSON.stringify(songSettingsSchema.parse(settings));
}

export function mergeSongSettings(current: SongSettings, patch: Partial<SongSettings>): SongSettings {
  return songSettingsSchema.parse({ ...current, ...patch });
}

export function songHasMasterAudio(settings: SongSettings): boolean {
  return !!settings.audioPath?.trim() && (settings.audioDurationSeconds ?? 0) > 0;
}

export function selectedSunoTrack(settings: SongSettings): SunoTrack | null {
  const tracks = settings.sunoTracks ?? [];
  if (tracks.length === 0) return null;
  const idx = Math.min(Math.max(0, settings.selectedTrackIndex ?? 0), tracks.length - 1);
  return tracks[idx] ?? null;
}
