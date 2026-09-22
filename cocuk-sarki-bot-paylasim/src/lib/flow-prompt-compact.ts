/**
 * Flow'a yazilacak prompt kisaltmasi.
 * Dil + diyalog + ekran-yazi yasagi ASLA dusmez (9:16 ve 16:9).
 */

export const FLOW_PROMPT_MAX = 8_000;

/**
 * SABIT KURAL: kullanici gomulu altyazi istemediyse ekranda hic yazi olmaz.
 * Klip 1 ile klip 1000 ayni metni alir — kisaltma / ozel sablon bu damgayi dusuremez.
 * Ust bant + alt bant (altyazi / lower-third) kesinlikle yasak; 8000 limitinde
 * bu bloklar rezerve edilir, asla dusmez.
 */
export const FLOW_NO_ONSCREEN_TEXT_HEAD = [
  "[SABIT KURAL — ALTYAZI YOK]",
  "[NO ON-SCREEN TEXT]",
  "ABSOLUTE BAN — zero written words in the picture, any language, first frame to last:",
  "NO text at the TOP of the frame, NO text at the BOTTOM of the frame, NO text in the middle.",
  "Forbidden: subtitles, captions, lower-thirds, karaoke/lyric overlays, titles, labels, readable signs, logos, watermarks, UI, letter glyphs.",
  "Sung/spoken words exist ONLY as audio — never burned into the image.",
].join(" ");

export const FLOW_NO_ONSCREEN_TEXT_TAIL = [
  "[SABIT KURAL SONU — ALTYAZI YOK]",
  "[FINAL HARD LOCK — ON-SCREEN TEXT]",
  "Final check: TOP band clean, BOTTOM band clean, center clean — 100% text-free to the last frame.",
  "No üst yazı, no alt yazı, no subtitles, no captions, no lyric text. Picture only.",
].join(" ");

const HEAD_MARKERS = /\[SABIT KURAL — ALTYAZI YOK\]/i;
const TAIL_MARKER_RE = /\[(?:SABIT KURAL SONU — ALTYAZI YOK|FINAL HARD LOCK[^\]]*)\]/i;

function joinBlocks(parts: Array<string | undefined | null>): string {
  return parts
    .filter((p): p is string => Boolean(p && p.trim()))
    .join("\n\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/**
 * Gomulu kuyruk damgasini siler ama SONRAKI bolumleri yemez.
 * Eski regex `[\s\S]*$` ilk kuyruktan string sonuna kadar her seyi (AUDIO / diyalog) siliyordu.
 */
export function stripEmbeddedOnscreenTextTails(prompt: string): string {
  let next = prompt.split(FLOW_NO_ONSCREEN_TEXT_TAIL).join("");
  next = next.replace(
    /\n*\[(?:SABIT KURAL SONU — ALTYAZI YOK|FINAL HARD LOCK[^\]]*)\][^\[]*(?=\n\[|$)/gi,
    ""
  );
  return next.replace(/\n{3,}/g, "\n\n").trim();
}

/** Govdeyi keser ama kuyruk kilidini her zaman sona yapistirir. Bas tarafi (diyalog) korunur. */
function packWithReservedTail(body: string, tail: string, maxChars: number): string {
  const tailBlock = `\n\n${tail}`;
  const budget = Math.max(80, maxChars - tailBlock.length);
  const trimmed = body.trim().slice(0, budget).trim();
  return `${trimmed}${tailBlock}`.slice(0, maxChars);
}

/** Bas (diyalog + kilitler) ASLA kesilmez; fazla uzunluk ortadan/sondan dusar. */
function packHeadMidTail(head: string, mid: string, tail: string, maxChars: number): string {
  const headBlock = head.trim();
  const tailBlock = `\n\n${tail}`;
  const budget = Math.max(0, maxChars - headBlock.length - tailBlock.length - 2);
  const midTrim = mid.trim().slice(0, budget).trim();
  const packed = `${headBlock}${midTrim ? `\n\n${midTrim}` : ""}${tailBlock}`;
  if (packed.length <= maxChars) return packed;
  // Head + kuyruk max'i astiysa kuyrugu koru, headi kisalt (nadir).
  const headBudget = Math.max(40, maxChars - tailBlock.length);
  return `${headBlock.slice(0, headBudget).trim()}${tailBlock}`.slice(0, maxChars);
}

/**
 * Prompttaki tirnakli konusma satirini bulur.
 * Sablon "says exactly" / [AUDIO] / [SPOKEN LINE] / hikaye kilidi sirasi.
 */
export function extractSpokenQuote(full: string): string {
  const patterns = [
    /\[SPOKEN LINE[^\]]*\][\s\S]{0,500}?"([^"]{4,500})"/i,
    /says exactly[^\n"]{0,120}:\s*\n*"([^"]{4,500})"/i,
    /voice-over says exactly[^\n"]{0,80}:\s*\n*"([^"]{4,500})"/i,
    /SINGS[^\n"]{0,80}:\s*"([^"]{4,500})"/i,
    /HEARD THIS CLIP[^"]{0,180}:\s*"([^"]{4,500})"/i,
    /This clip's AUDIO[^"]{0,180}:\s*"([^"]{4,500})"/i,
    /SUNG THIS CLIP \(exact\):\s*"([^"]{4,500})"/i,
    /AUDIO THIS CLIP[^"]{0,120}:\s*"([^"]{4,500})"/i,
    /Lyric line for lip-sync[^\n"]{0,80}:\s*"([^"]{4,500})"/i,
    /\[AUDIO(?: AND SPEECH)?\][\s\S]{0,2500}?"([^"]{4,500})"/i,
    /Spoken story line \(verbatim intent\):\s*"([^"]{4,500})"/i,
    /Spoken line \(audio, never subtitle\):\s*"([^"]{4,500})"/i,
    /The spoken line is AUDIO[^\n"]{0,80}:\s*"([^"]{4,500})"/i,
  ];
  for (const re of patterns) {
    const hit = full.match(re)?.[1]?.replace(/\s+/g, " ").trim();
    if (hit) return hit;
  }
  return "";
}

function spokenLinePriorityBlock(quote: string, lang: string): string {
  const q = quote.replace(/\s+/g, " ").trim().slice(0, 400);
  if (!q) return "";
  return [
    "[SPOKEN LINE — AUDIO FIRST — DO NOT DROP]",
    `Deliver this exact ${lang} line as the audible vocal (speak or narrate as the rest of the prompt requires). Word for word. No English unless ${lang} is English. Fill the full clip.`,
    `"${q}"`,
  ].join("\n");
}

/** Tirnakli sozu @referanstan hemen sonraya tasir — Flow uzun promptun ortasini atlayabiliyor. */
function hoistSpokenLine(prompt: string, quote: string, lang: string, maxChars: number): string {
  const spoken = spokenLinePriorityBlock(quote, lang);
  if (!spoken) return prompt;
  const atRefs = (prompt.match(/^(?:@[^\n]+\n)+/) || [""])[0];
  let rest = prompt.slice(atRefs.length).replace(/^\n+/, "");
  rest = rest.replace(/\[SPOKEN LINE[^\]]*\][\s\S]*?(?=\n\[(?!SPOKEN LINE)|$)/i, "").trim();
  const assembled = joinBlocks([atRefs.trim(), spoken, rest]);
  return packWithReservedTail(stripEmbeddedOnscreenTextTails(assembled), FLOW_NO_ONSCREEN_TEXT_TAIL, maxChars);
}

/**
 * Flow'a yazilacak promptu kisaltir.
 * Dil + diyalog + yazi yasagi (bas+son) ASLA dusmez.
 */
export function compactPromptForFlow(
  full: string,
  speechLanguage: string,
  maxChars = FLOW_PROMPT_MAX
): { text: string; truncated: boolean } {
  const trimmed = full.trim();
  const lang = speechLanguage.trim() || "Turkish";
  const quote = extractSpokenQuote(trimmed);

  if (trimmed.length <= maxChars) {
    const locked = ensureNoOnscreenTextLock(trimmed, maxChars);
    return { text: hoistSpokenLine(locked, quote, lang, maxChars), truncated: false };
  }

  const atRefs = (trimmed.match(/^(?:@[^\n]+\n)+/) || [""])[0];
  const body = stripEmbeddedOnscreenTextTails(trimmed.slice(atRefs.length).replace(/^\n+/, ""));

  const speechLock = [
    "[SPEECH LANGUAGE LOCK — NON-NEGOTIABLE]",
    `Spoken audio MUST be ${lang} only.`,
    /turkish|t[uü]rk/i.test(lang)
      ? "All audible dialogue MUST be Turkish. English speech, English narration and English ad-libs are FORBIDDEN."
      : `Do not switch to English unless ${lang} is English.`,
    `Deliver the quoted dialogue verbatim in ${lang} — never translate.`,
  ].join(" ");

  const spoken = spokenLinePriorityBlock(quote, lang);
  const hardEmotion = body.match(/\[HARD EMOTION[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const songConfirm = body.match(/\[SONG PICTURE CONFIRM[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const wordMap = body.match(/WORD-BY-WORD PICTURE MAP[\s\S]{0,2500}?(?=\n(?:CLEAR MUSIC|\[)|$)/i)?.[0] || "";
  const lyricLock = body.match(/\[LYRIC VISUAL LOCK\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const identity = body.match(/\[IDENTITY LOCK[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const charFidelity = body.match(/\[CHARACTER FIDELITY[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const secondBySecond = body.match(/\[SECOND-BY-SECOND ACTION\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  // Yeni sarki mimarisi: bu bloklar SABIT ayarlardir — 100 klipte de ayni kalir,
  // kesme durumunda ASLA dusmez (soz + kadro + audio kurali korunur).
  const songFilmHead = body.match(/\[ANIMATED SONG FILM[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const castLocked = body.match(/\[CAST[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const audioLock = body.match(/\[AUDIO\][\s\S]*?(?=\n\[|$)/i)?.[0] || "";
  // Dudak senkronu sabit ayardir: kesme olsa da her klipte AYNEN kalmali,
  // yoksa agiz sozden kopar ve master MP3 ile senkron bozulur.
  const lipSyncLock = body.match(/\[LIP SYNC\][\s\S]*?(?=\n\[|$)/i)?.[0] || "";

  const style = body.match(/\[STYLE\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const shot = body.match(/\[SHOT\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const charRef = body.match(/\[CHARACTER REFERENCE\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const continuity =
    body.match(/\[SCENE CONTINUITY\][\s\S]*?(?=\n\[)/i)?.[0] ||
    body.match(/\[SCENE\][\s\S]*?(?=\n\[)/i)?.[0] ||
    "";
  const camera = body.match(/\[CAMERA\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const performanceRaw = body.match(/\[PERFORMANCE[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const restrictions = body.match(/\[RESTRICTIONS\][\s\S]*?(?=\n\[FINAL|$)/i)?.[0] || "";
  const adventure = body.match(/\[PHYSICAL WORLD[\s\S]*?(?=\n\[)/i)?.[0] || "";
  const craft = body.match(/\[CINEMATIC CRAFT\][\s\S]*?(?=\n\[)|\[MV CRAFT\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const world =
    body.match(/\[WORLD[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] ||
    body.match(/\[ENVIRONMENT\][\s\S]*?(?=\n\[)/i)?.[0] ||
    "";
  const background = body.match(/\[BACKGROUND[^\]]*\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  const setDressing = body.match(/\[SET DRESSING\][\s\S]*?(?=\n\[)/i)?.[0] || "";
  // SET satiri shot plan icinde sonda olabiliyordu; bas tarafa cekilince
  // head kirpilsa bile dunya kilidi kalir.
  const setFromPerformance =
    performanceRaw.match(/SET \(locked for the WHOLE song\):[^\n]*/i)?.[0] ||
    performanceRaw.match(/^SET:[^\n]*/im)?.[0] ||
    "";

  const STYLE_RESERVE_LIMIT = 2_600;
  const styleReserved = style.length <= STYLE_RESERVE_LIMIT ? style : "";

  const locksBeforePerf = joinBlocks([
    atRefs.trim(),
    spoken,
    songFilmHead,
    songConfirm,
    wordMap,
    lyricLock,
    identity,
    charFidelity,
    castLocked,
    // KISA kilitler once: rezerve baslik yine de tasarsa packHeadMidTail
    // sondan kirpar; o durumda birkac satirlik ses/yazi kilitlerini degil,
    // buyuk bloklarin kuyrugunu kaybetmek dogru olandir.
    lipSyncLock,
    audioLock,
    hardEmotion,
    speechLock,
    FLOW_NO_ONSCREEN_TEXT_HEAD,
    // Stil + gerceklik + dunya ailesi kilidi: kesilirse Veo jenerik cizgi
    // film varsayilanina duser (arka planlar duz karton olur). Normal boyda
    // rezerve edilir; patolojik uzunlukta (ozel sablon) rezerve etmek kucuk
    // kilitleri disari itecegi icin kirpilabilir listede birakilir.
    styleReserved,
    setFromPerformance ? `[SET LOCK]\n${setFromPerformance}` : "",
  ]);
  const tailLen = FLOW_NO_ONSCREEN_TEXT_TAIL.length + 4;
  const perfBudget = Math.max(600, maxChars - locksBeforePerf.length - tailLen - 80);
  const performance =
    performanceRaw.length <= perfBudget ? performanceRaw : performanceRaw.slice(0, perfBudget).trim();

  const reservedHead = joinBlocks([locksBeforePerf, performance]);
  const midSource = joinBlocks([
    shot,
    secondBySecond,
    world,
    background,
    setDressing,
    charRef,
    continuity,
    camera,
    craft,
    adventure,
    restrictions,
    styleReserved ? "" : style,
  ]);
  const assembled = packHeadMidTail(reservedHead, midSource, FLOW_NO_ONSCREEN_TEXT_TAIL, maxChars);

  return { text: assembled, truncated: true };
}

/** Bas+son yazi yasagini garanti eder; kuyruk her zaman son satirdadir. */
export function ensureNoOnscreenTextLock(prompt: string, maxChars = FLOW_PROMPT_MAX): string {
  let next = stripEmbeddedOnscreenTextTails(prompt.trim());
  const atRefs = next.match(/^(?:@[^\n]+\n)+/);
  if (!HEAD_MARKERS.test(next)) {
    next = atRefs
      ? `${atRefs[0]}${FLOW_NO_ONSCREEN_TEXT_HEAD}\n\n${next.slice(atRefs[0].length).replace(/^\n+/, "")}`
      : `${FLOW_NO_ONSCREEN_TEXT_HEAD}\n\n${next}`;
  }
  if (TAIL_MARKER_RE.test(next) && !next.includes(FLOW_NO_ONSCREEN_TEXT_TAIL)) {
    next = stripEmbeddedOnscreenTextTails(next);
  }
  return packWithReservedTail(next, FLOW_NO_ONSCREEN_TEXT_TAIL, maxChars);
}

/**
 * Prompt kaydina yazilmadan once ayni damga. 1 klip veya 1000 klip:
 * bas ve son kilit birebir ayni metindir. Uzunluk siniri icin
 * `finalizeFlowPrompt` kullanin (kayit + Flow ayni 8000 kurali).
 */
export function stampNoOnscreenTextLock(prompt: string): string {
  let next = stripEmbeddedOnscreenTextTails(prompt.trim());
  const atRefs = next.match(/^(?:@[^\n]+\n)+/);
  if (!HEAD_MARKERS.test(next)) {
    next = atRefs
      ? `${atRefs[0]}${FLOW_NO_ONSCREEN_TEXT_HEAD}\n\n${next.slice(atRefs[0].length).replace(/^\n+/, "")}`
      : `${FLOW_NO_ONSCREEN_TEXT_HEAD}\n\n${next}`;
  }
  return `${next}\n\n${FLOW_NO_ONSCREEN_TEXT_TAIL}`.replace(/\n{3,}/g, "\n\n").trim();
}

/**
 * Kayit ve Flow icin nihai prompt: damga + 8000 hard limit.
 * Uretilen metin ASLA maxChars'i gecmez; dil / diyalog / yazi yasagi korunur.
 */
export function finalizeFlowPrompt(
  full: string,
  speechLanguage: string,
  maxChars = FLOW_PROMPT_MAX
): { text: string; truncated: boolean } {
  const stamped = stampNoOnscreenTextLock(full);
  const compacted = compactPromptForFlow(stamped, speechLanguage, maxChars);
  const text = ensureNoOnscreenTextLock(compacted.text, maxChars);
  return {
    text,
    truncated: compacted.truncated || stamped.length > maxChars || text.length > maxChars,
  };
}
