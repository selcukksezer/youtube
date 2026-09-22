/**
 * Gorsel stil AILESI — tek karar noktasi.
 *
 * Kullanicinin sectigi stil ("Gercekci canli cekim" / "3D Animasyon" / "Anime")
 * yalnizca bir cumle degil, DUNYANIN TAMAMINI baglayan bir kilittir:
 * canli cekim secildiyse karedeki her sey gercek kamera goruntusudur;
 * 3D secildiyse her sey ayni 3D lehcede render edilir. Karisim yasak.
 */

export type VisualStyleFamily = "live-action" | "cgi3d" | "anime2d";

const LIVE_ACTION_PRESET_IDS = new Set(["photorealistic", "cinematic", "documentary"]);

const LIVE_ACTION_TEXT = /ger[cç]ek[cç]?i?|canl[ıi]\s*[cç]ekim|live.?action|photo.?real|fotoger[cç]ek|real\s*(footage|film|camera)|belgesel|documentary/i;
const ANIME_TEXT = /anime|manga|2d\s*(cartoon|cel|anim)|cel.?shade/i;
const CGI_TEXT = /3d|pixar|cgi|animasyon|animated|animation/i;

/**
 * Proje stilinden gorsel aileyi cozer. Preset id'leri kesindir; serbest metin
 * icin once canli-cekim, sonra anime, sonra 3D kaliplari denenir. Bos stilde
 * cocuk sablonlari 3D, digerleri canli cekim varsayar.
 */
export function visualStyleFamilyOf(templateType: string, visualStyle: string | null | undefined): VisualStyleFamily {
  const raw = (visualStyle ?? "").trim();
  if (LIVE_ACTION_PRESET_IDS.has(raw)) return "live-action";
  if (raw === "pixar3d") return "cgi3d";
  if (raw === "anime") return "anime2d";
  if (raw) {
    if (ANIME_TEXT.test(raw)) return "anime2d";
    if (LIVE_ACTION_TEXT.test(raw) && !CGI_TEXT.test(raw)) return "live-action";
    if (CGI_TEXT.test(raw)) return "cgi3d";
    if (LIVE_ACTION_TEXT.test(raw)) return "live-action";
  }
  return templateType === "kids_animation" || templateType === "kids_song" ? "cgi3d" : "live-action";
}

/**
 * DUNYA AILESI KILIDI — secilen aile karedeki HER OGEYI baglar.
 * Prompta stil tarifinden sonra eklenir; karisik-medya kazalarini keser.
 */
export function worldFamilyLock(family: VisualStyleFamily): string {
  if (family === "live-action") {
    return [
      "WORLD FAMILY LOCK — 100% LIVE-ACTION:",
      "ground, sky, architecture, props, plants, food, background extras and EVERY character are real, physically built and filmed by one real camera in one real place.",
      "Characters are real costumed mascot performers or practical puppets with real fur, fabric and weight — they PERFORM ON the real geography of the song (forest floor, sand, barn dirt, park lawn), never floating on a blank plate.",
      "Lyric places must read as dense, photographable locations with real depth and weather — not painted backdrops.",
      "BANNED in frame: 3D CGI renders, cartoon or cel-shaded elements, illustration, anime, painterly or video-game looks. If anything looks rendered, the shot is wrong.",
    ].join(" ");
  }
  if (family === "anime2d") {
    return [
      "WORLD FAMILY LOCK — 100% 2D ANIME:",
      "backgrounds, props, effects and EVERY character are hand-drawn 2D anime in ONE consistent line and colour style.",
      "BANNED in frame: live-action footage, photographic textures, 3D CGI renders, photoreal humans.",
    ].join(" ");
  }
  return [
    "WORLD FAMILY LOCK — 100% STYLIZED 3D ANIMATION:",
    "ground, sky, architecture, props, plants, food, background extras and EVERY character are rendered in the SAME 3D dialect as one unified animated film — backgrounds get the same modelling, texturing and lighting care as the hero, never flat painted cartoon panels.",
    "Character bodies stay smooth and organic — never voxel, cube-built, faceted low-poly or Minecraft-like.",
    "BANNED in frame: live-action footage, photographic humans or animals, stock plates, 2D anime cels, photo-collage textures.",
  ].join(" ");
}

/** Sarki klibi promptu icin KISA canli-cekim fizik kilidi (8k butcesine sigar). */
export const LIVE_ACTION_SONG_REALISM = [
  "Live-action realism:",
  "one consistent light source — every shadow shares the same direction, length and color;",
  "real reflections in eyes, puddles, glass and metal mirroring the actual scene;",
  "true optical depth of field, natural motion blur, subtle sensor grain;",
  "real fabric weave and fur fibers, believable weight, solid ground contact, natural follow-through after every move;",
  "lyric places fill the frame as REAL filmed geography with sky/ground/depth — never a studio void or cartoon plate;",
  "nothing plastic, painted, warped or cartoon at any single moment — an unedited camera would record exactly this.",
].join(" ");

/**
 * Canli-cekim / sinematik: sozlerdeki mekanin kisa ama guclu kilidi.
 * STYLE veya SET yanina eklenir; uzun tutma — 8k butcesi.
 */
export function livePlaceAnchorLock(worldPositive?: string | null): string {
  const place = (worldPositive || "").replace(/\s+/g, " ").trim().slice(0, 280);
  return [
    "LIVE PLACE LOCK:",
    place
      ? `THIS real place dominates the frame: ${place}.`
      : "THIS clip's sung place dominates as real filmed geography (sky/ceiling, ground/floor, weather, deep parallax).",
    "Costumed mascot performers stand ON that real ground with contact shadows — like cartoon stars dropped into a real-world music video, but everything is photographed for real.",
    "No flat backdrop, no empty cyclorama, no painted cartoon plate behind them.",
  ].join(" ");
}
/**
 * 3D dilinde yazilmis sahne planini canli-cekim diline cevirir.
 * (Soz gorselleme hatti 3D lehcede yazar; canli cekim projede son promptta
 * celiski kalmasin.)
 */
export function convertShotPlanToLiveAction(text: string): string {
  return text
    .replace(/\b3d\s+animated\s+music.?video\s+shot\b/gi, "live-action music-video shot")
    .replace(/\b(stylized|theatrical)\s+3d\s+(cgi|animation|animated)\b/gi, "live-action")
    .replace(/\b3d\s+(cgi|animation|animated)\b/gi, "live-action")
    .replace(/\bcgi\b/gi, "live-action")
    .replace(/\bstylized\s+3d\b/gi, "real")
    .replace(/\b3d\b/gi, "real")
    .replace(/\bcartoon\s+mascot\b/gi, "costumed mascot performer")
    .replace(/\brender(ed)?\b/gi, "photographed");
}
