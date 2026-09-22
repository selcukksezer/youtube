import type { DnaCard } from "@/lib/song-character";

/**
 * KARAKTER SAYFASI PROMPTU (Flow Karakterler sayfasi / gorsel modu).
 *
 * Neden burada: kadro uyelerinin tum ayirt edici bilgisi (tur, silueti, boy,
 * palet, yuz, kostum, imza isareti) DNA kartinda duruyordu ama Flow'a yalnizca
 * kisa `imagePrompt` gidiyordu. Ayni sanat dili + ayni kisa tarif = birbirine
 * benzeyen kadro. Burada her uye icin ETIKETLI, genis ve AYIRT EDICI bir
 * karakter kunyesi kurulur.
 */

/** Boy bandi: kadro icinde silueti aninda ayiran en guclu tek degisken. */
export const CHARACTER_HEIGHT_BANDS = ["tiny", "short", "medium", "tall"] as const;
export type CharacterHeightBand = (typeof CHARACTER_HEIGHT_BANDS)[number];

const HEIGHT_PHRASE: Record<string, string> = {
  tiny: "tiny — head is nearly half the body, fits in two cupped hands",
  short: "short and compact — stocky, low center of gravity",
  medium: "medium — balanced mascot proportions",
  tall: "tall and lanky — long limbs, high shoulder line",
};

export function heightBandPhrase(band: string): string {
  const key = band.trim().toLowerCase();
  return HEIGHT_PHRASE[key] ?? (band.trim() ? band.trim() : HEIGHT_PHRASE.medium);
}

/**
 * Kadroda boy bandlarini benzersizlestirir.
 *
 * AI sik sik herkese ayni boyu verir; boy tek basina siluetin en gorunur
 * ayirdicisidir. Cakisanlar bos bandlara dagitilir (deterministik).
 */
export function spreadHeightBands(bands: string[]): CharacterHeightBand[] {
  const used = new Set<string>();
  const out: CharacterHeightBand[] = [];
  const isBand = (v: string): v is CharacterHeightBand =>
    (CHARACTER_HEIGHT_BANDS as readonly string[]).includes(v);

  for (const raw of bands) {
    const wanted = raw.trim().toLowerCase();
    if (isBand(wanted) && !used.has(wanted)) {
      used.add(wanted);
      out.push(wanted);
      continue;
    }
    const free = CHARACTER_HEIGHT_BANDS.find((b) => !used.has(b));
    // 4'ten fazla uye varsa bandlar tekrar eder; sira yine dengeli kalir
    const chosen = free ?? CHARACTER_HEIGHT_BANDS[out.length % CHARACTER_HEIGHT_BANDS.length];
    used.add(chosen);
    out.push(chosen);
  }
  return out;
}

function clean(value: string | null | undefined, max = 320): string {
  return (value ?? "").replace(/\s+/g, " ").trim().slice(0, max);
}

function paletteLine(colors: string[]): string {
  const list = colors.map((c) => clean(c, 40)).filter(Boolean).slice(0, 4);
  if (list.length === 0) return "";
  const roles = ["main body", "secondary", "accent", "detail"];
  return list.map((color, i) => `${roles[i] ?? "detail"} ${color}`).join(", ");
}

export interface CharacterSheetInput {
  name: string;
  dna: Partial<DnaCard> | null;
  /** DNA yoksa profilden gelen yedek gorunum metni. */
  fallbackAppearance: string;
  /** Profil kostum metni (DNA outfitDetail bos ise). */
  wardrobe?: string;
  /** Bu projenin sanat dili + malzeme dili. */
  artStyle: string;
  /** On/arka panel kimlik kilidi cumlesi. */
  identityLine?: string;
  /** Turnaround sayfasi kurallari (panel duzeni, etiketler). */
  sheetLock: string;
  /** Kadrodaki DIGER uyeler — kopya/renk-klon yasagi icin somut yasak gorunum. */
  castmates?: CastmateLock[];
}

/** Flow'a yazilan "sunlari CIZME" satiri: ad + tur + ana renk + siluet + imza. */
export type CastmateLock = {
  name: string;
  species?: string;
  mainColor?: string;
  silhouette?: string;
  distinguishingMark?: string;
};

export function formatCastmateForbiddenLook(mate: CastmateLock): string {
  const bits = [
    clean(mate.name, 40),
    clean(mate.species, 50),
    clean(mate.mainColor, 40) && `${clean(mate.mainColor, 40)} main body`,
    clean(mate.silhouette, 80),
    clean(mate.distinguishingMark, 80),
  ].filter(Boolean);
  return bits.join(", ");
}

/**
 * SIRINLIK KILIDI — her cocuk karakteri karsi konulmaz tatlilikta cikar.
 * Kimlik alanlarini (tur / siluet / boy / palet / imza isareti) EZMEZ;
 * ayni kimligi maksimum sevimlilikte ve her detayi net cizdirir.
 */
export const CHARACTER_CUTENESS_LOCK = [
  "CUTENESS LOCK — IRRESISTIBLY ADORABLE:",
  "oversized glossy eyes (huge, layered catchlights, one tiny star highlight, wet lid line, visible iris fibres), plump round cheeks with a soft natural blush, tiny button nose with a subtle moist sheen, warm gentle smile;",
  "soft rounded edges everywhere — zero sharp claws, zero scary teeth, zero harsh angles, zero blocky/voxel/cube-built/Minecraft-like shapes;",
  "squeezable huggable volume that makes a toddler want to hug it instantly;",
  "keep THIS character's own species, silhouette, height band, palette and unmistakable mark while maximizing charm — cuteness must never make cast members look alike.",
].join(" ");

/**
 * MALZEME GERCEKLIGI — karakterin "ucuz oyuncak render" gibi cikmasini onler.
 * Sirinlik kilidiyle birlikte yazilir: biri cazibeyi, bu kalite/dokuyu kilitler.
 */
export const CHARACTER_MATERIAL_REALISM_LOCK = [
  "MATERIAL REALISM — FEATURE-FILM RENDER QUALITY:",
  "fur is groomed strand-by-strand with visible undercoat, clumping, flyaway hairs and soft rim light through the edges; short velvety pile on the muzzle and ears, longer tufts on chest, cheeks and tail;",
  "fabric shows real weave, thread thickness, seams, stitching, hems, small folds that follow the pose and gentle wear at elbows, knees and cuffs;",
  "skin-like surfaces carry subsurface scattering — light glows warmly through ear edges, nose, fingers and thin membranes;",
  "eyes are wet and alive with corneal reflection of the actual surroundings, moist lower lid and a soft shadow from the upper lid;",
  "every accessory has real thickness, weight, contact shadow and its own material (metal glints, matte rubber, glazed ceramic, knitted wool);",
  "physically based shading: correct roughness and specular response per material, soft global illumination, occlusion in every crease, no flat plastic patches;",
  "the character reads like a photographed hero asset from a cinema animated feature — richly detailed, tactile, never a smooth untextured toy blob.",
].join(" ");

/**
 * Etiketli, genis karakter kunyesi. Alanlar bos ise satir hic yazilmaz —
 * prompt gereksiz "bilinmiyor" gurultusu tasimaz.
 */
export function composeCharacterSheetPrompt(input: CharacterSheetInput): string {
  const dna = input.dna ?? {};
  const name = clean(input.name, 60);
  const species = clean(dna.species, 80);
  const silhouette = clean(dna.silhouette, 160);
  const height = clean(dna.heightBand, 40);
  const body = clean(dna.bodyDetail, 240);
  const face = clean(dna.faceFeatures, 240);
  const palette = paletteLine(dna.colorPalette ?? []);
  const outfit = clean(dna.outfitDetail || input.wardrobe, 240);
  const mark = clean(dna.distinguishingMark, 160);
  const prop = clean(dna.signatureProp, 120);
  const personality = (dna.personality ?? []).map((p) => clean(p, 40)).filter(Boolean).slice(0, 4);
  const base = clean(dna.imagePrompt || input.fallbackAppearance, 700);

  const lines: string[] = [];

  lines.push(
    `CHARACTER: ${name || "song performer"}${species ? ` — ${species}` : ""}. ONE single unique creature only.`
  );
  lines.push(
    `NEW DESIGN: invent THIS mascot from scratch. Ignore any other character card already on this Flow page. Do not clone, recolor, or substitute a previous mascot. Both panels are the same unique ${species || "character"} named ${name || "this performer"}.`
  );
  if (base) lines.push(`LOOK: ${base}`);
  const bodyBits = [silhouette && `silhouette ${silhouette}`, height && `height ${heightBandPhrase(height)}`, body]
    .filter(Boolean)
    .join("; ");
  if (bodyBits) lines.push(`BODY: ${bodyBits}.`);
  if (face) lines.push(`FACE: ${face}.`);
  if (palette) lines.push(`EXACT COLORS: ${palette}. No other dominant hue on this character.`);
  if (outfit) lines.push(`OUTFIT: ${outfit}. Blank garments — no letters, numbers, logos or readable prints on the clothes.`);
  if (mark) lines.push(`UNMISTAKABLE MARK: ${mark} — clearly visible in BOTH panels; this is how viewers tell them apart.`);
  if (prop) lines.push(`SIGNATURE PROP: ${prop}, held or worn naturally.`);
  if (personality.length > 0) {
    lines.push(`PERSONALITY READ: ${personality.join(", ")} — show it in posture, ear/tail set and expression.`);
  }
  lines.push(CHARACTER_CUTENESS_LOCK);
  lines.push(CHARACTER_MATERIAL_REALISM_LOCK);

  const others = (input.castmates ?? [])
    .map((m) => formatCastmateForbiddenLook(m))
    .filter(Boolean)
    .slice(0, 5);
  if (others.length > 0) {
    lines.push(
      `FORBIDDEN LOOKS (do not draw, copy, recolor, or swap in): ${others.join(" | ")}.`
    );
    lines.push(
      `DISTINCT FROM CASTMATES: ${name || "this character"} must be a different SPECIES, different SILHOUETTE, and different MAIN BODY COLOR than every forbidden look. Do not draw those characters here. Do not put a previous mascot on the left or right panel.`
    );
  }

  lines.push(`STYLE: ${clean(input.artStyle, 700)}`);
  lines.push(input.sheetLock);

  return lines.join("\n").replace(/[ \t]+/g, " ").trim();
}
