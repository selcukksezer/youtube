import fs from "node:fs";
import path from "node:path";
import type { CharacterProfile, Project } from "@prisma/client";
import { prisma } from "@/server/db";
import { ensureProjectDirs, nextAvailablePath } from "@/server/lib/paths";
import { recordEvent } from "@/server/lib/logger";
import { extractFrameAt, probeVideo } from "@/server/services/ffmpeg";
import { buildCharacterLock, flowHandleFromName, getOrCreateMainCharacter } from "@/server/services/character";
import { engineStatus } from "@/server/automation/engine";
import {
  configureGeneration,
  createFlowCharacter,
  dismissFlowOverlays,
  downloadClipVideo,
  downloadImageAsset,
  enterPrompt,
  ensureFlowReady,
  ensureImageOutputMode,
  ensureVideoOutputMode,
  finalizeFlowCharacter,
  openCharactersPage,
  openFlowProject,
  returnToProjectEditor,
  saveImageFromElement,
  selectImageModel,
  startGeneration,
  waitForCompletion,
  waitForImageCompletion,
  waitForNewCharacterImage,
  isFlowWindowClosedError,
} from "@/server/automation/flow-adapter";
import { getProjectPage, openFlowBrowser } from "@/server/automation/browser";
import { enqueueProjectWork } from "@/server/automation/abort";
import { isKidsContent } from "@/lib/templates";
import { getSettings, parseModelSupportMatrix, resolveModelSupport } from "@/server/services/settings";
import { resolveSongVarietyPack, stripGenericStudioLabels } from "@/lib/song-variety";
import { dnaCardSchema, type DnaCard } from "@/lib/song-character";
import {
  CHARACTER_CUTENESS_LOCK,
  CHARACTER_MATERIAL_REALISM_LOCK,
  composeCharacterSheetPrompt,
  type CastmateLock,
} from "@/lib/song-character-sheet";
import { convertShotPlanToLiveAction, visualStyleFamilyOf, worldFamilyLock } from "@/lib/visual-style-family";

/**
 * Flow ile karakter referans gorseli.
 *
 * 1) BIRINCIL — KARAKTERLER SAYFASI (.../project/<id>/characters):
 *    Flow'un karakterlere ozel sayfasinda karakter TARIFTEN olusturulur
 *    (Nano Banana). Karakter adiyla kaydedilir ve kliplerde @adiyla
 *    cagirilabilir; profile otomatik @referans yazilir. Video uretilmez.
 *
 * 2) IKINCIL — GORSEL MODU: prompt cubugundaki cikti turu menusunden gorsel
 *    uretimine gecilip Nano Banana ile karakter fotografi uretilir.
 *
 * 3) SON CARE — KISA VIDEO + KARE CIKARMA: yukaridakiler kalibre edilemezse
 *    modelin destekledigi EN KISA surede sessiz bir video uretilir ve
 *    ortasindan kare alinir.
 *
 * Referans bicimi (cocuk + anlatici): TEK gorselde ON + ARKA turnaround.
 * Uc-ceyrek / yan / rastgele poz YASAK — Flow bunlari ayri kisi sanir.
 */

function kidsArtLock(project: Project): { style: string; identity: string } {
  // Kullanici "Gercekci canli cekim" sectiyse karakter de GERCEK olmali:
  // stüdyoda cekilmis el yapimi maskot/kukla fotografi — CGI render degil.
  if (visualStyleFamilyOf(project.templateType, project.visualStyle) === "live-action") {
    return {
      style: [
        "Photorealistic LIVE-ACTION photograph of ONE real, physically built mascot performer (premium movie-grade handcrafted fur-suit / practical puppet).",
        "Real dense fur fibers with combed pile, real stitched fabric and embroidered seams, living glass eyes with genuine catchlights, real fabric weight and wrinkles.",
        "Shot on a professional cinema camera with soft studio key light and true optical depth of field.",
        "Absolutely NOT a CGI render, NOT a cartoon, NOT an illustration — indistinguishable from a real photograph.",
        worldFamilyLock("live-action"),
      ].join(" "),
      identity:
        "Same single REAL mascot performer in BOTH panels — identical build, fur, colors, costume and proportions, photographed in the same studio setup.",
    };
  }
  if (project.templateType !== "kids_song") {
    return {
      style:
        "Stylized 3D animated character, feature-film render quality, physically based materials, every fur and fabric fiber faithful to the description.",
      identity:
        "Same single stylized 3D character in BOTH panels — identical face, species, colors, costume and proportions.",
    };
  }
  const pack = resolveSongVarietyPack(project);
  return { style: pack.characterRenderStyle, identity: pack.turnaroundIdentityLine };
}

function kidsSubject(project: Project, profile: CharacterProfile, fallback: string): string {
  const raw = profile.imagePrompt.trim() || profile.baseAppearancePrompt.trim() || fallback;
  const cleaned = project.templateType === "kids_song" ? stripGenericStudioLabels(raw) : raw;
  return visualStyleFamilyOf(project.templateType, project.visualStyle) === "live-action"
    ? convertShotPlanToLiveAction(cleaned)
    : cleaned;
}

/** DNA'yi projenin gorsel ailesine cevirir (canli cekimde 3D dili kalmasin). */
function dnaForStyle(project: Project, profile: CharacterProfile): Partial<DnaCard> | null {
  const dna = readDnaCard(profile);
  if (!dna) return dna;
  if (visualStyleFamilyOf(project.templateType, project.visualStyle) !== "live-action") return dna;
  return dna.imagePrompt ? { ...dna, imagePrompt: convertShotPlanToLiveAction(dna.imagePrompt) } : dna;
}

/** Tek gorselde on + arka karakter sayfasi kilidi (tum uretim yollari). */
export function characterTurnaroundSheetLock(kids: boolean, characterName?: string, identityLine?: string): string {
  const styleNote = kids
    ? identityLine ||
      "Same single stylized 3D character in BOTH panels — identical face, species, colors, costume and proportions."
    : "Same single person in BOTH panels — identical face, hair, age, outfit and proportions.";
  const labelNote =
    kids && characterName?.trim()
      ? [
          `Above both panels, large clear readable title: "${characterName.trim()}".`,
          "Small Turkish garment callout labels with thin leader lines to each visible clothing item on THIS outfit (e.g. MONT, TIŞÖRT, PANTOLON, AYAKKABI, ŞAPKA, ELDIVEN) — only items that exist; clean sans-serif, do not cover the face.",
        ].join(" ")
      : kids
        ? "Above both panels, large clear readable character NAME title. Small Turkish garment callout labels (MONT, TIŞÖRT, PANTOLON…) with thin leader lines to each visible clothing item."
        : "No text, no captions, no watermark, no logo, no labels like Front/Back written on the image.";
  return [
    "ONE reference image = a clean 2-panel CHARACTER TURNAROUND SHEET only.",
    "LEFT panel: FRONT view, full body head-to-toe, feet visible, standing straight, facing the camera, arms relaxed, neutral expression.",
    "RIGHT panel: BACK view, full body head-to-toe, feet visible, standing straight, back to the camera, same pose scale.",
    "Exactly two panels side by side, equal size, thin divider or soft gap, identical studio lighting and neutral background.",
    "NO three-quarter angle, NO side profile, NO action pose, NO close-up, NO extra characters, NO extra panels.",
    "Do not copy another mascot from this project; left and right panels are the SAME unique character, never a previous design.",
    styleNote,
    labelNote,
  ].join(" ");
}

/** Kadrodaki diger uyelerin somut gorunumu (kopya yasagi icin). */
async function loadCastmates(projectId: string, exceptId: string): Promise<CastmateLock[]> {
  const others = await prisma.characterProfile.findMany({
    where: { projectId, id: { not: exceptId } },
    select: { name: true, dnaCard: true },
    orderBy: [{ role: "asc" }, { createdAt: "asc" }],
  });
  return others
    .filter((o) => o.name.trim())
    .map((o) => {
      let dna: Partial<DnaCard> = {};
      try {
        dna = JSON.parse(o.dnaCard || "{}") as Partial<DnaCard>;
      } catch {
        dna = {};
      }
      const mainColor = Array.isArray(dna.colorPalette) ? String(dna.colorPalette[0] ?? "").trim() : "";
      return {
        name: o.name.trim(),
        species: dna.species?.trim() ?? "",
        mainColor,
        silhouette: dna.silhouette?.trim() ?? "",
        distinguishingMark: dna.distinguishingMark?.trim() ?? "",
      };
    });
}

/** Profilin DNA kartini guvenli okur (bozuk/eski kayitta null). */
function readDnaCard(profile: CharacterProfile): Partial<DnaCard> | null {
  if (!profile.dnaCard || profile.dnaCard.trim() === "" || profile.dnaCard.trim() === "{}") return null;
  try {
    return dnaCardSchema.partial().parse(JSON.parse(profile.dnaCard));
  } catch {
    return null;
  }
}

/**
 * Karakterler sayfasindaki tarif kutusuna yazilacak karakter kunyesi.
 *
 * Kadro uyeleri ayni sanat dilini paylasir; ayrimi TUR + SILUET + BOY + PALET
 * + IMZA ISARETI yapar. Bu alanlar DNA kartinda duruyordu ama prompta
 * girmiyordu — sonuc birbirine benzeyen kadroydu. Artik hepsi yaziliyor.
 *
 * @param castmates kadrodaki diger uyeler (benzememe kilidi icin)
 */
export function buildFlowCharacterDescription(
  project: Project,
  profile: CharacterProfile,
  castmates: CastmateLock[] = []
): string {
  const lock = buildCharacterLock(profile);
  const kids = isKidsContent(project.templateType);

  if (!kids) {
    const style =
      "Photorealistic real person. Render every real-world detail exactly as described: skin pores, individual hair strands, fabric weave, stitching and wear, the exact accessories in their stated placement, and the exact clothing condition (crisp, worn, faded or torn). Do not beautify or change any detail.";
    const wardrobe = lock.baseWardrobePrompt ? ` Wardrobe: ${lock.baseWardrobePrompt}.` : "";
    return `${lock.baseAppearancePrompt}${wardrobe} ${style} ${characterTurnaroundSheetLock(false, profile.name)}`
      .replace(/\s+/g, " ")
      .trim();
  }

  const art = kidsArtLock(project);
  return composeCharacterSheetPrompt({
    name: profile.name,
    dna: dnaForStyle(project, profile),
    fallbackAppearance: kidsSubject(project, profile, "A friendly stylized 3D animal mascot performer"),
    wardrobe: lock.baseWardrobePrompt,
    artStyle: art.style,
    identityLine: art.identity,
    sheetLock: characterTurnaroundSheetLock(true, profile.name, art.identity),
    castmates,
  });
}

/** Gorsel modu (Nano Banana) icin karakter fotografi promptu. */
export function buildFlowCharacterImagePrompt(
  project: Project,
  profile: CharacterProfile,
  castmates: CastmateLock[] = []
): string {
  const lock = buildCharacterLock(profile);
  const kids = isKidsContent(project.templateType);

  const art = kids ? kidsArtLock(project) : null;
  const subject = kids
    ? composeCharacterSheetPrompt({
        name: profile.name,
        dna: dnaForStyle(project, profile),
        fallbackAppearance: kidsSubject(project, profile, "A friendly stylized 3D animal mascot performer"),
        wardrobe: lock.baseWardrobePrompt,
        artStyle: art!.style,
        identityLine: art!.identity,
        sheetLock: "",
        castmates,
      })
    : lock.baseAppearancePrompt;

  const style = kids
    ? art!.style
    : "Photorealistic photograph, natural skin texture, sharp focus, cinematic soft key light. No cartoon, no CGI, no illustration.";

  const detail = kids
    ? CHARACTER_MATERIAL_REALISM_LOCK
    : "Render every real-world detail exactly as described: skin pores and natural imperfections, individual hair strands, fabric weave, stitching, wrinkles and wear. Show the exact accessories described (watch, rings, earrings, necklace, glasses) in their stated placement, and the exact clothing condition (crisp, worn, faded or torn) — do not clean up, beautify or change any of it.";

  const wardrobe = lock.baseWardrobePrompt ? ` Wardrobe: ${lock.baseWardrobePrompt}.` : "";

  return [
    characterTurnaroundSheetLock(kids, profile.name, art?.identity),
    `Character: ${subject}${wardrobe}`,
    "Even soft studio lighting on both panels, clean neutral uncluttered background.",
    style,
    detail,
    kids
      ? "No watermark, no logo. Name title + Turkish garment labels ARE required on this bible sheet."
      : "No text, no captions, no watermark, no logo, no labels like Front/Back written on the image.",
  ]
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Yedek yontem: Flow'a gonderilecek karakter sayfasi VIDEO promptu. */
export function buildFlowCharacterPrompt(project: Project, profile: CharacterProfile): string {
  const lock = buildCharacterLock(profile);
  const kids = isKidsContent(project.templateType);

  const art = kids ? kidsArtLock(project) : null;
  const subject = kids
    ? kidsSubject(project, profile, "A friendly 3D animated animal character")
    : lock.baseAppearancePrompt;

  const style = kids
    ? art!.style
    : "Photorealistic live-action footage, natural skin texture, cinematic soft key light, sharp focus on the face. No cartoon or CGI look.";

  const wardrobe = lock.baseWardrobePrompt ? `Wardrobe: ${lock.baseWardrobePrompt}.` : "";
  const environment = lock.baseEnvironmentPrompt ? `Setting: ${lock.baseEnvironmentPrompt}.` : "";

  return [
    "[STYLE]",
    style,
    "",
    "[CHARACTER SHEET — FRONT + BACK ONLY]",
    `${subject} ${wardrobe} ${environment}`.trim(),
    characterTurnaroundSheetLock(kids, profile.name, art?.identity),
    kids ? CHARACTER_CUTENESS_LOCK : "",
    kids
      ? CHARACTER_MATERIAL_REALISM_LOCK
      : "Render every real-world detail exactly as described: skin pores, individual hair strands, fabric weave and stitching, the exact accessories in their stated placement, and the exact clothing condition (crisp, worn, faded or torn) — do not beautify or change any of it.",
    "",
    "[SHOT]",
    "Static 2-panel turnaround plate on screen for the whole clip: LEFT front, RIGHT back. Locked-off camera, no movement, no cuts, no zoom.",
    "Even, flattering lighting. Clean uncluttered studio background.",
    "",
    "[RESTRICTIONS]",
    "The character does not speak and does not sing. Silence.",
    kids
      ? "No other people, no watermark, no logo. Name title + Turkish garment labels ARE required on this bible sheet."
      : "No other people, no text, no captions, no watermark, no logo.",
    "Do not change the face, hair, outfit or body proportions between the two panels.",
  ]
    .filter((line) => line !== undefined)
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function imageFingerprint(filePath: string): string {
  const buf = fs.readFileSync(filePath);
  const head = buf.subarray(0, 96).toString("hex");
  const tail = buf.subarray(Math.max(0, buf.length - 48)).toString("hex");
  return `${buf.length}:${head}:${tail}`;
}

async function isDuplicateCharacterImage(projectId: string, imagePath: string, currentId: string): Promise<boolean> {
  if (!fs.existsSync(imagePath)) return false;
  const others = await prisma.characterProfile.findMany({
    where: { projectId, id: { not: currentId }, referenceImagePath: { not: null } },
    select: { referenceImagePath: true },
  });
  const fp = imageFingerprint(imagePath);
  for (const other of others) {
    const otherPath = other.referenceImagePath;
    if (!otherPath || !fs.existsSync(otherPath)) continue;
    try {
      if (imageFingerprint(otherPath) === fp) return true;
    } catch {
      /* okunamayan dosyayi atla */
    }
  }
  return false;
}

export class FlowCharacterBusyError extends Error {
  constructor() {
    super("Bu projenin otomasyonu calisiyor (ayni Flow sekmesi kullaniliyor). Karakter gorselini Flow ile uretmek icin once bu projenin otomasyonunu durdurun.");
    this.name = "FlowCharacterBusyError";
  }
}

/**
 * Flow'da karakter referans gorseli uretir. Once gorsel modu (Nano Banana)
 * denenir; menu bulunamazsa kisa video + kare cikarma yontemine dusulur.
 * Onay kullanicida kalir. characterId verilmezse ana karakter kullanilir.
 */
export async function generateCharacterImageWithFlow(
  projectId: string,
  customPrompt?: string,
  characterId?: string
): Promise<CharacterProfile> {
  return enqueueProjectWork(projectId, async () => {
    const MAX_WINDOW_RETRIES = 3;
    let lastErr: unknown;
    try {
      for (let attempt = 1; attempt <= MAX_WINDOW_RETRIES; attempt++) {
        try {
          return await generateCharacterImageWithFlowOnce(projectId, customPrompt, characterId);
        } catch (err) {
          lastErr = err;
          if (!isFlowWindowClosedError(err) || attempt === MAX_WINDOW_RETRIES) throw err;
          await recordEvent({
            projectId,
            step: "character",
            level: "warning",
            message: `Flow penceresi kapandi; tarayici yeniden acilip karakter tekrar denenecek (${attempt}/${MAX_WINDOW_RETRIES})`,
          });
          await openFlowBrowser();
        }
      }
      throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
    } finally {
      // KARISMA KILIDI: karakter uretimi hangi yoldan cikarsa ciksin (karakter
      // sayfasi / gorsel modu / yedek video) Flow VIDEO modunda birakilir.
      // Aksi halde sonraki klip jpeg uretir.
      await restoreVideoOutputMode(projectId);
    }
  });
}

/** Karakter isinden sonra prompt cubugunu klip uretimi icin VIDEO moduna dondurur. */
async function restoreVideoOutputMode(projectId: string): Promise<void> {
  try {
    const page = getProjectPage(projectId);
    if (!page || page.isClosed()) return;
    const project = await prisma.project.findUnique({ where: { id: projectId } });
    if (!project) return;
    await ensureVideoOutputMode(page, project);
  } catch {
    // Mod geri alinamadiysa klip akisi kendi basinda yeniden zorlar
  }
}

async function generateCharacterImageWithFlowOnce(
  projectId: string,
  customPrompt?: string,
  characterId?: string
): Promise<CharacterProfile> {
  // Yalnizca BU projenin otomasyonu engel: baska projeler kendi sekmelerinde
  // calisirken karakter uretimi yapilabilir.
  if (engineStatus(projectId).runningJobId) throw new FlowCharacterBusyError();

  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const profile = characterId
    ? await prisma.characterProfile.findUniqueOrThrow({ where: { id: characterId } })
    : await getOrCreateMainCharacter(projectId);
  if (profile.projectId !== projectId) throw new Error("Karakter bu projeye ait degil");

  const root = ensureProjectDirs(project.slug);
  const slug = (profile.name || "karakter").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "karakter";

  // Kadronun DIGER uyeleri: "bunlara benzemesin" kilidi icin
  const castmates = await loadCastmates(projectId, profile.id);

  const page = await ensureFlowReady(projectId, project.flowProjectUrl);
  await openFlowProject(page, project);

  // ---- 1) BIRINCIL YONTEM: Karakterler sayfasi ----
  const charactersOpened = await openCharactersPage(page, project);
  if (charactersOpened) {
    try {
      const flowName = (profile.name || "").trim();
      const description = customPrompt?.trim() || buildFlowCharacterDescription(project, profile, castmates);
      await recordEvent({
        projectId,
        step: "character",
        message: `Karakter, Flow'un Karakterler sayfasinda olusturuluyor${flowName ? `: ${flowName}` : ""}`,
      });

      // Flow tarafinda uretim ara sira gecici olarak "Basarisiz" olur;
      // ayni tarifle birkaç kez daha denemek genelde yeterlidir.
      const MAX_ATTEMPTS = 4;
      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        if (attempt > 1) {
          await recordEvent({
            projectId,
            step: "character",
            level: "warning",
            message: `Flow uretimi basarisiz oldu; karakter olusturma yeniden deneniyor (${attempt}/${MAX_ATTEMPTS})${flowName ? `: ${flowName}` : ""}`,
          });
          await dismissFlowOverlays(page);
          await openCharactersPage(page, project, { forceReload: true });
        }

        const created = await createFlowCharacter(page, project, flowName, description);
        if (!created.started) {
          await openCharactersPage(page, project, { forceReload: true });
          continue;
        }

        let found: Awaited<ReturnType<typeof waitForNewCharacterImage>> = null;
        try {
          found = await waitForNewCharacterImage(page, project, created.imageSourcesBefore, { minWaitMs: 3_500 });
        } catch (err) {
          if (attempt < MAX_ATTEMPTS) continue;
          throw err;
        }
        if (!found) {
          await openCharactersPage(page, project, { forceReload: true });
          continue;
        }

        const imagePath = await saveImageFromElement(
          page,
          found.locator,
          found.src,
          path.join(root, "character", `reference-flow-${slug}.png`)
        );
        if (await isDuplicateCharacterImage(projectId, imagePath, profile.id)) {
          await recordEvent({
            projectId,
            step: "character",
            level: "warning",
            message: `${flowName || "Karakter"} icin gelen gorsel baska kadro uyesinin kopyasi — yeniden denenecek`,
          });
          fs.rmSync(imagePath, { force: true });
          await openCharactersPage(page, project, { forceReload: true });
          continue;
        }

        await finalizeFlowCharacter(page, project, flowName).catch((err) => {
          void recordEvent({
            projectId,
            step: "character",
            level: "warning",
            message: `Karakter gorseli geldi ama Flow 'Bitti' kaydi atlanamadi: ${err instanceof Error ? err.message : String(err)}`,
          });
        });

        const bytes = fs.statSync(imagePath).size;
        const character = await prisma.characterProfile.update({
          where: { id: profile.id },
          data: {
            referenceImagePath: imagePath,
            imagePrompt: description,
            imageApproved: false,
            flowCharacterReference: flowHandleFromName(flowName) || profile.flowCharacterReference,
          },
        });
        await prisma.generatedAsset.create({
          data: {
            projectId,
            kind: "character_image",
            path: imagePath,
            bytes,
            meta: JSON.stringify({ source: "flow-characters-page", character: profile.name, attempt }),
          },
        });
        await recordEvent({
          projectId,
          step: "character",
          message: `Flow karakteri hazir${flowName ? `: ${flowName} (@${flowName} olarak kliplerde kullanilabilir)` : ""}; kullanici onayi bekleniyor`,
        });
        return character;
      }
      await recordEvent({
        projectId,
        step: "character",
        level: "warning",
        message: "Karakterler sayfasinda olusturma tamamlanamadi; gorsel moduna gecilecek",
      });
    } finally {
      await returnToProjectEditor(page, project).catch(() => {});
    }
  }

  // ---- 2) IKINCIL YONTEM: gorsel modu (Nano Banana) ----
  // ensureImageOutputMode etiketi DOGRULAR (switchOutputType yalnizca tiklar):
  // "gorsel moduna gectim" sanip video uretmeyi onler.
  const imageMode = await ensureImageOutputMode(page, project);
  if (imageMode) {
    try {
      const imagePromptText = customPrompt?.trim() || buildFlowCharacterImagePrompt(project, profile, castmates);
      await recordEvent({
        projectId,
        step: "character",
        message: `Karakter gorseli Flow'un GORSEL modunda uretiliyor (Nano Banana 2)${profile.name ? `: ${profile.name}` : ""}`,
      });

      await selectImageModel(page, project);
      await enterPrompt(page, project, imagePromptText);
      await startGeneration(page, project, project.generateButtonMode === "manual" ? "manual" : "auto", {
        output: "image",
      });
      await waitForImageCompletion(page, project);

      const imagePath = await downloadImageAsset(
        page,
        project,
        path.join(root, "character", `reference-flow-${slug}.png`)
      );

      const bytes = fs.statSync(imagePath).size;
      const character = await prisma.characterProfile.update({
        where: { id: profile.id },
        data: {
          referenceImagePath: imagePath,
          imagePrompt: imagePromptText,
          imageApproved: false,
          flowCharacterReference: flowHandleFromName(profile.name) || profile.flowCharacterReference,
        },
      });
      await prisma.generatedAsset.create({
        data: {
          projectId,
          kind: "character_image",
          path: imagePath,
          bytes,
          meta: JSON.stringify({ source: "flow-image-mode", character: profile.name }),
        },
      });
      await recordEvent({
        projectId,
        step: "character",
        message: `Flow gorsel modu karakter fotografi hazir${profile.name ? `: ${profile.name}` : ""}; kullanici onayi bekleniyor`,
      });
      return character;
    } finally {
      // Klip otomasyonu video modunda calisir; Flow'u gorsel modunda birakma.
      await ensureVideoOutputMode(page, project).catch(() => {});
    }
  }

  // ---- 3) SON CARE: kisa video + kare cikarma ----
  const prompt = customPrompt?.trim() || buildFlowCharacterPrompt(project, profile);

  // Tek kare icin modelin destekledigi EN KISA sure yeterli (or. 8sn yerine 4sn).
  const settings = await getSettings();
  const matrix = parseModelSupportMatrix(settings);
  const supportedDurations = resolveModelSupport(matrix, project.flowModel)?.durations;
  const shortestDuration =
    supportedDurations && supportedDurations.length > 0 ? Math.min(...supportedDurations) : Math.min(4, project.clipSeconds);
  const shootProject: Project = { ...project, clipSeconds: shortestDuration, audioEnabled: false };

  await recordEvent({
    projectId,
    step: "character",
    message: `Gorsel modu kullanilamadi; karakter gorseli yedek yontemle uretiliyor (${shortestDuration}sn video + kare cikarma)`,
  });

  // Karakter cekimi Flow'u KISA sureye (or. 4sn) alir. Klip otomasyonu her klipte
  // ayarlari yeniden uygular, ancak ayar paneli bulunamazsa (log: "Uretim ayarlari
  // paneli bulunamadi") Flow'da kalan 4sn degeri klibe sizabilir. Bu yuzden cekim
  // bitince — hata olsa bile — projenin GERCEK ayarlari geri yuklenir.
  let videoPath: string;
  try {
    // Bu yol VIDEO uretir: gorsel modu sizmis olabilir, once VIDEO'ya sabitle.
    await ensureVideoOutputMode(page, shootProject);
    await configureGeneration(page, shootProject);
    await enterPrompt(page, shootProject, prompt);
    await startGeneration(page, shootProject, shootProject.generateButtonMode === "manual" ? "manual" : "auto");
    await waitForCompletion(page, shootProject);

    videoPath = nextAvailablePath(path.join(root, "character", `flow-${slug}.mp4`));
    await downloadClipVideo(page, shootProject, videoPath);
  } finally {
    if (shortestDuration !== project.clipSeconds) {
      await configureGeneration(page, project).catch(() => {});
    }
  }

  // Ortadaki kare en kararli olanidir: acilis pozu oturmus, kapanis bulanikligi yok.
  const info = await probeVideo(videoPath).catch(() => null);
  const middle = info && info.durationSeconds > 1 ? info.durationSeconds / 2 : 1;
  const imagePath = nextAvailablePath(path.join(root, "character", `reference-flow-${slug}.png`));
  await extractFrameAt(videoPath, middle, imagePath);

  const bytes = fs.statSync(imagePath).size;
  const character = await prisma.characterProfile.update({
    where: { id: profile.id },
    data: {
      referenceImagePath: imagePath,
      imagePrompt: prompt,
      imageApproved: false,
      flowCharacterReference: flowHandleFromName(profile.name) || profile.flowCharacterReference,
    },
  });
  await prisma.generatedAsset.create({
    data: {
      projectId,
      kind: "character_image",
      path: imagePath,
      bytes,
      meta: JSON.stringify({
        source: "flow",
        character: profile.name,
        videoPath,
        frameSeconds: Number(middle.toFixed(2)),
        clipSeconds: shortestDuration,
      }),
    },
  });

  await recordEvent({
    projectId,
    step: "character",
    message: `Flow karakter gorseli hazir${profile.name ? `: ${profile.name}` : ""}; kullanici onayi bekleniyor`,
  });
  return character;
}
