/** Legacy uzun form ayarlari — sarki-only uygulamada stub. */
export type LongformGenreId = string;
export type LongformVoiceId = string;
export type LongformStillInterval = 10 | 15 | 20;
export type LongformStillMotion = "none" | "ken_burns" | "parallax";

export interface LongformSettings {
  genreId: LongformGenreId;
  voiceId: LongformVoiceId;
  stillIntervalSeconds: LongformStillInterval;
  stillMotion: LongformStillMotion;
  ttsRate: number;
  ttsSpeed: number;
  ttsPitch: number;
  imageSource: string;
  imageProvider: string;
  imageModel: string;
}

export const LONGFORM_DURATION_PRESETS: Array<{ label: string; value: number }> = [];
export const LONGFORM_GENRES: Array<{ id: LongformGenreId; label: string }> = [];
export const LONGFORM_STILL_INTERVALS: LongformStillInterval[] = [10, 15, 20];
export const LONGFORM_VOICES: Array<{ id: LongformVoiceId; label: string }> = [];

export function parseLongformSettings(_raw?: string | null): LongformSettings {
  return {
    genreId: "ozel",
    voiceId: "default",
    stillIntervalSeconds: 10,
    stillMotion: "ken_burns",
    ttsRate: 0,
    ttsSpeed: 1,
    ttsPitch: 0,
    imageSource: "",
    imageProvider: "openai",
    imageModel: "",
  };
}

export function isLongformDramaGenre(_genreId?: string | null): boolean {
  return false;
}
