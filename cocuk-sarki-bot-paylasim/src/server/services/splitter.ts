/**
 * Metin bolme ve klip kelime butcesi yardimcilari.
 */

export interface SplitOptions {
  clipSeconds: number;
  wpm: number;
  /** Konusma / klip orani. */
  safetyRatio?: number;
}

export interface ClipDraft {
  index: number;
  dialogue: string;
  estimatedWords: number;
  estimatedDurationSeconds: number;
  hasHook: boolean;
  curiosityScore: number;
}

const DEFAULT_SAFETY_RATIO = 0.85;

/** Konusma metninin klip suresine sigmasi icin doldurma orani. */
export const SPEECH_FILL_RATIO = 0.98;

/** Enerjik Flow okuyusu erken bitsin diye cocuk diyaloguna biraz daha kelime. */
export const KIDS_SPEECH_FILL_RATIO = 1.12;

/** Sinema anlatici (legacy test uyumu). */
export const NARRATOR_SPEECH_FILL_RATIO = 1.12;

const ABBREVIATIONS = new Set(["dr", "prof", "doc", "vb", "vs", "or", "bkz", "sn", "no", "mr", "mrs", "ms", "st"]);

export function speechFillRatioFor(templateType: string | null | undefined): number {
  if (templateType === "kids_animation" || templateType === "kids_song") return KIDS_SPEECH_FILL_RATIO;
  if (templateType === "narrator") return NARRATOR_SPEECH_FILL_RATIO;
  return SPEECH_FILL_RATIO;
}

export function splitIntoSentences(text: string): string[] {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return [];
  const sentences: string[] = [];
  let current = "";
  for (let i = 0; i < normalized.length; i++) {
    const ch = normalized[i];
    current += ch;
    if (ch === "." || ch === "!" || ch === "?" || ch === "…") {
      while (i + 1 < normalized.length && (normalized[i + 1] === "." || normalized[i + 1] === "!" || normalized[i + 1] === "?")) {
        current += normalized[i + 1];
        i++;
      }
      const next = normalized[i + 1];
      const prevChar = normalized[i - 1];
      const isDecimal = ch === "." && prevChar >= "0" && prevChar <= "9" && next !== undefined && next >= "0" && next <= "9";
      const lastWord = current
        .slice(0, -1)
        .split(/\s+/)
        .pop()
        ?.toLowerCase()
        .replace(/[^a-zçğıöşü]/g, "");
      const isAbbrev = ch === "." && !!lastWord && ABBREVIATIONS.has(lastWord);
      const nextIsSpace = next === " " || next === undefined;
      if (!isDecimal && !isAbbrev && nextIsSpace) {
        sentences.push(current.trim());
        current = "";
        if (next === " ") i++;
      }
    }
  }
  if (current.trim()) sentences.push(current.trim());
  return sentences;
}

export function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function detectHook(sentence: string): { hasHook: boolean; score: number } {
  const s = sentence.trim().toLowerCase();
  let score = 0;
  if (/\?$/.test(s)) score += 4;
  if (/(\.\.\.|…)$/.test(s)) score += 4;
  const hookPhrases = [
    "ama ",
    "fakat ",
    "birden",
    "aniden",
    "o an",
    "acaba",
    "surpriz",
    "sürpriz",
    "en tuhaf",
  ];
  for (const phrase of hookPhrases) {
    if (s.includes(phrase)) score += 2;
  }
  score = Math.min(10, score);
  return { hasHook: score >= 3, score };
}

export function maxWordsForClipSeconds(clipSeconds: number, wpm: number, fillRatio = SPEECH_FILL_RATIO): number {
  const seconds = Math.max(2, clipSeconds || 8);
  const pace = Math.max(40, wpm || 100);
  return Math.max(6, Math.floor((seconds * fillRatio * pace) / 60));
}

export function minWordsForClipSeconds(clipSeconds: number, wpm: number, fillRatio = SPEECH_FILL_RATIO): number {
  const max = maxWordsForClipSeconds(clipSeconds, wpm, fillRatio);
  return Math.max(6, Math.floor(max * 0.82));
}

export function fitTextToMaxWords(text: string, maxWords: number): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  const words = normalized.split(/\s+/);
  if (words.length <= maxWords) return normalized;
  let cut = maxWords;
  const floor = Math.max(3, Math.floor(maxWords * 0.75));
  for (let i = maxWords - 1; i >= floor; i--) {
    if (/[.!?;…]$/.test(words[i]) || /[.!?;…]["”']$/.test(words[i])) {
      cut = i + 1;
      break;
    }
  }
  const slice = words.slice(0, cut).join(" ").trim();
  if (/[.!?…]$/.test(slice)) return slice;
  return `${slice}.`;
}

function splitLongSentence(sentence: string, maxWords: number): string[] {
  if (countWords(sentence) <= maxWords) return [sentence];
  const parts = sentence.split(/(?<=[,;:—])\s+/);
  const chunks: string[] = [];
  let current = "";
  for (const part of parts) {
    const candidate = current ? `${current} ${part}` : part;
    if (countWords(candidate) > maxWords && current) {
      chunks.push(current.trim());
      current = part;
    } else {
      current = candidate;
    }
  }
  if (current.trim()) chunks.push(current.trim());
  const result: string[] = [];
  for (const chunk of chunks) {
    if (countWords(chunk) <= maxWords) {
      result.push(chunk);
      continue;
    }
    const words = chunk.split(/\s+/);
    for (let i = 0; i < words.length; i += maxWords) {
      result.push(words.slice(i, i + maxWords).join(" "));
    }
  }
  return result;
}

export function splitStoryIntoClips(fullStory: string, options: SplitOptions): ClipDraft[] {
  const safetyRatio = options.safetyRatio ?? DEFAULT_SAFETY_RATIO;
  const budgetSeconds = options.clipSeconds * safetyRatio;
  const targetWords = Math.max(3, Math.floor((budgetSeconds / 60) * options.wpm));
  const minWords = Math.max(2, Math.floor(targetWords * 0.35));

  const sentences = splitIntoSentences(fullStory).flatMap((s) => splitLongSentence(s, targetWords));
  if (sentences.length === 0) return [];

  interface Piece {
    text: string;
    words: number;
    hook: { hasHook: boolean; score: number };
  }
  const pieces: Piece[] = sentences.map((s) => ({ text: s, words: countWords(s), hook: detectHook(s) }));

  const clips: string[][] = [];
  let current: Piece[] = [];
  let currentWords = 0;

  const flush = () => {
    if (current.length > 0) {
      clips.push(current.map((p) => p.text));
      current = [];
      currentWords = 0;
    }
  };

  for (let i = 0; i < pieces.length; i++) {
    const piece = pieces[i];
    const wouldBe = currentWords + piece.words;

    if (wouldBe > targetWords && current.length > 0) {
      const tolerance = Math.floor(targetWords * 1.15);
      if (!current[current.length - 1].hook.hasHook && piece.hook.hasHook && wouldBe <= tolerance) {
        current.push(piece);
        flush();
        continue;
      }
      flush();
    }
    current.push(piece);
    currentWords += piece.words;

    if (currentWords >= targetWords * 0.8 && piece.hook.hasHook) {
      flush();
    }
  }
  flush();

  if (clips.length >= 2) {
    const lastWords = countWords(clips[clips.length - 1].join(" "));
    if (lastWords < minWords) {
      const last = clips.pop()!;
      clips[clips.length - 1].push(...last);
    }
  }

  return clips.map((sentenceGroup, i) => {
    const dialogue = sentenceGroup.join(" ");
    const words = countWords(dialogue);
    const lastSentence = sentenceGroup[sentenceGroup.length - 1] ?? "";
    const hook = detectHook(lastSentence);
    return {
      index: i + 1,
      dialogue,
      estimatedWords: words,
      estimatedDurationSeconds: Number(((words / options.wpm) * 60).toFixed(1)),
      hasHook: hook.hasHook,
      curiosityScore: hook.score,
    };
  });
}
