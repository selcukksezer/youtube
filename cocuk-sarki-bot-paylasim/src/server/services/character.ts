import fs from "node:fs";
import path from "node:path";
import { z } from "zod";
import type { CharacterProfile, Project } from "@prisma/client";
import { prisma } from "@/server/db";
import { generateImage, structuredCall } from "@/server/services/openai";
import { ensureProjectDirs, nextAvailablePath } from "@/server/lib/paths";
import { recordEvent } from "@/server/lib/logger";
import { syncSongDnaCardForCharacter } from "@/server/services/song-dna";

/**
 * Karakter profili, Karakter Kilidi ve referans gorsel yonetimi.
 */

export const ALLOWED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];

/** Ana karakteri getirir; yoksa varsayilan degerlerle olusturur. */
export async function getOrCreateMainCharacter(projectId: string): Promise<CharacterProfile> {
  const existing = await prisma.characterProfile.findFirst({ where: { projectId, role: "main" } });
  if (existing) return existing;
  return prisma.characterProfile.create({ data: { projectId, role: "main" } });
}

/** Yas kontrolu: 18 alti kabul edilmez; yetiskin varsayilani 20. */
export function normalizeAge(age: number | undefined): number {
  if (!age || age < 18) return 20;
  return age;
}

/**
 * Karakter Kilidi promptlarini profil alanlarindan uretir.
 * Bu metinler her klipte AYNEN kullanilir; hikaye parcasi disinda degismez.
 */
export function buildCharacterLock(profile: CharacterProfile): {
  baseAppearancePrompt: string;
  baseWardrobePrompt: string;
  baseEnvironmentPrompt: string;
  baseCameraPrompt: string;
  baseVoicePrompt: string;
} {
  // Kadro (side) karakterleri: cast.ts zaten cinsiyet, sac, goz, ten ve
  // yapi bilgisini tek tek belirtilmis, ic ice gecmis tam bir gorunum
  // metni olarak uretti (bkz. composeCastAppearance). Burada fragmanlardan
  // yeniden kurmaya calismak bu bilgiyi KAYBEDER — ornegin cinsiyet
  // asagida "woman" olarak sabitlenirdi ve "Sinan" gibi erkek bir kadro
  // karakteri kadin yuzuyle uretilirdi. O yuzden side karakterler icin
  // saklanan alanlari OLDUGU GIBI kullaniyoruz.
  if (profile.role === "side") {
    return {
      baseAppearancePrompt: profile.baseAppearancePrompt || profile.imagePrompt || "",
      baseWardrobePrompt: profile.wardrobe || profile.baseWardrobePrompt || "",
      baseEnvironmentPrompt: profile.environment || profile.baseEnvironmentPrompt || "",
      baseCameraPrompt: "Fixed tripod camera. No cuts, no zoom, no camera movement, no angle change.",
      baseVoicePrompt: profile.voiceCharacter || profile.baseVoicePrompt || "",
    };
  }

  const appearance: string[] = [];
  appearance.push(`A ${profile.age}-year-old adult`);
  if (profile.nationalityLook) appearance.push(profile.nationalityLook);
  appearance.push(profile.gender === "male" ? "man" : "woman"); // anlatici sablonu varsayilan olarak kadin
  if (profile.hair) appearance.push(`with ${profile.hair}`);
  if (profile.faceFeatures) appearance.push(profile.faceFeatures);
  if (profile.makeup) appearance.push(`makeup: ${profile.makeup}`);
  if (profile.role === "main" && profile.storyNote.trim()) {
    appearance.push(`must match this brief exactly: ${profile.storyNote.trim()}`);
  }

  const camera: string[] = [];
  if (profile.bodyFraming) camera.push(profile.bodyFraming);
  if (profile.cameraAngle) camera.push(profile.cameraAngle);
  if (profile.lensLook) camera.push(`lens: ${profile.lensLook}`);
  camera.push("Fixed tripod camera. No cuts, no zoom, no camera movement, no angle change.");

  const environment: string[] = [];
  if (profile.environment) environment.push(profile.environment);
  if (profile.sittingPose) environment.push(`${profile.gender === "male" ? "He" : "She"} is ${profile.sittingPose}`);
  if (profile.lighting) environment.push(`Lighting: ${profile.lighting}`);
  if (profile.background) environment.push(`Background: ${profile.background}`);

  const voice: string[] = [];
  if (profile.voiceCharacter) voice.push(profile.voiceCharacter);
  if (profile.emotionTone) voice.push(`emotional tone: ${profile.emotionTone}`);
  if (profile.gestureLevel) voice.push(`gesture level: ${profile.gestureLevel}`);

  return {
    baseAppearancePrompt: appearance.join(", ") + ".",
    baseWardrobePrompt: profile.wardrobe || "",
    baseEnvironmentPrompt: environment.join(". "),
    baseCameraPrompt: camera.join(". "),
    baseVoicePrompt: voice.join(", "),
  };
}

/**
 * Ses kilidinden sabit duygu tonu parcasini cikarir.
 *
 * Ayni karakterle yeni film acildiginda ses KIMLIGI (tini, aksan, tempo) korunur
 * ama eski filmden gelen sabit duygu tonu tasinmaz — duygu her klipte sahnenin
 * kendi senaryosundan gelir.
 */
export function stripEmotionTonePhrase(voicePrompt: string | null | undefined): string {
  return (voicePrompt || "")
    .replace(/,?\s*emotional tone:[^,.]*/gi, "")
    .replace(/\s{2,}/g, " ")
    .replace(/^[,.\s]+/, "")
    .replace(/[,\s]+$/, "")
    .trim();
}

/** Profili gunceller ve Karakter Kilidi promptlarini yeniden uretir. */
export async function updateCharacterProfile(
  characterId: string,
  data: Partial<
    Pick<
      CharacterProfile,
      | "name"
      | "age"
      | "adult"
      | "gender"
      | "nationalityLook"
      | "hair"
      | "faceFeatures"
      | "makeup"
      | "wardrobe"
      | "bodyFraming"
      | "sittingPose"
      | "gestureLevel"
      | "voiceCharacter"
      | "emotionTone"
      | "environment"
      | "lighting"
      | "cameraAngle"
      | "lensLook"
      | "background"
      | "negativePrompt"
      | "flowCharacterReference"
      | "storyNote"
    >
  >
): Promise<CharacterProfile> {
  const normalizedAge = data.age !== undefined ? normalizeAge(data.age) : undefined;
  const updated = await prisma.characterProfile.update({
    where: { id: characterId },
    data: { ...data, ...(normalizedAge !== undefined ? { age: normalizedAge, adult: true } : {}) },
  });
  const lock = buildCharacterLock(updated);
  const saved = await prisma.characterProfile.update({ where: { id: characterId }, data: lock });
  await syncSongDnaCardForCharacter(characterId);
  return prisma.characterProfile.findUniqueOrThrow({ where: { id: saved.id } });
}

export const characterNoteExpandSchema = z.object({
  name: z.string().min(1),
  age: z.number().int(),
  gender: z.enum(["female", "male"]),
  nationalityLook: z.string(),
  hair: z.string(),
  faceFeatures: z.string(),
  makeup: z.string(),
  wardrobe: z.string(),
  bodyFraming: z.string(),
  sittingPose: z.string(),
  gestureLevel: z.string(),
  voiceCharacter: z.string(),
  emotionTone: z.string(),
  environment: z.string(),
  lighting: z.string(),
  cameraAngle: z.string(),
  lensLook: z.string(),
  background: z.string(),
  negativePrompt: z.string(),
});

export type ExpandedCharacterNote = z.infer<typeof characterNoteExpandSchema>;

const NOTE_EXPAND_JSON: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  properties: {
    name: { type: "string" },
    age: { type: "integer" },
    gender: { type: "string", enum: ["female", "male"] },
    nationalityLook: { type: "string" },
    hair: { type: "string" },
    faceFeatures: { type: "string" },
    makeup: { type: "string" },
    wardrobe: { type: "string" },
    bodyFraming: { type: "string" },
    sittingPose: { type: "string" },
    gestureLevel: { type: "string" },
    voiceCharacter: { type: "string" },
    emotionTone: { type: "string" },
    environment: { type: "string" },
    lighting: { type: "string" },
    cameraAngle: { type: "string" },
    lensLook: { type: "string" },
    background: { type: "string" },
    negativePrompt: { type: "string" },
  },
  required: [
    "name",
    "age",
    "gender",
    "nationalityLook",
    "hair",
    "faceFeatures",
    "makeup",
    "wardrobe",
    "bodyFraming",
    "sittingPose",
    "gestureLevel",
    "voiceCharacter",
    "emotionTone",
    "environment",
    "lighting",
    "cameraAngle",
    "lensLook",
    "background",
    "negativePrompt",
  ],
};

/** OpenAI yoksa veya cagri dusurse notu kilide yine de gommek icin yedek. */
export function fallbackExpandCharacterNote(note: string, existingName?: string): ExpandedCharacterNote {
  const brief = note.replace(/\s+/g, " ").trim();
  const name = existingName?.trim() || "Lena";
  return {
    name,
    age: 20,
    gender: "female",
    nationalityLook: "",
    hair: brief,
    faceFeatures: brief,
    makeup: "natural adult makeup, no beauty-filter look",
    wardrobe: brief,
    bodyFraming: "full body visible, natural adult proportions",
    sittingPose: "standing then seated as the scene requires, relaxed adult posture",
    gestureLevel: "subtle",
    voiceCharacter: "calm warm adult female voice",
    emotionTone: "natural, scene-led",
    environment: "clean cinematic interior matching the story",
    lighting: "soft natural key light",
    cameraAngle: "eye-level fixed camera",
    lensLook: "natural 35mm photographic look",
    background: "uncluttered, no readable text",
    negativePrompt: "no child, no teen, no underage, no text, no watermark, no logo",
  };
}

export function flowHandleFromName(name: string): string {
  const cleaned = name.replace(/^@+/, "").replace(/[^\p{L}\p{N}]+/gu, "").trim();
  return cleaned ? `@${cleaned}` : "";
}

/** Kullanici notasini sahne kilidi alanlarina cevirir (Ingilizce uretim alanlari). */
export async function expandCharacterNote(
  note: string,
  options?: { existingName?: string; language?: string; genre?: string }
): Promise<ExpandedCharacterNote> {
  const brief = note.replace(/\s+/g, " ").trim();
  if (!brief) throw new Error("Karakter notu bos");
  try {
    const result = await structuredCall<ExpandedCharacterNote>({
      system: `You expand a short informal character note into a complete adult character bible for video production.
Rules:
- Adult only. Age must be 18-45. If age is missing, use 22.
- Keep EVERY user detail (hair, eyes, clothes, body, mood). Expand it into concrete visual English, do not drop or soften it.
- Do not invent a different person. Do not make the look more modest or more glamorous than the note.
- Fields are English production phrases, not Turkish labels.
- name: short given name; reuse existing name if provided.
- hair / faceFeatures / wardrobe must be detailed enough for a still photo (color, length, texture, fit, fabric).
- bodyFraming: how much body is visible; honor the note if it asks for full body.
- cameraAngle default "eye-level fixed camera"; lensLook default "natural 35mm".
- negativePrompt: block children, text, watermark, extra people.`,
      user: [
        `User note: ${brief}`,
        options?.existingName ? `Existing name (keep unless note names someone else): ${options.existingName}` : "",
        options?.language ? `Story language: ${options.language}` : "",
        options?.genre ? `Genre: ${options.genre}` : "",
      ]
        .filter(Boolean)
        .join("\n"),
      schemaName: "character_note_expand",
      jsonSchema: NOTE_EXPAND_JSON,
      zodSchema: characterNoteExpandSchema,
      maxOutputTokens: 4_000,
    });
    return {
      ...result,
      name: result.name.trim() || options?.existingName?.trim() || "Lena",
      age: normalizeAge(result.age),
    };
  } catch {
    return fallbackExpandCharacterNote(brief, options?.existingName);
  }
}

export async function applyCharacterNote(projectId: string, note: string): Promise<CharacterProfile> {
  const brief = note.replace(/\s+/g, " ").trim();
  if (!brief) throw new Error("Karakter notu bos");
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const main = await getOrCreateMainCharacter(projectId);
  const expanded = await expandCharacterNote(brief, {
    existingName: main.name,
    language: project.speechLanguage,
    genre: project.genre,
  });
  const { name, age, gender, ...rest } = expanded;
  return updateCharacterProfile(main.id, {
    ...rest,
    name,
    age,
    gender,
    storyNote: brief,
    flowCharacterReference: flowHandleFromName(name) || main.flowCharacterReference,
  });
}

/** Kullanicinin yukledigi referans gorselini proje klasorune kopyalar. */
export async function saveUploadedCharacterImage(
  project: Project,
  characterId: string,
  file: { name: string; buffer: Buffer }
): Promise<CharacterProfile> {
  const ext = path.extname(file.name).toLowerCase();
  if (!ALLOWED_IMAGE_EXTENSIONS.includes(ext)) {
    throw new Error(`Desteklenmeyen gorsel bicimi: ${ext}. Desteklenen: ${ALLOWED_IMAGE_EXTENSIONS.join(", ")}`);
  }
  if (file.buffer.length < 1024) throw new Error("Gorsel dosyasi cok kucuk veya bos");
  if (file.buffer.length > 25 * 1024 * 1024) throw new Error("Gorsel dosyasi 25MB sinirini asiyor");

  const root = ensureProjectDirs(project.slug);
  const target = nextAvailablePath(path.join(root, "character", `reference${ext}`));
  fs.writeFileSync(target, file.buffer);

  await prisma.characterProfile.update({
    where: { id: characterId },
    data: { referenceImagePath: target, imageApproved: true },
  });
  await prisma.generatedAsset.create({
    data: { projectId: project.id, kind: "character_image", path: target, bytes: file.buffer.length, meta: JSON.stringify({ source: "upload" }) },
  });
  await recordEvent({ projectId: project.id, step: "character", message: `Karakter referans gorseli yuklendi (${path.basename(target)})` });
  await syncSongDnaCardForCharacter(characterId);
  return prisma.characterProfile.findUniqueOrThrow({ where: { id: characterId } });
}

const characterImagePromptSchema = z.object({ prompt: z.string().min(20) });

/** Karakter tanimlarindan gorsel uretim promptu olusturur. */
export async function buildCharacterImagePrompt(project: Project, profile: CharacterProfile): Promise<string> {
  if (profile.imagePrompt.trim()) return profile.imagePrompt;
  const lock = buildCharacterLock(profile);
  const result = await structuredCall<{ prompt: string }>({
    system:
      "You write concise, high-quality image generation prompts. Output English only. The image must contain a single adult character facing the camera, seated, face clearly visible, natural hands, no text or watermark. Preserve EVERY physical detail from the description exactly: gender, hair, eyes, skin tone, accessories (watch, rings, earrings, necklace, glasses) in their stated placement, and clothing condition (crisp, worn, faded or torn). Do not beautify, clean up or change any detail.",
    user: `Create an image generation prompt for a character reference photo.
Character: ${lock.baseAppearancePrompt}
Wardrobe: ${lock.baseWardrobePrompt}
Environment (the video will be generated in the same environment): ${lock.baseEnvironmentPrompt}
Camera: medium close-up, facing camera, seated.
Aspect ratio: ${project.aspectRatio}.
Style: photorealistic, cinematic lighting, sharp focus on face, visible skin pores, individual hair strands, fabric weave and stitching.`,
    schemaName: "image_prompt",
    jsonSchema: {
      type: "object",
      additionalProperties: false,
      properties: { prompt: { type: "string" } },
      required: ["prompt"],
    },
    zodSchema: characterImagePromptSchema,
  });
  return result.prompt;
}

/** OpenAI ile karakter referans gorseli uretir (onay kullanicida). */
export async function generateCharacterImage(projectId: string, customPrompt?: string): Promise<CharacterProfile> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const profile = await getOrCreateMainCharacter(projectId);

  const prompt = customPrompt?.trim() || (await buildCharacterImagePrompt(project, profile));
  await recordEvent({ projectId, step: "character", message: "Karakter gorseli uretimi baslatildi (gpt-image-1)" });

  const aspect = project.aspectRatio === "9:16" ? "9:16" : "16:9";
  const buffer = await generateImage(prompt, aspect);

  const root = ensureProjectDirs(project.slug);
  const target = nextAvailablePath(path.join(root, "character", "reference-generated.png"));
  fs.writeFileSync(target, buffer);

  const character = await prisma.characterProfile.update({
    where: { id: profile.id },
    data: { referenceImagePath: target, imagePrompt: prompt, imageApproved: false },
  });
  await prisma.generatedAsset.create({
    data: { projectId, kind: "character_image", path: target, bytes: buffer.length, meta: JSON.stringify({ source: "gpt-image-1" }) },
  });
  await recordEvent({ projectId, step: "character", message: "Karakter gorseli uretildi; kullanici onayi bekleniyor" });
  await syncSongDnaCardForCharacter(profile.id);
  return prisma.characterProfile.findUniqueOrThrow({ where: { id: profile.id } });
}

/** Uretilen gorseli onaylar (Flow otomasyonu onaysiz gorselle baslamaz). */
export async function approveCharacterImage(characterId: string): Promise<CharacterProfile> {
  await prisma.characterProfile.update({ where: { id: characterId }, data: { imageApproved: true } });
  await syncSongDnaCardForCharacter(characterId);
  return prisma.characterProfile.findUniqueOrThrow({ where: { id: characterId } });
}
