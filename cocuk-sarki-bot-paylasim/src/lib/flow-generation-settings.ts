/**
 * Flow uretim cubugu ozeti (or. "Video · 10scrop_9_16x1") ve model/sure
 * uyumu. Playwright yok — adapter ve testler ayni kurallari kullanir.
 */

export type FlowAspectRatio = "16:9" | "9:16";

export interface FlowSettingsChip {
  durationSec: number | null;
  aspect: FlowAspectRatio | null;
  outputs: number | null;
  looksLikeSettingsChip: boolean;
}

const VEO_NO_TEN = /veo\s*3\.1\s*-?\s*(fast|lite)/i;
const QUALITY_OR_OMNI = /omni|quality/i;

/** Modelin bildigimiz sure listesi (matris yoksa). Fast/Lite 10 sn destemez. */
export function defaultDurationsForFlowModel(model: string): number[] {
  if (QUALITY_OR_OMNI.test(model)) return [4, 6, 8, 10];
  if (VEO_NO_TEN.test(model) || /veo/i.test(model)) return [4, 6, 8];
  return [4, 6, 8];
}

/**
 * Flow'a gonderilecek klip suresi. Veo Fast/Lite + 10 sn (short'ta sik
 * kalan varsayilan) 8 sn'ye cekilir; aksi halde modelin listesine oturtulur.
 */
export function flowClipSeconds(flowModel: string, clipSeconds: number, supportedDurations?: number[]): number {
  const wanted = Math.round(Number(clipSeconds) || 8);
  const supported =
    supportedDurations && supportedDurations.length > 0
      ? supportedDurations
      : defaultDurationsForFlowModel(flowModel);
  if (supported.includes(wanted)) return wanted;
  if (supported.includes(8)) return 8;
  return supported[supported.length - 1] ?? 8;
}

/** Quality / Omni 10 sn kabul eder. Fast/Lite 8'e iner. 8 = eski varsayilan, 10'a cekilir. */
export function preferredNarratorClipSeconds(flowModel: string, currentClipSeconds?: number): number {
  const current = Math.round(Number(currentClipSeconds) || 0);
  const wanted = current > 0 && current !== 8 ? current : 10;
  return flowClipSeconds(flowModel, wanted);
}

/**
 * Flow sure sekmesinin erisilebilir adi: "8s" / "8 s" / "8sn" / "8 sn".
 * Tam eslesme (^...$) yerine sayi sinirlarini (komsu basamak yok) kontrol
 * eder — ikon ligature metni ("schedule" gibi) sekme adina karisip basa/sona
 * eklenirse (or. "schedule 8s") de eslesir; "18s"/"80s" gibi yanlis
 * eslesmeler basamak sinir kontrolu sayesinde onlenir.
 */
export function flowDurationTabPattern(seconds: number): RegExp {
  return new RegExp(`(?<!\\d)${seconds}(?!\\d)\\s*(s|sn|sec)\\b`, "i");
}

/**
 * Ayarlar ozeti ("Video · 720pcrop_16_9x1") video sinyali verir ama
 * "Metinden görüntüye" dugmesi yoksa tek basina zayif kalir. Bu ozet
 * GORUNTU degilse video kabul edilir — yanlis "dogrulanamadi" uyarisi olmasin.
 */
export function isTrustedVideoOutputLabel(label: string): boolean {
  return isVideoOutputModeLabel(label) && !isImageOutputModeLabel(label);
}

export function parseFlowSettingsChip(label: string): FlowSettingsChip {
  const text = (label || "").replace(/\s+/g, " ").trim();
  const duration = text.match(/(\d+)\s*s/i);
  const crop = text.match(/crop_(\d+)_(\d+)/i);
  const colon = text.match(/\b(16:9|9:16)\b/);
  const outputs = text.match(/x\s*([1-4])\b/i);

  let aspect: FlowAspectRatio | null = null;
  if (crop) {
    const ratio = `${crop[1]}:${crop[2]}`;
    if (ratio === "16:9" || ratio === "9:16") aspect = ratio;
  } else if (colon?.[1] === "16:9" || colon?.[1] === "9:16") {
    aspect = colon[1];
  }

  const looksLikeSettingsChip =
    /crop_(16_9|9_16)/i.test(text) ||
    (/\d+\s*s/i.test(text) && /video|g[oö]r[uü]nt[uü]|image|crop_/i.test(text));

  return {
    durationSec: duration ? Number(duration[1]) : null,
    aspect,
    outputs: outputs ? Number(outputs[1]) : null,
    looksLikeSettingsChip,
  };
}

export function chipNeedsRepair(
  chip: FlowSettingsChip,
  want: { durationSec: number; aspect: string; outputs?: number }
): { duration: boolean; aspect: boolean; outputs: boolean } {
  return {
    duration: chip.durationSec != null && chip.durationSec !== want.durationSec,
    aspect: chip.aspect != null && chip.aspect !== want.aspect,
    outputs: want.outputs != null && chip.outputs != null && chip.outputs !== want.outputs,
  };
}

export function isImageFlowModel(name: string): boolean {
  return /nano\s*banana|banana/i.test(name);
}

/**
 * CIKTI TURU AYRIMI — goruntu/video karismasinin tek karar noktasi.
 *
 * Flow prompt cubugunda iki ayri etiket gorunur:
 *  - Cikti turu dugmesi: "Metinden videoya", "Malzemelerden görüntü", "Nano Banana"…
 *  - Ayarlar ozeti: "Videocrop_16_9x1" (bu HER ZAMAN "Video" der, zayif sinyal)
 *
 * Klip = video, karakter referansi = goruntu. Yanlis siniflandirma
 * "video yerine jpeg" veya "karakter yerine video" demektir.
 */
/**
 * Modu belirleyen sey KAYNAK degil HEDEFTIR: "Görüntüden videoya" bir VIDEO
 * modudur (referans gorsel ekliyken Flow bunu gosterir). Yalnizca "görüntü"
 * kelimesine bakmak bu modu goruntu sanip klip uretimini bloke ediyordu.
 */
const VIDEO_OUTPUT_TARGET = /videoya|to video|malzemelerden video|ingredients to video|frames to video|video olu[sş]tur/i;
const IMAGE_OUTPUT_TARGET =
  /g[oö]r[uü]nt[uü]ye|to image|malzemelerden g[oö]r[uü]nt[uü]|ingredients to image|nano\s*banana|g[oö]rsel olu[sş]tur/i;

export function isImageOutputModeLabel(label: string): boolean {
  if (!label) return false;
  if (VIDEO_OUTPUT_TARGET.test(label)) return false;
  if (IMAGE_OUTPUT_TARGET.test(label)) return true;
  // Ayarlar ozeti: "Görüntücrop_16_9x1" goruntu, "Videocrop_16_9x1" video
  return /^\s*(g[oö]r[uü]nt[uü]|image)/i.test(label);
}

export function isVideoOutputModeLabel(label: string): boolean {
  if (!label) return false;
  if (isImageOutputModeLabel(label)) return false;
  // "Videocrop_16_9x1" video sayilir ama ZAYIF sinyal: cagiran taraf
  // (ensureVideoOutputMode) menuden ayrica dogrular.
  return /video|veo|malzemelerden|ingredients|frames to/i.test(label);
}

export function normalizeFlowModelName(value: string): string {
  return value
    .replace(/volume_up|arrow_drop_down|arrow_drop_up/gi, " ")
    .toLowerCase()
    .replace(/[-_.]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Pro ile 2 karismasin: "Nano Banana Pro" "Nano Banana 2" ile eslesmez. */
export function imageModelNamesMatch(uiText: string, target: string): boolean {
  const a = normalizeFlowModelName(uiText);
  const b = normalizeFlowModelName(target);
  if (!a || !b) return false;
  const aPro = /\bpro\b/.test(a);
  const bPro = /\bpro\b/.test(b);
  if (aPro !== bPro) return false;
  const aTwo = /\b2\b/.test(a);
  const bTwo = /\b2\b/.test(b);
  if (aTwo !== bTwo) return false;
  if (a.includes("banana") && b.includes("banana")) return true;
  return a === b || a.includes(b) || b.includes(a);
}

/** Flow'un "hatayi cozuyoruz / tekrar deneniyor" takili toast'i. */
export const FLOW_STUCK_RESOLVING_TEXT =
  /hatay[ıi].{0,48}ç[oö]z|ç[oö]z[uü]l[uü]yor|hatay[ıi] b[oö]yle|yeniden den[ie]n|tekrar den[ie]n|error.?resolv|trying (again|to (fix|resolve))|we.?re (fixing|resolving)/i;

export function isStuckFlowResolvingText(text: string): boolean {
  return FLOW_STUCK_RESOLVING_TEXT.test(text || "");
}

export function generationChipMismatchMessage(label: string, aspect: string, seconds: number): string {
  return `Flow ayari uyumsuz (ozet: "${(label || "?").slice(0, 48)}", hedef ${aspect} ${seconds}s). 9:16 short 10s'de kalirsa Veo Fast video uretmez; sure/oran yeniden ayarlanacak.`;
}
