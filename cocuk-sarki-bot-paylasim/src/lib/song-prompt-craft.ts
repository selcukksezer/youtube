/**
 * Sarki klibi Flow prompt zanaati: saniye-saniye plan, dis/set dunyasi,
 * malzeme ve karakter sabitligi. Prompt builder + composeShotPrompt ortak kullanir.
 */

import { extractSongPictureBeats, detectSongWorld, worldPositiveForLive } from "./song-lyric-visual";
import { livePlaceAnchorLock } from "./visual-style-family";

/**
 * Saniye-saniye plan iki bicimde yazilabiliyor:
 *  - "Second-by-second action (...):" (eski/uzun bicim, ; ile ayrilir)
 *  - "ACTION TIMELINE 0-8s (...):"    (sarki cekirdegi, satir satir)
 * Ikisi de yakalanmali; aksi halde onceki klibin bitisi promptta hic gorunmez.
 */
const SECOND_TIMELINE_RE =
  /(?:Second-by-second action|ACTION TIMELINE\s*0-\d+s)[^\n:]*:\s*([\s\S]+?)(?:\n\n|Prop craft|Serial continuity|Clarity lock|Identity lock|Micro-realism|MUST BE VISIBLE|Lyric fidelity|Music-video|SET \(locked|CRAFT:|FINAL FRAME|\[|$)/i;

/** Dis mekan + set yogunlugu — bos void / stüdyo cyclorama yasak. */
export const SONG_WORLD_CRAFT_LOCK = `WORLD / EXTERIOR / SET CRAFT (NON-NEGOTIABLE):
- This is a FULL inhabited music-video world, not a character on a void. Always show THREE depth layers: foreground lyric-props with thickness + contact shadows; mid-ground locked singer on a real floor; deep readable background with architecture or landscape.
- EXTERIOR: ground underfoot (grass/wood/stone/sand with grain) + sky or weather ceiling + horizon line + distant unreadable living extras (tiny bouncing silhouettes, flags, trees, windows with warm glow) — never a blank white-sky plate.
- INTERIOR: ceiling, floor, at least two walls, a window or doorway that reveals a REAL exterior beyond, practical lamps, clutter that belongs to this song world.
- TIME OF DAY + WEATHER stay continuous across the whole song unless THIS lyric beat explicitly changes them (golden hour stays golden hour).
- Materials must survive a close-up: fabric weave, fur strands, wood grain, paint chips, ceramic glaze, metal glints, leaf veins, water caustics. Every foot and prop has a contact shadow on the ground.
- Distant world stays ALIVE on the beat: parallax, drifting particles, curtains, leaves, bubbles, lights — never a frozen postcard backdrop.`;

/** Her saniye gorunur bir beat; donuk portre yasak. */
export const SONG_SECOND_BY_SECOND_LOCK = `SECOND-BY-SECOND DIRECTOR LOCK:
- Every integer second of this clip must have a READABLE change: gesture, prop contact, camera micro-move, expression OR background pulse. Frozen idle longer than 1s FAILS.
- Hit lyric meaning IN ORDER as the line would be sung — last syllable pose lands in the FINAL second.
- Clip 2+: second 0 is MATCH-ON-ACTION from the previous last second (same planted feet, same floor, mid-groove body, mouth still in phrase energy).
- Last 0.5s: soft handoff pose into the NEXT clip — do not cut mid-gesture.`;

export function extractSecondBySecondTail(imagePrompt: string | null | undefined): string {
  const ip = imagePrompt?.trim() || "";
  const m = ip.match(SECOND_TIMELINE_RE);
  const timeline = m?.[1]?.trim() || "";
  if (!timeline) return "";
  // Eski bicim ";" ile, sarki cekirdegi satir sonu ile ayirir.
  const chunks = timeline
    .split(/;\s*|\n+/)
    .map((p) => p.trim())
    .filter(Boolean);
  return chunks.slice(-2).join("; ");
}

/**
 * Kayitli sahne planindan look pack paragrafini ayiklar.
 *
 * Eski surumde ayni look pack hem SHOT PLAN icine hem [STYLE] blogua
 * yaziliyordu (~900 karakter tekrar). Tekrar, 8k limitinde [STYLE] blogunun
 * tamamen kesilmesine yol aciyordu. Yeni promptta look pack yalnizca
 * [STYLE] icinde; bu fonksiyon eski kayitlari da ayni hizaya getirir.
 */
export function stripEmbeddedLookPack(imagePrompt: string): string {
  return imagePrompt
    .replace(/^\s*(PROJECT )?LOOK PACK [\s\S]*?(?=\n[A-Z][A-Z /()-]{2,}:|\n*$)/gim, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function extractSecondBySecondFull(imagePrompt: string | null | undefined): string {
  const ip = imagePrompt?.trim() || "";
  const m = ip.match(SECOND_TIMELINE_RE);
  return m?.[1]?.replace(/\s+/g, " ").trim() || "";
}

function splitLyricBeats(lyrics: string, slotCount: number): string[] {
  const clean = lyrics.replace(/\s+/g, " ").trim();
  if (!clean || slotCount <= 0) return [];
  const byLine = clean
    .split(/[,\n/|]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 2);
  if (byLine.length >= slotCount) return byLine.slice(0, slotCount);
  const words = clean.split(" ").filter(Boolean);
  if (words.length === 0) return Array.from({ length: slotCount }, () => "groove bounce on the beat");
  const beats: string[] = [];
  const per = Math.max(1, Math.ceil(words.length / slotCount));
  for (let i = 0; i < slotCount; i++) {
    const slice = words.slice(i * per, (i + 1) * per).join(" ");
    beats.push(slice || words[words.length - 1] || "hold smile on beat");
  }
  return beats;
}

/**
 * Mevcut yonetmen planinda saniye satiri yoksa sozlerden profesyonel timeline uretir.
 */
export function buildSongSecondBySecondPlan(opts: {
  lyrics: string;
  seconds: number;
  isFirstClip: boolean;
  previousTail?: string;
  lyricSyncAction?: string;
  choreography?: string;
  beatVerb?: (second: number) => string;
  coldOpen?: string;
  handoff?: string;
}): string {
  const seconds = Math.max(4, Math.min(20, Math.round(opts.seconds) || 8));
  const lyrics = opts.lyrics.replace(/\s+/g, " ").trim();

  const openSlots = opts.isFirstClip ? seconds - 1 : seconds - 2;
  const lyricSlots = Math.max(2, openSlots);
  const beats = splitLyricBeats(lyrics, lyricSlots);
  const lines: string[] = [];
  const verbAt = (t: number, fallback: string) => opts.beatVerb?.(t) || fallback;

  if (opts.isFirstClip) {
    const open = opts.coldOpen?.trim() || "cold-open — singer already mid-groove on planted feet, living set pulses";
    lines.push(
      `0s: ${open}; mouth shaping the first syllable of "${lyrics.slice(0, 48)}"`
    );
  } else {
    const bridge = opts.previousTail?.trim()
      ? `match-on-action from previous last beat (${opts.previousTail.slice(0, 140)})`
      : "match-on-action: same floor, same costume, body still mid-bounce, gaze still engaged";
    lines.push(`0s: ${bridge} — do not reset the world`);
  }

  const start = 1;
  for (let i = 0; i < beats.length; i++) {
    const t = start + i;
    if (t >= seconds - 1) break;
    const phrase = beats[i].slice(0, 72);
    const syncHint = opts.lyricSyncAction?.trim() && i === 0 ? ` (${opts.lyricSyncAction.slice(0, 80)})` : "";
    const verb = verbAt(t, "syllable visemes + beat bounce");
    lines.push(
      `${t}s: ${verb} while mime "${phrase}"; SHOW those words as real on-screen things in the same second (skip none)${syncHint}`
    );
  }

  const choreo = opts.choreography?.replace(/\s+/g, " ").trim().slice(0, 90);
  if (choreo && seconds >= 5) {
    lines.push(`${Math.max(2, seconds - 2)}s: ${choreo} — still on-model, planted feet, lyric prop stays in frame`);
  }

  const handoff =
    opts.handoff?.trim() ||
    "last-syllable pose + soft handoff toward the NEXT clip (same set, same singer, no cut mid-gesture)";
  lines.push(`${seconds - 1}s–${seconds}s: ${handoff}`);

  return lines.join("; ");
}

/** Bir söz parçasının görsel karşılığı — tırnaksız, İngilizce. */
function phraseVisual(phrase: string): string {
  const beats = extractSongPictureBeats(phrase);
  if (beats.length === 0) {
    return "clear singing visemes on every syllable plus a gesture that acts out this phrase's meaning, feet planted with a beat bounce";
  }
  return beats.map((b) => b.visible.split(/[—(]/)[0].trim()).join("; ");
}

/**
 * Tırnaksız saniye-saniye plan: söz metni ekrana yazı bastırmasın diye
 * cümleler ALINTILANMAZ — "sung phrase N" diye sıra ile anılır ve her
 * saniyeye o parçanın GÖRSEL karşılığı yazılır.
 */
export function buildLyricActionTimeline(opts: {
  lyrics: string;
  seconds: number;
  isFirstClip: boolean;
  choreography?: string;
  coldOpen?: string;
  handoff?: string;
}): string {
  const seconds = Math.max(4, Math.min(20, Math.round(opts.seconds) || 8));
  const phrases = splitLyricBeats(opts.lyrics, Math.max(2, seconds - 2));
  const lines: string[] = [];

  if (opts.isFirstClip) {
    const open =
      opts.coldOpen?.trim() ||
      "cold open — the singer is already mid-groove on planted feet, the whole set alive and moving";
    lines.push(`0s: ${open}; mouth already shaping the first syllable`);
  } else {
    lines.push("0s: match-on-action from the previous clip's last frame — body mid-move, world never resets");
  }

  // Ayni gorsel arka arkaya tekrar etmesin: AI ayni beati birden cok saniyeye
  // yaydiginda prompt bosuna sisiyor ve gercek yonerge yer kaybediyordu.
  let lastVisual = "";
  for (let i = 0; i < phrases.length; i++) {
    const t = 1 + i;
    if (t >= seconds - 1) break;
    const visual = phraseVisual(phrases[i]);
    const line =
      visual === lastVisual
        ? `${t}s: phrase ${i + 1} — keep that action alive, new gesture accent on the beat`
        : `${t}s: phrase ${i + 1} — ${visual}`;
    lastVisual = visual;
    lines.push(line);
  }

  const choreo = opts.choreography?.replace(/\s+/g, " ").trim().slice(0, 90);
  if (choreo && seconds >= 5) {
    lines.push(`${seconds - 2}s: ${choreo} — on-model, planted feet, lyric props still in frame`);
  }

  const handoff =
    opts.handoff?.trim() ||
    "last-syllable pose, then a soft handoff into the next clip — same set, same singer, no cut mid-gesture";
  lines.push(`${seconds - 1}-${seconds}s: ${handoff}`);

  return lines.join("\n");
}

/**
 * KLIPLER ARASI KOPMA KILIDI.
 *
 * Sarki promptu eskiden yalnizca genel bir "match-on-action" cumlesi
 * tasiyordu; onceki klibin SOMUT bitis hali prompta hic girmiyordu. Sonuc:
 * her klip kendi sahnesini yeniden kuruyor, kiyafet/isik/kamera atliyordu.
 * Burada onceki klibin gercek bitis verisi (son 1-2 saniye, sahne, duygu)
 * yaziya dokulur. Soz metni ALINTILANMAZ — tirnakli metin Veo'ya "bunu
 * ekrana yaz" sinyali verir (soz yalnizca SHOT PLAN icinde 1 kez gecer).
 */
export function formatSongClipBridge(opts: {
  clipIndex: number;
  isFirstClip: boolean;
  previousImagePrompt?: string | null;
  previousScene?: string | null;
  previousEmotion?: string | null;
  previousVoiceTone?: string | null;
}): string {
  if (opts.isFirstClip) {
    return [
      "CONTINUITY — CLIP 1 IS THE COLD OPEN:",
      "establish this song's world, light, cast and costumes now; every later clip continues THIS setup and never resets it.",
      "The singer is already mid-performance at frame 1 — no fade-in, no title card, no walking into an empty set.",
    ].join(" ");
  }

  const prevIndex = Math.max(1, opts.clipIndex - 1);
  const tail = extractSecondBySecondTail(opts.previousImagePrompt).replace(/\s+/g, " ").trim();
  const scene = (opts.previousScene || "").replace(/\s+/g, " ").trim();
  const mood = [opts.previousEmotion, opts.previousVoiceTone]
    .map((v) => (v || "").replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join(" / ");

  return [
    `CONTINUITY — MATCH-ON-ACTION FROM CLIP ${prevIndex}: frame 1 here is the frame right after clip ${prevIndex}'s last frame; the take never stopped.`,
    tail ? `Clip ${prevIndex} ended on: ${tail.slice(0, 130)} — continue from that pose and momentum.` : "",
    scene ? `Clip ${prevIndex} beat: ${scene.slice(0, 100)}.` : "",
    mood ? `Keep the feeling: ${mood.slice(0, 50)}.` : "",
    "IDENTICAL: same location, camera side, time of day, weather, light direction and colour, costumes, props in the same hands, cast on the same floor marks.",
    "FORBIDDEN AT THE CUT: new location, teleporting, changed or recoloured outfit, changed prop, relit scene, redesigned or new character, fade in/out, establishing reset, walking into frame, re-introduction pose.",
  ]
    .filter(Boolean)
    .join(" ");
}

/**
 * DUDAK SENKRONU / SARKI SOYLEME KILIDI.
 *
 * Klip sessizdir; final film onceden kaydedilmis master MP3 ile birlesir.
 * Bu yuzden agiz, saniye saniye o klibin sozune oturmali. Soz metni burada
 * TEKRAR TIRNAKLANMAZ (ekrana yazi riski) — SHOT PLAN'daki satira atif yapilir.
 */
export function songLipSyncLock(opts: {
  seconds: number;
  isFirstClip: boolean;
  singerName?: string | null;
  hasLyrics: boolean;
}): string {
  const seconds = Math.max(4, Math.min(20, Math.round(opts.seconds) || 8));
  const singer = (opts.singerName || "").replace(/\s+/g, " ").trim();
  const who = singer ? singer : "the lead singer";

  if (!opts.hasLyrics) {
    return [
      "LIP SYNC — INSTRUMENTAL SECONDS (NO SUNG LINE):",
      `${who} does NOT sing or talk here: mouth stays closed or softly smiling, no random jaw flapping, no mumbling, no invented words.`,
      "Perform the music with the body instead — beat bounce, claps, prop play, expression, on tempo.",
    ].join(" ");
  }

  return [
    "LIP SYNC — MIME THE MASTER TRACK EXACTLY:",
    `${who} silently mimes the Turkish lyric line in the SHOT PLAN; that line is the ONLY thing the mouth performs.`,
    `Each syllable gets its own visible mouth shape, in order, at the song's tempo — first syllable in second 0${opts.isFirstClip ? "" : " (mouth already mid-phrase from the previous clip)"}, last syllable inside the final second of this ${seconds}s clip.`,
    "Turkish visemes: open jaw a/e, rounded lips o/ö/u/ü, spread i/ı, closed lips m/b/p, teeth on lip f/v, tongue tip l/t/d/n.",
    "Jaw, cheeks, throat and breath move with the phrase; brows accent stressed syllables — no stiff mask, no random jaw flapping.",
    "BANS: rushing the line then standing mouth-closed, singing past its end, extra or improvised words, speech, voice-over.",
    "Friends do not sing lead — they clap, bounce and react. Body bounce and prop hits land on the syllable beats so the picture cuts onto the master track.",
  ].join(" ");
}

export function songWorldDetailFromClip(opts: {
  imagePrompt?: string | null;
  sceneDescription?: string | null;
  environment?: string | null;
  isFirstClip: boolean;
}): string {
  const visual = [opts.environment, opts.imagePrompt, opts.sceneDescription]
    .filter(Boolean)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
  const envHint = opts.environment?.replace(/\s+/g, " ").trim() || "";
  const looksInterior = /\b(room|kitchen|classroom|hallway|interior|ceiling|window|indoor|ev|oda|sinif)\b/i.test(
    visual
  );
  const looksExterior = /\b(garden|park|street|sky|outdoor|yard|field|meadow|playground|bahce|park|sokak|gokyuzu)\b/i.test(
    visual
  );

  return [
    SONG_WORLD_CRAFT_LOCK,
    envHint ? `THIS CLIP SET LOCK: ${envHint}` : "",
    looksInterior && !looksExterior
      ? "Stage as INTERIOR-with-exterior: ceiling + two walls + floor + a window/door showing real weather and sky beyond; practical lamps; lived-in clutter; never a cyclorama."
      : looksExterior
        ? "Stage as EXTERIOR: ground material + sky/weather + horizon + distant living extras; singer planted on real terrain with contact shadow."
        : "If the lyric does not force a location change, keep the SAME established MV set family — dress both a readable exterior depth AND tactile foreground.",
    opts.isFirstClip
      ? "Opening world: establish this song's home set NOW (architecture, palette, time of day, weather) so every later clip can continue it."
      : "World does not reset: same geography, same time of day, same weather family, same materials as the previous consecutive seconds.",
    "Foreground lyric-props stay tactile and counted correctly; background is dense, colorful, and beat-alive — never sparse toy-on-void.",
  ]
    .filter(Boolean)
    .join(" ");
}

/**
 * Canli-cekim / sinematik shot plan: sozlerdeki mekani fotografik yogunlukta
 * guclendirir. SET satirini live positive ile degistirir + kisa PLACE LOCK ekler.
 */
export function boostLiveActionShotPlan(shotPlan: string, lyrics: string, topic = ""): string {
  const text = (shotPlan || "").trim();
  if (!text) return text;
  const world = detectSongWorld([lyrics, topic].join("\n"));
  const livePositive = world ? worldPositiveForLive(world) : "";
  const placeLock = livePlaceAnchorLock(livePositive || null);

  let next = text;
  if (world && /SET \(locked for the WHOLE song\):/i.test(next)) {
    next = next.replace(
      /SET \(locked for the WHOLE song\):[^\n]*/i,
      `SET (locked for the WHOLE song): ${livePositive}. NEVER show: ${world.never} — unless this clip's sung line explicitly names them.`
    );
  } else if (world && /^SET:/im.test(next)) {
    next = next.replace(/^SET:[^\n]*/im, `SET: ${livePositive}`);
  } else if (world && !/SET \(locked|LIVE PLACE LOCK/i.test(next)) {
    next = `SET (locked for the WHOLE song): ${livePositive}. NEVER show: ${world.never}.\n${next}`;
  }

  if (!/LIVE PLACE LOCK/i.test(next)) {
    if (/SET \(locked for the WHOLE song\):[^\n]*/i.test(next)) {
      next = next.replace(/(SET \(locked for the WHOLE song\):[^\n]*)/i, `$1\n${placeLock}`);
    } else {
      next = `${placeLock}\n${next}`;
    }
  }
  return next.replace(/\n{3,}/g, "\n\n").trim();
}
