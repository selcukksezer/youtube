/**
 * SRT altyazi uretimi.
 * Zamanlama: her klibin GERCEK suresi (ffprobe) bilinir; klip icindeki
 * cumleler kelime sayisina orantili dagitilir.
 * Standartlar: satir basina ~42 karakter, gosterim suresi 1-7 sn.
 */

export interface SrtClipInput {
  index: number;
  dialogue: string;
  durationSeconds: number;
}

export interface SrtCue {
  index: number;
  startSeconds: number;
  endSeconds: number;
  text: string;
}

const MAX_LINE_LENGTH = 42;
const MIN_CUE_SECONDS = 1;
const MAX_CUE_SECONDS = 7;

/** Metni en fazla iki satirli, satir basina ~42 karakterlik bloklara sarar. */
export function wrapSubtitleText(text: string): string {
  const words = text.trim().split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > MAX_LINE_LENGTH && current) {
      lines.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) lines.push(current);
  return lines.join("\n");
}

/** Cumleyi ~2 satirlik altyazi parcalarina boler. */
function chunkSentence(sentence: string): string[] {
  const wrapped = wrapSubtitleText(sentence);
  const lines = wrapped.split("\n");
  const chunks: string[] = [];
  for (let i = 0; i < lines.length; i += 2) {
    chunks.push(lines.slice(i, i + 2).join("\n"));
  }
  return chunks.length > 0 ? chunks : [sentence];
}

/** Kliplerden zaman damgali altyazi kuyruklari uretir. */
export function buildSrtCues(clips: SrtClipInput[]): SrtCue[] {
  const cues: SrtCue[] = [];
  let clipStart = 0;
  let cueNumber = 1;
  let lastEnd = 0;

  for (const clip of [...clips].sort((a, b) => a.index - b.index)) {
    const words = clip.dialogue.trim().split(/\s+/).filter(Boolean);
    if (words.length === 0 || clip.durationSeconds <= 0) {
      clipStart += Math.max(clip.durationSeconds, 0);
      continue;
    }

    // Cumle -> parca listesi
    const sentences = clip.dialogue
      .split(/(?<=[.!?…])\s+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const chunks = sentences.flatMap(chunkSentence);
    const totalWords = words.length;
    const secondsPerWord = clip.durationSeconds / totalWords;

    let offset = 0;
    for (const chunk of chunks) {
      const chunkWords = chunk.split(/\s+/).filter(Boolean).length;
      // Onceki kuyrukla ortusme olmasin
      let start = Math.max(clipStart + offset, lastEnd);
      const clipEnd = clipStart + clip.durationSeconds;
      if (start >= clipEnd) start = Math.max(clipEnd - 0.2, lastEnd);
      let end = start + chunkWords * secondsPerWord;
      // Kuyruk suresini standartlara cek ama klip sinirini tasma
      end = Math.min(Math.max(end, start + MIN_CUE_SECONDS), clipEnd);
      if (end - start > MAX_CUE_SECONDS) end = start + MAX_CUE_SECONDS;
      if (end <= start) end = start + 0.5;

      cues.push({ index: cueNumber++, startSeconds: start, endSeconds: end, text: chunk.replace(/\n/g, "\n") });
      lastEnd = end;
      offset += chunkWords * secondsPerWord;
    }
    clipStart += clip.durationSeconds;
  }
  return cues;
}

function formatSrtTime(totalSeconds: number): string {
  const ms = Math.round((totalSeconds % 1) * 1000);
  const seconds = Math.floor(totalSeconds) % 60;
  const minutes = Math.floor(totalSeconds / 60) % 60;
  const hours = Math.floor(totalSeconds / 3600);
  const pad = (n: number, len = 2) => String(n).padStart(len, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)},${pad(ms, 3)}`;
}

/** TTS cumle zaman damgalarindan SRT kuyruklari uretir. */
export function buildSrtCuesFromTimestamps(
  items: Array<{ text: string; startSeconds: number; endSeconds: number }>
): SrtCue[] {
  const cues: SrtCue[] = [];
  let cueNumber = 1;
  let lastEnd = 0;
  for (const item of items) {
    const text = item.text.trim();
    if (!text) continue;
    const chunks = chunkSentence(text);
    const span = Math.max(0.4, item.endSeconds - item.startSeconds);
    const slice = span / chunks.length;
    chunks.forEach((chunk, i) => {
      const start = Math.max(item.startSeconds + i * slice, lastEnd);
      const end = Math.max(start + Math.min(slice, MAX_CUE_SECONDS), start + 0.4);
      cues.push({
        index: cueNumber++,
        startSeconds: start,
        endSeconds: Math.min(end, item.endSeconds > start ? item.endSeconds : end),
        text: chunk,
      });
      lastEnd = cues[cues.length - 1].endSeconds;
    });
  }
  return cues;
}

/** SRT dosya icerigini uretir. */
export function buildSrtContent(cues: SrtCue[]): string {
  return cues
    .map((cue) => `${cue.index}\n${formatSrtTime(cue.startSeconds)} --> ${formatSrtTime(cue.endSeconds)}\n${cue.text}\n`)
    .join("\n");
}
