import fs from "node:fs";
import path from "node:path";
import { z } from "zod";
import { prisma } from "@/server/db";
import { structuredCall, generateImage } from "@/server/services/openai";
import { getSettings } from "@/server/services/settings";
import { buildSrtContent, buildSrtCues, buildSrtCuesFromTimestamps } from "@/server/services/srt";
import { extractFrameAt, probeVideo, burnTextOntoImage } from "@/server/services/ffmpeg";
import { ensureProjectDirs, nextAvailablePath, safeProjectPath } from "@/server/lib/paths";
import { recordEvent } from "@/server/lib/logger";

/**
 * Yayin paketi — YouTube / kanal yayini icin en yuksek model + deep reasoning.
 * Izleyici metinleri dogal insan dili; thumbnail yazisiz, CTR odakli.
 */

const chapterSchema = z.object({
  time: z.string().default("0:00"),
  label: z.string().default(""),
  beat: z.string().default(""),
});

const thumbnailConceptSchema = z.object({
  name: z.string().default("Konsept"),
  emotion: z.string().default(""),
  hook: z.string().default(""),
  prompt: z.string().default(""),
});

/** AI ciktisi icin esnek sema (eksik alanlar normalize edilir). */
const publishMetaSchema = z.object({
  titleVariants: z.array(z.string()).default([]),
  primaryTitle: z.string().default(""),
  description: z.string().default(""),
  tags: z.array(z.string()).default([]),
  hashtags: z.array(z.string()).default([]),
  seoKeywords: z
    .object({
      primary: z.string().default(""),
      secondary: z.array(z.string()).default([]),
    })
    .default({ primary: "", secondary: [] }),
  targetAudience: z.string().default(""),
  thumbnailPrompt: z.string().default(""),
  /** Kapak uzerine bindirilecek kisa, ilgi cekici yazi (2-6 kelime) */
  thumbnailText: z.string().default(""),
  thumbnailConcepts: z.array(thumbnailConceptSchema).default([]),
  chapters: z.array(chapterSchema).default([]),
  pinnedComment: z.string().default(""),
  communityPost: z.string().default(""),
  shortsHooks: z.array(z.string()).default([]),
  endScreenCta: z.string().default(""),
  postingStrategy: z.string().default(""),
  uploadChecklist: z.array(z.string()).default([]),
  kidsSafetyNotes: z.string().default(""),
  contentWarnings: z.array(z.string()).default([]),
  seriesHook: z.string().default(""),
});

export type PublishMeta = z.infer<typeof publishMetaSchema> & {
  modelUsed: string;
  reasoningEffort: string;
  generatedAt: string;
};

export type PublishPackage = {
  meta: PublishMeta | null;
  thumbnails: Array<{ path: string; createdAt: string }>;
  srtPath: string | null;
  /** YouTube TR/EN/DE/ES/AR altyazi dosyalari */
  subtitleFiles: Array<{
    code: string;
    name: string;
    youtube: string;
    path: string;
    downloadName: string;
  }>;
  metaJsonPath: string | null;
  metaTxtPath: string | null;
};

export type GeneratePublishOptions = {
  /** Plan sonrasi birincil thumbnail'i otomatik uret */
  autoThumbnail?: boolean;
};

/** Yayin isleri icin en guclu uygun modeli sec (flagship + high reasoning). */
export async function resolvePublishAiModel(): Promise<{ model: string; reasoningEffort: "high" }> {
  const settings = await getSettings();
  const configured = (settings.openaiModel || "").trim();
  const model = /^(gpt-5|o3|o4|o1)/i.test(configured) ? configured : "gpt-5";
  return { model, reasoningEffort: "high" };
}

/**
 * Oto bitir / klip gorsel plani: Ayarlar'daki modeli kullan, reasoning'i low tut.
 * Yayin yolundaki gpt-5 + high, 10+ klipte tek cagrida zaman asimine dusuyor.
 */
export async function resolveSongPlannerAi(): Promise<{ model: string; reasoningEffort: "low" }> {
  const settings = await getSettings();
  const model = (settings.openaiModel || "").trim() || "gpt-5";
  return { model, reasoningEffort: "low" };
}

function formatTime(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(s / 60);
  const seconds = s % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function buildTimelineBrief(
  clips: Array<{
    index: number;
    dialogue: string;
    sceneDescription: string;
    emotionLabel: string;
    actualDurationSeconds: number | null;
    estimatedDurationSeconds: number;
  }>
): { brief: string; durations: number[]; totalSeconds: number } {
  const durations = clips.map((c) => c.actualDurationSeconds ?? c.estimatedDurationSeconds ?? 8);
  let elapsed = 0;
  const lines: string[] = [];
  for (let i = 0; i < clips.length; i++) {
    const c = clips[i];
    const dur = durations[i];
    const start = formatTime(elapsed);
    const end = formatTime(elapsed + dur);
    lines.push(
      `#${c.index} [${start}-${end}] duygu=${c.emotionLabel || "-"} | ${c.sceneDescription.slice(0, 120).replace(/\n/g, " ")} | diyalog: "${c.dialogue.slice(0, 100)}"`
    );
    elapsed += dur;
  }
  return { brief: lines.join("\n"), durations, totalSeconds: elapsed };
}

function cleanTitle(t: string | null | undefined): string {
  return String(t || "")
    .replace(/\s+/g, " ")
    .replace(/[!?]{2,}/g, "?")
    .replace(/[.]{3,}/g, "…")
    .trim();
}

function ensureHash(tag: string): string {
  const t = String(tag || "")
    .trim()
    .replace(/^#+/, "");
  return t ? `#${t.replace(/\s+/g, "")}` : "";
}

/**
 * Kapak yazisini YouTube CTR tarzina cevirir.
 * Arastirma (2025–2026): 0–3 kelime, kalin, basligi tekrar etme; yalnizca Turkce.
 * Ornek: "Neler Oldu?", "Ip Gerildi!", "Sakın Kaçırma"
 */
export function looksLikeEnglishOverlay(text: string): boolean {
  const t = text.trim();
  if (!t) return false;
  // Turkce ozel harf varsa Turkce kabul
  if (/[ğüşıöçĞÜŞİÖÇ]/.test(t)) return false;
  const lower = t.toLowerCase();
  const englishHits =
    /\b(the|and|what|happened|wow|amazing|don't|miss|watch|now|this|that|you|will|never|believe|shocking|epic|wait|until|end|oh no|look|next|happened)\b/i.test(
      lower
    );
  // Latin-only + inglezce ipucu veya tipik Ingilizce kapak kaliplari
  if (englishHits) return true;
  if (/^[A-Za-z0-9 ?!'….,\-]+$/.test(t) && /\b(what|wow|miss|watch|happened|don't|next)\b/i.test(lower)) return true;
  return false;
}

/** YouTube icin kisa Turkce kanca havuzu (duyguya gore). */
export function turkishThumbnailHooks(emotion?: string): string[] {
  const e = (emotion || "").toLowerCase();
  if (/gergin|kork|panik|kayma|kriz|tehlike|slip|fear|adrenalin/.test(e)) {
    return ["Neler Oldu?", "Ip Gerildi!", "Sakın!", "Tutun!"];
  }
  if (/zafer|cosku|neseli|triumph|joy|mutlu/.test(e)) {
    return ["İnanılmaz!", "Başardık!", "İşte O An!"];
  }
  if (/merak|sasir|curious|shock|heyecan/.test(e)) {
    return ["Şimdi Ne?", "Bak Buna!", "Vay Canına!"];
  }
  if (/uzgun|yorgun|endise/.test(e)) {
    return ["Dayan!", "Son Şans!", "Nefes Al!"];
  }
  return ["Bunu Kaçırma!", "Sakın Kaçırma!", "Şimdi İzle!"];
}

export function craftThumbnailOverlayText(input: {
  thumbnailText?: string;
  primaryTitle?: string;
  shortsHooks?: string[];
  emotionLabel?: string;
  /** Varsayilan Turkce — kapak yazisi her zaman TR */
  language?: string;
  /** Ayni duygu icin farkli kanca sec (ceşitlilik) */
  rotateSalt?: number;
}): string {
  void input.language;
  const hooks = turkishThumbnailHooks(input.emotionLabel);
  const salt = Math.abs(Math.floor(input.rotateSalt ?? Date.now())) % Math.max(1, hooks.length);
  const fallback = hooks[salt] || hooks[0] || "Bunu Kaçırma!";

  // Oncelik: kullanici / plan yazisi (TR) > kisa TR short hook > asla uzun baslik
  const candidates = [input.thumbnailText, ...(input.shortsHooks || [])]
    .map((s) => (s || "").replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .filter((s) => !looksLikeEnglishOverlay(s))
    // YouTube: 3 kelimeden uzun adaylari ele (baslik tekrarini engelle)
    .filter((s) => s.split(/\s+/).filter(Boolean).length <= 4);

  let raw = candidates[0] || fallback;
  if (looksLikeEnglishOverlay(raw)) raw = fallback;

  // CTR kurali: max 3 kelime / ~22 karakter (mobilde okunur)
  const words = raw.split(/\s+/).filter(Boolean);
  if (words.length > 3) raw = words.slice(0, 3).join(" ");
  if (raw.length > 22) raw = `${raw.slice(0, 20).trim()}…`;

  raw = raw
    .replace(/\b(bu videoda|kesfetmeye hazir|unutulmaz)\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();

  if (!raw || looksLikeEnglishOverlay(raw)) {
    raw = fallback;
  }

  raw = raw.replace(/[!?]{2,}/g, "?").replace(/[.]{2,}/g, "…");
  return raw;
}

/**
 * YouTube aciklamasini kisa-merak metnine cevirir.
 * Hedef: ~3 cumle / ~280-340 karakter govde (makale degil; 13-17 kelime nefes payi).
 */
export function forceShortCuriosityDescription(
  raw: string,
  opts: { title: string; hashtags?: string[] }
): string {
  const title = String(opts.title || "Bu video");
  const trimmed = String(raw || "").replace(/\r\n/g, "\n").trim();
  const hashFromBody: string[] = [];
  const bodyLines: string[] = [];
  for (const line of trimmed.split("\n")) {
    const t = line.trim();
    if (!t) continue;
    if (/^#\S/.test(t) && t.split(/\s+/).every((w) => w.startsWith("#"))) {
      hashFromBody.push(...t.split(/\s+/));
      continue;
    }
    bodyLines.push(t);
  }

  let body = bodyLines.join(" ").replace(/\s+/g, " ").trim();
  // CTA / abone nutuklarini at
  body = body
    .replace(/\bEğer\b[^.!?…]{0,280}[.!?…]/gi, " ")
    .replace(/\babone\s+ol[^.!?…]{0,120}[.!?…]/gi, " ")
    .replace(/\b(like|beğen|yorum yaz|paylaş|zil aç)[^.!?…]{0,80}[.!?…]/gi, " ")
    .replace(/\s+/g, " ")
    .trim();

  const sentences = body
    .split(/(?<=[.!?…])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 12 && !/abone|kaçırmamak|beğendiyseniz/i.test(s));

  // 3 kisa cumle: merak + bir nefes + izlemeye ceken kapanis
  let short = sentences.slice(0, 3).join(" ").trim();
  if (short.length > 340 && sentences.length >= 2) {
    short = sentences.slice(0, 2).join(" ").trim();
  }
  if (short.length > 360) {
    short = `${short.slice(0, 340).replace(/\s+\S*$/, "").trim()}…`;
  }
  if (short.length < 40) {
    const hook = title.replace(/[.!?…]+$/g, "").trim() || "Bu macera";
    short = `${hook} — bir an her şeyi değiştiriyor. Sis incelirken adım ritmi bozuluyor; ne olacağını izleyince görürsün.`;
  }

  const hashes = [...(opts.hashtags || []), ...hashFromBody]
    .map((h) => ensureHash(String(h || "")))
    .filter(Boolean)
    .filter((h, i, arr) => arr.indexOf(h) === i)
    .slice(0, 6)
    .join(" ");

  return hashes ? `${short}\n\n${hashes}` : short;
}

/**
 * YouTube aciklamasini kisa + merakli tutar (forceShort sarmalayici).
 */
export function tightenCuriosityDescription(raw: string, title = "Bu video"): string {
  return forceShortCuriosityDescription(raw, { title });
}

/** AI sonucunu yayina hazir hale getirir (eksik alanlari tamamlar). */
export function normalizePublishMeta(
  raw: z.infer<typeof publishMetaSchema>,
  ctx: { titleFallback: string; isKids: boolean; totalSeconds: number }
): z.infer<typeof publishMetaSchema> {
  const primary =
    cleanTitle(raw.primaryTitle) ||
    cleanTitle(raw.titleVariants[0] || "") ||
    cleanTitle(ctx.titleFallback) ||
    "Yeni video";

  let titleVariants = [...raw.titleVariants.map(cleanTitle).filter(Boolean)];
  if (!titleVariants.includes(primary)) titleVariants = [primary, ...titleVariants];
  titleVariants = [...new Set(titleVariants)].slice(0, 8);
  while (titleVariants.length < 5) {
    titleVariants.push(`${primary}${titleVariants.length === 1 ? "" : ` (${titleVariants.length})`}`);
  }

  let description = raw.description.trim();
  if (description.length < 40) {
    const hook = primary.replace(/[.!?]+$/, "");
    description = forceShortCuriosityDescription(
      `${hook} — bir an, sonra her şey değişiyor. Ne olduğunu söylemiyoruz. İzle, gör.`,
      { title: primary, hashtags: (raw.hashtags || []).slice(0, 5) }
    );
  } else {
    description = forceShortCuriosityDescription(description, {
      title: primary,
      hashtags: raw.hashtags || [],
    });
  }

  let tags = (raw.tags || []).map((t) => String(t || "").trim().toLowerCase()).filter(Boolean);
  if (tags.length < 12) {
    const extras = ctx.isKids
      ? [
          "çocuk",
          "çocuk videosu",
          "ebeveyn",
          "eğitici",
          "animasyon",
          "hikaye",
          "okul öncesi",
          "aile",
          "çocuk kanalı",
          "masal",
          "oyun",
          "öğrenme",
        ]
      : ["youtube", "hikaye", "anlatı", "video", "kanal", "yeni video", "önerilen"];
    tags = [...new Set([...tags, ...extras, primary.toLowerCase().slice(0, 40)])].slice(0, 30);
  }

  let hashtags = (raw.hashtags || []).map((h) => ensureHash(String(h || ""))).filter(Boolean);
  if (hashtags.length < 5) {
    const extras = ctx.isKids
      ? ["#youtube", "#çocuk", "#animasyon", "#hikaye", "#aile", "#yeni"]
      : ["#youtube", "#video", "#hikaye", "#yeni", "#önerilen"];
    hashtags = [...new Set([...hashtags, ...extras])].slice(0, 12);
  }

  const seo = raw.seoKeywords ?? { primary: "", secondary: [] };
  const seoPrimary = String(seo.primary || "").trim() || primary.split(/\s+/).slice(0, 4).join(" ");
  let seoSecondary = (seo.secondary || []).map((s) => String(s || "").trim()).filter(Boolean);
  if (seoSecondary.length < 3) {
    seoSecondary = [...new Set([...seoSecondary, ...tags.slice(0, 6)])].slice(0, 10);
  }

  let chapters = (raw.chapters || [])
    .map((c) => ({
      time: String(c?.time || "").trim() || "0:00",
      label: String(c?.label || "").trim() || "Sahne",
      beat: String(c?.beat || "").trim(),
    }))
    .filter((c) => c.label);
  if (chapters.length < 3) {
    const mid = formatTime(Math.floor(ctx.totalSeconds / 2));
    const late = formatTime(Math.floor(ctx.totalSeconds * 0.75));
    chapters = [
      { time: "0:00", label: "Başlangıç", beat: "açılış" },
      { time: mid, label: "Orta", beat: "gelişme" },
      { time: late, label: "Son", beat: "kapanış" },
      ...chapters,
    ].slice(0, 12);
  }
  if (chapters[0]) chapters[0] = { ...chapters[0], time: "0:00" };

  let thumbnailConcepts = (raw.thumbnailConcepts || [])
    .map((c, i) => ({
      name: String(c?.name || "").trim() || `Konsept ${i + 1}`,
      emotion: String(c?.emotion || "").trim() || "merak",
      hook: String(c?.hook || "").trim() || primary,
      prompt: String(c?.prompt || "").trim(),
    }))
    .filter((c) => c.prompt.length >= 20);
  if (thumbnailConcepts.length < 3) {
    const style = ctx.isKids
      ? "Feature-quality 3D Pixar-style kids character, soft cinematic lighting"
      : "Cinematic photorealistic subject, dramatic key light";
    thumbnailConcepts = [
      {
        name: "Yüz yakını",
        emotion: "şaşkınlık",
        hook: "İlk saniye merakı",
        prompt: `${style}, extreme close-up of the main character's face filling half the frame, eyes wide with clear emotion, high contrast, shallow depth of field, 16:9 YouTube thumbnail, absolutely no text no logos no watermarks`,
      },
      {
        name: "Aksiyon anı",
        emotion: "gerilim",
        hook: "Ortadaki kriz",
        prompt: `${style}, medium-wide shot of the peak action beat, clear silhouette, saturated but natural colors, cinematic composition rule of thirds, 16:9 YouTube thumbnail, absolutely no text no logos`,
      },
      {
        name: "Duygu kapanışı",
        emotion: "rahatlama",
        hook: "Sonuç öncesi nefes",
        prompt: `${style}, warm emotional two-shot or hero portrait after tension, soft rim light, readable at small size, 16:9 YouTube thumbnail, absolutely no text no captions`,
      },
      ...thumbnailConcepts,
    ].slice(0, 5);
  }

  const thumbnailPrompt =
    String(raw.thumbnailPrompt || "").trim().length >= 20
      ? String(raw.thumbnailPrompt || "").trim()
      : thumbnailConcepts[0]?.prompt ||
        `Professional 16:9 YouTube thumbnail, clear emotional hero subject, high contrast, no text no logos`;

  const thumbnailText = craftThumbnailOverlayText({
    thumbnailText: raw.thumbnailText || "",
    primaryTitle: primary,
    shortsHooks: raw.shortsHooks || [],
  });

  const defaults = {
    pinnedComment:
      String(raw.pinnedComment || "").trim() ||
      (ctx.isKids
        ? "Bu bölümü birlikte mi izlediniz? En sevdiğiniz anı yoruma yazın — bir sonrakinde ona göre sürpriz yapalım."
        : "İzlediğin için teşekkürler. En çok hangi kısım aklında kaldı? Yaz, okuyorum."),
    communityPost:
      String(raw.communityPost || "").trim() ||
      `Yeni video yayında: ${primary}\nKısa bir bakış atıp ne düşündüğünü söylemen yeterli.`,
    shortsHooks:
      (raw.shortsHooks || []).filter(Boolean).length >= 3
        ? (raw.shortsHooks || []).filter(Boolean).slice(0, 6)
        : [
            "Bir saniye — bunu kaçırmayın.",
            "Tam burada her şey değişiyor.",
            "Sonuna kadar bekleyin.",
          ],
    endScreenCta:
      String(raw.endScreenCta || "").trim() ||
      "Beğendiyseniz bir sonraki bölüme geçin; kanalda devamı var.",
    postingStrategy:
      String(raw.postingStrategy || "").trim() ||
      "Akşam aile saatine denk gelecek şekilde yayınla. İlk saatte sabit yorumu ekle. Shorts kancasından birini 24 saat içinde kes.",
    uploadChecklist:
      (raw.uploadChecklist || []).filter(Boolean).length >= 6
        ? (raw.uploadChecklist || []).filter(Boolean).slice(0, 16)
        : [
            "Başlığı yapıştır",
            "Açıklamayı yapıştır (bölümler dahil)",
            "Thumbnail yükle",
            "Etiketleri ekle",
            "Sabit yorumu yayın sonrası sabitle",
            "Çocuk içeriğiyse doğru yaş / Made for Kids işaretini kontrol et",
            "Önizlemeyi telefonda kontrol et",
          ],
    targetAudience:
      String(raw.targetAudience || "").trim() ||
      (ctx.isKids
        ? "Okul öncesi / ilkokul çocukları ve onlarla birlikte izleyen ebeveynler."
        : "Hikaye ve anlatı seven genel YouTube izleyicisi."),
    seriesHook: String(raw.seriesHook || "").trim(),
    kidsSafetyNotes:
      String(raw.kidsSafetyNotes || "").trim() ||
      (ctx.isKids
        ? "Korku yok; gerilim kısa ve ekipman/takımla çözülüyor. Ebeveyn yanında izleyebilir."
        : ""),
    contentWarnings: (raw.contentWarnings || []).filter(Boolean),
  };

  return {
    titleVariants,
    primaryTitle: primary,
    description,
    tags,
    hashtags,
    seoKeywords: { primary: seoPrimary, secondary: seoSecondary },
    targetAudience: defaults.targetAudience,
    thumbnailPrompt,
    thumbnailText,
    thumbnailConcepts,
    chapters,
    pinnedComment: defaults.pinnedComment,
    communityPost: defaults.communityPost,
    shortsHooks: defaults.shortsHooks,
    endScreenCta: defaults.endScreenCta,
    postingStrategy: defaults.postingStrategy,
    uploadChecklist: defaults.uploadChecklist,
    kidsSafetyNotes: defaults.kidsSafetyNotes,
    contentWarnings: defaults.contentWarnings,
    seriesHook: defaults.seriesHook,
  };
}

/** Image modeline giden promptu profesyonel thumbnail kurallariyla guclendirir. */
export function enhanceThumbnailPrompt(raw: string, opts?: { isKids?: boolean; characterHint?: string }): string {
  const style = opts?.isKids
    ? "Feature-film 3D kids animation look (Pixar/DreamWorks craft), soft global illumination, expressive big eyes"
    : "Cinematic high-end commercial still, rich color grade, dramatic motivated lighting";
  const character = opts?.characterHint?.trim()
    ? `Hero identity lock: ${opts.characterHint.trim().slice(0, 220)}.`
    : "";
  const core = raw.replace(/\s+/g, " ").trim();
  return [
    "Professional YouTube thumbnail, 16:9 landscape, ultra sharp, designed to read clearly at small mobile size.",
    style + ".",
    "Composition: one dominant subject occupying 40-65% of frame, strong eye contact or clear emotional beat, rule of thirds, deep but uncluttered background.",
    "Lighting: high contrast key + soft fill + subtle rim; saturated but natural colors; no muddy midtones.",
    character,
    `Scene brief: ${core}`,
    "ABSOLUTELY NO text, letters, numbers, logos, watermarks, UI, captions, speech bubbles, or borders.",
    "No collage, no split-screen spam, no stock-photo stiffness — one cohesive cinematic moment.",
  ]
    .filter(Boolean)
    .join(" ");
}

/** YouTube / kanal yayin planini en yuksek model ile uretir. */
export async function generatePublishMetadata(
  projectId: string,
  options?: GeneratePublishOptions
): Promise<{ meta: PublishMeta; thumbnailPath: string | null }> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const story = await prisma.story.findUnique({
    where: { projectId_languageVariant: { projectId, languageVariant: "primary" } },
  });
  const character = await prisma.characterProfile.findFirst({ where: { projectId, role: "main" } });
  const sides = await prisma.characterProfile.findMany({ where: { projectId, role: "side" } });
  const clips = await prisma.clip.findMany({
    where: { projectId, languageVariant: "primary" },
    orderBy: { index: "asc" },
  });

  const storyText = story?.fullStory || clips.map((c) => c.dialogue).filter(Boolean).join(" ");
  if (!storyText.trim() && clips.every((c) => !c.dialogue.trim() && !c.sceneDescription.trim())) {
    throw new Error("Meta verisi uretilecek icerik yok (hikaye/diyalog/sahne bos)");
  }

  const { model, reasoningEffort } = await resolvePublishAiModel();
  const timeline = buildTimelineBrief(clips);
  const isKids = project.templateType === "kids_animation" || project.templateType === "kids_song";
  const castLine = [character?.name, ...sides.map((s) => s.name)].filter(Boolean).join(", ");
  const characterHint = [character?.baseAppearancePrompt, character?.baseWardrobePrompt]
    .filter(Boolean)
    .join(" | ");

  await recordEvent({
    projectId,
    step: "publish",
    message: `Yayin plani uretiliyor (model=${model}, reasoning=${reasoningEffort})...`,
  });

  const result = await structuredCall<z.infer<typeof publishMetaSchema>>({
    model,
    reasoningEffort,
    maxOutputTokens: 24_000,
    timeoutMs: 600_000,
    system: `Sen deneyimli bir YouTube kanal yoneticisisin ve ayni zamanda iyi bir copywriter'sin.
Izleyiciye giden her cumle GERCEK BIR INSAN tarafindan yazilmis gibi olmali — sicak, net, sade, profesyonel.

DIL: ${project.storyLanguage || "Turkish"}

KOPYAYAZIM KURALLARI (EN KRITIK):
- Konusur gibi yaz. Kisa cumleler. Somut vaat. Gereksiz sus yok.
- Yasak AI / ajans kokusu: "kesfetmeye hazir misiniz", "unutulmaz yolculuk", "bu videoda sizlerle", "etkilesimi artirin", "SEO uyumlu", "icerik zenginligi", "merak uyandiran macera sizi bekliyor", "tiklayin ve abone olun simdi".
- Yasak: !!!, emoji yigini, BUYUK HARF BAGIRMA, sahte heycan, anahtar kelime doldurma.
- Baslik (primaryTitle + titleVariants): insanin gercekten tiklayacagi; meraklı ama duzgun; clickbait korku/tuzak yok; 40-70 karakter civari ideal.
- ACIKLAMA (YouTube — KISA + HAFIF MERAK; FILM ANLATMA / SPOILER YASAK):
  * Amac: okuyucu "ne oluyor?" desin ve VIDEOyu izlesin. Aciklamayi okuyup doymasın.
  * Uzunluk: GOVDE 3 kisa cumle (ideal ~200-320 karakter, hashtag haric). Makale / 4+ paragraf YASAK.
  * Yapi: (1) merak kancasi + ana arama kelimesi; (2) bir nefes/atmosfer (~15 kelime ekstra); (3) izlemeye ceken kapanis; (4) hashtagler en sonda.
  * Yasak: sahne sahne anlatim, "sonra / ardindan / sonunda", uzun CTA duvari, "Bu videoda...", abone/like nutuklari.
  * SEO: anahtar kelime ilk ~60 karakterde dogal.
- Etiket / hashtag: ebeveynlerin / cocuklarin gercekten aratacagi kelimeler.
- Sabit yorum + community: sohbet sorusu; samimi; spoiler yok.
- Shorts kancalari: tek nefeste soylenecek gercek cumleler (reklam sloganı degil).
- Checklist / strateji: kisa pratik not — kurumsal madde dili yok.
- chapters: timeline'a uyumlu MM:SS; kisa beat adi ("Kayma anı"); "Bolum 1" yasak.
${
  isKids
    ? `- COCUK (${project.ageBand || "3-8"}): ebeveyn guvenmeli; yumusak, net. kidsSafetyNotes vaaz gibi degil, duzgun Turkce.`
    : "- Genel izleyici; net vaat, samimi ton."
}

THUMBNAIL NOTU:
- thumbnailText: KAPAK YAZISI — ZORUNLU TURKCE (asla Ingilizce yazma). YouTube CTR: EN FAZLA 3 KELIME, yumruk gibi; ornek: "Neler Oldu?", "Ip Gerildi!", "Sakın Kaçırma". Spoiler yok; film anlatma. Latin harflerle Turkce yaz (ı/ğ/ü/ş/ö/ç kullan).
- thumbnailPrompt / thumbnailConcepts: yedek AI gorsel promptlari (Ingilizce). Asıl kapak tercihen videodaki ilgi cekici kare + thumbnailText bindirmesi.
- Konseptler duygusal farkli anlari tarif etsin (yuz / aksiyon / nefes ani).
- Karakter: ${characterHint.slice(0, 180) || "ana kahraman"}.

ALANLAR: titleVariants(5-8), primaryTitle, description, tags(12-30), hashtags(5-12), seoKeywords, targetAudience, thumbnailPrompt, thumbnailText, thumbnailConcepts(3-5), chapters(3+), pinnedComment, communityPost, shortsHooks(3-6), endScreenCta, postingStrategy, uploadChecklist(6+), kidsSafetyNotes, contentWarnings[], seriesHook.`,
    user: `KANAL / PROJE
Ad: ${project.channelName || project.name}
Baslik: ${project.title || project.name}
Tur: ${project.genre}
Sablon: ${project.templateType}
Tema/ders: ${project.moralLesson || "-"}
Yas: ${project.ageBand || "-"}
Kadro: ${castLine || "-"}
Kahraman gorsel: ${characterHint.slice(0, 300) || "-"}
Hedef sure ~${Math.round((timeline.totalSeconds || project.targetDurationSeconds) / 60)} dk (${Math.round(timeline.totalSeconds)} sn)
Dil: ${project.storyLanguage} / konusma: ${project.speechLanguage}

HIKAYE / OZET (SADECE senin baglamin — aciklamaya KOPYALAMA; film anlatma, spoiler yok):
${(story?.summary || storyText).slice(0, 4_000)}

KLIP TIMELINE (bolum zamanlari BUNA gore; uydurma):
${timeline.brief.slice(0, 12_000)}

Tam yayin paketini yaz.
Aciklama OZEL KURALI: 3 kisa cumle + hashtag (~15 kelime ekstra nefes). Izleyici doymasın — videoya cekilsin.`,
    schemaName: "publish_plan_v3",
    jsonSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        titleVariants: { type: "array", items: { type: "string" } },
        primaryTitle: { type: "string" },
        description: { type: "string" },
        tags: { type: "array", items: { type: "string" } },
        hashtags: { type: "array", items: { type: "string" } },
        seoKeywords: {
          type: "object",
          additionalProperties: false,
          properties: {
            primary: { type: "string" },
            secondary: { type: "array", items: { type: "string" } },
          },
          required: ["primary", "secondary"],
        },
        targetAudience: { type: "string" },
        thumbnailPrompt: { type: "string" },
        thumbnailText: { type: "string" },
        thumbnailConcepts: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            properties: {
              name: { type: "string" },
              emotion: { type: "string" },
              hook: { type: "string" },
              prompt: { type: "string" },
            },
            required: ["name", "emotion", "hook", "prompt"],
          },
        },
        chapters: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            properties: {
              time: { type: "string" },
              label: { type: "string" },
              beat: { type: "string" },
            },
            required: ["time", "label", "beat"],
          },
        },
        pinnedComment: { type: "string" },
        communityPost: { type: "string" },
        shortsHooks: { type: "array", items: { type: "string" } },
        endScreenCta: { type: "string" },
        postingStrategy: { type: "string" },
        uploadChecklist: { type: "array", items: { type: "string" } },
        kidsSafetyNotes: { type: "string" },
        contentWarnings: { type: "array", items: { type: "string" } },
        seriesHook: { type: "string" },
      },
      required: [
        "titleVariants",
        "primaryTitle",
        "description",
        "tags",
        "hashtags",
        "seoKeywords",
        "targetAudience",
        "thumbnailPrompt",
        "thumbnailText",
        "thumbnailConcepts",
        "chapters",
        "pinnedComment",
        "communityPost",
        "shortsHooks",
        "endScreenCta",
        "postingStrategy",
        "uploadChecklist",
        "kidsSafetyNotes",
        "contentWarnings",
        "seriesHook",
      ],
    },
    zodSchema: publishMetaSchema,
  });

  const normalized = normalizePublishMeta(result, {
    titleFallback: project.title || project.name,
    isKids,
    totalSeconds: timeline.totalSeconds || project.targetDurationSeconds || 60,
  });
  const snappedChapters = snapChaptersToTimeline(normalized.chapters, timeline.durations);

  const meta: PublishMeta = {
    ...normalized,
    chapters: snappedChapters,
    modelUsed: model,
    reasoningEffort,
    generatedAt: new Date().toISOString(),
  };

  await persistPublishMeta(projectId, project.slug, meta, model, reasoningEffort);

  let thumbnailPath: string | null = null;
  if (options?.autoThumbnail !== false) {
    try {
      await recordEvent({
        projectId,
        step: "publish",
        message: "Thumbnail: videodan ilgi cekici kare seciliyor...",
      });
      const picked = await generateThumbnailFromVideo(projectId);
      thumbnailPath = picked.path;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      await recordEvent({
        projectId,
        step: "publish",
        level: "warning",
        message: `Videodan thumbnail secilemedi: ${msg.slice(0, 160)}`,
      });
    }
  }

  await recordEvent({
    projectId,
    step: "publish",
    message: `Yayin plani hazir (${model}/${reasoningEffort}): ${meta.primaryTitle.slice(0, 60)}`,
  });
  return { meta, thumbnailPath };
}

async function persistPublishMeta(
  projectId: string,
  slug: string,
  meta: PublishMeta,
  model: string,
  reasoningEffort: string
): Promise<{ metaPath: string; txtPath: string }> {
  const root = ensureProjectDirs(slug);
  const publishDir = path.join(root, "output", "publish");
  const metaPath = path.join(publishDir, "youtube-meta.json");
  const txtPath = path.join(publishDir, "youtube-meta.txt");
  fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2), "utf8");
  fs.writeFileSync(txtPath, formatPublishReadable(meta), "utf8");
  await prisma.generatedAsset.create({
    data: {
      projectId,
      kind: "publish_meta",
      path: metaPath,
      bytes: fs.statSync(metaPath).size,
      meta: JSON.stringify({ model, reasoningEffort }),
    },
  });
  return { metaPath, txtPath };
}

/** Elle duzenlenen alanlari kaydeder (baslik, aciklama, etiket...). */
export async function savePublishMetadata(
  projectId: string,
  patch: Partial<z.infer<typeof publishMetaSchema>>
): Promise<PublishMeta> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const existing = (await loadPublishMetadata(projectId)) || {
    titleVariants: [],
    primaryTitle: project.title || project.name,
    description: "",
    tags: [],
    hashtags: [],
    seoKeywords: { primary: "", secondary: [] },
    targetAudience: "",
    thumbnailPrompt: "",
    thumbnailText: "",
    thumbnailConcepts: [],
    chapters: [],
    pinnedComment: "",
    communityPost: "",
    shortsHooks: [],
    endScreenCta: "",
    postingStrategy: "",
    uploadChecklist: [],
    kidsSafetyNotes: "",
    contentWarnings: [],
    seriesHook: "",
    modelUsed: "manual",
    reasoningEffort: "n/a",
    generatedAt: new Date().toISOString(),
  };

  const merged = {
    ...existing,
    ...patch,
    seoKeywords: patch.seoKeywords
      ? {
          primary: patch.seoKeywords.primary ?? existing.seoKeywords.primary,
          secondary: patch.seoKeywords.secondary ?? existing.seoKeywords.secondary,
        }
      : existing.seoKeywords,
    generatedAt: new Date().toISOString(),
  };

  const isKids = project.templateType === "kids_animation" || project.templateType === "kids_song";
  const normalized = normalizePublishMeta(merged, {
    titleFallback: project.title || project.name,
    isKids,
    totalSeconds: project.targetDurationSeconds || 60,
  });

  const meta: PublishMeta = {
    ...normalized,
    modelUsed: existing.modelUsed || "manual",
    reasoningEffort: existing.reasoningEffort || "n/a",
    generatedAt: merged.generatedAt,
  };
  await persistPublishMeta(projectId, project.slug, meta, meta.modelUsed, meta.reasoningEffort);
  await recordEvent({ projectId, step: "publish", message: "Yayin plani elle guncellendi" });
  return meta;
}

const descriptionRefreshSchema = z.object({
  description: z.string().default(""),
  hashtags: z.array(z.string()).default([]),
});

/**
 * Sadece YouTube aciklamasini GPT-5 (high) ile yeniden yazar:
 * kisa, spoiler yok, hafif merak — izlemeye ceker.
 */
export async function regeneratePublishDescription(projectId: string): Promise<PublishMeta> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const [story, clips, character, sides, existing] = await Promise.all([
    prisma.story.findUnique({
      where: { projectId_languageVariant: { projectId, languageVariant: "primary" } },
    }),
    prisma.clip.findMany({
      where: { projectId, languageVariant: "primary" },
      orderBy: { index: "asc" },
    }),
    prisma.characterProfile.findFirst({ where: { projectId, role: "main" } }),
    prisma.characterProfile.findMany({ where: { projectId, role: "side" } }),
    loadPublishMetadata(projectId),
  ]);

  const storyText = story?.fullStory || clips.map((c) => c.dialogue).filter(Boolean).join(" ");
  if (!storyText.trim() && !story?.summary?.trim()) {
    throw new Error("Aciklama icin hikaye/diyalog yok");
  }

  const { model } = await resolvePublishAiModel();
  // Aciklama yenilemede high cok yavas kaliyor; gpt-5 + low ile hizli, sonra ZORUNLU kisaltma
  const reasoningEffort = "low" as const;
  const isKids = project.templateType === "kids_animation" || project.templateType === "kids_song";
  const title =
    existing?.primaryTitle ||
    existing?.titleVariants?.[0] ||
    project.title ||
    project.name ||
    "Bu video";
  const castLine = [character?.name, ...sides.map((s) => s.name)].filter(Boolean).join(", ");

  await recordEvent({
    projectId,
    step: "publish",
    message: `Aciklama yenileniyor (${model}/${reasoningEffort}) — zorunlu kisa merak metni...`,
  });

  let aiDescription = "";
  let aiHashtags: string[] = [];
  try {
    const result = await structuredCall<z.infer<typeof descriptionRefreshSchema>>({
      model,
      reasoningEffort,
      maxOutputTokens: 900,
      timeoutMs: 120_000,
      system: `YouTube aciklama yazari. DIL: ${project.storyLanguage || "Turkish"}.

ZORUNLU CIKTI:
- description govdesi 3 KISA CUMLE (toplam ~200-320 karakter; oncekinden ~15 kelime daha nefes).
- Spoiler yok. Film ozeti yok. Malzeme listesi yok. Abone/like nutugu YOK.
- Yapi: (1) merak kancasi + anahtar kelime, (2) bir nefes/atmosfer, (3) "izleyince gor" hissi.
- Okuyucu doymasın; videoyu izleme geregi duysun.
- hashtags: 4-6 adet.
${isKids ? `Cocuk icerik (${project.ageBand || "3-8"}): guvenli ton.` : ""}

ORNEK TARZ — SADECE YAPI/TON icin; ornekteki mekan, konu ve etiketleri ASLA kullanma. Mekan/etiketler filmin KENDI temasindan gelir:
"Sis inceliyor — üç küçük kâşif adım ritmini bulabilecek mi? Bir an rüzgârın tonu değişiyor. Ne olduğunu izleyince görürsün.

#çocukanimasyonu #dostluk"`,
      user: `BASLIK: ${title}
KADRO: ${castLine || "-"}
TEMA: ${project.moralLesson || "-"}

BAGLAM (ASLA makale yazma; 3 kisa cumlelik merak uret, ~15 kelime ekstra nefes payi):
${(story?.summary || storyText).slice(0, 1_200)}

Simdi kisa ama bir nebze daha dolu merak aciklamasi yaz.`,
      schemaName: "publish_description_refresh_v3",
      jsonSchema: {
        type: "object",
        additionalProperties: false,
        properties: {
          description: { type: "string" },
          hashtags: { type: "array", items: { type: "string" } },
        },
        required: ["description", "hashtags"],
      },
      zodSchema: descriptionRefreshSchema,
    });
    aiDescription = String(result?.description || "");
    aiHashtags = Array.isArray(result?.hashtags) ? result.hashtags.map((h) => String(h || "")) : [];
  } catch (err) {
    await recordEvent({
      projectId,
      step: "publish",
      level: "warning",
      message: `Aciklama AI basarisiz, mevcut metin kisaltilacak: ${err instanceof Error ? err.message : String(err)}`,
    });
    aiDescription = existing?.description || title;
    aiHashtags = existing?.hashtags || [];
  }

  const tags = (aiHashtags.length ? aiHashtags : existing?.hashtags || [])
    .map((h) => ensureHash(String(h || "")))
    .filter(Boolean)
    .slice(0, 6);

  // Model uzun yazsa / hata olsa bile burada kisa merak metni kesinlesir
  const description = forceShortCuriosityDescription(aiDescription || existing?.description || title, {
    title,
    hashtags: tags,
  });

  const base = existing || {
    titleVariants: [title],
    primaryTitle: title,
    description: "",
    tags: [],
    hashtags: [],
    seoKeywords: { primary: title, secondary: [] },
    targetAudience: "",
    thumbnailPrompt: "",
    thumbnailText: "",
    thumbnailConcepts: [],
    chapters: [],
    pinnedComment: "",
    communityPost: "",
    shortsHooks: [],
    endScreenCta: "",
    postingStrategy: "",
    uploadChecklist: [],
    kidsSafetyNotes: "",
    contentWarnings: [],
    seriesHook: "",
    modelUsed: model,
    reasoningEffort,
    generatedAt: new Date().toISOString(),
  };

  const normalized = normalizePublishMeta(
    {
      ...base,
      description,
      hashtags: tags.length ? tags : base.hashtags,
    },
    {
      titleFallback: title,
      isKids,
      totalSeconds: project.targetDurationSeconds || 60,
    }
  );

  const meta: PublishMeta = {
    ...normalized,
    modelUsed: model,
    reasoningEffort,
    generatedAt: new Date().toISOString(),
  };

  await persistPublishMeta(projectId, project.slug, meta, model, reasoningEffort);
  await recordEvent({
    projectId,
    step: "publish",
    message: `Aciklama yenilendi (${model}): ${meta.description.slice(0, 80).replace(/\n/g, " ")}…`,
  });
  return meta;
}

function snapChaptersToTimeline(
  chapters: Array<{ time: string; label: string; beat: string }>,
  durations: number[]
): Array<{ time: string; label: string; beat: string }> {
  if (durations.length === 0) return chapters;
  const boundaries: number[] = [0];
  let t = 0;
  for (const d of durations) {
    t += d;
    boundaries.push(t);
  }
  const total = boundaries[boundaries.length - 1] || 1;

  return chapters.map((ch, i) => {
    const parsed = parseClock(ch.time);
    let nearest = boundaries[0];
    let best = Infinity;
    for (const b of boundaries) {
      const dist = Math.abs(b - parsed);
      if (dist < best) {
        best = dist;
        nearest = b;
      }
    }
    if (i === 0) nearest = 0;
    if (nearest > total * 0.95) nearest = boundaries[Math.max(0, boundaries.length - 2)] ?? 0;
    return { ...ch, time: formatTime(nearest) };
  });
}

function parseClock(time: string): number {
  const parts = time.trim().split(":").map(Number);
  if (parts.length === 2 && parts.every((n) => Number.isFinite(n))) return parts[0] * 60 + parts[1];
  if (parts.length === 3 && parts.every((n) => Number.isFinite(n))) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return 0;
}

function formatPublishReadable(meta: PublishMeta): string {
  return [
    `=== MODEL: ${meta.modelUsed} (reasoning=${meta.reasoningEffort}) ===`,
    `Uretildi: ${meta.generatedAt}`,
    "",
    "=== BIRINCIL BASLIK ===",
    meta.primaryTitle,
    "",
    "=== BASLIK VARYANTLARI ===",
    ...meta.titleVariants.map((t, i) => `${i + 1}. ${t}`),
    "",
    "=== HEDEF KITLE ===",
    meta.targetAudience,
    "",
    "=== SEO ===",
    `Ana: ${meta.seoKeywords.primary}`,
    `Ikincil: ${meta.seoKeywords.secondary.join(", ")}`,
    "",
    "=== ACIKLAMA ===",
    meta.description,
    "",
    "=== BOLUMLER ===",
    ...meta.chapters.map((c) => `${c.time} ${c.label}${c.beat ? ` [${c.beat}]` : ""}`),
    "",
    "=== ETIKETLER ===",
    meta.tags.join(", "),
    "",
    "=== HASHTAGS ===",
    meta.hashtags.join(" "),
    "",
    "=== SABIT YORUM ===",
    meta.pinnedComment,
    "",
    "=== COMMUNITY POST ===",
    meta.communityPost,
    "",
    "=== SHORTS KANCALARI ===",
    ...meta.shortsHooks.map((h, i) => `${i + 1}. ${h}`),
    "",
    "=== END SCREEN CTA ===",
    meta.endScreenCta,
    "",
    "=== YAYIN STRATEJISI ===",
    meta.postingStrategy,
    "",
    "=== SERI KANCASI ===",
    meta.seriesHook || "(yok)",
    "",
    "=== COCUK GUVENLIGI ===",
    meta.kidsSafetyNotes || "(yok)",
    "",
    "=== UYARILAR ===",
    meta.contentWarnings.length ? meta.contentWarnings.join(", ") : "(yok)",
    "",
    "=== YUKLEME CHECKLIST ===",
    ...meta.uploadChecklist.map((c, i) => `${i + 1}. ${c}`),
    "",
    "=== THUMBNAIL YAZISI ===",
    meta.thumbnailText || "(yok)",
    "",
    "=== THUMBNAIL KONSEPTLERI ===",
    ...meta.thumbnailConcepts.flatMap((c, i) => [`${i + 1}. ${c.name} — ${c.emotion} — ${c.hook}`, c.prompt, ""]),
    "=== THUMBNAIL PROMPT (SECILI) ===",
    meta.thumbnailPrompt,
  ].join("\n");
}

/** Kayitli yayin planini okur (varsa). */
export async function loadPublishMetadata(projectId: string): Promise<PublishMeta | null> {
  const project = await prisma.project.findUnique({ where: { id: projectId }, select: { slug: true } });
  if (!project) return null;
  const metaPath = safeProjectPath(project.slug, "output", "publish", "youtube-meta.json");
  if (!fs.existsSync(metaPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(metaPath, "utf8")) as PublishMeta;
  } catch {
    return null;
  }
}

/** Meta + son thumbnail/SRT yollari (UI kaliciligi). */
export async function loadPublishPackage(projectId: string): Promise<PublishPackage> {
  const project = await prisma.project.findUnique({ where: { id: projectId }, select: { slug: true } });
  if (!project) {
    return { meta: null, thumbnails: [], srtPath: null, subtitleFiles: [], metaJsonPath: null, metaTxtPath: null };
  }

  const meta = await loadPublishMetadata(projectId);
  const metaJsonPath = safeProjectPath(project.slug, "output", "publish", "youtube-meta.json");
  const metaTxtPath = safeProjectPath(project.slug, "output", "publish", "youtube-meta.txt");

  const assets = await prisma.generatedAsset.findMany({
    where: { projectId, kind: { in: ["thumbnail", "srt"] } },
    orderBy: { createdAt: "desc" },
    take: 40,
  });

  const thumbnails = assets
    .filter((a) => a.kind === "thumbnail" && a.path && fs.existsSync(a.path))
    .slice(0, 8)
    .map((a) => ({ path: a.path, createdAt: a.createdAt.toISOString() }));

  // Diskte DB kaydi olmayan thumbnail'leri de tara
  const publishDir = path.join(ensureProjectDirs(project.slug), "output", "publish");
  if (fs.existsSync(publishDir)) {
    for (const name of fs.readdirSync(publishDir)) {
      if (!/^thumbnail(-\d+)?\.png$/i.test(name)) continue;
      const full = path.join(publishDir, name);
      if (!thumbnails.some((t) => t.path === full) && fs.existsSync(full)) {
        thumbnails.push({ path: full, createdAt: fs.statSync(full).mtime.toISOString() });
      }
    }
  }
  thumbnails.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));

  const srtAsset = assets.find((a) => a.kind === "srt" && a.path && fs.existsSync(a.path));
  let srtPath = srtAsset?.path ?? null;
  if (!srtPath) {
    const root = ensureProjectDirs(project.slug);
    const candidate = path.join(root, "output", "final.srt");
    if (fs.existsSync(candidate)) srtPath = candidate;
  }

  const { listYoutubeSubtitleFiles } = await import("@/server/services/youtube-subtitles");
  const subtitleFiles = listYoutubeSubtitleFiles(project.slug).map((f) => ({
    code: f.code,
    name: f.name,
    youtube: f.youtube,
    path: f.path,
    downloadName: f.downloadName,
  }));
  if (subtitleFiles[0] && !srtPath) srtPath = subtitleFiles[0].path;

  return {
    meta,
    thumbnails: thumbnails.slice(0, 8),
    srtPath,
    subtitleFiles,
    metaJsonPath: fs.existsSync(metaJsonPath) ? metaJsonPath : null,
    metaTxtPath: fs.existsSync(metaTxtPath) ? metaTxtPath : null,
  };
}

function emotionScore(label: string): number {
  const t = label.toLowerCase();
  // YouTube: abartili duygu (sasirma/gerilim/heyecan) CTR'yi en cok artirir
  if (/kork|panik|gergin|kriz|kayma|tehlike|sasir|sok|adrenalin/.test(t)) return 5;
  if (/heyecan|merak|neseli|zafer|cosku|mutlu/.test(t)) return 4;
  if (/uzgun|yorgun|endise|umut/.test(t)) return 2;
  if (/sakin|notr|idle|duragan/.test(t)) return 0;
  return 1;
}

type RankedClip = {
  index: number;
  score: number;
  reason: string;
  emotionLabel: string;
  videoPath: string | null;
  lastFramePath: string | null;
  sceneImagePath: string | null;
  duration: number;
};

/** Ilgi cekici thumbnail adaylarini merak/duygu/kanca ile siralar (YouTube yuz+duygu odakli). */
export function rankThumbnailClips(
  clips: Array<{
    index: number;
    status: string;
    curiosityScore: number;
    hasHook: boolean;
    emotionLabel: string;
    videoPath: string | null;
    lastFramePath: string | null;
    sceneImagePath: string | null;
    actualDurationSeconds: number | null;
    estimatedDurationSeconds: number;
  }>
): RankedClip[] {
  const usable = clips.filter(
    (c) =>
      c.status === "completed" && Boolean(c.videoPath || c.lastFramePath || c.sceneImagePath)
  );
  if (usable.length === 0) return [];

  const n = usable.length;
  return usable
    .map((c, i) => {
      const pos = n <= 1 ? 0.5 : i / (n - 1);
      // Ortaya / doruga yakin (ilk acilis ve final daha zayif — YouTube'da "aksiyon anı" daha iyi)
      const positionBoost = pos >= 0.25 && pos <= 0.8 ? 4 : pos >= 0.15 && pos < 0.25 ? 2 : pos > 0.8 ? 1 : 0;
      const score =
        (c.curiosityScore || 0) * 2 +
        (c.hasHook ? 3 : 0) +
        emotionScore(c.emotionLabel || "") +
        positionBoost;
      const reason = [
        c.hasHook ? "kancali beat" : null,
        c.curiosityScore >= 7 ? `yuksek merak (${c.curiosityScore})` : null,
        c.emotionLabel ? `duygu: ${c.emotionLabel}` : null,
        positionBoost >= 3 ? "filmin orta-doruk bolgesi" : null,
      ]
        .filter(Boolean)
        .join(", ");
      return {
        index: c.index,
        score,
        reason: reason || `sahne #${c.index}`,
        emotionLabel: c.emotionLabel || "",
        videoPath: c.videoPath,
        lastFramePath: c.lastFramePath,
        sceneImagePath: c.sceneImagePath,
        duration: c.actualDurationSeconds ?? c.estimatedDurationSeconds ?? 8,
      };
    })
    .sort((a, b) => b.score - a.score || a.index - b.index);
}

/** Son uretilen video-thumbnail'lerde kullanilan klip + saniye (tekrar engeli). */
export async function loadRecentThumbnailPicks(
  projectId: string,
  limit = 8
): Promise<Array<{ clipIndex: number; atSec: number | null }>> {
  const assets = await prisma.generatedAsset.findMany({
    where: { projectId, kind: "thumbnail" },
    orderBy: { createdAt: "desc" },
    take: limit,
    select: { meta: true },
  });
  const out: Array<{ clipIndex: number; atSec: number | null }> = [];
  for (const a of assets) {
    try {
      const meta = JSON.parse(a.meta || "{}") as {
        source?: string;
        clipIndex?: number;
        detail?: string;
      };
      if (meta.source !== "video" || meta.clipIndex == null) continue;
      const atMatch = String(meta.detail || "").match(/@(\d+(?:\.\d+)?)s/);
      out.push({
        clipIndex: meta.clipIndex,
        atSec: atMatch ? Number(atMatch[1]) : null,
      });
    } catch {
      // ignore
    }
  }
  return out;
}

/**
 * Ust siradaki adaylardan biri — son kullanilan klipleri / ayni saniyeyi atlar.
 * Her tiklamada farkli kare uretmek icin.
 */
export function pickDiverseThumbnailCandidate(
  ranked: RankedClip[],
  recent: Array<{ clipIndex: number; atSec: number | null }>,
  preferredClipIndex?: number
): { clip: RankedClip; frameRatio: number } {
  if (ranked.length === 0) throw new Error("Thumbnail adayi yok");

  if (preferredClipIndex != null) {
    const forced = ranked.find((r) => r.index === preferredClipIndex);
    if (forced) {
      const usedAts = recent.filter((r) => r.clipIndex === forced.index).map((r) => r.atSec);
      const ratios = [0.28, 0.42, 0.55, 0.68, 0.78];
      const frameRatio =
        ratios.find((r) => !usedAts.some((u) => u != null && Math.abs(u - forced.duration * r) < 0.35)) ||
        ratios[recent.length % ratios.length];
      return { clip: forced, frameRatio };
    }
  }

  const recentIndexes = new Set(recent.slice(0, 5).map((r) => r.clipIndex));
  const topPool = ranked.slice(0, Math.min(6, ranked.length));
  const fresh = topPool.filter((r) => !recentIndexes.has(r.index));
  const pool = fresh.length > 0 ? fresh : topPool;

  // Skora gore agirlikli secim — her seferinde #1'i zorlamaz
  const weights = pool.map((r, i) => Math.max(1, r.score) * (pool.length - i));
  const total = weights.reduce((a, b) => a + b, 0);
  let roll = (Date.now() + ranked.length * 17) % total;
  let chosen = pool[0];
  for (let i = 0; i < pool.length; i++) {
    roll -= weights[i];
    if (roll < 0) {
      chosen = pool[i];
      break;
    }
  }

  const usedAts = recent.filter((r) => r.clipIndex === chosen.index).map((r) => r.atSec);
  // Duygusal doruk: klip ortasi-sonrasi (0.45 sabitini kir)
  const ratios = [0.32, 0.45, 0.58, 0.7, 0.22];
  const frameRatio =
    ratios.find((r) => !usedAts.some((u) => u != null && Math.abs(u - chosen.duration * r) < 0.4)) ||
    ratios[(recent.length + chosen.index) % ratios.length];

  return { clip: chosen, frameRatio };
}

/**
 * Videodaki ilgi cekici klibin cesitli bir karesinden kapak secer
 * ve uzerine YouTube tarzi kalin Turkce yazi bindirir (ust safe-zone).
 * OpenAI image_generation KULLANMAZ — hiz siniri yok.
 */
export async function generateThumbnailFromVideo(
  projectId: string,
  options?: {
    preferredClipIndex?: number;
    overlayText?: string;
    /** varsayilan true — kapaga yazi yaz */
    withText?: boolean;
  }
): Promise<{ path: string; clipIndex: number; reason: string; overlayText: string }> {
  const preferredClipIndex = options?.preferredClipIndex;
  const withText = options?.withText !== false;

  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const clips = await prisma.clip.findMany({
    where: { projectId, languageVariant: "primary" },
    orderBy: { index: "asc" },
    select: {
      index: true,
      status: true,
      curiosityScore: true,
      hasHook: true,
      emotionLabel: true,
      videoPath: true,
      lastFramePath: true,
      sceneImagePath: true,
      actualDurationSeconds: true,
      estimatedDurationSeconds: true,
    },
  });

  const ranked = rankThumbnailClips(clips).filter(
    (r) =>
      (r.videoPath && fs.existsSync(r.videoPath)) ||
      (r.lastFramePath && fs.existsSync(r.lastFramePath)) ||
      (r.sceneImagePath && fs.existsSync(r.sceneImagePath))
  );
  if (ranked.length === 0) {
    throw new Error("Tamamlanmis klip videosu yok — once klipleri uretin veya AI thumbnail deneyin.");
  }

  const recent = await loadRecentThumbnailPicks(projectId, 10);
  const { clip: picked, frameRatio } = pickDiverseThumbnailCandidate(ranked, recent, preferredClipIndex);

  const meta = await loadPublishMetadata(projectId);
  const overlayText = craftThumbnailOverlayText({
    thumbnailText: options?.overlayText || meta?.thumbnailText,
    shortsHooks: meta?.shortsHooks,
    emotionLabel: picked.emotionLabel || picked.reason,
    language: "Turkish",
    rotateSalt: Date.now() + picked.index * 13,
  });

  const root = ensureProjectDirs(project.slug);
  const publishDir = path.join(root, "output", "publish");
  fs.mkdirSync(publishDir, { recursive: true });
  const plainPath = nextAvailablePath(path.join(publishDir, "thumbnail-plain.png"));
  const thumbPath = nextAvailablePath(path.join(publishDir, "thumbnail.png"));

  let sourceNote = "frame";
  if (picked.videoPath && fs.existsSync(picked.videoPath)) {
    let at = Math.max(0.35, picked.duration * frameRatio);
    try {
      const info = await probeVideo(picked.videoPath);
      if (info.durationSeconds > 0.8) {
        at = Math.min(
          info.durationSeconds - 0.25,
          Math.max(0.25, info.durationSeconds * frameRatio)
        );
      }
    } catch {
      // probe basarisizsa tahmini sureyle devam
    }
    await extractFrameAt(picked.videoPath, at, plainPath);
    sourceNote = `clip#${picked.index}@${at.toFixed(1)}s`;
  } else if (picked.lastFramePath && fs.existsSync(picked.lastFramePath)) {
    fs.copyFileSync(picked.lastFramePath, plainPath);
    sourceNote = `lastFrame#${picked.index}`;
  } else if (picked.sceneImagePath && fs.existsSync(picked.sceneImagePath)) {
    fs.copyFileSync(picked.sceneImagePath, plainPath);
    sourceNote = `sceneImage#${picked.index}`;
  } else {
    throw new Error(`Sahne #${picked.index} icin kullanilabilir kare yok`);
  }

  if (!fs.existsSync(plainPath) || fs.statSync(plainPath).size < 800) {
    throw new Error("Thumbnail karesi yazilamadi");
  }

  let finalPath = plainPath;
  let textNote = "";
  if (withText && overlayText) {
    try {
      // YouTube: yazi USTTE — sag-alt sure rozeti kapamasin
      await burnTextOntoImage(plainPath, thumbPath, overlayText, { position: "top" });
      finalPath = thumbPath;
      textNote = overlayText;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      await recordEvent({
        projectId,
        step: "publish",
        level: "warning",
        message: `Kapak yazisi bindirilemedi (${msg.slice(0, 120)}); duz kare kullanildi`,
      });
      fs.copyFileSync(plainPath, thumbPath);
      finalPath = thumbPath;
    }
  } else {
    fs.copyFileSync(plainPath, thumbPath);
    finalPath = thumbPath;
  }

  await prisma.generatedAsset.create({
    data: {
      projectId,
      kind: "thumbnail",
      path: finalPath,
      bytes: fs.statSync(finalPath).size,
      meta: JSON.stringify({
        source: "video",
        clipIndex: picked.index,
        reason: picked.reason,
        detail: sourceNote,
        score: picked.score,
        frameRatio,
        overlayText: textNote || null,
      }),
    },
  });
  await recordEvent({
    projectId,
    step: "publish",
    message: textNote
      ? `Thumbnail videodan + yazi: sahne #${picked.index} — "${textNote}" (${sourceNote})`
      : `Thumbnail videodan secildi: sahne #${picked.index} (${picked.reason})`,
  });
  return { path: finalPath, clipIndex: picked.index, reason: picked.reason, overlayText: textNote || overlayText };
}

/** AI ile thumbnail uretir (yedek yol; rate limit'te yeniden dener). */
export async function generateThumbnail(projectId: string, customPrompt?: string): Promise<string> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const isKids = project.templateType === "kids_animation" || project.templateType === "kids_song";
  const character = await prisma.characterProfile.findFirst({ where: { projectId, role: "main" } });
  const characterHint = [character?.baseAppearancePrompt, character?.baseWardrobePrompt, character?.name]
    .filter(Boolean)
    .join(" | ");

  let prompt = customPrompt?.trim();
  if (!prompt) {
    const metaPath = safeProjectPath(project.slug, "output", "publish", "youtube-meta.json");
    if (fs.existsSync(metaPath)) {
      const meta = JSON.parse(fs.readFileSync(metaPath, "utf8")) as { thumbnailPrompt?: string };
      prompt = meta.thumbnailPrompt;
    }
  }
  if (!prompt) throw new Error("Thumbnail promptu yok. Once yayin planini uretin veya prompt girin.");

  const enhanced = enhanceThumbnailPrompt(prompt, { isKids, characterHint });
  const buffer = await generateImage(enhanced, "16:9");
  const root = ensureProjectDirs(project.slug);
  const thumbPath = nextAvailablePath(path.join(root, "output", "publish", "thumbnail.png"));
  fs.writeFileSync(thumbPath, buffer);
  await prisma.generatedAsset.create({
    data: {
      projectId,
      kind: "thumbnail",
      path: thumbPath,
      bytes: buffer.length,
      meta: JSON.stringify({ enhanced: true, source: "ai" }),
    },
  });
  await recordEvent({
    projectId,
    step: "publish",
    message: `AI thumbnail uretildi: ${path.basename(thumbPath)}`,
  });
  return thumbPath;
}

/** Final videoyla uyumlu SRT dosyasi uretir (tek dil / eski yol). */
export async function generateSrtFile(projectId: string, languageVariant = "primary"): Promise<string> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType === "longform" && languageVariant === "primary") {
    const tsPath = path.join(ensureProjectDirs(project.slug), "longform", "timestamps.json");
    if (fs.existsSync(tsPath)) {
      const items = JSON.parse(fs.readFileSync(tsPath, "utf8")) as Array<{
        text: string;
        startSeconds: number;
        endSeconds: number;
      }>;
      const cues = buildSrtCuesFromTimestamps(items);
      const content = buildSrtContent(cues);
      const root = ensureProjectDirs(project.slug);
      const srtPath = path.join(root, "output", "publish", "youtube-altyazi-ana-dil.srt");
      fs.mkdirSync(path.dirname(srtPath), { recursive: true });
      fs.writeFileSync(srtPath, `\uFEFF${content}`, "utf8");
      await prisma.generatedAsset.create({
        data: { projectId, kind: "srt", path: srtPath, bytes: Buffer.byteLength(content, "utf8"), languageVariant },
      });
      await recordEvent({
        projectId,
        step: "publish",
        message: `SRT altyazi uretildi (TTS zaman damgasi): ${path.basename(srtPath)} (${cues.length} kuyruk)`,
      });
      return srtPath;
    }
  }
  const clips = await prisma.clip.findMany({
    where: { projectId, languageVariant },
    orderBy: { index: "asc" },
  });
  const { selectClipsForRender } = await import("@/server/services/render");
  // Primary'de final ile ayni klip seti; diger varyantlarda diyalog+estimated sure
  const timed =
    languageVariant === "primary"
      ? selectClipsForRender(clips).included.map((row) => {
          const c = clips.find((x) => x.index === row.index)!;
          return {
            index: c.index,
            dialogue: c.dialogue,
            durationSeconds: c.actualDurationSeconds ?? c.estimatedDurationSeconds,
          };
        })
      : clips
          .filter((c) => c.dialogue.trim())
          .map((c) => ({
            index: c.index,
            dialogue: c.dialogue,
            durationSeconds: c.actualDurationSeconds ?? c.estimatedDurationSeconds,
          }));
  if (timed.length === 0) throw new Error("SRT icin diyaloglu / videosu olan klip yok");

  const cues = buildSrtCues(timed);
  const content = buildSrtContent(cues);

  const root = ensureProjectDirs(project.slug);
  const label = languageVariant === "primary" ? "ana-dil" : languageVariant;
  const srtPath = path.join(root, "output", "publish", `youtube-altyazi-${label}.srt`);
  fs.mkdirSync(path.dirname(srtPath), { recursive: true });
  fs.writeFileSync(srtPath, `\uFEFF${content}`, "utf8");
  await prisma.generatedAsset.create({
    data: { projectId, kind: "srt", path: srtPath, bytes: Buffer.byteLength(content, "utf8"), languageVariant },
  });
  await recordEvent({
    projectId,
    step: "publish",
    message: `SRT altyazi uretildi: ${path.basename(srtPath)} (${cues.length} kuyruk)`,
  });
  return srtPath;
}
