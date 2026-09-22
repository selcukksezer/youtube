import fs from "node:fs";
import path from "node:path";
import type { Clip } from "@prisma/client";
import { prisma } from "@/server/db";
import {
  splitIntoSentences,
  countWords,
  detectHook,
  maxWordsForClipSeconds,
  fitTextToMaxWords,
  speechFillRatioFor,
} from "@/server/services/splitter";
import { wpmForPace, getSettings } from "@/server/services/settings";
import { buildClipPrompt } from "@/server/services/prompt-builder";
import { finalizeFlowPrompt, FLOW_PROMPT_MAX } from "@/lib/flow-prompt-compact";
import { ensureProjectDirs } from "@/server/lib/paths";
import { recordEvent } from "@/server/lib/logger";
import { publishEvent } from "@/server/lib/events";
import { reportCuriosityFlow } from "@/server/services/curiosity";
import { emptyDialogueHint } from "@/lib/templates";
import { sanitizeKidsPromptForFlow } from "@/lib/flow-prompt-safety";
import { stripEmbeddedLookPack } from "@/lib/song-prompt-craft";
import { resolveClipCastMembers } from "@/server/services/song-refs";

/** Klip metnini gunceller; klip suresi kelime butcesine sigdirir ve sure tahminini hesaplar. */
export async function updateClipDialogue(clipId: string, dialogue: string): Promise<Clip> {
  const clip = await prisma.clip.findUniqueOrThrow({ where: { id: clipId } });
  const project = await prisma.project.findUniqueOrThrow({ where: { id: clip.projectId } });
  const settings = await getSettings();
  const wpm = wpmForPace(settings, project.speechPace);
  const maxWords = maxWordsForClipSeconds(project.clipSeconds, wpm, speechFillRatioFor(project.templateType));
  const fitted = fitTextToMaxWords(dialogue, maxWords);
  const words = countWords(fitted);
  const lastSentence = splitIntoSentences(fitted).pop() ?? "";
  const hook = detectHook(lastSentence);
  const updated = await prisma.clip.update({
    where: { id: clipId },
    data: {
      dialogue: fitted,
      estimatedWords: words,
      estimatedDurationSeconds: Number(((words / wpm) * 60).toFixed(1)),
      hasHook: hook.hasHook,
      curiosityScore: hook.score,
      prompt: "",
      status: clip.status === "completed" ? "draft" : clip.status,
    },
  });
  await persistClipsJson(clip.projectId);
  return updated;
}

/** Projeyi klip suresi / konusma hizina gore diyalog butcesine ceker. */
export async function fitProjectDialoguesToClipBudget(projectId: string): Promise<number> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const settings = await getSettings();
  const wpm = wpmForPace(settings, project.speechPace);
  const maxWords = maxWordsForClipSeconds(project.clipSeconds, wpm, speechFillRatioFor(project.templateType));
  const clips = await prisma.clip.findMany({
    where: { projectId, languageVariant: "primary" },
    orderBy: { index: "asc" },
  });

  let updated = 0;
  for (const clip of clips) {
    if (!clip.dialogue?.trim()) continue;
    const fitted = fitTextToMaxWords(clip.dialogue, maxWords);
    const words = countWords(fitted);
    const estimatedDurationSeconds = Number(((words / wpm) * 60).toFixed(1));
    const dialogueChanged = fitted !== clip.dialogue;
    if (!dialogueChanged && words === clip.estimatedWords && estimatedDurationSeconds === clip.estimatedDurationSeconds) {
      continue;
    }
    await prisma.clip.update({
      where: { id: clip.id },
      data: {
        dialogue: fitted,
        estimatedWords: words,
        estimatedDurationSeconds,
        ...(dialogueChanged ? { prompt: "" } : {}),
      },
    });
    updated++;
  }

  if (updated > 0) {
    await persistClipsJson(projectId);
    await recordEvent({
      projectId,
      step: "clips",
      message: `${updated} klip diyalogu ${project.clipSeconds} sn butcesine (~${maxWords} kelime) sigdirildi`,
    });
  }
  return updated;
}

export async function mergeClipWithNext(clipId: string): Promise<Clip> {
  const clip = await prisma.clip.findUniqueOrThrow({ where: { id: clipId } });
  const next = await prisma.clip.findFirst({
    where: { projectId: clip.projectId, languageVariant: clip.languageVariant, index: clip.index + 1 },
  });
  if (!next) throw new Error("Birlestirilecek sonraki klip yok");
  if (clip.status === "completed" || next.status === "completed") {
    throw new Error("Tamamlanmis klipler birlestirilemez");
  }

  const merged = await updateClipDialogue(clip.id, `${clip.dialogue} ${next.dialogue}`.trim());
  await prisma.clip.delete({ where: { id: next.id } });
  await renumberClips(clip.projectId, clip.languageVariant);
  await recordEvent({ projectId: clip.projectId, step: "clips", message: `Klip ${clip.index} ile ${next.index} birlestirildi` });
  return merged;
}

export async function splitClipInTwo(clipId: string): Promise<[Clip, Clip]> {
  const clip = await prisma.clip.findUniqueOrThrow({ where: { id: clipId } });
  if (clip.status === "completed") throw new Error("Tamamlanmis klip bolunemez");
  const sentences = splitIntoSentences(clip.dialogue);
  if (sentences.length < 2) throw new Error("Klip tek cumleden olusuyor; cumle sinirindan bolunemez");

  const totalWords = countWords(clip.dialogue);
  let acc = 0;
  let splitAt = 1;
  for (let i = 0; i < sentences.length - 1; i++) {
    acc += countWords(sentences[i]);
    if (acc >= totalWords / 2) {
      splitAt = i + 1;
      break;
    }
  }
  const firstText = sentences.slice(0, splitAt).join(" ");
  const secondText = sentences.slice(splitAt).join(" ");

  const laterClips = await prisma.clip.findMany({
    where: { projectId: clip.projectId, languageVariant: clip.languageVariant, index: { gt: clip.index } },
    orderBy: { index: "desc" },
  });
  for (const later of laterClips) {
    await prisma.clip.update({ where: { id: later.id }, data: { index: later.index + 1 } });
  }

  const first = await updateClipDialogue(clip.id, firstText);
  const project = await prisma.project.findUniqueOrThrow({ where: { id: clip.projectId } });
  const settings = await getSettings();
  const wpm = wpmForPace(settings, project.speechPace);
  const secondWords = countWords(secondText);
  const lastSentence = splitIntoSentences(secondText).pop() ?? "";
  const hook = detectHook(lastSentence);
  const second = await prisma.clip.create({
    data: {
      projectId: clip.projectId,
      languageVariant: clip.languageVariant,
      index: clip.index + 1,
      dialogue: secondText,
      estimatedWords: secondWords,
      estimatedDurationSeconds: Number(((secondWords / wpm) * 60).toFixed(1)),
      hasHook: hook.hasHook,
      curiosityScore: hook.score,
      status: "draft",
    },
  });
  await persistClipsJson(clip.projectId);
  await recordEvent({ projectId: clip.projectId, step: "clips", message: `Klip ${clip.index} ikiye bolundu` });
  return [first, second];
}

export async function reorderClips(projectId: string, orderedClipIds: string[]): Promise<void> {
  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant: "primary" } });
  const byId = new Map(clips.map((c) => [c.id, c]));
  if (orderedClipIds.length !== clips.length || orderedClipIds.some((id) => !byId.has(id))) {
    throw new Error("Siralama listesi klip setiyle eslesmiyor");
  }
  for (let i = 0; i < orderedClipIds.length; i++) {
    await prisma.clip.update({ where: { id: orderedClipIds[i] }, data: { index: -(i + 1) } });
  }
  for (let i = 0; i < orderedClipIds.length; i++) {
    await prisma.clip.update({ where: { id: orderedClipIds[i] }, data: { index: i + 1 } });
  }
  await persistClipsJson(projectId);
  await recordEvent({ projectId, step: "clips", message: "Klip siralamasi guncellendi" });
}

async function renumberClips(projectId: string, languageVariant: string): Promise<void> {
  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant }, orderBy: { index: "asc" } });
  for (let i = 0; i < clips.length; i++) {
    if (clips[i].index !== i + 1) {
      await prisma.clip.update({ where: { id: clips[i].id }, data: { index: -(i + 1) } });
    }
  }
  const renumbered = await prisma.clip.findMany({ where: { projectId, languageVariant }, orderBy: { index: "desc" } });
  for (const clip of renumbered) {
    if (clip.index < 0) {
      await prisma.clip.update({ where: { id: clip.id }, data: { index: -clip.index } });
    }
  }
}

/** Tum klipler icin Flow promptlarini uretir. */
export async function buildPromptsForProject(projectId: string, languageVariant = "primary"): Promise<Clip[]> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  // NOT: burada gorsel stil EZILMEZ. Eskiden canli-cekim secimi zorla
  // "pixar3d" yaziliyordu; ayarlari kaydetmek build-prompts'u tetikledigi
  // icin kullanicinin "gercekci canli cekim" secimi her seferinde 3D'ye
  // donuyordu. Aile secimi artik visualStyleFamilyOf ile prompt uretiminde
  // yapilir; bos stil zaten cocukta 3D varsayilanina duser.

  const allCharacters = await prisma.characterProfile.findMany({
    where: { projectId },
    orderBy: [{ role: "asc" }, { createdAt: "asc" }],
  });
  const character = allCharacters.find((c) => c.role === "main") ?? allCharacters[0] ?? null;
  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant }, orderBy: { index: "asc" } });
  if (clips.length === 0) throw new Error("Prompt uretilecek klip yok");

  const root = ensureProjectDirs(project.slug);
  const promptsDir = path.join(root, "prompts");

  const updated: Clip[] = [];
  for (const clip of clips) {
    // Look pack artik yalnizca [STYLE] blogunda yazilir; eski kayitlarda
    // sahne planinin icine de gomulmustu (tekrar = limit asimi).
    let imagePrompt = stripEmbeddedLookPack(sanitizeKidsPromptForFlow(clip.imagePrompt || ""));
    if (imagePrompt !== clip.imagePrompt) {
      await prisma.clip.update({ where: { id: clip.id }, data: { imagePrompt } });
    }

    const previousClip =
      clip.index > 1
        ? clips.find((c) => c.index === clip.index - 1 && c.languageVariant === clip.languageVariant) ?? null
        : null;

    const sceneCharacter =
      (clip.characterId ? allCharacters.find((c) => c.id === clip.characterId) : null) ?? character;
    const otherCast = allCharacters.filter((c) => c.id !== sceneCharacter?.id && c.id !== character?.id);
    // Bu sahnede GERCEKTEN gerekli kadro: soz + sahne aciklamasinda adi gecenler
    // (yoksa kucuk kadro/grup sinyaliyle hepsi, aksi halde bos — bkz. resolveClipCastMembers).
    const supportingCast = resolveClipCastMembers(`${clip.dialogue} ${clip.sceneDescription} ${imagePrompt}`, otherCast).map(
      (c) => ({
        name: c.name,
        role: c.role,
        storyRole: c.role === "main" ? "lead singer" : "support",
        baseAppearancePrompt: c.baseAppearancePrompt,
        baseWardrobePrompt: c.baseWardrobePrompt,
        flowCharacterReference: c.flowCharacterReference,
      })
    );

    const raw = buildClipPrompt({
      project,
      character,
      clip: { ...clip, imagePrompt },
      sceneCharacter,
      supportingCast,
      isFirstClip: clip.index === 1,
      previousClip,
      storyGearLock: "",
    });
    const { text: prompt, truncated } = finalizeFlowPrompt(
      raw,
      project.speechLanguage || "Turkish",
      FLOW_PROMPT_MAX
    );
    const saved = await prisma.clip.update({
      where: { id: clip.id },
      data: { prompt, status: clip.status === "draft" ? "pending" : clip.status },
    });
    fs.writeFileSync(path.join(promptsDir, `${String(clip.index).padStart(3, "0")}.txt`), prompt, "utf8");
    updated.push(saved);
    if (truncated) {
      await recordEvent({
        projectId,
        step: "prompts",
        level: "info",
        message: `Klip ${clip.index}: prompt ${FLOW_PROMPT_MAX} karaktere sigdirildi (Flow limiti)`,
      });
    }
  }

  await prisma.project.update({ where: { id: projectId }, data: { status: "prompts_ready" } });
  publishEvent(projectId, { type: "project", payload: { id: projectId, status: "prompts_ready" } });
  await recordEvent({
    projectId,
    step: "prompts",
    message: `${updated.length} klip icin Flow promptu uretildi (max ${FLOW_PROMPT_MAX} karakter)`,
  });

  const emptyDialogue = updated.filter((c) => !c.dialogue.trim()).length;
  if (emptyDialogue > 0) {
    await recordEvent({
      projectId,
      step: "prompts",
      level: "warning",
      message: `DIKKAT: ${emptyDialogue} sahnenin soz/diyalogu bos. ${emptyDialogueHint(project.templateType)}`,
    });
  }
  await reportCuriosityFlow(projectId);
  return updated;
}

export async function rebuildClipPrompt(clipId: string): Promise<Clip> {
  const clip = await prisma.clip.findUniqueOrThrow({ where: { id: clipId } });
  const project = await prisma.project.findUniqueOrThrow({ where: { id: clip.projectId } });
  const allCharacters = await prisma.characterProfile.findMany({
    where: { projectId: clip.projectId },
    orderBy: [{ role: "asc" }, { createdAt: "asc" }],
  });
  const character = allCharacters.find((c) => c.role === "main") ?? allCharacters[0] ?? null;
  const previousClip =
    clip.index > 1
      ? await prisma.clip.findFirst({
          where: { projectId: clip.projectId, languageVariant: clip.languageVariant, index: clip.index - 1 },
        })
      : null;
  const sceneCharacter =
    (clip.characterId ? allCharacters.find((c) => c.id === clip.characterId) : null) ?? character;
  let imagePrompt = stripEmbeddedLookPack(sanitizeKidsPromptForFlow(clip.imagePrompt || ""));
  if (imagePrompt !== clip.imagePrompt) {
    await prisma.clip.update({ where: { id: clip.id }, data: { imagePrompt } });
  }
  const otherCast = allCharacters.filter((c) => c.id !== sceneCharacter?.id && c.id !== character?.id);
  const supportingCast = resolveClipCastMembers(`${clip.dialogue} ${clip.sceneDescription} ${imagePrompt}`, otherCast).map(
    (c) => ({
      name: c.name,
      role: c.role,
      storyRole: c.role === "main" ? "lead singer" : "support",
      baseAppearancePrompt: c.baseAppearancePrompt,
      baseWardrobePrompt: c.baseWardrobePrompt,
      flowCharacterReference: c.flowCharacterReference,
    })
  );
  const { text: prompt } = finalizeFlowPrompt(
    buildClipPrompt({
      project,
      character,
      clip: { ...clip, imagePrompt },
      sceneCharacter,
      supportingCast,
      isFirstClip: clip.index === 1,
      previousClip,
      storyGearLock: "",
    }),
    project.speechLanguage || "Turkish",
    FLOW_PROMPT_MAX
  );
  const root = ensureProjectDirs(project.slug);
  fs.writeFileSync(path.join(root, "prompts", `${String(clip.index).padStart(3, "0")}.txt`), prompt, "utf8");
  return prisma.clip.update({ where: { id: clipId }, data: { prompt } });
}

export async function persistClipsJson(projectId: string): Promise<void> {
  const project = await prisma.project.findUnique({ where: { id: projectId } });
  if (!project) return;
  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant: "primary" }, orderBy: { index: "asc" } });
  const root = ensureProjectDirs(project.slug);
  fs.writeFileSync(
    path.join(root, "clips.json"),
    JSON.stringify(
      clips.map((c) => ({
        index: c.index,
        dialogue: c.dialogue,
        estimatedWords: c.estimatedWords,
        estimatedDurationSeconds: c.estimatedDurationSeconds,
        status: c.status,
        flowPrompt: c.prompt,
        attemptCount: c.attemptCount,
        videoPath: c.videoPath,
        lastFramePath: c.lastFramePath,
        errorMessage: c.errorMessage,
      })),
      null,
      2
    ),
    "utf8"
  );
}

export async function exportClipsCsv(projectId: string): Promise<string> {
  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant: "primary" }, orderBy: { index: "asc" } });
  const escape = (value: string) => `"${value.replace(/"/g, '""')}"`;
  const header = ["index", "dialogue", "estimatedWords", "estimatedDurationSeconds", "status", "attemptCount", "videoPath", "errorMessage"];
  const rows = clips.map((c) =>
    [
      c.index,
      escape(c.dialogue),
      c.estimatedWords,
      c.estimatedDurationSeconds,
      escape(c.status),
      c.attemptCount,
      escape(c.videoPath ?? ""),
      escape(c.errorMessage ?? ""),
    ].join(",")
  );
  return "\uFEFF" + [header.join(","), ...rows].join("\r\n");
}

export async function exportClipsJson(projectId: string): Promise<string> {
  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant: "primary" }, orderBy: { index: "asc" } });
  return JSON.stringify(
    clips.map((c) => ({
      index: c.index,
      dialogue: c.dialogue,
      estimatedWords: c.estimatedWords,
      estimatedDurationSeconds: c.estimatedDurationSeconds,
      status: c.status,
      flowPrompt: c.prompt,
      attemptCount: c.attemptCount,
      videoPath: c.videoPath,
      lastFramePath: c.lastFramePath,
      errorMessage: c.errorMessage,
    })),
    null,
    2
  );
}
