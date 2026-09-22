/** Yuklenebilir master ses — kayipsiz once, kayipli sonra. */
export const SONG_AUDIO_ACCEPT = ".wav,.flac,.aiff,.aif,.mp3,.m4a,.aac,.ogg,audio/*";

export const SONG_AUDIO_EXTS = new Set([
  ".wav",
  ".flac",
  ".aiff",
  ".aif",
  ".mp3",
  ".m4a",
  ".aac",
  ".ogg",
]);

function audioExt(fileName?: string | null): string {
  const n = (fileName || "").toLowerCase();
  const i = n.lastIndexOf(".");
  return i >= 0 ? n.slice(i) : "";
}

export function isLosslessSongAudio(fileName?: string | null): boolean {
  const ext = audioExt(fileName);
  return ext === ".wav" || ext === ".flac" || ext === ".aiff" || ext === ".aif";
}

export function songAudioBadgeLabel(fileName?: string | null, durationSeconds?: number): string {
  const ext = audioExt(fileName);
  const dur = durationSeconds && durationSeconds > 0 ? ` · ${Math.round(durationSeconds)} sn` : "";
  if (ext === ".wav" || ext === ".aiff" || ext === ".aif") return `WAV${dur}`;
  if (ext === ".flac") return `FLAC${dur}`;
  if (ext === ".mp3") return `MP3${dur}`;
  if (ext === ".m4a" || ext === ".aac") return `AAC${dur}`;
  return `Ses${dur}`;
}
