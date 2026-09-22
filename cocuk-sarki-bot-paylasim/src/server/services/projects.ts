import fs from "node:fs";
import path from "node:path";
import { z } from "zod";
import type { Project } from "@prisma/client";
import { prisma } from "@/server/db";
import { ensureProjectDirs, safeProjectPath, slugify } from "@/server/lib/paths";
import { getSettings, wpmForPace } from "@/server/services/settings";
import { buildCharacterLock, normalizeAge } from "@/server/services/character";
import { recordEvent } from "@/server/lib/logger";

function computeTargetWords(targetDurationSeconds: number, wpm: number): number {
  return Math.round((targetDurationSeconds / 60) * wpm);
}

/**
 * Proje olusturma / listeleme / silme ve ornek test projesi.
 */

export const createProjectSchema = z.object({
  name: z.string().min(1, "Proje adi gerekli").max(120),
  title: z.string().default(""),
  topic: z.string().default(""),
  genre: z.string().default("gizem"),
  targetDurationSeconds: z.number().int().min(20).max(3600).default(180),
  // Dil adlari Ingilizce saklanir: Flow'a giden yonetmen talimatlari Ingilizcedir
  // ("She speaks clearly in Turkish") ve model bunu daha guvenilir yorumlar.
  storyLanguage: z.string().default("Turkish"),
  speechLanguage: z.string().default("Turkish"),
  audience: z.string().default(""),
  narrationStyle: z.string().default(""),
  openingHook: z.string().default(""),
  avoidList: z.string().default(""),
  speechPace: z.enum(["slow", "normal", "fast"]).default("normal"),
  targetWordCount: z.number().int().min(0).default(0),
  templateType: z.enum(["kids_song"]).default("kids_song"),
  longformSettings: z.string().default(""),
  seriesHook: z.string().default(""),
  flowModel: z.string().default(""),
  // 0 = ayarlar ekranindaki varsayilan klip suresi kullanilir
  clipSeconds: z
    .number()
    .int()
    .max(20)
    .default(0)
    .refine((v) => v === 0 || v >= 2, { message: "Klip suresi en az 2 saniye olmali (0 = varsayilan)" }),
  aspectRatio: z.string().default(""),
  outputsPerGeneration: z.number().int().min(1).max(4).default(1),
  audioEnabled: z.boolean().default(true),
  useReference: z.boolean().default(true),
  useFlowCharacter: z.boolean().default(false),
  useStartFrame: z.boolean().default(false),
  usePrevLastFrame: z.boolean().default(true),
  reuseFlowProject: z.boolean().default(true),
  flowProjectName: z.string().default(""),
  flowProjectUrl: z.string().default(""),
  generateButtonMode: z.enum(["auto", "manual"]).default("auto"),
  automationMode: z.enum(["full", "semi"]).default("full"),
  allowSubtitles: z.boolean().default(false),
  ageBand: z.string().default(""),
  moralLesson: z.string().default(""),
  visualStyle: z.string().default(""),
  channelName: z.string().default(""),
  character: z
    .object({
      name: z.string().default(""),
      age: z.number().int().default(20),
      nationalityLook: z.string().default(""),
      hair: z.string().default(""),
      faceFeatures: z.string().default(""),
      makeup: z.string().default(""),
      wardrobe: z.string().default(""),
      bodyFraming: z.string().default(""),
      sittingPose: z.string().default(""),
      gestureLevel: z.string().default(""),
      voiceCharacter: z.string().default(""),
      emotionTone: z.string().default(""),
      environment: z.string().default(""),
      lighting: z.string().default(""),
      cameraAngle: z.string().default(""),
      lensLook: z.string().default(""),
      background: z.string().default(""),
      negativePrompt: z.string().default(""),
      flowCharacterReference: z.string().default(""),
    })
    .optional(),
});

export type CreateProjectInput = z.infer<typeof createProjectSchema>;

async function uniqueSlug(base: string): Promise<string> {
  let slug = slugify(base);
  let i = 2;
  while (await prisma.project.findUnique({ where: { slug } })) {
    slug = `${slugify(base)}-${i}`;
    i++;
  }
  return slug;
}

export async function createProject(input: CreateProjectInput): Promise<Project> {
  const settings = await getSettings();
  const slug = await uniqueSlug(input.name);
  const wpm = wpmForPace(settings, input.speechPace);
  const targetWordCount = input.targetWordCount > 0 ? input.targetWordCount : computeTargetWords(input.targetDurationSeconds, wpm);

  const project = await prisma.project.create({
    data: {
      name: input.name,
      slug,
      title: input.title,
      topic: input.topic,
      genre: input.genre,
      targetDurationSeconds: input.targetDurationSeconds,
      storyLanguage: input.storyLanguage,
      speechLanguage: input.speechLanguage,
      audience: input.audience,
      narrationStyle: input.narrationStyle,
      openingHook: input.openingHook,
      avoidList: input.avoidList,
      speechPace: input.speechPace,
      targetWordCount,
      templateType: input.templateType,
      flowModel: input.flowModel || settings.defaultFlowModel,
      clipSeconds: input.clipSeconds || settings.defaultClipSeconds,
      aspectRatio: input.aspectRatio || settings.defaultAspectRatio,
      outputsPerGeneration: input.outputsPerGeneration,
      audioEnabled: input.templateType === "kids_song" ? false : input.audioEnabled,
      useReference: input.useReference,
      useFlowCharacter: input.useFlowCharacter,
      useStartFrame: input.useStartFrame,
      usePrevLastFrame: input.usePrevLastFrame,
      reuseFlowProject: input.reuseFlowProject,
      flowProjectName: input.flowProjectName,
      flowProjectUrl: input.flowProjectUrl.trim(),
      generateButtonMode: input.generateButtonMode,
      automationMode: input.automationMode,
      allowSubtitles: false,
      ageBand: input.ageBand,
      moralLesson: input.moralLesson,
      visualStyle: input.visualStyle,
      channelName: input.channelName,
      seriesHook: input.seriesHook || "",
      longformSettings: "{}",
    },
  });

  // Ana karakter profili
  const characterInput = input.character;
  const character = await prisma.characterProfile.create({
    data: {
      projectId: project.id,
      role: "main",
      name: characterInput?.name ?? "",
      age: normalizeAge(characterInput?.age),
      adult: true,
      nationalityLook: characterInput?.nationalityLook ?? "",
      hair: characterInput?.hair ?? "",
      faceFeatures: characterInput?.faceFeatures ?? "",
      makeup: characterInput?.makeup ?? "",
      wardrobe: characterInput?.wardrobe ?? "",
      bodyFraming: characterInput?.bodyFraming ?? "",
      sittingPose: characterInput?.sittingPose ?? "",
      gestureLevel: characterInput?.gestureLevel ?? "",
      voiceCharacter: characterInput?.voiceCharacter ?? "",
      emotionTone: characterInput?.emotionTone ?? "",
      environment: characterInput?.environment ?? "",
      lighting: characterInput?.lighting ?? "",
      cameraAngle: characterInput?.cameraAngle ?? "",
      lensLook: characterInput?.lensLook ?? "",
      background: characterInput?.background ?? "",
      negativePrompt: characterInput?.negativePrompt ?? "",
      flowCharacterReference: characterInput?.flowCharacterReference ?? "",
    },
  });
  const lock = buildCharacterLock(character);
  await prisma.characterProfile.update({ where: { id: character.id }, data: lock });

  const root = ensureProjectDirs(slug);
  fs.writeFileSync(
    path.join(root, "project.json"),
    JSON.stringify({ id: project.id, name: project.name, slug, templateType: project.templateType, createdAt: project.createdAt }, null, 2),
    "utf8"
  );

  await recordEvent({ projectId: project.id, step: "project", message: `Proje olusturuldu: ${project.name} (${project.templateType})` });
  return project;
}

/**
 * Bos sarki klibi projesi.
 * URETIM AYARLARI MIRASI: her yeni proje, en son olusturulan sarki projesinin
 * ayarlariyla dogar (model, sure, oran, referans/karakter anahtarlari, stil,
 * dil, tempo, ozel prompt sablonu...). Boylece bir kez yapilan ayar 100 projede
 * de ayni gecerli olur. Icerik alanlari (ad, baslik, konu, sozler) miras ALINMAZ.
 */
export async function createQuickSongProject(): Promise<Project> {
  const settings = await getSettings();
  const last = await prisma.project.findFirst({
    where: { templateType: "kids_song" },
    orderBy: { createdAt: "desc" },
  });
  const stamp = new Date().toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const project = await createProject(
    createProjectSchema.parse({
      name: `Yeni sarki klibi ${stamp}`,
      title: "",
      topic: "",
      genre: "Cocuk sarkisi",
      templateType: "kids_song",
      targetDurationSeconds: last?.targetDurationSeconds ?? 90,
      storyLanguage: last?.storyLanguage || "Turkish",
      speechLanguage: last?.speechLanguage || "Turkish",
      speechPace: (last?.speechPace as "slow" | "normal" | "fast") || "normal",
      audience: last?.audience ?? "",
      avoidList: last?.avoidList ?? "",
      flowModel: last?.flowModel || settings.defaultFlowModel,
      clipSeconds: last?.clipSeconds || settings.defaultClipSeconds,
      aspectRatio: last?.aspectRatio || settings.defaultAspectRatio,
      outputsPerGeneration: last?.outputsPerGeneration ?? 1,
      audioEnabled: false,
      useReference: last?.useReference ?? true,
      useFlowCharacter: last?.useFlowCharacter ?? false,
      useStartFrame: last?.useStartFrame ?? false,
      usePrevLastFrame: last?.usePrevLastFrame ?? true,
      reuseFlowProject: last?.reuseFlowProject ?? true,
      flowProjectName: last?.flowProjectName ?? "",
      // Ayni Flow projesini miras almak paralel otomasyonda prompt/indirme carpisir.
      flowProjectUrl: "",
      generateButtonMode: (last?.generateButtonMode as "auto" | "manual") || "auto",
      automationMode: (last?.automationMode as "full" | "semi") || "full",
      ageBand: last?.ageBand || "3-5",
      narrationStyle: last?.narrationStyle || "kidspop",
      visualStyle: last?.visualStyle || "pixar3d",
      channelName: last?.channelName ?? "",
    })
  );
  // Sema disi sabitler de mirasa dahil: ozel prompt sablonu
  if (last?.promptTemplate?.trim()) {
    await prisma.project.update({ where: { id: project.id }, data: { promptTemplate: last.promptTemplate } });
  }
  if (last) {
    await recordEvent({
      projectId: project.id,
      step: "project",
      message: `Uretim ayarlari "${last.name}" projesinden miras alindi (model, sure, oran, stil, anahtarlar)`,
    });
  }
  return project;
}

/** Eski sablon projelerini siler (kids_song disindaki tum kayitlar). */
export async function purgeLegacyProjects(deleteFiles = true): Promise<{ deleted: number }> {
  const legacy = await prisma.project.findMany({
    where: { NOT: { templateType: "kids_song" } },
    select: { id: true, slug: true, name: true },
  });
  for (const p of legacy) {
    await deleteProject(p.id, deleteFiles);
  }
  return { deleted: legacy.length };
}

/** Projeyi ve istege bagli olarak dosyalarini siler. */
export async function deleteProject(projectId: string, deleteFiles: boolean): Promise<void> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  await prisma.project.delete({ where: { id: projectId } });
  if (deleteFiles) {
    const root = safeProjectPath(project.slug);
    if (fs.existsSync(root)) fs.rmSync(root, { recursive: true, force: true });
  }
  await recordEvent({ step: "project", message: `Proje silindi: ${project.name}${deleteFiles ? " (dosyalar dahil)" : ""}` });
}

/** Kurulum sihirbazindaki ornek test projesi. */
export async function createSampleProject(): Promise<Project> {
  const clip1 = "Kucuk yildiz parliyor, gokyuzunde dans ediyor.";
  const clip2 = "Bir iki uc, dort bes alti, saymayi ogrenelim birlikte.";
  const clip3 = "El ele tutusup, neseyle sarkimizi soyleyelim!";

  const project = await createProject(
    createProjectSchema.parse({
      name: "Ornek Sarki Klibi",
      title: "Kucuk Yildiz",
      topic: "Sayma ve dans",
      genre: "egitici",
      targetDurationSeconds: 60,
      speechPace: "normal",
      visualStyle: "pixar3d",
      character: {
        name: "Yildiz",
        age: 20,
        nationalityLook: "Turkish",
        hair: "short brown hair",
        faceFeatures: "round friendly face, big expressive eyes",
        wardrobe: "colorful kids music-video outfit",
        gestureLevel: "energetic dance gestures",
        voiceCharacter: "bright cheerful singing voice",
        negativePrompt: "no scary imagery, no weapons, no violence",
      },
    })
  );

  const settings = await getSettings();
  const wpm = wpmForPace(settings, "normal");
  const dialogues = [clip1, clip2, clip3];
  for (let i = 0; i < dialogues.length; i++) {
    const words = dialogues[i].split(/\s+/).length;
    await prisma.clip.create({
      data: {
        projectId: project.id,
        languageVariant: "primary",
        index: i + 1,
        dialogue: dialogues[i],
        estimatedWords: words,
        estimatedDurationSeconds: Number(((words / wpm) * 60).toFixed(1)),
        hasHook: i === 2,
        curiosityScore: i === 2 ? 7 : 5,
        status: "draft",
        sceneDescription: `Sarki sahnesi ${i + 1}`,
        imagePrompt: `3D Pixar-style music video scene ${i + 1}, colorful stage, singer dancing`,
      },
    });
  }
  await prisma.project.update({ where: { id: project.id }, data: { status: "clips_ready" } });
  await recordEvent({ projectId: project.id, step: "project", message: "Ornek sarki klibi test projesi hazir" });
  return project;
}
