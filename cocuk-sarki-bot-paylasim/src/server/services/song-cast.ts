import { z } from "zod";
import type { CharacterProfile, Project } from "@prisma/client";
import { prisma } from "@/server/db";
import { structuredCall } from "@/server/services/openai";
import { recordEvent } from "@/server/lib/logger";
import { buildCharacterLock, getOrCreateMainCharacter, flowHandleFromName } from "@/server/services/character";
import { generateCharacterImageWithFlow } from "@/server/services/character-flow";
import { getSettings } from "@/server/services/settings";
import {
  dismissFlowOverlays,
  ensureFlowReady,
  isFlowWindowClosedError,
  openCharactersPage,
  openFlowProject,
  returnToProjectEditor,
} from "@/server/automation/flow-adapter";
import { openFlowBrowser } from "@/server/automation/browser";
import {
  AutomationStoppedError,
  assertAutomationContinuing,
  beginNonJobWork,
  endNonJobWork,
  runInProjectContext,
} from "@/server/automation/abort";
import { loadSongSettings } from "@/server/services/song-settings-store";
import { resolveSongPlannerAi } from "@/server/services/publish";
import { dnaCardSchema, type DnaCard } from "@/lib/song-character";
import { spreadHeightBands } from "@/lib/song-character-sheet";
import { formatCastVarietyLock, resolveSongVarietyPack } from "@/lib/song-variety";

export const songCastMemberSchema = z.object({
  name: z.string().min(1),
  species: z.string().min(1),
  role: z.enum(["lead", "support"]),
  personality: z.array(z.string()).min(1),
  catchphrase: z.string().min(1),
  signatureGesture: z.string().min(1),
  voiceDescription: z.string().min(1),
  loves: z.string().min(1),
  colorPalette: z.array(z.string()).min(1),
  imagePrompt: z.string().min(20),
  bodyDetail: z.string().default(""),
  outfitDetail: z.string().default(""),
  signatureProp: z.string().default(""),
  hair: z.string().default(""),
  faceFeatures: z.string().default(""),
  wardrobe: z.string().default(""),
  // AYIRT EDICILIK: bu uc alan olmadan kadro renk kopyasina donuyor
  silhouette: z.string().default(""),
  heightBand: z.string().default(""),
  distinguishingMark: z.string().default(""),
});

export type SongCastMember = z.infer<typeof songCastMemberSchema>;

const castAnalysisSchema = z.object({
  castCount: z.number().int().min(1).max(6),
  rationale: z.string().min(10),
  members: z.array(songCastMemberSchema).min(1).max(6),
});

const CAST_JSON_SCHEMA: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  properties: {
    castCount: { type: "integer", description: "How many distinct performers (1-6)" },
    rationale: { type: "string", description: "Turkish: why this cast size fits the lyrics" },
    members: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          name: { type: "string" },
          species: { type: "string" },
          role: { type: "string", enum: ["lead", "support"] },
          personality: { type: "array", items: { type: "string" } },
          catchphrase: { type: "string" },
          signatureGesture: { type: "string" },
          voiceDescription: { type: "string" },
          loves: { type: "string" },
          colorPalette: { type: "array", items: { type: "string" } },
          imagePrompt: {
            type: "string",
            description:
              "English stylized 3D mascot in THIS project's art dialect (not generic Pixar), full body, 80+ chars, no child/minor terms",
          },
          bodyDetail: { type: "string" },
          outfitDetail: { type: "string" },
          signatureProp: { type: "string" },
          hair: { type: "string" },
          faceFeatures: { type: "string" },
          wardrobe: { type: "string" },
          silhouette: {
            type: "string",
            description: "Body shape in a few words, unique in this cast (e.g. pear-shaped and round, lanky with long neck)",
          },
          heightBand: {
            type: "string",
            enum: ["tiny", "short", "medium", "tall"],
            description: "Each cast member must get a DIFFERENT band",
          },
          distinguishingMark: {
            type: "string",
            description: "One unmistakable visual detail only this character has (chipped horn, star-shaped tail tuft, one blue sock…)",
          },
        },
        required: [
          "name",
          "species",
          "role",
          "personality",
          "catchphrase",
          "signatureGesture",
          "voiceDescription",
          "loves",
          "colorPalette",
          "imagePrompt",
          "bodyDetail",
          "outfitDetail",
          "signatureProp",
          "hair",
          "faceFeatures",
          "wardrobe",
          "silhouette",
          "heightBand",
          "distinguishingMark",
        ],
      },
    },
  },
  required: ["castCount", "rationale", "members"],
};

function memberToDna(member: SongCastMember, visualStyle: string): DnaCard {
  return dnaCardSchema.parse({
    name: member.name,
    species: member.species,
    personality: member.personality,
    catchphrase: member.catchphrase,
    signatureGesture: member.signatureGesture,
    voiceDescription: member.voiceDescription,
    fears: "dark scary imagery, violence, loud shocks",
    loves: member.loves,
    colorPalette: member.colorPalette,
    imagePrompt: member.imagePrompt,
    bodyDetail: member.bodyDetail || member.hair,
    outfitDetail: member.outfitDetail || member.wardrobe,
    signatureProp: member.signatureProp,
    styleLabel: visualStyle || "stylized3d",
    silhouette: member.silhouette,
    heightBand: member.heightBand,
    distinguishingMark: member.distinguishingMark,
    faceFeatures: member.faceFeatures || member.bodyDetail,
  });
}

function profileFieldsFromMember(member: SongCastMember, dna: DnaCard) {
  return {
    name: member.name,
    hair: member.hair || member.bodyDetail,
    faceFeatures: member.faceFeatures || member.bodyDetail,
    wardrobe: member.wardrobe || member.outfitDetail,
    gestureLevel: member.signatureGesture,
    voiceCharacter: member.voiceDescription,
    emotionTone: member.personality.join(", "),
    imagePrompt: member.imagePrompt,
    flowCharacterReference: flowHandleFromName(member.name) || `@${member.name.replace(/\s+/g, "")}`,
    dnaCard: JSON.stringify(dna),
    imageApproved: false,
    referenceImagePath: null,
  };
}

/** Sozlerden kac performer / karakter gerektigini AI ile belirler. */
export async function analyzeCastFromLyrics(
  formattedLyrics: string,
  project: Project,
  ageBand: string,
  themeSummary: string,
  model: string,
  reasoningEffort: "low" | "medium" | "high" | undefined
): Promise<{ castCount: number; rationale: string; members: SongCastMember[] }> {
  const variety = resolveSongVarietyPack(project);
  const result = await structuredCall({
    model,
    system: `Sen cocuk muzik videosu casting yonetmenisin. TAM sarki sozlerini okuyup kac ayri PERFORMER (sahne karakteri) gerektigini belirle.

KURALLAR:
- 1 ile 6 arasi karakter sec. Sozler kac farkli ses/figur/hayvan anlatiyorsa o kadar.
- Tek soylenen sarki = genelde 1 lead. Cagri-yanit, diyalog, farkli hayvanlar, grup korosu = 2-6.
- Her karakter stylized 3D cartoon mascot / fantasy performer — INSAN COCUK / minor TARIF ETME.
- imagePrompt Ingilizce, BU PROJENIN art dialect'inde, full body, yayin guvenli. "Pixar-style" YAZMA.
- Ilk uygun karakter "lead", digerleri "support".
- members.length ZORUNLU castCount ile AYNI.

AYIRT EDICILIK (EN ONEMLI KURAL — kadro birbirine benzemeyecek, kopya YASAK):
- Her uye BASKA BIR TUR olacak (hepsi tilki/ayi/domates olmaz). Sozler tek tur soyluyorsa alt turleri ayir.
- imagePrompt'un ILK CUMLESI o uyenin kendi turunu yazsin; baska kadro uyesinin turunu, rengini veya siluetini yazma.
- heightBand her uyede FARKLI: tiny / short / medium / tall.
- silhouette farkli olacak: yuvarlak-armut, uzun-ince, kare-tiknaz, minik-toparlak gibi acikca ayri govde bicimleri.
- colorPalette[0] (ana govde rengi) her uyede FARKLI bir renk ailesi olacak.
- distinguishingMark: yalnizca o karaktere ait, tek bakista taninan bir detay (kirik boynuz, yildiz bicimli kuyruk puskulu, tek mavi corap, gozunun etrafinda maske deseni).
- faceFeatures ve bodyDetail'i somut yaz: goz bicimi/rengi, kulak bicimi, burun, tuy dokusu, kuyruk.
- outfitDetail'de parcalari say (ust, alt, ayakkabi, sapka/aksesuar) — kiyafetlerde YAZI/LOGO YOK.
- Renk kopyasi / klon / "ayni mascot farkli renk" YASAK: her uye yeni bir yaratik.
- Destek karakteri lead'in kopyasi olamaz — Flow onceki karta bakip ayni yuzu tekrar etmesin.

TATLILIK (her uye COK TATLI olacak — vasat/jenerik/karanlik tasarim YASAK):
- Kocaman parlak pirlanta gozler: imagePrompt'ta goz RENGINI ve catchlight'i acikca yaz.
- Tombul yuvarlak yanaklar + hafif dogal allik, minik dugme burun, yumusak sicak gulumseme.
- Her kenar yuvarlak ve sarilasi: sivri pence, korkutucu dis, sert hat YOK.
- imagePrompt her detayi TEK TEK yazsin: goz sekli/rengi, yanak/allik, burun, kulak ve kuyruk bicimi,
  tuy/kumas mikro dokusu, pati/el detayi, ic-kulak rengi, 2-3 minik aksesuar veya imza detayi.
- "cute mascot" gibi bos genellemeler yetmez — okuyan kisi karakteri cizebilecek kadar somut olsun.

${formatCastVarietyLock(variety)}`,
    user: `Yas bandi: ${ageBand}
Dil: ${project.speechLanguage}
Tema ozeti: ${themeSummary}
Look pack: ${variety.packId}
Stil: ${variety.shotStylePhrase}

SOZLER:
${formattedLyrics.slice(0, 14_000)}

Kac karakterle bu MV yapilmali? Her biri icin tam profil yaz. Karakterler birbirinin kopyasi olmasin.`,
    schemaName: "song_cast_analysis",
    jsonSchema: CAST_JSON_SCHEMA,
    zodSchema: castAnalysisSchema,
    maxOutputTokens: 8_000,
    reasoningEffort,
    timeoutMs: 180_000,
  });

  const members = result.members.slice(0, result.castCount);
  while (members.length < result.castCount && members.length > 0) {
    members.push({ ...members[members.length - 1], name: `${members[members.length - 1].name} ${members.length + 1}`, role: "support" });
  }
  return { castCount: members.length, rationale: result.rationale, members: diversifyCastMembers(members) };
}

/**
 * AI sik sik tum kadroya ayni boyu (veya bos boy) verir; boy siluetin en
 * gorunur ayirdicisidir. Cakisan bandlar deterministik olarak dagitilir.
 */
export function diversifyCastMembers(members: SongCastMember[]): SongCastMember[] {
  const bands = spreadHeightBands(members.map((m) => m.heightBand));
  return members.map((member, i) => ({ ...member, heightBand: bands[i] }));
}

/** Studyo sozlerinden sabit MV karakterlerini planlar ve kaydeder. */
export async function planSongCastFromProject(projectId: string): Promise<{
  castCount: number;
  rationale: string;
  names: string[];
}> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki klibi");

  const settings = await loadSongSettings(projectId);
  const formattedLyrics = (settings.formattedLyrics || "").trim();
  if (!formattedLyrics) throw new Error("Once soz metni ekleyin — uretim sayfasindaki parca paneline yapistirin");

  const ageBand = project.ageBand || "3-5";
  const { model, reasoningEffort } = await resolveSongPlannerAi();

  let themeSummary = project.topic?.trim() || "";
  if (!themeSummary) {
    const { analyzeLyricsForProduction } = await import("@/server/services/song");
    const ctx = await analyzeLyricsForProduction(formattedLyrics, project, ageBand, model, reasoningEffort);
    themeSummary = ctx.themeSummary;
  }

  await recordEvent({ projectId, step: "character", message: "Sarki sozleri analiz ediliyor — sabit karakter sayisi belirleniyor" });

  const castAnalysis = await analyzeCastFromLyrics(
    formattedLyrics,
    project,
    ageBand,
    themeSummary,
    model,
    reasoningEffort
  );
  const profiles = await persistSongCast(projectId, castAnalysis.members);

  return {
    castCount: castAnalysis.castCount,
    rationale: castAnalysis.rationale,
    names: profiles.map((p) => p.name),
  };
}

/** AI kadrosunu CharacterProfile kayitlarina yazar (main + side). */
export async function persistSongCast(projectId: string, members: SongCastMember[]): Promise<CharacterProfile[]> {
  if (members.length === 0) throw new Error("Kadro bos — soz analizi basarisiz");

  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  await prisma.characterProfile.deleteMany({ where: { projectId, role: "side" } });

  const main = await getOrCreateMainCharacter(projectId);
  const saved: CharacterProfile[] = [];
  const variety = resolveSongVarietyPack(project);

  for (let i = 0; i < members.length; i++) {
    const member = members[i]!;
    const dna = memberToDna(member, variety.styleLabel);
    const fields = profileFieldsFromMember(member, dna);
    const isMain = i === 0;

    let profile: CharacterProfile;
    if (isMain) {
      profile = await prisma.characterProfile.update({
        where: { id: main.id },
        data: { role: "main", ...fields },
      });
    } else {
      profile = await prisma.characterProfile.create({
        data: { projectId, role: "side", ...fields },
      });
    }
    const lock = buildCharacterLock(profile);
    profile = await prisma.characterProfile.update({ where: { id: profile.id }, data: lock });
    saved.push(profile);
  }

  await recordEvent({
    projectId,
    step: "song",
    message: `AI kadro: ${saved.length} karakter — ${saved.map((c) => c.name).join(", ")}`,
  });
  return saved;
}

export function formatCastForVisualsPrompt(cast: CharacterProfile[]): string {
  return cast
    .map((c) => {
      let dna: DnaCard | null = null;
      try {
        dna = dnaCardSchema.parse(JSON.parse(c.dnaCard));
      } catch {
        /* ignore */
      }
      return `- ${c.name} (${dna?.species || "mascot"}) — ${dna?.personality.join(", ") || c.emotionTone}; imza: ${dna?.signatureGesture || c.gestureLevel}; renk: ${dna?.colorPalette.join(", ") || "-"}`;
    })
    .join("\n");
}

export function resolveCharacterIdByName(cast: CharacterProfile[], singerName: string | undefined): string | null {
  const needle = (singerName || "").trim().toLowerCase();
  if (!needle) return cast.find((c) => c.role === "main")?.id ?? cast[0]?.id ?? null;
  const hit =
    cast.find((c) => c.name.trim().toLowerCase() === needle) ||
    cast.find((c) => c.name.trim().toLowerCase().includes(needle)) ||
    cast.find((c) => needle.includes(c.name.trim().toLowerCase()));
  return hit?.id ?? cast.find((c) => c.role === "main")?.id ?? cast[0]?.id ?? null;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function namedCastOf(projectId: string): Promise<CharacterProfile[]> {
  const cast = await prisma.characterProfile.findMany({
    where: { projectId },
    orderBy: [{ role: "asc" }, { createdAt: "asc" }],
  });
  return cast.filter((c) => c.name.trim());
}

async function recoverFlowCharacterUi(projectId: string, flowProjectUrl: string | null): Promise<void> {
  try {
    await openFlowBrowser();
    const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
    const page = await ensureFlowReady(projectId, flowProjectUrl ?? undefined);
    await dismissFlowOverlays(page);
    await returnToProjectEditor(page, project).catch(() => {});
    await openFlowProject(page, project).catch(() => {});
    await openCharactersPage(page, project, { forceReload: true }).catch(() => {});
  } catch {
    /* sonraki generateCharacterImageWithFlow Flow'u yeniden acar */
  }
}

async function approveFlowCharacter(profile: CharacterProfile): Promise<void> {
  await prisma.characterProfile.update({
    where: { id: profile.id },
    data: {
      imageApproved: true,
      flowCharacterReference: flowHandleFromName(profile.name) || `@${profile.name.replace(/\s+/g, "")}`,
    },
  });
}

type BulkCastResult = { created: number; total: number; failed: string[]; names: string[]; cancelled?: boolean };

const bulkCastInflight = new Map<string, Promise<BulkCastResult>>();

/**
 * Flow ile tum kadroyu sirayla olusturur; basarisiz kalanlari otomatik tekrar dener.
 * IPTAL EDILEBILIR: proje baglaminda calisir, boylece "Durdur" bu uzun islemi de
 * (Playwright beklemeleri dahil) aninda keser.
 *
 * "Topluca uret" ve "Oto bitir" AYNI isi cagirir. Ikinci istek yeni bir dongu
 * acmaz — mevcut uretime katilir; aksi halde iki is ayni Flow sekmesini bozar.
 */
export async function bulkCreateSongCastViaFlow(projectId: string): Promise<BulkCastResult> {
  const existing = bulkCastInflight.get(projectId);
  if (existing) {
    await recordEvent({
      projectId,
      step: "character",
      message: "Kadro uretimi zaten suruyor — Topluca uret / Oto bitir mevcut ise katiliyor",
    });
    return existing;
  }

  const work = (async (): Promise<BulkCastResult> => {
    beginNonJobWork(projectId);
    try {
      return await runInProjectContext(projectId, () => bulkCreateSongCastLoop(projectId));
    } catch (err) {
      if (err instanceof AutomationStoppedError) {
        await recordEvent({
          projectId,
          step: "character",
          level: "warning",
          message: "Karakter uretimi kullanici istegiyle durduruldu",
        });
        const snapshot = await namedCastOf(projectId);
        return {
          created: snapshot.filter((c) => c.referenceImagePath).length,
          total: snapshot.length,
          failed: [],
          names: snapshot.map((c) => c.name),
          cancelled: true,
        };
      }
      throw err;
    } finally {
      endNonJobWork(projectId);
    }
  })();

  bulkCastInflight.set(projectId, work);
  try {
    return await work;
  } finally {
    if (bulkCastInflight.get(projectId) === work) bulkCastInflight.delete(projectId);
  }
}

async function bulkCreateSongCastLoop(
  projectId: string
): Promise<{ created: number; total: number; failed: string[]; names: string[] }> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const named = await namedCastOf(projectId);
  if (named.length === 0) {
    throw new Error("Adi gecen karakter yok — once sozleri eslestirin veya Karakter sekmesinde kadro planini calistirin");
  }

  for (const profile of named) {
    if (profile.referenceImagePath && !profile.imageApproved) {
      await approveFlowCharacter(profile);
    }
  }

  const names = named.map((c) => c.name);
  const alreadyReady = named.filter((c) => c.referenceImagePath).length;
  if (alreadyReady === named.length) {
    await prisma.project.update({ where: { id: projectId }, data: { useFlowCharacter: true, useReference: true } });
    return { created: 0, total: named.length, failed: [], names };
  }

  await ensureFlowReady(projectId, project.flowProjectUrl);
  const settings = await getSettings();
  const pauseMs = Math.max(4_000, settings.waitBetweenGenerationsMs || 4_000);
  const MAX_PASSES = 5;
  let created = 0;
  const lastError = new Map<string, string>();

  for (let pass = 1; pass <= MAX_PASSES; pass++) {
    assertAutomationContinuing();
    const snapshot = await namedCastOf(projectId);
    const missing = snapshot.filter((c) => !c.referenceImagePath);
    if (missing.length === 0) break;

    if (pass === 1) {
      await recordEvent({
        projectId,
        step: "character",
        message: `Flow acildi — ${missing.length} karakter sirayla uretilecek: ${missing.map((c) => c.name).join(", ")}`,
      });
    } else {
      await recordEvent({
        projectId,
        step: "character",
        level: "warning",
        message: `Eksik karakterler otomatik tekrar deneniyor (tur ${pass}/${MAX_PASSES}): ${missing.map((c) => c.name).join(", ")}`,
      });
      await recoverFlowCharacterUi(projectId, project.flowProjectUrl);
      await sleep(Math.min(8_000 * pass, 28_000));
    }

    for (let i = 0; i < missing.length; i++) {
      assertAutomationContinuing();
      const profile = missing[i]!;
      await recordEvent({
        projectId,
        step: "character",
        message: `Flow kadro (tur ${pass}, ${i + 1}/${missing.length}): ${profile.name} olusturuluyor…`,
      });
      try {
        await generateCharacterImageWithFlow(projectId, undefined, profile.id);
        await approveFlowCharacter(profile);
        created++;
        lastError.delete(profile.id);
      } catch (err) {
        if (err instanceof AutomationStoppedError) throw err;
        const message = err instanceof Error ? err.message : String(err);
        lastError.set(profile.id, message);
        await recordEvent({
          projectId,
          step: "character",
          level: "warning",
          message: `${profile.name} Flow'da olusturulamadi (tur ${pass}): ${message.slice(0, 180)} — kalanlar ve bu karakter tekrar denenecek`,
        });
        if (isFlowWindowClosedError(err)) {
          await recordEvent({
            projectId,
            step: "character",
            level: "warning",
            message: "Flow penceresi kapandi — Chrome yeniden acilacak, karakterler kaldigi yerden denenecek",
          });
          await openFlowBrowser().catch(() => {});
        }
        await recoverFlowCharacterUi(projectId, project.flowProjectUrl);
      }
      if (i < missing.length - 1) {
        await sleep(pauseMs);
      }
    }
  }

  const leftover = (await namedCastOf(projectId)).filter((c) => !c.referenceImagePath);
  const failed = leftover.map((c) => `${c.name}: ${lastError.get(c.id) || "gorsel yok"}`);

  // Referans anahtarlari YALNIZCA tum kadronun gorseli varsa acilir.
  // Aksi halde proje "Flow referansi zorunlu" moduna gecer ve otomasyon
  // "karakterin Flow referansi yok" diyerek hic baslamaz — eskiden karakter
  // uretimi tamamen basarisiz olsa bile bu anahtarlar aciliyordu.
  const allReady = leftover.length === 0;
  await prisma.project.update({
    where: { id: projectId },
    data: { useFlowCharacter: allReady, useReference: allReady },
  });
  await recordEvent({
    projectId,
    step: "character",
    message: `Flow kadro bitti: ${created} yeni / ${named.length} toplam${failed.length ? ` · ${failed.length} hâlâ eksik (otomatik tekrar denendi)` : ""}`,
  });
  if (!allReady) {
    await recordEvent({
      projectId,
      step: "character",
      level: "warning",
      message:
        `${leftover.length} karakterin Flow gorseli yok. Klipler DURMAZ: promptlardaki yazili yuz/kostum kilidi kullanilacak. ` +
        `Gorselleri sonra "Topluca uret" ile tamamlayip kalan klipleri yeniden uretebilirsiniz.`,
    });
  }

  return { created, total: named.length, failed, names };
}

export async function listSongCast(projectId: string): Promise<CharacterProfile[]> {
  return prisma.characterProfile.findMany({
    where: { projectId },
    orderBy: [{ role: "asc" }, { createdAt: "asc" }],
  });
}
