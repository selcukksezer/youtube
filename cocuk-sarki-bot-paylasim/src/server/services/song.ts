import { z } from "zod";
import type { Project } from "@prisma/client";
import { prisma } from "@/server/db";
import { structuredCall } from "@/server/services/openai";
import { recordEvent } from "@/server/lib/logger";
import { publishEvent } from "@/server/lib/events";
import { dnaCardSchema, type DnaCard } from "@/lib/song-character";
import { ensureSongDnaCard } from "@/server/services/song-dna";
import {
  analyzeCastFromLyrics,
  formatCastForVisualsPrompt,
  persistSongCast,
  resolveCharacterIdByName,
  listSongCast,
} from "@/server/services/song-cast";
import { runSafetyCheck, type SafetyResult } from "@/server/services/song-safety";
import { curiosityRulesFor, reportCuriosityFlow } from "@/server/services/curiosity";
import {
  SONG_THEMES,
  SONG_STYLES,
  SONG_DURATION_PRESETS,
  SONG_MV_LIVELINESS_LOCK,
  SONG_LYRIC_CRAFT_LOCK,
  SONG_VOICE_IDENTITY_LOCK,
  SONG_MV_PRODUCTION_LOCK,
  SONG_OPENING_CLOSING_CRAFT,
  SONG_LYRIC_PICTURE_SYNC_LOCK,
  SONG_CHARACTER_FIDELITY_LOCK,
  buildSongArcBlueprint,
  type SongTheme,
  type SongStyle,
} from "@/lib/song-catalog";
import { resolvePublishAiModel, resolveSongPlannerAi } from "@/server/services/publish";
import { loadSongSettings, updateSongSettings } from "@/server/services/song-settings-store";
import { songHasMasterAudio } from "@/lib/song-settings";
// DIKKAT: bu dosyada ayrica yerel bir `songClipCount` (hedef sureden sahne
// sayisi, Math.round) vardir. Ses omurgasina gore klip sayisi HER ZAMAN yukari
// yuvarlanmali (sarkinin sonu goruntusuz kalmasin), bu yuzden takma adla alinir.
import { songClipAudioWindow, songClipCount as songClipCountForAudio } from "@/lib/song-clip-timeline";
import { buildLyricActionTimeline } from "@/lib/song-prompt-craft";
import {
  detectHeroSubject,
  detectSongWorld,
  environmentConflictsWorld,
  formatLyricStagingLine,
  isSpokenOrTalkSing,
  lyricsNameHero,
  type HeroSubject,
  type SongWorldLock,
} from "@/lib/song-lyric-visual";
import {
  clipVarietyAccent,
  fallbackShotPrompt,
  formatLyricsContextVarietyHint,
  formatStyleOverlay,
  formatVisualsVarietyLock,
  resolveSongVarietyPack,
  type SongVarietyPack,
} from "@/lib/song-variety";

/**
 * Cocuk sarki klibi stüdyosu.
 * Yas bandina ve hedef sureye gore profesyonel, soylenebilir sozler +
 * klip klip muzik videosu sahneleri uretir.
 *
 * Tema/stil katalogu: src/lib/song-catalog.ts (client + server tek kaynak).
 */

export type { SongTheme, SongStyle };
export {
  SONG_THEMES,
  SONG_STYLES,
  SONG_DURATION_PRESETS,
  SONG_LYRIC_CRAFT_LOCK,
  SONG_VOICE_IDENTITY_LOCK,
  SONG_MV_PRODUCTION_LOCK,
  SONG_OPENING_CLOSING_CRAFT,
  SONG_LYRIC_PICTURE_SYNC_LOCK,
  SONG_CHARACTER_FIDELITY_LOCK,
  buildSongArcBlueprint,
};

/** Hedef sure ve klip uzunlugundan sahne sayisi. */
export function songClipCount(targetSeconds: number, clipSeconds: number): number {
  const clip = Math.max(2, clipSeconds || 8);
  return Math.max(4, Math.round(targetSeconds / clip));
}

/**
 * Yas bandina gore saniyede hece.
 * Gercek cocuk sarkilarinda 8 saniyeye iki dolu dize sigar; dusuk butce
 * klipleri "bos/ruhsuz" birakir, bu yuzden tempoya yakin degerler kullanilir.
 */
export function syllableBudgetPerSecond(ageBand: string): number {
  if (ageBand === "1-3") return 2.2;
  if (ageBand === "6-8") return 3.6;
  return 3.0;
}

export function syllableBudgetForClip(ageBand: string, clipSeconds: number): number {
  return Math.max(12, Math.round(syllableBudgetPerSecond(ageBand) * clipSeconds));
}

/** Klibin yarim/bos kalmamasi icin alt sinir (hedefin ~%65'i). */
export function syllableFloorForClip(ageBand: string, clipSeconds: number): number {
  return Math.max(8, Math.round(syllableBudgetForClip(ageBand, clipSeconds) * 0.65));
}

/** Klip basina beklenen dize sayisi (yas bandina gore). */
export function lineCountForClip(ageBand: string): string {
  if (ageBand === "1-3") return "2 kisa dize (veya 1 dize + 1 tekrar)";
  if (ageBand === "6-8") return "2-3 dize";
  return "2 dize";
}

export function recommendedBpm(ageBand: string, styleId: string): { min: number; max: number } {
  const style = SONG_STYLES.find((s) => s.id === styleId);
  if (style?.bpmRange) {
    if (ageBand === "1-3") {
      return { min: Math.min(style.bpmRange.min, 90), max: Math.min(style.bpmRange.max, 105) };
    }
    return { ...style.bpmRange };
  }
  if (styleId === "lullaby" || ageBand === "1-3") return { min: 70, max: 100 };
  if (styleId === "kidspop" || ageBand === "6-8") return { min: 108, max: 128 };
  return { min: 90, max: 118 };
}

function ageCraftRules(ageBand: string): string {
  if (ageBand === "1-3") {
    return `YAS 1-3 (bebek/yurumeye baslayan):
- Kelime dagarcigi: 1-3 heceli, gunluk kelimeler + tatli yansima sesleri (sip sip, pat pat, cik cik, hop hop)
- Dizeler kisa ama YARATICI: her klipte iki kucuk dize; en az birinde komik ses veya beklenmedik kucuk imge
- Soyut ders, ironi, korku, ayrilik YASAK — ama "ogretmen emri" de YASAK; oyun dili kullan
- Melodi dar aralikta, yavas tempo; ayni sticky nakarat en az 3 kez donsun
- Hareket: el calmak, sallanmak, isaret etmek; hizli dans yok`;
  }
  if (ageBand === "6-8") {
    return `YAS 6-8:
- Mini hikaye yayi (istek -> kucuk engel -> birlikte cozum -> kutlama), korkutmadan; her kitada bir twist satir
- Nakarat akilda kalici ve sticky; kitalar hikayeyi + siradisi imgeleri ilerletsin
- Kafiye AABB veya ABAB; ic kafiye ve aliterasyon ZORUNLU en az bir yerde
- Somut ayrinti: isim, sayi, renk, koku, ses — vaaz cumlesi yok
- Ders olayin icinden dogsun; karakterin tipik sozu en az bir kez dogal aksın
- Nakaratta kisa arkadas korosu / echo dizeleri serbest`;
  }
  return `YAS 3-5:
- Her dize 6-12 hece; net AABB kafiye, guclu ritim; B satirinda kucuk surpriz
- Nakarat 2-4 dize sticky poster cumlesi; en az iki kez birebir ayni donsun
- Somut ve duyusal: renk, sayi, ses, dokunma — metafor cocuk anlayacak kadar basit olsun
- Call-and-response ve yansima sesleri sarkiyi canlandirir (emir listesi degil)
- Ogretici icerik oyun gibi; ogretmen/talimat tonu YASAK
- Korku, karanlik, kaybolma, ceza yok`;
}

function structureForDuration(targetSeconds: number, clipCount: number, clipSeconds: number): string {
  return buildSongArcBlueprint({ targetSeconds, clipCount, clipSeconds });
}

/**
 * Eski kayitlarin da acilabilmesi icin yeni alanlar varsayilanlidir;
 * yeni uretimlerde model hepsini doldurur.
 */
const songClipSchema = z.object({
  index: z.number().int().min(1),
  section: z.enum(["intro", "hook", "verse", "prechorus", "chorus", "bridge", "outro"]),
  lyrics: z.string().min(1),
  syllableCount: z.number().int().min(1),
  sceneDescription: z.string().min(1),
  imagePrompt: z.string().min(20),
  choreography: z.string().min(1),
  voiceTone: z.string().min(1),
  emotion: z.string().min(1),
  environment: z.string().default(""),
  lighting: z.string().default(""),
  cameraShot: z.string().default(""),
  motionDetail: z.string().default(""),
  microExpression: z.string().default(""),
  /**
   * Sozde gecen ve kadroda ZORUNLU gorunecek prop listesi (Ingilizce).
   * Ornek: "exactly 3 colorful wooden toy train cars on a short track, counted left-to-right"
   */
  mustShowProps: z.string().default(""),
  lyricSyncAction: z.string().default(""),
  secondBySecond: z.string().default(""),
  weatherTimeOfDay: z.string().default(""),
  exteriorWorld: z.string().default(""),
  hookNote: z.string().default(""),
  curiosityScore: z.number().min(0).max(10).default(5),
  /** Klip icin soyleyen performer adi (AI kadrodan). */
  singerName: z.string().default(""),
});

const songPackageSchema = z.object({
  title: z.string().min(1),
  titleTurkish: z.string().min(1),
  hookLine: z.string().min(1),
  bpm: z.number().int().min(60).max(160),
  musicalKey: z.string().min(1),
  mood: z.string().min(1),
  instrumentation: z.string().min(1),
  vocalStyle: z.string().min(1),
  rhymeScheme: z.string().min(1),
  estimatedDurationSeconds: z.number().int().min(20),
  formattedLyrics: z.string().min(10),
  clips: z.array(songClipSchema).min(4),
});

export type SongPackage = z.infer<typeof songPackageSchema>;

/** API rotalari ayni semayi kullanir; aksi halde yeni alanlar kayitta silinir. */
export { songPackageSchema };

/* -------------------------------------------------------------------------
 * Sarki uretimi IKI CAGRIDA yapilir.
 *
 * Tek cagrida 11 klip x 16 alan (cogu 40-80 kelimelik Ingilizce paragraf)
 * istendiginde gpt-5 + "medium" akil yurutme 4 dakikalik zaman asimini
 * asiyordu. Bolme, modeli DUSURMEDEN her cagriyi yariya indirir; ustelik
 * gorsel yonetmen ikinci cagrida BITMIS sozleri gordugu icin sahneler
 * sozlerle daha iyi ortusur.
 *
 *  1) SOZ + MUZIK  : yaratici cekirdek (derin akil yurutme burada)
 *  2) GORSEL PLAN  : her klip icin kamera/isik/hareket/koreografi
 * ------------------------------------------------------------------------- */

const LYRICS_JSON_SCHEMA: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  properties: {
    title: { type: "string", description: "English song title, catchy, no clickbait" },
    titleTurkish: { type: "string" },
    hookLine: { type: "string", description: "The most memorable sung line (speech language)" },
    bpm: { type: "integer" },
    musicalKey: { type: "string", description: "e.g. C major" },
    mood: { type: "string" },
    instrumentation: { type: "string", description: "English, kids-safe arrangement" },
    vocalStyle: { type: "string", description: "How the character sings" },
    rhymeScheme: { type: "string" },
    formattedLyrics: { type: "string", description: "Full lyrics with section headers, speech language" },
    clips: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          index: { type: "integer" },
          section: { type: "string", enum: ["intro", "hook", "verse", "prechorus", "chorus", "bridge", "outro"] },
          lyrics: { type: "string", description: "ONLY the sung words for this clip, speech language, 2 lines with line break" },
          syllableCount: { type: "integer" },
          emotion: { type: "string", description: "Turkish, one word for the panel badge" },
          voiceTone: { type: "string", description: "ENGLISH, how this line is sung, e.g. 'bright and bouncy, smiling tone'" },
          hookNote: { type: "string", description: "Turkish. The question this clip leaves in the listener's mind, one sentence" },
          curiosityScore: { type: "integer", description: "0-10 curiosity score for this clip" },
        },
        required: ["index", "section", "lyrics", "syllableCount", "emotion", "voiceTone", "hookNote", "curiosityScore"],
      },
    },
  },
  required: [
    "title",
    "titleTurkish",
    "hookLine",
    "bpm",
    "musicalKey",
    "mood",
    "instrumentation",
    "vocalStyle",
    "rhymeScheme",
    "formattedLyrics",
    "clips",
  ],
};

const lyricsResultSchema = z.object({
  title: z.string().min(1),
  titleTurkish: z.string().min(1),
  hookLine: z.string().min(1),
  bpm: z.number().int().min(60).max(160),
  musicalKey: z.string().min(1),
  mood: z.string().min(1),
  instrumentation: z.string().min(1),
  vocalStyle: z.string().min(1),
  rhymeScheme: z.string().min(1),
  formattedLyrics: z.string().min(10),
  clips: z
    .array(
      z.object({
        index: z.number().int().min(1),
        section: z.enum(["intro", "hook", "verse", "prechorus", "chorus", "bridge", "outro"]),
        lyrics: z.string().min(1),
        syllableCount: z.number().int().min(1),
        emotion: z.string().min(1),
        voiceTone: z.string().min(1),
        hookNote: z.string().default(""),
        curiosityScore: z.number().min(0).max(10).default(5),
      })
    )
    .min(4),
});

const VISUALS_JSON_SCHEMA: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  properties: {
    shots: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          index: { type: "integer" },
          sceneDescription: { type: "string", description: "Turkish short summary for the panel" },
          imagePrompt: {
            type: "string",
            description:
              "English. MUST start with: While singing: \"[exact lyric]\". On-screen: [action+props matching those words]. Then directed shot: subject, action, set layers, materials, sky/ground, camera. 80-140 words. No vague fluff.",
          },
          choreography: { type: "string", description: "Turkish, simple age-safe moves that MATCH the lyric meaning" },
          environment: {
            type: "string",
            description: "English. Dense set: surfaces, textures, background depth, weather, time of day — never empty void",
          },
          lighting: {
            type: "string",
            description: "English. Key/fill/rim light, color temperature, bounce, shadow softness, volumetric beams",
          },
          cameraShot: {
            type: "string",
            description: "English. Shot size, lens mm, height, and at most one slow move (push-in, gentle arc) or locked off",
          },
          motionDetail: {
            type: "string",
            description: "English. Secondary animation: fur/fabric sway, bubbles, dust motes, water ripples, hair bounce, props reacting",
          },
          microExpression: {
            type: "string",
            description: "English. Face acting: eyebrow, ear, tail, blink, breath, eye sparkle, weight shift on the beat",
          },
          mustShowProps: {
            type: "string",
            description:
              "English. Non-negotiable on-screen props extracted from THIS clip's lyrics ONLY: exact counts, materials, placement. Example: 'exactly 3 red wooden toy train wagons lined on a track, wheels and couplings visible'. Empty-air counting FORBIDDEN.",
          },
          lyricSyncAction: {
            type: "string",
            description:
              "English. 1-2 sentences: as each lyric phrase is sung, what EXACTLY happens on screen (gesture + prop contact). Must map lyric words → visible beats in order.",
          },
          secondBySecond: {
            type: "string",
            description:
              "English. Mandatory 0-Ns timeline, semicolon-separated, one beat per second: gesture + lyric phrase + prop contact + camera micro-move. Last second is handoff pose.",
          },
          weatherTimeOfDay: {
            type: "string",
            description: "English. Locked time of day + weather for this song world (e.g. late-afternoon golden hour, clear sky, warm breeze).",
          },
          exteriorWorld: {
            type: "string",
            description:
              "English. Exterior/set depth: ground material, sky/horizon, architecture or landscape, distant living extras, window-to-outside if interior.",
          },
          singerName: {
            type: "string",
            description: "Exact name of the performer singing this clip — must match one cast member name",
          },
        },
        required: [
          "index",
          "sceneDescription",
          "imagePrompt",
          "choreography",
          "environment",
          "lighting",
          "cameraShot",
          "motionDetail",
          "microExpression",
          "mustShowProps",
          "lyricSyncAction",
          "secondBySecond",
          "weatherTimeOfDay",
          "exteriorWorld",
          "singerName",
        ],
      },
    },
  },
  required: ["shots"],
};

const visualsResultSchema = z.object({
  shots: z
    .array(
      z.object({
        index: z.number().int().min(1),
        sceneDescription: z.string().min(1),
        imagePrompt: z.string().min(20),
        choreography: z.string().min(1),
        environment: z.string().default(""),
        lighting: z.string().default(""),
        cameraShot: z.string().default(""),
        motionDetail: z.string().default(""),
        microExpression: z.string().default(""),
        mustShowProps: z.string().min(8),
        lyricSyncAction: z.string().min(8).default(""),
        secondBySecond: z.string().default(""),
        weatherTimeOfDay: z.string().default(""),
        exteriorWorld: z.string().default(""),
        singerName: z.string().min(1).default(""),
      })
    )
    .min(1),
});

type VisualShot = z.infer<typeof visualsResultSchema>["shots"][number];

type VisualClipStub = {
  index: number;
  section: string;
  lyrics: string;
  emotion?: string;
};

/** Oto bitir gorsel plani: tek 10dk cagri yerine kucuk paketler. */
export const SONG_VISUALS_BATCH_SIZE = 6;
const VISUALS_BATCH_CONCURRENCY = 2;
const VISUALS_BATCH_TIMEOUT_MS = 150_000;
const VISUALS_TOKENS_PER_CLIP = 1_600;

export function chunkSongVisualBatches<T>(items: T[], size = SONG_VISUALS_BATCH_SIZE): T[][] {
  const chunk = Math.max(1, size);
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += chunk) out.push(items.slice(i, i + chunk));
  return out;
}

async function mapPool<T, R>(items: T[], concurrency: number, fn: (item: T, index: number) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (true) {
      const i = cursor++;
      if (i >= items.length) return;
      results[i] = await fn(items[i]!, i);
    }
  }
  const n = Math.max(1, Math.min(concurrency, items.length));
  await Promise.all(Array.from({ length: n }, () => worker()));
  return results;
}

function isRetryableVisualsError(err: unknown): boolean {
  const message = err instanceof Error ? err.message : String(err);
  return /zaman asimina|timed?\s*out|yapilandirilmis cikti uretemedi/i.test(message);
}

type VisualsBatchPlanOpts = {
  projectId: string;
  model: string;
  reasoningEffort: "minimal" | "low" | "medium" | "high" | undefined;
  schemaName: string;
  clips: VisualClipStub[];
  clipSeconds: number;
  targetSeconds: number;
  variety: SongVarietyPack;
  castPrompt: string;
  leadName: string;
  leadSpecies: string;
  leadPersonality: string;
  leadGesture: string;
  leadLoves: string;
  leadPalette: string;
  ageBand: string;
  avoidList: string;
  arcBlueprint: string;
  propBank: string;
  stagingHint: string;
  meaningPromise: string;
  themeTitle: string;
  themeSummary: string;
  hookLine: string;
  mood: string;
  bpmHint: string;
  styleLabel: string;
  shotStylePhrase: string;
  vocalStyle?: string;
  beatVisuals?: string;
};

async function planOneVisualBatch(opts: VisualsBatchPlanOpts, batch: VisualClipStub[]): Promise<VisualShot[]> {
  const total = opts.clips.length;
  const indexes = batch.map((c) => c.index);
  const first = indexes[0]!;
  const last = indexes[indexes.length - 1]!;
  const prevClip = opts.clips.find((c) => c.index === first - 1);
  const nextClip = opts.clips.find((c) => c.index === last + 1);
  const lyricBlock = batch
    .map((c) => `Klip ${c.index} [${c.section}]${c.emotion ? ` duygu:${c.emotion}` : ""}\n${c.lyrics}`)
    .join("\n\n");

  const result = await structuredCall({
    model: opts.model,
    system: `Sen 3D kids MV gorsel yonetmenisin. SADECE klipler ${indexes.join(", ")} (tum sarki ${total} klip, her biri ${opts.clipSeconds}sn). shots.length = ${batch.length}. index alanina GERCEK klip numarasini yaz.

YAYIN GUVENLIGI: insan cocuk / minor / toddler / kid / child / baby / kiss yasak. Stylized 3D cartoon mascot. Yuze/buruna parmak dokunma yok.

${SONG_LYRIC_PICTURE_SYNC_LOCK}

KAPSAMLI SOZ↔GORSEL (KIRMIZI CIZGI):
- Bu klibin lyrics satirindaki HER icerik kelimesi (isim, fiil, renk, sayi, hayvan, yer, konusma) mustShowProps + lyricSyncAction + secondBySecond icinde somut sahne olsun.
- Ornek: "kelebek uçar" = BU klipte kanat cirpan kelebek HAVADA — cikartma, sonraki klip veya ima YASAK.
- Konusma/talk-sing (merhaba, bakın, hadi) generic dansla örtülmez; ağız + jest o kelimeleri onaylar.
- Hicbir soz imgelerini sonraki klipe erteleme. singerName kadrodan birebir; yuz/kostum kilidi her shotta dogrulanir.

SUREKLILIK (tek film saniyeleri): her klip oncekinin dogrudan devamı (match-on-action). Ayni dunya, kostum, karakter, isik sicakligi. Mini-hikaye sifirlamasi YASAK. Kamera/koreografi degisebilir.
${formatVisualsVarietyLock(opts.variety)}
${opts.beatVisuals ? `Beat visuals: ${opts.beatVisuals}` : ""}
${opts.vocalStyle ? `Tek sarkici kimligi: ${opts.vocalStyle}` : ""}

Prop bank: ${opts.propBank}
Sahneleme: ${opts.stagingHint}
Vaat: ${opts.meaningPromise}

KADRO (singerName listeden birebir):
${opts.castPrompt}

imagePrompt 80-140 kelime Ingilizce; "${opts.shotStylePhrase}" ifadesini "While singing:" sonrasi kullansin.
sceneDescription + choreography Turkce.
secondBySecond: 0-${opts.clipSeconds}s noktali virgulle (jest + soz parcasi + prop).
environment, lighting, cameraShot, motionDetail, microExpression, weatherTimeOfDay, exteriorWorld doldur.`,
    user: `Tema: ${opts.themeTitle}
${opts.themeSummary}
Hook: ${opts.hookLine}
Mood: ${opts.mood} · ${opts.bpmHint}
Sure: ${opts.targetSeconds}sn · bu paket klipler ${first}–${last} / ${total}
Stil: ${opts.styleLabel}
Lead: ${opts.leadName} (${opts.leadSpecies}) — ${opts.leadPersonality}
Imza: ${opts.leadGesture} · ${opts.leadLoves}
Palet: ${opts.leadPalette}
Yas: ${opts.ageBand}
Istenmeyen: ${opts.avoidList}

YAY (tum film omurgasi):
${opts.arcBlueprint}

${prevClip ? `ONCEKI KLIP ${prevClip.index} (devam et, dunya sifirlama):\n${prevClip.lyrics}` : "Bu paket sarkinin basindan (cold-open)."}
${nextClip ? `SONRAKI KLIP ${nextClip.index} (son saniye soft handoff):\n${nextClip.lyrics}` : "Bu paket sarkinin sonuna yakin olabilir (soft outro)."}

KLIP SOZLERI:
${lyricBlock}`,
    schemaName: opts.schemaName,
    jsonSchema: VISUALS_JSON_SCHEMA,
    zodSchema: visualsResultSchema,
    maxOutputTokens: Math.min(16_000, Math.max(6_000, batch.length * VISUALS_TOKENS_PER_CLIP)),
    reasoningEffort: opts.reasoningEffort,
    timeoutMs: VISUALS_BATCH_TIMEOUT_MS,
  });

  return result.shots;
}

async function planVisualBatchWithSplit(opts: VisualsBatchPlanOpts, batch: VisualClipStub[]): Promise<VisualShot[]> {
  try {
    return await planOneVisualBatch(opts, batch);
  } catch (err) {
    if (batch.length <= 2 || !isRetryableVisualsError(err)) throw err;
    const mid = Math.ceil(batch.length / 2);
    await recordEvent({
      projectId: opts.projectId,
      step: "song",
      message: `Gorsel paket yavas kaldi — klipler ${batch[0]!.index}–${batch[batch.length - 1]!.index} ikiye bolunuyor`,
    });
    const first = await planVisualBatchWithSplit(opts, batch.slice(0, mid));
    const second = await planVisualBatchWithSplit(opts, batch.slice(mid));
    return [...first, ...second];
  }
}

async function planVisualShotsInBatches(opts: VisualsBatchPlanOpts): Promise<VisualShot[]> {
  const batches = chunkSongVisualBatches(opts.clips, SONG_VISUALS_BATCH_SIZE);
  await recordEvent({
    projectId: opts.projectId,
    step: "song",
    message: `Gorsel plan: ${opts.clips.length} klip, ${batches.length} paket (paralel ${Math.min(
      VISUALS_BATCH_CONCURRENCY,
      batches.length
    )}, reasoning ${opts.reasoningEffort || "low"})`,
  });

  const batchResults = await mapPool(batches, VISUALS_BATCH_CONCURRENCY, async (batch, batchIndex) => {
    const first = batch[0]!.index;
    const last = batch[batch.length - 1]!.index;
    await recordEvent({
      projectId: opts.projectId,
      step: "song",
      message: `Gorsel paket ${batchIndex + 1}/${batches.length}: klipler ${first}–${last}`,
    });
    return planVisualBatchWithSplit(opts, batch);
  });

  return batchResults.flat();
}

export function parseSongPackage(raw: string | null | undefined): SongPackage | null {
  if (!raw?.trim()) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    const result = songPackageSchema.safeParse(parsed);
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}

function themeFor(project: Project): SongTheme | undefined {
  return SONG_THEMES.find((t) => t.id === project.moralLesson);
}

function styleFor(project: Project): SongStyle | undefined {
  return SONG_STYLES.find((s) => s.id === project.narrationStyle || s.label === project.narrationStyle);
}

const titleSuggestionsSchema = z.object({
  titles: z
    .array(
      z.object({
        english: z.string().min(2).max(70),
        turkish: z.string().min(2).max(70),
        premise: z.string().min(12).max(220),
        hookLine: z.string().min(4).max(80),
        vibe: z.string().min(2).max(40),
      })
    )
    .min(5)
    .max(6),
});

export type SongTitleSuggestion = z.infer<typeof titleSuggestionsSchema>["titles"][number];

const topicSuggestionsSchema = z.object({
  topics: z
    .array(
      z.object({
        topic: z.string().min(3).max(120),
        angle: z.string().min(8).max(220),
        propHook: z.string().min(3).max(160),
      })
    )
    .min(5)
    .max(8),
});

/** Sarkiya uygun 5-6 hit baslik onerir (YouTube kids MV poster adi). */
export async function suggestSongTitles(projectId: string): Promise<SongTitleSuggestion[]> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType !== "kids_song") throw new Error("Bu islem yalnizca cocuk sarki klibi sablonunda calisir");
  const cast = await prisma.characterProfile.findMany({ where: { projectId }, orderBy: [{ role: "asc" }] });
  let dna: DnaCard | null = null;
  const lead = cast.find((c) => c.role === "main") ?? cast[0];
  if (lead?.dnaCard && lead.dnaCard !== "{}") {
    try {
      dna = JSON.parse(lead.dnaCard) as DnaCard;
    } catch {
      /* ignore */
    }
  }
  const theme = themeFor(project);
  const style = styleFor(project);
  const ageBand = project.ageBand || "3-5";
  const { model, reasoningEffort } = await resolvePublishAiModel();
  const speechIsTurkish = /turk/i.test(project.speechLanguage || "Turkish");

  const result = await structuredCall<{ titles: SongTitleSuggestion[] }>({
    model,
    reasoningEffort,
    timeoutMs: 180_000,
    system: `Sen odullu bir cocuk YouTube muzik kanali icin HIT BASLIK yazarisin (kids-pop + nursery rhyme yayinciligi).

GOREV: Tam 5 cesitli, yayinlanabilir sarki basligi oner. Bunlar sarkinin POSTER ADI — soz yazimi bu ismi merkeze alacak.

HIT BASLIK DNA'SI:
- Kisa, soylenebilir, sticky: 2-6 kelime. Araba koltugunda mirildanilabilir.
- ANLAM tasir: baslik sarkinin duygusal vaadini (meaningPromise) poster gibi soylesin — sadece "Tap Tap / Sayalim / Renkler" ezberi YASAK.
- Somut imge tasir (renk, prop, ev, yol, kucak) AMA imge bir HIKAYEYE hizmet etsin.
- Bos slogan YASAK ("Harika Gun", "Cok Eglenceli Sarki", "Hadi Oynayalim").
- Yas bandina uygun, korkutmayan, tiklama tuzagi yok (BUYUK HARF BAGIRISI, "SHOCKING", "!!!", sahte merak yok).
- Tema + ek konu + karakter sesiyle uyumlu; baska temaya kacma.
- 5 oneri BIRBIRININ KOPYASI olmasin: farkli aci (duygu / sahne / karakter / prop / ritim) — hepsi AYNI vaadi farkli kapidan.
- Var olan hit sarkilari, marka ve karakterleri KOPYALAMA / adini anma.

ALANLAR:
- turkish: yayin adi (soz dili Turkce ise asil baslik burasi). Temiz Turkce, dogal vurgu.
- english: ayni vaadin Ingilizce karsiligi (YouTube arama / uluslararasi). Ayni fikir, ceviri-robotu gibi kelime kelime degil.
- premise: 1 cumle — sarki NE ANLATIYOR (duygu vaadi) + hangi sahne/prop, kim soyluyor. Sadece oyun mekanigi yazma.
- hookLine: nakaratin sticky kalbi; vaadi tasiyan kisa soylenebilir cumle (soz dilinde). "Tap tap / tık tık" listesi YASAK.
- vibe: 1-3 kelimelik etiket (or. "Dans hook", "Kopuk partisi", "Sayma oyunu", "Ninni veda").

YASAK: ogretmen emri basliklari ("Hadi Yikalim"), jenerik "Kids Song / Nursery Rhymes" eki, karakter adini her basliga zorla sokmak (en fazla 1-2 oneride dogal kullan).`,
    user: `Kanal: ${project.channelName || project.name}
Soz / konusma dili: ${project.speechLanguage} ${speechIsTurkish ? "(Turkce baslik ONCELIKLI)" : ""}
Yas bandi: ${ageBand}
Hedef sure: ${project.targetDurationSeconds} sn (~${(project.targetDurationSeconds / 60).toFixed(1)} dk)
Tema: ${theme ? `${theme.label} — ${theme.tagline}` : project.moralLesson || "ozel / serbest"}
Tema brief: ${theme?.description || "-"}
DUYGUSAL VAAT (meaningPromise — baslik BUNU soylesin): ${theme?.meaningPromise || "-"}
Kita yayi (verseArc): ${theme?.verseArc || "-"}
Hook acisi: ${theme?.hookAngle || "-"}
Oyun mekanigi: ${theme?.gameMechanic || "-"}
Lyric spark: ${theme?.lyricSpark || "-"}
Prop bankasi: ${theme?.propBank || "-"}
Muzik stili: ${style ? `${style.label} — ${style.tagline}` : project.narrationStyle || "-"}
Stil groove: ${style?.groove || "-"}
Ek konu / ozel istek: ${project.topic?.trim() || "(bos)"}
Karakter: ${dna ? `${dna.name} (${dna.species})` : "(henuz belirlenmedi — soz analizi sonrasi AI kadro olusturur)"}
Kisilik: ${dna ? dna.personality.join(", ") : "-"}
Tipik soz: ${dna ? `"${dna.catchphrase}"` : "-"}
Sevdigi: ${dna?.loves || "-"}

5 hit sarki basligi oner. Cesitli, sticky, tema+stil+ek konuya sadik.`,
    schemaName: "song_title_suggestions",
    jsonSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        titles: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            properties: {
              english: { type: "string" },
              turkish: { type: "string" },
              premise: { type: "string" },
              hookLine: { type: "string" },
              vibe: { type: "string" },
            },
            required: ["english", "turkish", "premise", "hookLine", "vibe"],
          },
        },
      },
      required: ["titles"],
    },
    zodSchema: titleSuggestionsSchema,
  });
  return result.titles;
}

/**
 * Kanal/tema adiminda "Ek konu / ozel istek" alani icin AI onerileri.
 * Karakter yokken de calisir — tema + yas + stil + kanal bağlamı yeter.
 */
export async function suggestSongTopics(
  projectId: string
): Promise<Array<{ topic: string; angle: string; propHook: string }>> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType !== "kids_song") throw new Error("Bu islem yalnizca cocuk sarki klibi sablonunda calisir");
  const theme = themeFor(project);
  const style = styleFor(project);
  const ageBand = project.ageBand || "3-5";
  const character = await prisma.characterProfile.findFirst({ where: { projectId, role: "main" } });
  let characterHint = "";
  if (character?.dnaCard && character.dnaCard !== "{}") {
    try {
      const dna = JSON.parse(character.dnaCard) as DnaCard;
      characterHint = `${dna.name} (${dna.species}) — sever: ${dna.loves}; tipik soz: ${dna.catchphrase}`;
    } catch {
      /* ignore */
    }
  }

  const result = await structuredCall<{ topics: Array<{ topic: string; angle: string; propHook: string }> }>({
    system: `Sen cocuk YouTube sarki kanallari icin YARATICI KONU / OZEL ISTEK oneren bir yayin stratejistisin.

GOREV: Secilen tema ve yas bandina uygun, soz+ekran uyumlu, somut "ek konu" onerileri uret.
Kullanici bunlardan birini "Ek konu / ozel istek" kutusuna yapistiracak — sarki yazimi bu notu kullanir.

KALITE:
- Her oneri ANLAM + SAHNE tasiin: duygu vaadi (neden soyluyoruz) ve somut prop. Sadece "daha cok tap tap / yeni hayvan sesi" YASAK.
- Her oneri SOMUT olsun (renk, prop, mini olay, mekan) ve o somut sey bir HISSE hizmet etsin. Soyut slogan tek basina YASAK.
- Tema ile CELISME: temayi guclendirsin, baska temaya kacmasin. meaningPromise'i incelt, tersine cevirme.
- Yas-guvenli: korku, siddet, karanlik, ceza yok.
- Cesitlilik: 6 oneri birbirinin kopyasi olmasin (farkli prop / oyun acisi).
- topic alani kisa ve net (Turkce, 3-12 kelime) — kutuya yazilacak metin.
- angle: bu konunun sarkiya nasil islenecegi (1 cumle).
- propHook: kadroda gorunecek 1-2 somut prop ipucu.
- Var olan hit sarkilari / marka adlarini kopyalama.`,
    user: `Kanal: ${project.channelName || project.name}
Yas bandi: ${ageBand}
Tema: ${theme ? `${theme.label} — ${theme.tagline}` : project.moralLesson || "ozel / serbest"}
Tema brief: ${theme?.description || "-"}
DUYGUSAL VAAT: ${theme?.meaningPromise || "-"}
Kita yayi: ${theme?.verseArc || "-"}
Prop bankasi: ${theme?.propBank || "-"}
Hook acisi: ${theme?.hookAngle || "-"}
Oyun mekanigi: ${theme?.gameMechanic || "-"}
Muzik stili: ${style ? `${style.label} — ${style.tagline}` : project.narrationStyle || "-"}
Hedef sure: ${project.targetDurationSeconds} sn
Mevcut ek konu (varsa, tekrarlama): ${project.topic?.trim() || "(bos)"}
Karakter (opsiyonel): ${characterHint || "(henuz secilmedi)"}
Dil: ${project.speechLanguage}

6 cesitli ek konu / ozel istek oner. topic alani kutuya yapistirilacak kisa Turkce metin olsun.`,
    schemaName: "song_topic_suggestions",
    jsonSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        topics: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            properties: {
              topic: { type: "string" },
              angle: { type: "string" },
              propHook: { type: "string" },
            },
            required: ["topic", "angle", "propHook"],
          },
        },
      },
      required: ["topics"],
    },
    zodSchema: topicSuggestionsSchema,
    reasoningEffort: "low",
    timeoutMs: 120_000,
  });
  return result.topics;
}

function persistSong(projectId: string, project: Project, song: SongPackage) {
  return prisma.story.upsert({
    where: { projectId_languageVariant: { projectId, languageVariant: "primary" } },
    create: {
      projectId,
      languageVariant: "primary",
      title: song.title,
      summary: song.hookLine,
      hook: song.hookLine,
      fullStory: song.formattedLyrics,
      estimatedWords: song.formattedLyrics.split(/\s+/).filter(Boolean).length,
      estimatedDurationSeconds: song.estimatedDurationSeconds,
      language: project.speechLanguage,
      characterVoiceNotes: JSON.stringify(song),
    },
    update: {
      title: song.title,
      summary: song.hookLine,
      hook: song.hookLine,
      fullStory: song.formattedLyrics,
      estimatedWords: song.formattedLyrics.split(/\s+/).filter(Boolean).length,
      estimatedDurationSeconds: song.estimatedDurationSeconds,
      language: project.speechLanguage,
      characterVoiceNotes: JSON.stringify(song),
    },
  });
}

/** Profesyonel cocuk sarkisi + klip plani uretir (henuz Clip kaydi acmaz). */
export async function generateSong(projectId: string, titleOverride?: string): Promise<SongPackage> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType !== "kids_song") throw new Error("Bu islem yalnizca cocuk sarki klibi sablonunda calisir");
  const cast = await prisma.characterProfile.findMany({ where: { projectId }, orderBy: [{ role: "asc" }] });
  const lead = cast.find((c) => c.role === "main") ?? cast[0];
  let dna: DnaCard | null = null;
  if (lead?.dnaCard && lead.dnaCard !== "{}") {
    try {
      dna = JSON.parse(lead.dnaCard) as DnaCard;
    } catch {
      /* yeniden uretilecek */
    }
  }
  if (!dna && lead) {
    const { buildSongDnaCardFromProfile } = await import("@/lib/song-character");
    dna = buildSongDnaCardFromProfile(lead, project);
  }
  if (!dna) {
    dna = dnaCardSchema.parse({
      name: "Yildiz",
      species: "stylized 3D cartoon mascot",
      personality: ["cheerful", "playful"],
      catchphrase: "Hadi birlikte!",
      signatureGesture: "rhythmic dance",
      voiceDescription: "bright kids pop vocal",
      fears: "scary imagery",
      loves: "music and dance",
      colorPalette: ["#FFD166", "#06D6A0"],
      imagePrompt: "stylized 3D cheerful mascot performer, colorful outfit, full body, kids music video hero",
      bodyDetail: "",
      outfitDetail: "",
      signatureProp: "microphone",
      styleLabel: "stylized3d",
    });
  }

  const clipSeconds = project.clipSeconds || 8;
  const clipCount = songClipCount(project.targetDurationSeconds, clipSeconds);
  const ageBand = project.ageBand || "3-5";
  const maxSyllables = syllableBudgetForClip(ageBand, clipSeconds);
  const minSyllables = syllableFloorForClip(ageBand, clipSeconds);
  const theme = themeFor(project);
  const style = styleFor(project);
  const bpm = recommendedBpm(project.ageBand || "3-5", style?.id || "kidspop");
  const title = (titleOverride || project.title || "").trim();
  const targetSeconds = project.targetDurationSeconds;
  const arcBlueprint = structureForDuration(targetSeconds, clipCount, clipSeconds);
  const { model: songModel, reasoningEffort: songReasoning } = await resolvePublishAiModel();
  const variety = resolveSongVarietyPack(project);
  await updateSongSettings(projectId, { varietySeed: variety.seed });

  await recordEvent({
    projectId,
    step: "song",
    message: `Sarki yazimi basladi — 1/2: sozler ve yay (${clipCount} klip, ~${targetSeconds}sn / ${(targetSeconds / 60).toFixed(1)} dk) · model ${songModel}`,
  });

  const lyricsResult = await structuredCall({
    model: songModel,
    system: `Sen odullu bir cocuk sarkisi YAZARI ve GERCEK bir kids-pop SANATCISISIN (mikrofon basinda soyleyen yazar). Calisma kagidi / ogretmen talimati YAZMAZSIN. Flagship model kalitesinde yaz: sozler yayinlanabilir hit gibi aksin; sureye gore kusursuz ACILIS + KAPANIS.

GOREV: Tam olarak ${clipCount} kliplik / ${targetSeconds} sn (~${(targetSeconds / 60).toFixed(1)} dk) soylenebilir, RUHU OLAN, YARATICI, SANATCI AGZINDAN profesyonel bir cocuk sarkisi yaz. Sozler ilk dinleyiste akilda kalsin; araba koltugunda mirildanilabilsin. Baslangic ve bitis bu sureye GORE guzel ve tatmin edici olsun. Her dize soylenebilir ve gurur duyulacak kadar temiz olsun.

${curiosityRulesFor("kids_song")}

${SONG_LYRIC_CRAFT_LOCK}

${SONG_OPENING_CLOSING_CRAFT}

PIYASADA TUTAN COCUK SARKILARININ ORTAK MUHENDISLIGI (BUNLARI UYGULA — ICERIK KOPYALAMA):
- HOOK ONCE GELIR: ilk 5 saniyede sarkinin en yapiskan cumlesi soylenir. Uzun giris, "merhaba arkadaslar / hadi baslayalim" isinmasi YASAK.
- NAKARAT BEBEK GIBI TEKRARLANIR: ayni sozler, ayni melodi kalibi, video boyunca en az 3 kez. Her ~20-25 saniyede bir nakarat gelsin.
- TEKRAR + KUCUK DEGISIM: dizeler A-A-B; B satiri surpriz getirsin. Cocuk ikinci dinlemede birlikte soyleyebilsin.
- CAGRI-YANIT: bazi dizeler soru/cagri, sonraki yanit ("Kim o?" / "Kedi!") — oyun icinde, emir listesi degil.
- SES OYUNU: yansima sesler, sayma, hece oyunlari, alliterasyon — tutundurucu olsun.
- HAREKET DAVETI: beden harekete gelsin ama YONERGE LISTESI gibi degil, sozun icinde akarak.
- DAR MELODI ARALIGI: cocuk sesiyle soylenebilecek dar aralik.
- HAREKETLI GROOVE: nakaratta dans edilebilir enerji; tempo sabit.
- SON DOKUNUS: outro nakaratin son cumlesini yumusakca tekrarlayip kapatsin.
- OZGUNLUK KIRMIZI CIZGI: var olan hicbir sarkinin sozunu/melodisini/karakterini KOPYALAMA, adini anma.

KARAKTER + SAHNE (sozler Canli olsun):
- Sozler bir SAHNE anlatsin; talimat listesi olmasin. "Soyle:", "Tekrarla:", "Simdi yap:", "Hadi ..." emir kaliplari YASAK.
- Her dize somut ve duyusal: renk, koku, ses, dokunus, sayi, kucuk olay. Genel gecer bos sozler tek basina yasak.
- Karakterin kendi sesi: mizahi, tipik sozu ("${dna.catchphrase}"), imza hareketi soze sinsin.
- Duygu yayi: merak -> keyif -> minik aksilik -> birlikte cozum -> kutlama. Nakarat yayin kalbi.
- hookNote: klibin biraktigi merak sorusu; curiosityScore ile puanla.
- Kafiye temiz, Turkce dogal aksan; zorlama kafiye yok.
- Nakarat mirildanilabilir sticky hook tasisin.

SOZ → EKRAN SOZLESMESI (KIRMIZI CIZGI — GERCEKLIK HİSSİ):
- Sozde SAYILAN, ISMI GECEN veya ISARET EDILEN her nesne/hayvan/tasit o klipte KADRODA olacak sekilde yaz. "Kac vagon? 1 2 3" diyorsan sozleri, o sahnede GERCEKTEN 3 vagon varken soylenecek gibi kur.
- Bos havaya sayma / hayali prop YASAK. Once prop'u sec, sonra sozu o prop uzerinden yaz.
- Her kitada 1-3 SOMUT prop sec (tema prop bankasindan); renk, malzeme, sayi soze sinsin ki gorsel yonetmen ayni seyi cizebilsin.
- Tema prop bankasi: ${theme?.propBank || "konuya ozel dokunulabilir prop'lar; sayilan nesneler dogru sayida"}

SURE VE PROZODI (KIRMIZI CIZGI — DAKIKA HEDEFI):
- HEDEF SURE = tam ${targetSeconds} saniye (~${(targetSeconds / 60).toFixed(1)} dk). Bu sureyi ${clipCount} klip × ${clipSeconds} sn ile doldur.
- clips.length ZORUNLU ${clipCount}; eksik/fazla klip YASAK. estimatedDurationSeconds = ${clipCount * clipSeconds}.
- formattedLyrics bu hedefin tamamini dolduracak uzunlukta olsun (kisa ozet sarki YASAK).
- Her klip ${clipSeconds} saniye. lyrics alani o klipte SOYLENECEK kelimelerdir; konusma metni DEGIL, sarki sozudur.
- Her klipte ${lineCountForClip(ageBand)} olsun; dizeleri satir sonu ile ayir.
- syllableCount ${minSyllables} ile ${maxSyllables} ARASINDA olsun. ${minSyllables} altina DUSME: klip bos ve ruhsuz kalir. ${maxSyllables} ustune de cikma: sozler klibe sigmaz.
- Sozler nefeste bitsin: klip bitmeden son hece tamamlansin. Yarim kelime, yarim kafiye yok.
- Nakarat kliplerinin lyrics'i birebir AYNI olsun (koreografi/enerji/kamera degisebilir).

TEMA YAPIM BRIEF'I (UYGULA — anlam once, sonra spark):
- DUYGUSAL VAAT (meaningPromise — KIRMIZI CIZGI): ${theme?.meaningPromise || "Sarkinin 1 cumlelik kalbi olsun; bos ritim oyunu yasak."}
- Kita yayi (verseArc — verse'ler BUNU ilerletsin): ${theme?.verseArc || "V1 vaadi sahneye koy; V2 kucuk aksilik; V3 ayni anlami sicak kapat."}
- Hook acisi: ${theme?.hookAngle || "Ilk 5 sn en akilda kalici cumleyi soyle; uzun isinma yok."}
- Oyun mekanigi: ${theme?.gameMechanic || "Tekrarli nakarat + somut prop oyunu."}
- YARATICI KIVILCIM (lyricSpark — buna uy, tohum listeyi ezberleme): ${theme?.lyricSpark || "Beklenmedik somut imge + sticky hook; ogretmen tonu yok."}
- Soz tohum kelimeleri (CESNI; listeyi dokme): ${theme?.lyricSeedWords || "somut, duyusal, yas-uygun kelimeler"}
- Aranjman ipucu: ${theme?.arrangementHint || "kids-safe major groove"}
- BPM rehberi (tema): ${theme?.bpmGuide || `${bpm.min}-${bpm.max}`}
- YASAK: uzuv/renk/gun/hayvan-sesi LISTESI olarak sarki yazmak. Her dizede bir HIS veya KUCUK OLAY olsun.

${ageCraftRules(ageBand)}

YAPI / SUREYE GORE YAY (UYULA — ACILIS + ORTA + KAPANIS):
${arcBlueprint}

MUZIK YONETMENLIGI:
- Stil: ${style ? `${style.label} (${style.tagline}) — ${style.prompt}` : "bright pop, major key, catchy chorus"}
- Groove (TR): ${style?.groove || "dans edilebilir, net nabiz"}
- Miks rengi (EN): ${style?.mixColor || "clean bright kids mix"}
- Gorsel sahneleme (stil ile uyumlu): ${style?.stagingHint || "props land on the beat; every named object is tangible"}
- TURUNE OZEL CANLI MV RITMI (EN beatVisuals): ${style?.beatVisuals || "body and props move on the beat; living background"}
- ${SONG_MV_LIVELINESS_LOCK}
- BPM ${bpm.min}-${bpm.max} araliginda, yas bandina uygun; tempo TUM sarki boyunca sabit
- KRITIK — instrumentation alani SOMUT bir aranjman tarifi olsun (INGILIZCE): 3-5 enstruman + davul/groove karakteri + CONTINUOUS audible bed under the vocal (kick/shaker/bass/pad as style requires — never a silent bed) + nakaratta eklenen katman. Bu tarif HER KLIBIN muzigine birebir islenecek; "cheerful music" gibi genel gecer yazma.
- Enstruman: cocuklara uygun. Distortion, trap 808, korku sting'i YASAK
- Ilk klip ilk saniyelerde hook'u soylesin
- vocalStyle: TEK kilitli sarki sesi tarifi (INGILIZCE) — tum kliplerde AYNI kalacak. Ornek: "warm clear mezzo, bright pop lead, crisp Turkish diction, gentle vibrato on sustained notes, never a thin cartoon squeak". Bu alan sarki boyunca DEGISTIRILMEZ.
- voiceTone alani INGILIZCE ve o dizeye ozel ENERJI notu olsun ("bright and bouncy, smiling tone", "soft and hushed, almost whispering") — ses kimligini DEGISTIRMEZ; ayni vocalStyle uzerinden sadece duygu/enerji.

GUVENLIK: Korkutucu, silah, karanlik, yalnizlik/terk edilme, ceza yok.

formattedLyrics: bolum baslikli tam soz metni (konusma dilinde) — secilen ${targetSeconds} sn sureyi doldurur; ilk bolum ACILIS, son bolum(ler) KAPANIS net okunsun.
clips.length ZORUNLU ${clipCount}. index 1..${clipCount} sirali.
Ilk klip section intro|hook; son 1-2 klip section outro (gerekirse bir onceki chorus + outro).
Bu adimda YALNIZCA sozler ve muzik yonetmenligi istenir; kamera/isik/sahne planlari SONRAKI adimda yazilacak.`,
    user: `Kanal: ${project.channelName || project.name}
Baslik: ${title || "(sen oner; title + titleTurkish doldur — poster gibi sticky bir baslik)"}
Istenen nakarat hook'u (Adim 3'te secildiyse birebir koru, yoksa basliktan turet): ${
      project.openingHook?.trim() || "(basliktan sticky hook turet)"
    }
Tema: ${theme ? `${theme.label} — ${theme.tagline}` : project.topic || project.moralLesson || "neseli cocuk sarkisi"}
Tema brief: ${theme?.description || "-"}
DUYGUSAL VAAT (sozler BUNU anlatsin): ${theme?.meaningPromise || "-"}
Kita yayi: ${theme?.verseArc || "-"}
Mood: ${theme?.moodHint || "-"}
Hook acisi: ${theme?.hookAngle || "-"}
Oyun mekanigi: ${theme?.gameMechanic || "-"}
YARATICI KIVILCIM (lyricSpark): ${theme?.lyricSpark || "-"}
Soz tohumlari (cesni): ${theme?.lyricSeedWords || "-"}
Prop bankasi (soz+ekran): ${theme?.propBank || project.topic || "somut, sayilabilir, dokunulabilir prop'lar"}
Muzik stili: ${style ? `${style.label} — ${style.tagline}` : "-"}
Stil groove: ${style?.groove || "-"}
Stil miks: ${style?.mixColor || "-"}
Muzik stili sahneleme: ${style?.stagingHint || "-"}
Ek konu notu: ${project.topic || "-"}
Yas bandi: ${ageBand}
Konusma/soz dili: ${project.speechLanguage}
HEDEF SURE (dakika kilidi): ${targetSeconds} saniye = ${(targetSeconds / 60).toFixed(1)} dk
Klip suresi: ${clipSeconds} saniye
ZORUNLU klip sayisi: ${clipCount} (tamami doldurulacak)
Klip basina hece: ${minSyllables}-${maxSyllables}
Karakter: ${dna.name} (${dna.species})
Kisilik: ${dna.personality.join(", ")}
Tipik soz: "${dna.catchphrase}"
Imza hareketi: ${dna.signatureGesture}
Sevdigi: ${dna.loves} · Cekindigi: ${dna.fears}
Ses: ${dna.voiceDescription}
Renk paleti: ${dna.colorPalette.join(", ")}
Istenmeyen: ${project.avoidList || "korku, siddet, karanlik, yetiskin mizahi"}

SUREYE GORE YAY OZETI (uygula):
${arcBlueprint}

${clipCount} kliplik / ${targetSeconds} sn (~${(targetSeconds / 60).toFixed(1)} dk) sarkinin SOZLERINI simdi yaz.
ANLAM ONCE: meaningPromise'i 1 cumlede koru; nakarat onu soylesin; verse'ler verseArc ile ilerlesin.
GERCEK SANATCI AGZI: yayinlanabilir kids-pop hit — dogal prosodi, sticky nakarat, siradisi imgeler, karakter sesi.
OGRETMEN CALISMASI DEGIL. ACILIS cold open + sticky hook; KAPANIS tatmin edici outro (ani kesme yok).
"Hadi yapalim / Simdi sayalim / Ayak tap tap burun tik tik" klişelerine DUSME.
Her soz hem ANLAM tasiin hem kadroda gosterilebilir somut bir sey tasişin.`,
    schemaName: "kids_song_lyrics",
    jsonSchema: LYRICS_JSON_SCHEMA,
    zodSchema: lyricsResultSchema,
    // Uzun sure (10–20 dk) + flagship reasoning: bol cikti butcesi
    maxOutputTokens: 32_000,
    reasoningEffort: songReasoning,
    timeoutMs: 600_000,
  });

  await recordEvent({
    projectId,
    step: "song",
    message: `Sozler hazir: "${lyricsResult.title}" (${lyricsResult.bpm} BPM) — 2/2: her klip icin gorsel yonetmenlik yaziliyor`,
  });

  const visualShots = await planVisualShotsInBatches({
    projectId,
    model: songModel,
    reasoningEffort: "low",
    schemaName: "kids_song_visuals",
    clips: lyricsResult.clips,
    clipSeconds,
    targetSeconds,
    variety,
    castPrompt: `${dna.name} (lead) — ${dna.species}\n${dna.imagePrompt.slice(0, 500)}`,
    leadName: dna.name,
    leadSpecies: dna.species,
    leadPersonality: dna.personality.join(", "),
    leadGesture: dna.signatureGesture,
    leadLoves: dna.loves,
    leadPalette: dna.colorPalette.join(", "),
    ageBand,
    avoidList: project.avoidList || "korku, siddet, karanlik, yetiskin mizahi",
    arcBlueprint,
    propBank: theme?.propBank || "somut prop'lar",
    stagingHint: style?.stagingHint || "props land on the beat; living background layers",
    meaningPromise: lyricsResult.hookLine,
    themeTitle: lyricsResult.titleTurkish || lyricsResult.title,
    themeSummary: `${lyricsResult.mood} · ${lyricsResult.instrumentation}`,
    hookLine: lyricsResult.hookLine,
    mood: lyricsResult.mood,
    bpmHint: `${lyricsResult.bpm} BPM · ${lyricsResult.musicalKey}`,
    styleLabel: style ? `${style.label} — ${style.prompt}` : variety.shotStylePhrase,
    shotStylePhrase: variety.shotStylePhrase,
    vocalStyle: lyricsResult.vocalStyle,
    beatVisuals: style?.beatVisuals,
  });

  // Iki cagrinin ciktisini tek pakette birlestir (indeks uzerinden esle)
  const shotByIndex = new Map(visualShots.map((s) => [s.index, s]));
  const result: SongPackage = {
    ...lyricsResult,
    estimatedDurationSeconds: clipCount * clipSeconds,
    clips: lyricsResult.clips.map((clip) => {
      const shot = shotByIndex.get(clip.index);
      const accent = clipVarietyAccent(variety, clip.index);
      return {
        ...clip,
        sceneDescription: shot?.sceneDescription || clip.lyrics.split("\n")[0].slice(0, 90),
        imagePrompt:
          shot?.imagePrompt ||
          fallbackShotPrompt(variety, {
            name: dna.name,
            species: dna.species,
            lyrics: clip.lyrics.replace(/\n/g, " "),
            clipIndex: clip.index,
          }),
        choreography: shot?.choreography || accent.choreoTr,
        environment: shot?.environment || variety.world.prompt,
        lighting: shot?.lighting || `${variety.lighting.prompt}; ${accent.lightingAccent}`,
        cameraShot: shot?.cameraShot || accent.camera,
        motionDetail: shot?.motionDetail || variety.materialLanguage,
        microExpression: shot?.microExpression ?? "",
        mustShowProps: shot?.mustShowProps ?? "",
        lyricSyncAction: shot?.lyricSyncAction ?? "",
        secondBySecond: shot?.secondBySecond ?? "",
        weatherTimeOfDay: shot?.weatherTimeOfDay || variety.weather,
        exteriorWorld: shot?.exteriorWorld || variety.exteriorWorld,
        singerName: shot?.singerName || dna.name,
      };
    }),
  };

  if (result.clips.length !== clipCount) {
    // Model saparsa kirp / fazla ise kes; az ise yine kaydet ama uyar.
    result.clips = result.clips
      .sort((a, b) => a.index - b.index)
      .slice(0, clipCount)
      .map((clip, i) => ({ ...clip, index: i + 1 }));
  }

  result.estimatedDurationSeconds = clipCount * clipSeconds;

  await persistSong(projectId, project, result);
  await prisma.project.update({
    where: { id: projectId },
    data: {
      title: title || result.title,
      emotionCurve: JSON.stringify({
        kind: "song",
        bpm: result.bpm,
        key: result.musicalKey,
        mood: result.mood,
        instrumentation: result.instrumentation,
        vocalStyle: result.vocalStyle,
        hookLine: result.hookLine,
        styleId: style?.id || project.narrationStyle || "",
        beatVisuals: style?.beatVisuals || "",
        groove: style?.groove || "",
        varietySeed: variety.seed,
        varietyPackId: variety.packId,
      }),
      status: "story_ready",
    },
  });
  publishEvent(projectId, { type: "project", payload: { id: projectId, status: "story_ready" } });
  await recordEvent({
    projectId,
    step: "song",
    message: `"${result.title}" yazildi — ${result.clips.length} klip, ${result.bpm} BPM, ${result.musicalKey}`,
  });
  return result;
}

export async function saveSongPackage(projectId: string, song: SongPackage): Promise<SongPackage> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const validated = songPackageSchema.parse(song);
  const style = styleFor(project);
  const variety = resolveSongVarietyPack(project);
  await persistSong(projectId, project, validated);
  await prisma.project.update({
    where: { id: projectId },
    data: {
      title: project.title || validated.title,
      emotionCurve: JSON.stringify({
        kind: "song",
        bpm: validated.bpm,
        key: validated.musicalKey,
        mood: validated.mood,
        instrumentation: validated.instrumentation,
        vocalStyle: validated.vocalStyle,
        hookLine: validated.hookLine,
        styleId: style?.id || project.narrationStyle || "",
        beatVisuals: style?.beatVisuals || "",
        groove: style?.groove || "",
        varietySeed: variety.seed,
        varietyPackId: variety.packId,
      }),
    },
  });
  return validated;
}

export async function loadSongPackage(projectId: string): Promise<SongPackage | null> {
  const story = await prisma.story.findUnique({
    where: { projectId_languageVariant: { projectId, languageVariant: "primary" } },
  });
  return parseSongPackage(story?.characterVoiceNotes);
}

/**
 * Klibin gorsel katmanlarini TEK, temiz, profesyonel bir Ingilizce yonetmen
 * brief'ine cevirir. Kurallar:
 * - Soz metni promptta YALNIZCA BIR KEZ tirnaklanir (lip-sync icin);
 *   baska hicbir yerde alintilanmaz — Veo tirnakli metni ekrana yazi olarak
 *   basabildigi icin geri kalan her sey Ingilizce gorsel tariftir.
 * - Dunya kilidi: soz "ormanda" diyorsa set ORMAN olur, asla dag/sehir olmaz.
 * - Her saniye sozle uyumlu bir gorsel beat alir (tirnaksiz timeline).
 */
export function composeShotPrompt(
  clip: z.infer<typeof songClipSchema>,
  clipSeconds = 8,
  variety?: SongVarietyPack,
  worldLock?: SongWorldLock | null,
  heroProp?: HeroSubject | null
): string {
  const lyrics = clip.lyrics.replace(/\s+/g, " ").trim();
  const seconds = Math.max(4, Math.min(20, Math.round(clipSeconds) || 8));
  const singer = clip.singerName?.trim() || "the lead singer";
  const world = worldLock !== undefined ? worldLock : detectSongWorld(lyrics);
  const hero = heroProp !== undefined ? heroProp : detectHeroSubject(lyrics);
  const heroNamed = lyricsNameHero(lyrics, hero ?? null);
  const heroLine = hero
    ? [
        `HERO WITH LEAD (NON-NEGOTIABLE): ${hero.visible}`,
        `${singer} shares EVERY frame with this ${hero.label} — hold it, point to it, swim/play beside it, or dance with it.`,
        heroNamed
          ? "This line NAMES it — center stage now, big in frame, sharp focus."
          : "This line may not name it — still keep it clearly on screen with the lead (foreground or in a paw), never off-screen.",
        `FAIL if the ${hero.label} is missing, tiny in the far background, or replaced by a generic prop.`,
      ].join(" ")
    : "";

  const stagingRaw = formatLyricStagingLine(lyrics, (clip.mustShowProps || "").replace(/["“”']/g, ""));
  // Kahraman staging'te ONCE yazilir; 200 karakter kirpmasi baligi yutmasin.
  const staging = (
    hero ? `${hero.label} with the lead (large, readable); ${stagingRaw}` : stagingRaw
  ).slice(0, hero ? 260 : 200);
  const sync = (clip.lyricSyncAction || "")
    .replace(/\s+/g, " ")
    .replace(/["“”']/g, "")
    .trim()
    .slice(0, 140);
  const shot = clip.imagePrompt
    .replace(/\s+/g, " ")
    .replace(/^while\s+singing\s*:\s*/i, "")
    .replace(/["“”']/g, "")
    .trim()
    .slice(0, 240);

  const timeline = buildLyricActionTimeline({
    lyrics,
    seconds,
    isFirstClip: clip.index === 1,
    choreography: clip.choreography,
    coldOpen: variety?.coldOpen,
    handoff: variety?.handoff,
  });

  const spokenNote = isSpokenOrTalkSing(lyrics)
    ? " The line includes spoken / talk-sing words — act them straight to camera or to a friend (a wave, a come-on gesture, a look-and-listen beat), not a generic dance."
    : "";

  const envRaw = (clip.environment || "").replace(/\s+/g, " ").trim().slice(0, 120);
  const env = environmentConflictsWorld(envRaw, world ?? null) ? "" : envRaw;
  const extRaw = (clip.exteriorWorld || "").replace(/\s+/g, " ").trim().slice(0, 120);
  const ext = environmentConflictsWorld(extRaw, world ?? null) ? "" : extRaw;

  // SET erken: Flow 8k limitinde kuyruk kirpilirsa set/dunya dusmesin.
  const setLine = world
    ? `SET (locked for the WHOLE song): ${world.positive}. NEVER show: ${world.never} — unless this clip's sung line explicitly names them.${env ? ` This clip's corner of that world: ${env}` : ""}`
    : env
      ? `SET: ${env}`
      : "";

  const craft = hero
    ? `CRAFT: three depth layers — ${hero.label} + lead together in front/mid with contact shadows, living background on the beat; never a static portrait, empty void, or hero-free frame.`
    : "CRAFT: three depth layers — tactile props front, singer mid with contact shadow, living background on the beat; never a static portrait or empty void.";

  return [
    `SONG LINE THIS CLIP (Turkish, pre-recorded on the master track): "${lyrics}"`,
    `Those words are HEARD only — never written into the picture. ${singer} performs them with clear singing visemes matching every syllable, joyful face acting, timed to the beat.${spokenNote}`,
    setLine,
    ext ? `WORLD DEPTH: ${ext}` : "",
    clip.weatherTimeOfDay?.trim()
      ? `TIME OF DAY / WEATHER (locked for the whole song): ${clip.weatherTimeOfDay.trim().slice(0, 100)}`
      : "",
    heroLine,
    sync ? `SYNC ACTION: ${sync}` : "",
    `STAGE EVERY SUNG WORD (all visible in THIS clip): ${staging}.`,
    shot ? `SHOT PLAN: ${shot}` : "",
    `ACTION TIMELINE 0-${seconds}s (one continuous take):\n${timeline}`,
    clip.cameraShot?.trim() ? `CAMERA: ${clip.cameraShot.trim().slice(0, 100)}` : "",
    clip.lighting?.trim() ? `LIGHTING: ${clip.lighting.trim().slice(0, 100)}` : "",
    clip.microExpression?.trim() ? `FACE ACTING: ${clip.microExpression.trim().slice(0, 80)}` : "",
    clip.motionDetail?.trim() ? `SECONDARY MOTION: ${clip.motionDetail.trim().slice(0, 80)}` : "",
    // NOT: look pack kilidi burada TEKRARLANMAZ — nihai promptun [STYLE]
    // blogu onu bir kez yazar. Ikisi birden yazilinca ayni paragraf promptta
    // iki kez yer kapliyor ve limit asilinca [STYLE] tamamen kesiliyordu.
    craft,
  ]
    .filter(Boolean)
    .join("\n");
}

/** Kayitli sarkidan Clip satirlari olusturur; sozler diyalog alanina yazilir. */
export async function buildSongClips(projectId: string, songOverride?: SongPackage): Promise<{ clipCount: number }> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const song = songOverride ? songPackageSchema.parse(songOverride) : await loadSongPackage(projectId);
  if (!song) throw new Error("Once sarkiyi yazdirin");

  const completedCount = await prisma.clip.count({ where: { projectId, languageVariant: "primary", status: "completed" } });
  if (completedCount > 0) {
    throw new Error(`${completedCount} klip zaten uretilmis. Yeniden sahneleme tamamlanan klipleri gecersiz kilar.`);
  }

  if (songOverride) await saveSongPackage(projectId, song);

  await prisma.clip.deleteMany({ where: { projectId, languageVariant: "primary" } });
  const characters = await prisma.characterProfile.findMany({ where: { projectId } });
  const sorted = [...song.clips].sort((a, b) => a.index - b.index);
  const settings = await loadSongSettings(projectId);
  const audioDuration = settings.audioDurationSeconds || project.targetDurationSeconds;
  const clipSeconds = project.clipSeconds || 8;
  const variety = resolveSongVarietyPack(project);
  // Dunya kilidi TUM sarkidan tespit edilir: "ormanda" gecen sarki bastan sona ormanda cekilir.
  const worldLock = detectSongWorld(
    [sorted.map((c) => c.lyrics).join(" "), project.topic || "", project.title || ""].join(" ")
  );
  // Kahraman nesne: sarki bir nesne hakkindaysa (salatalik, domates, balon...)
  // o nesne HER klipte gorunur — adinin gectigi satirlarda sahnenin merkezine alinir.
  const heroProp = detectHeroSubject(
    [sorted.map((c) => c.lyrics).join("\n"), project.topic || "", project.title || ""].join("\n"),
    [project.title || "", project.name || ""].join(" ")
  );
  if (heroProp) {
    await recordEvent({
      projectId,
      step: "song",
      message: `Kahraman nesne kilitlendi: "${heroProp.surface}" (${heroProp.label}) — tum kliplerde on planda tutulacak`,
    });
  }
  for (let i = 0; i < sorted.length; i++) {
    const clip = sorted[i];
    const words = clip.lyrics.trim().split(/\s+/).filter(Boolean).length;
    const characterId = resolveCharacterIdByName(characters, clip.singerName);
    const window = songClipAudioWindow({
      index: i + 1,
      clipCount: sorted.length,
      clipSeconds,
      audioDurationSeconds: audioDuration,
    });
    // sceneDescription panelde okunur (Turkce); imagePrompt prompta girer (Ingilizce).
    await prisma.clip.create({
      data: {
        projectId,
        languageVariant: "primary",
        index: i + 1,
        characterId,
        dialogue: clip.lyrics.trim(),
        sceneDescription: `${clip.section.toUpperCase()} · ${window.startSeconds.toFixed(1)}–${window.endSeconds.toFixed(1)}s · ${clip.sceneDescription} ${clip.choreography}`.trim(),
        imagePrompt: composeShotPrompt(
          clip,
          window.durationSeconds > clipSeconds - 0.3 ? clipSeconds : Math.ceil(window.durationSeconds),
          variety,
          worldLock,
          heroProp
        ),
        emotionLabel: clip.emotion,
        curiosityScore: Math.round(clip.curiosityScore),
        hasHook: clip.hookNote.trim().length > 0,
        voiceTone: clip.voiceTone,
        estimatedWords: words,
        estimatedDurationSeconds: window.durationSeconds,
        status: "draft",
      },
    });
  }

  await prisma.project.update({ where: { id: projectId }, data: { status: "clips_ready" } });
  publishEvent(projectId, { type: "project", payload: { id: projectId, status: "clips_ready" } });
  await recordEvent({ projectId, step: "song", message: `${sorted.length} sarki klibi olusturuldu` });
  await reportCuriosityFlow(projectId);
  const { buildPromptsForProject } = await import("@/server/services/clips");
  await buildPromptsForProject(projectId);
  return { clipCount: sorted.length };
}

const SECTION_ORDER = ["intro", "hook", "verse", "prechorus", "chorus", "bridge", "outro"] as const;
type SongSection = (typeof SECTION_ORDER)[number];

function guessSection(index: number, total: number): SongSection {
  if (index === 1) return "intro";
  if (index >= total) return "outro";
  if (index === 2) return "hook";
  if (index % 3 === 0) return "chorus";
  return "verse";
}

function estimateSyllables(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean);
  return Math.max(4, words.reduce((sum, w) => sum + Math.max(1, Math.round(w.replace(/[^a-zA-ZçğıöşüÇĞİÖŞÜ]/g, "").length / 2.5)), 0));
}

/** Uzun bir soz satirini soyleme kaliplarina (nida/virgul) boler. */
function splitLyricLineIntoPhrases(line: string): string[] {
  const parts = line
    .split(/(?<=[!?])\s+|\s*[/|]\s*|,\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return parts.length > 1 ? parts : [line];
}

/** Satir sayisi klip sayisindan azsa, uzun satirlari bolerek birim uretir. */
function expandLyricUnits(lines: string[], count: number): string[] {
  const units = [...lines];
  while (units.length < count) {
    let target = -1;
    let longest = 0;
    for (let i = 0; i < units.length; i++) {
      const unit = units[i]!;
      if (splitLyricLineIntoPhrases(unit).length > 1 && unit.length > longest) {
        longest = unit.length;
        target = i;
      }
    }
    if (target < 0) break;
    units.splice(target, 1, ...splitLyricLineIntoPhrases(units[target]!));
  }
  return units;
}

/** Kaba soyleme agirligi: Turkce'de hece sayisi ~ sesli harf sayisi. */
function lyricLineWeight(line: string): number {
  const vowels = line.toLocaleLowerCase("tr-TR").match(/[aeıioöuüâîû]/g);
  return Math.max(1, vowels?.length ?? 1);
}

/**
 * Noktalama tasimayan uzun satiri kelime sinirindan ikiye boler.
 * Sarkida klip siniri zaten dizenin ortasina denk gelebilir; onemli olan
 * klibin soyleme butcesini asmamasidir.
 */
function splitLyricLineByWords(line: string): string[] {
  const words = line.split(/\s+/).filter(Boolean);
  if (words.length < 4) return [line];
  const mid = Math.ceil(words.length / 2);
  return [words.slice(0, mid).join(" "), words.slice(mid).join(" ")];
}

/** Once nida/virgul, olmazsa kelime sinirindan bolme dener. */
function splitOverweightLyricUnit(line: string): string[] {
  const phrases = splitLyricLineIntoPhrases(line);
  if (phrases.length > 1) return phrases;
  return splitLyricLineByWords(line);
}

/**
 * Soz satirlarini kliplere DENGELI dagitir — SATIR SAYISINA degil, SOYLEME
 * AGIRLIGINA (hece) gore.
 *
 * Neden: satir uzunluklari cok farklidir. Esit satir sayisi dagitirsan bir klip
 * 14 heceyle bos kalirken digeri 40 heceyle tasar ("cumle video bitmeden
 * tamamlanamaz" uyarisi). Hece esasli dagitimda her klip ~ayni miktarda soz
 * alir: ne bosluk ne tasma.
 *
 * Ek onlem: tek basina klip butcesini asan uzun satirlar once nida/virgul
 * sinirlarindan cumlelere bolunur.
 */
export function distributeLyricLines(lines: string[], clipCount: number): string[][] {
  const count = Math.max(1, clipCount);
  let units = lines.length >= count ? [...lines] : expandLyricUnits(lines, count);

  const totalWeight = () => units.reduce((sum, u) => sum + lyricLineWeight(u), 0);

  // Butceyi asan birimleri bol (tasmayi kaynaginda onler)
  for (let guard = 0; guard < 80; guard++) {
    const budget = totalWeight() / count;
    const idx = units.findIndex(
      (u) => lyricLineWeight(u) > budget * 1.2 && splitOverweightLyricUnit(u).length > 1
    );
    if (idx < 0) break;
    units.splice(idx, 1, ...splitOverweightLyricUnit(units[idx]!));
  }

  // Birim sayisi klipten az: tekrarlar sona yigilmasin. Once sirayi koru,
  // fazla klipleri son nakarat penceresinde dondur (tek dizeyi 4 kez yapistirma).
  if (units.length < count) {
    const out: string[][] = units.map((unit) => [unit]);
    const extra = count - units.length;
    const windowSize = Math.min(units.length, Math.max(3, Math.ceil(units.length / 3)));
    const window = units.slice(-windowSize);
    for (let i = 0; i < extra; i++) out.push([window[i % window.length]!]);
    return out;
  }

  // Agirlik esasli sirali dagitim; her klip en az bir birim alir.
  const out: string[][] = [];
  let cursor = 0;
  let remainingWeight = totalWeight();
  for (let clip = 0; clip < count; clip++) {
    const clipsLeft = count - clip;
    const unitsLeft = units.length - cursor;
    if (clipsLeft === 1) {
      out.push(units.slice(cursor));
      cursor = units.length;
      break;
    }
    // Her klibe en az 1 birim kalmasi icin ust sinir
    const maxTake = unitsLeft - (clipsLeft - 1);
    const budget = remainingWeight / clipsLeft;
    const slice: string[] = [];
    let acc = 0;
    while (slice.length < maxTake) {
      const next = units[cursor]!;
      const w = lyricLineWeight(next);
      // EN IYI UYUM: birimi eklemek butceye YAKLASTIRIYORSA ekle, uzaklastiriyorsa
      // birak. Duz "asarsa dur" kurali, siradaki birim cok agir oldugunda klibi
      // yari bos birakiyordu.
      if (slice.length > 0 && Math.abs(acc + w - budget) >= Math.abs(acc - budget)) break;
      slice.push(next);
      acc += w;
      cursor++;
    }
    remainingWeight -= acc;
    out.push(slice);
  }
  return out;
}

/** Tam söz metnini klip sayisina bol — Suno veya manuel yukleme sonrasi. */
export function segmentLyricsForClips(
  formattedLyrics: string,
  clipCount: number,
  ageBand: string
): Array<{ index: number; section: SongSection; lyrics: string; syllableCount: number }> {
  const rawLines = formattedLyrics
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !/^[\[\(].*[\]\)]$/.test(line));

  const lines =
    rawLines.length > 0
      ? rawLines
      : formattedLyrics
          .split(/(?<=[.!?])\s+/)
          .map((s) => s.trim())
          .filter(Boolean);

  if (lines.length === 0) throw new Error("Soz metni okunamadi — once parca veya soz ekleyin");

  const count = Math.max(1, clipCount);
  const clips: Array<{ index: number; section: SongSection; lyrics: string; syllableCount: number }> = [];
  const distribution = distributeLyricLines(lines, count);

  for (let i = 0; i < count; i++) {
    const slice = distribution[i] ?? [];
    if (slice.length === 0) continue;
    const lyrics = slice.join("\n");
    clips.push({
      index: clips.length + 1,
      section: guessSection(clips.length + 1, count),
      lyrics,
      syllableCount: Math.min(
        syllableBudgetForClip(ageBand, 8),
        Math.max(syllableFloorForClip(ageBand, 8), estimateSyllables(lyrics))
      ),
    });
  }

  return clips;
}

const sunoLyricsSchema = z.object({
  title: z.string().min(1),
  titleTurkish: z.string().min(1),
  hookLine: z.string().min(1),
  formattedLyrics: z.string().min(40),
});

const SUNO_LYRICS_JSON_SCHEMA = {
  type: "object" as const,
  properties: {
    title: { type: "string" },
    titleTurkish: { type: "string" },
    hookLine: { type: "string" },
    formattedLyrics: { type: "string", description: "Full song lyrics with [Verse]/[Chorus] headers in speech language" },
  },
  required: ["title", "titleTurkish", "hookLine", "formattedLyrics"],
  additionalProperties: false,
};

export type SunoLyricsPackage = z.infer<typeof sunoLyricsSchema>;

/** Suno icin yalnizca soz metni uretir (tema catalogu yok — konu opsiyonel). */
export async function composeLyricsForSuno(
  projectId: string,
  input: {
    ageBand?: string;
    targetDurationSeconds?: number;
    topic?: string;
    title?: string;
    styleId?: string;
    language?: string;
  }
): Promise<SunoLyricsPackage> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");

  const ageBand = input.ageBand || project.ageBand || "3-5";
  const targetSeconds = Math.max(30, Math.min(1200, input.targetDurationSeconds || project.targetDurationSeconds || 90));
  const styleId = input.styleId || project.narrationStyle || "kidspop";
  const style = SONG_STYLES.find((s) => s.id === styleId) ?? SONG_STYLES[0];
  const language = input.language || project.speechLanguage || "Turkish";
  const topic = (input.topic || project.topic || "").trim();
  const topicHint = topic || "Yas bandina uygun neşeli, yaratıcı, somut imgeli bir konu sen sec";
  const bpm = recommendedBpm(ageBand, style.id);
  const minutes = (targetSeconds / 60).toFixed(1);

  if (input.ageBand || input.targetDurationSeconds || input.topic || input.styleId) {
    await prisma.project.update({
      where: { id: projectId },
      data: {
        ageBand: input.ageBand ?? project.ageBand,
        targetDurationSeconds: targetSeconds,
        topic: input.topic ?? project.topic,
        narrationStyle: styleId,
        title: input.title?.trim() || project.title,
      },
    });
  }

  const { model, reasoningEffort } = await resolvePublishAiModel();

  await recordEvent({
    projectId,
    step: "song",
    message: `Suno soz yazimi: ${ageBand} yas, ${minutes} dk${topic ? `, "${topic.slice(0, 40)}"` : ""}`,
  });

  const result = await structuredCall({
    model,
    system: `Sen cocuk sarkisi soz yazarisin. GOREV: Suno API'ye verilecek TAM sarki sozlerini yaz.

HEDEF: ${ageBand} yas cocuklar icin ${targetSeconds} saniye (~${minutes} dk) surecek, ${language} dilinde, soylenebilir profesyonel cocuk sarkisi.
Muzik stili: ${style.label} — ${style.prompt}

${SONG_LYRIC_CRAFT_LOCK}
${SONG_OPENING_CLOSING_CRAFT}
${ageCraftRules(ageBand)}

KURALLAR:
- formattedLyrics: [Intro]/[Verse]/[Chorus]/[Outro] basliklari ile tam metin; ${language} dilinde.
- Sure ${targetSeconds} sn'yi dolduracak kadar uzun olsun (kisa ozet YASAK).
- Nakarat sticky ve tekrarlanabilir; ilk 5 sn'de hook.
- Somut imgeler, sayilar, prop'lar kullan — gorsel yonetmen sozlerden sahne cizecek.
- Cocuklara uygun; korku/siddet yok.
- Ogretmen emri / "simdi soyle" kalibi YASAK — sahne ve duygu ile yaz.`,
    user: `Konu (bos ise yaratıcı sec): ${topicHint}
Baslik onerisi: ${input.title?.trim() || project.title || "(sen uret)"}
BPM araligi: ${bpm.min}-${bpm.max}`,
    jsonSchema: SUNO_LYRICS_JSON_SCHEMA,
    zodSchema: sunoLyricsSchema,
    schemaName: "suno_lyrics_compose",
    maxOutputTokens: 16_000,
    reasoningEffort,
    timeoutMs: 300_000,
  });

  await updateSongSettings(projectId, {
    formattedLyrics: result.formattedLyrics,
    lyricsSource: "manual",
  });

  if (result.titleTurkish || result.title) {
    await prisma.project.update({
      where: { id: projectId },
      data: {
        title: result.titleTurkish || result.title,
        openingHook: result.hookLine,
      },
    });
  }

  await recordEvent({ projectId, step: "song", message: `Suno sozleri hazir: "${result.titleTurkish || result.title}"` });
  return result;
}

const lyricsContextSchema = z.object({
  themeTitle: z.string().min(2),
  themeSummary: z.string().min(20),
  meaningPromise: z.string().min(10),
  mood: z.string().min(2),
  propBank: z.string().min(20),
  hookLine: z.string().min(4),
  verseArc: z.string().min(10),
  stagingHint: z.string().min(10),
});

type LyricsProductionContext = z.infer<typeof lyricsContextSchema>;

const LYRICS_CONTEXT_JSON_SCHEMA = {
  type: "object" as const,
  properties: {
    themeTitle: { type: "string" },
    themeSummary: { type: "string" },
    meaningPromise: { type: "string" },
    mood: { type: "string" },
    propBank: { type: "string" },
    hookLine: { type: "string" },
    verseArc: { type: "string" },
    stagingHint: { type: "string" },
  },
  required: ["themeTitle", "themeSummary", "meaningPromise", "mood", "propBank", "hookLine", "verseArc", "stagingHint"],
  additionalProperties: false,
};

/** Soz metninden tema + MV uretim brief'i cikarir (catalog tema secimi yok). */
export async function analyzeLyricsForProduction(
  formattedLyrics: string,
  project: Project,
  ageBand: string,
  model: string,
  reasoningEffort: "low" | "medium" | "high" | undefined
): Promise<LyricsProductionContext> {
  return structuredCall({
    model,
    system: `Sen cocuk sarki muzik videosu yapim brief analistisin.
GOREV: Verilen TAM sarki sozlerinden tema, duygusal vaat, prop bankasi ve sahneleme brief'i cikar.
Sozler TEK kaynak — hazir tema katalogu veya dis brief kullanma.

Cikti alanlari:
- themeTitle: 2-6 kelimelik poster basligi
- themeSummary: 1-2 cumle konu ozeti
- meaningPromise: sarkinin 1 cumlelik kalbi
- mood: Ingilizce mood etiketi
- propBank: sozlerde gecen TUM somut nesne/hayvan/tasit/renk/sayi envanteri (Ingilizce, sayi+materyal)
- hookLine: en sticky nakarat cumlesi
- verseArc: kitelerin anlam yayi (Turkce, kisa)
- stagingHint: MV sahneleme ipucu (Ingilizce, beat'e oturan prop hareketi)

${formatLyricsContextVarietyHint(resolveSongVarietyPack(project))}`,
    user: `Yas bandi: ${ageBand}
Dil: ${project.speechLanguage}

SOZLER:
${formattedLyrics.slice(0, 14_000)}`,
    schemaName: "lyrics_production_context",
    jsonSchema: LYRICS_CONTEXT_JSON_SCHEMA,
    zodSchema: lyricsContextSchema,
    maxOutputTokens: 4_000,
    reasoningEffort,
    timeoutMs: 120_000,
  });
}

/**
 * Suno/manuel parcadan gelen sozleri kliple eslestirir + gorsel plan uretir.
 * OpenAI tam sarki yazmaz; yalnizca segmentasyon sonrasi MV sahnelerini planlar.
 */
export async function syncSongClips(
  projectId: string,
  lyricsOverride?: string
): Promise<{ clipCount: number; song: SongPackage }> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki klibi");
  const settings = await loadSongSettings(projectId);
  if (!songHasMasterAudio(settings)) throw new Error("Once master parcayi (WAV/FLAC veya MP3) yukleyin");

  const formattedLyrics = (lyricsOverride || settings.formattedLyrics || "").trim();
  if (!formattedLyrics) throw new Error("Soz metni yok — Suno prompt veya manuel soz girin");

  if (lyricsOverride) {
    await updateSongSettings(projectId, { formattedLyrics, lyricsSource: "manual" });
  }

  const clipSeconds = project.clipSeconds || 8;
  const audioDuration = settings.audioDurationSeconds || project.targetDurationSeconds;
  // Yukari yuvarla: parcanin son saniyeleri de bir klibe dusmeli (bosluk olmasin).
  const clipCount = songClipCountForAudio(audioDuration, clipSeconds);
  const ageBand = project.ageBand || "3-5";
  const style = styleFor(project);
  const bpm = recommendedBpm(ageBand, style?.id || "kidspop");
  const title = project.title || project.name;
  const targetSeconds = Math.round(audioDuration);
  const arcBlueprint = structureForDuration(targetSeconds, clipCount, clipSeconds);
  const { model: songModel, reasoningEffort: songReasoning } = await resolveSongPlannerAi();

  const lyricClips = segmentLyricsForClips(formattedLyrics, clipCount, ageBand);
  const variety = resolveSongVarietyPack(project);
  await updateSongSettings(projectId, { varietySeed: variety.seed });

  await recordEvent({
    projectId,
    step: "song",
    message: `Soz analizi: tema + prop bankasi cikariliyor · look pack ${variety.packId}`,
  });

  const lyricsContext = await analyzeLyricsForProduction(formattedLyrics, project, ageBand, songModel, songReasoning);

  await recordEvent({
    projectId,
    step: "song",
    message: `Soz analizi: kadro kontrol ediliyor`,
  });

  let castProfiles = await listSongCast(projectId);
  const castReady = castProfiles.some((c) => c.name.trim() && c.dnaCard && c.dnaCard !== "{}");

  if (castReady) {
    await recordEvent({
      projectId,
      step: "song",
      message: `Mevcut sabit kadro kullaniliyor (${castProfiles.length} karakter)`,
    });
  } else {
    const castAnalysis = await analyzeCastFromLyrics(
      formattedLyrics,
      project,
      ageBand,
      lyricsContext.themeSummary,
      songModel,
      songReasoning
    );
    castProfiles = await persistSongCast(projectId, castAnalysis.members);
    await recordEvent({
      projectId,
      step: "song",
      message: `Kadro: ${castAnalysis.castCount} karakter — ${castAnalysis.rationale.slice(0, 120)}`,
    });
  }

  const castPrompt = formatCastForVisualsPrompt(castProfiles);
  const lead = castProfiles.find((c) => c.role === "main") ?? castProfiles[0]!;
  let leadDna: DnaCard;
  try {
    leadDna = JSON.parse(lead.dnaCard) as DnaCard;
  } catch {
    const { buildSongDnaCardFromProfile } = await import("@/lib/song-character");
    leadDna = buildSongDnaCardFromProfile(lead, project);
  }

  await prisma.project.update({
    where: { id: projectId },
    data: {
      title: project.title || lyricsContext.themeTitle,
      topic: lyricsContext.themeSummary,
      moralLesson: lyricsContext.themeTitle,
      openingHook: lyricsContext.hookLine,
    },
  });

  await recordEvent({
    projectId,
    step: "song",
    message: `Soz→klip eslestirme: ${lyricClips.length} klip (${audioDuration.toFixed(1)} sn) · tema: "${lyricsContext.themeTitle}"`,
  });

  const visualShots = await planVisualShotsInBatches({
    projectId,
    model: songModel,
    reasoningEffort: songReasoning,
    schemaName: "kids_song_visuals_sync",
    clips: lyricClips,
    clipSeconds,
    targetSeconds,
    variety,
    castPrompt,
    leadName: leadDna.name,
    leadSpecies: leadDna.species,
    leadPersonality: leadDna.personality.join(", "),
    leadGesture: leadDna.signatureGesture,
    leadLoves: leadDna.loves,
    leadPalette: leadDna.colorPalette.join(", "),
    ageBand,
    avoidList: project.avoidList || "korku, siddet, karanlik, yetiskin mizahi",
    arcBlueprint,
    propBank: lyricsContext.propBank,
    stagingHint: style?.stagingHint || lyricsContext.stagingHint,
    meaningPromise: lyricsContext.meaningPromise,
    themeTitle: lyricsContext.themeTitle,
    themeSummary: lyricsContext.themeSummary,
    hookLine: lyricsContext.hookLine,
    mood: lyricsContext.mood,
    bpmHint: `BPM ~${Math.round((bpm.min + bpm.max) / 2)}`,
    styleLabel: style ? `${style.label} — ${style.prompt}` : variety.shotStylePhrase,
    shotStylePhrase: variety.shotStylePhrase,
    beatVisuals: style?.beatVisuals,
  });

  const shotByIndex = new Map(visualShots.map((s) => [s.index, s]));
  const baseClips = lyricClips.map((clip) => {
    const shot = shotByIndex.get(clip.index);
    const accent = clipVarietyAccent(variety, clip.index);
    return {
      index: clip.index,
      section: clip.section,
      lyrics: clip.lyrics,
      syllableCount: clip.syllableCount,
      emotion: accent.emotion,
      voiceTone: accent.voiceTone,
      hookNote: "",
      curiosityScore: 5,
      sceneDescription: shot?.sceneDescription || clip.lyrics.split("\n")[0].slice(0, 90),
      imagePrompt:
        shot?.imagePrompt ||
        fallbackShotPrompt(variety, {
          name: leadDna.name,
          species: leadDna.species,
          lyrics: clip.lyrics.replace(/\n/g, " "),
          clipIndex: clip.index,
        }),
      choreography: shot?.choreography || accent.choreoTr,
      environment: shot?.environment || variety.world.prompt,
      lighting: shot?.lighting || `${variety.lighting.prompt}; ${accent.lightingAccent}`,
      cameraShot: shot?.cameraShot || accent.camera,
      motionDetail: shot?.motionDetail || variety.materialLanguage,
      microExpression: shot?.microExpression ?? "",
      mustShowProps: shot?.mustShowProps ?? "",
      lyricSyncAction: shot?.lyricSyncAction ?? "",
      secondBySecond: shot?.secondBySecond ?? "",
      weatherTimeOfDay: shot?.weatherTimeOfDay || variety.weather,
      exteriorWorld: shot?.exteriorWorld || variety.exteriorWorld,
      singerName: shot?.singerName || leadDna.name,
    };
  });

  const song: SongPackage = {
    title,
    titleTurkish: title,
    hookLine: lyricsContext.hookLine || project.openingHook || lyricClips[0]?.lyrics.split("\n")[0] || title,
    bpm: Math.round((bpm.min + bpm.max) / 2),
    musicalKey: "C major",
    mood: lyricsContext.mood,
    instrumentation: style?.prompt?.slice(0, 200) || "bright kids pop arrangement",
    vocalStyle: "warm clear kids pop lead vocal, crisp diction",
    rhymeScheme: "AABB",
    estimatedDurationSeconds: Math.round(audioDuration),
    formattedLyrics,
    clips: baseClips,
  };

  await persistSong(projectId, project, song);
  await prisma.project.update({
    where: { id: projectId },
    data: {
      targetDurationSeconds: Math.max(20, Math.round(audioDuration)),
      audioEnabled: false,
      emotionCurve: JSON.stringify({
        kind: "song",
        bpm: song.bpm,
        mood: song.mood,
        vocalStyle: song.vocalStyle,
        hookLine: song.hookLine,
        styleId: style?.id || project.narrationStyle || "",
        musicSource: settings.musicSource,
        varietySeed: variety.seed,
        varietyPackId: variety.packId,
      }),
    },
  });

  const { clipCount: built } = await buildSongClips(projectId, song);
  return { clipCount: built, song };
}

/** Yuklenen MP3 + soz → klip plani + Flow promptlari. Suno API cagrilmaz. */
export async function prepareSongProduction(
  projectId: string,
  lyricsOverride?: string
): Promise<{ clipCount: number; prompted: number }> {
  const synced = await syncSongClips(projectId, lyricsOverride);
  const { buildPromptsForProject } = await import("@/server/services/clips");
  const clips = await buildPromptsForProject(projectId);
  await recordEvent({
    projectId,
    step: "song",
    message: `Uretim hazir: ${synced.clipCount} klip + ${clips.length} prompt (ses = yuklenen master parca)`,
  });
  return { clipCount: synced.clipCount, prompted: clips.length };
}

export async function runSongSafetyCheck(projectId: string): Promise<SafetyResult> {
  return runSafetyCheck(projectId);
}
