import fs from "node:fs";
import OpenAI from "openai";
import { z } from "zod";
import { resolveOpenAiKey, getSettings } from "@/server/services/settings";
import { logger } from "@/server/lib/logger";

/**
 * OpenAI erisim katmani.
 * - Anahtar yalnizca sunucu tarafinda cozulur
 * - Yapilandirilmis JSON ciktilar Responses API + json_schema ile alinir
 * - Zod ile dogrulanir; bozuk cikti gelirse bir kez yeniden denenir
 */

export class OpenAiKeyMissingError extends Error {
  constructor() {
    super("OpenAI API anahtari ayarlanmamis. Ayarlar ekranindan anahtari girin.");
    this.name = "OpenAiKeyMissingError";
  }
}

export async function getOpenAiClient(): Promise<OpenAI> {
  const key = await resolveOpenAiKey();
  if (!key) throw new OpenAiKeyMissingError();
  return new OpenAI({ apiKey: key });
}

async function getClient(): Promise<OpenAI> {
  return getOpenAiClient();
}

/** Anahtar ve model ile kucuk bir baglanti testi yapar. */
export async function testOpenAiConnection(): Promise<{ ok: boolean; model: string; message: string }> {
  const settings = await getSettings();
  try {
    const client = await getClient();
    const response = await client.responses.create({
      model: settings.openaiModel,
      input: "Yanit olarak yalnizca OK yaz.",
      max_output_tokens: 16,
    });
    const text = (response.output_text ?? "").trim();
    return { ok: true, model: settings.openaiModel, message: `Baglanti basarili (${text.slice(0, 20) || "yanit alindi"})` };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, model: settings.openaiModel, message };
  }
}

export interface StructuredCallOptions<T> {
  system: string;
  user: string;
  schemaName: string;
  /** OpenAI json_schema bicimi (strict) */
  jsonSchema: Record<string, unknown>;
  /** Sunucu tarafi dogrulama. Girdi tipi serbest: varsayilanli (.default) alanlar da kabul edilir. */
  zodSchema: z.ZodType<T, z.ZodTypeDef, unknown>;
  model?: string;
  maxOutputTokens?: number;
  /**
   * Akil yurutme derinligi (yalnizca gpt-5 / o-serisi).
   * "low" belirgin sekilde hizlidir; cok parcali yapilandirilmis ciktilarda
   * ("medium") tutarlilik artar.
   */
  reasoningEffort?: "minimal" | "low" | "medium" | "high";
  /** Istek zaman asimi; asilirsa anlasilir bir hata doner (varsayilan 4 dk). */
  timeoutMs?: number;
}

/** Akil yurutme parametresini kabul eden model aileleri. */
const REASONING_MODELS = /^(gpt-5|o1|o3|o4)/i;

const DEFAULT_CALL_TIMEOUT_MS = 240_000;

function isBillingOrQuotaError(err: unknown): boolean {
  const message = err instanceof Error ? err.message : String(err);
  const code = String((err as { code?: string })?.code || "").toLowerCase();
  return (
    code === "insufficient_quota" ||
    /insufficient_quota|billing|exceeded your current quota|you exceeded your.*quota|payment|bakiy/i.test(message)
  );
}

function friendlyOpenAiError(err: unknown, schemaName: string): Error {
  const message = err instanceof Error ? err.message : String(err);
  if (/timed?\s*out|ETIMEDOUT|ECONNRESET/i.test(message)) {
    return new Error(
      `OpenAI yaniti zaman asimina ugradi (${schemaName}). Uzun hikaye on bilgisi veya cok sahne icin tekrar deneyin; sorun surerse Ayarlar'dan daha hizli bir model secin.`
    );
  }
  // Bakiye/kota bitince OpenAI bazen 429 doner — once bunu yakala
  if (isBillingOrQuotaError(err)) {
    return new Error(
      `OpenAI bakiyesi / kotasi yetersiz (${schemaName}). platform.openai.com uzerinden faturalandirmayi kontrol edip bakiye yukleyin.`
    );
  }
  if (/rate limit|429|too many requests/i.test(message)) {
    return new Error(`OpenAI hiz siniri asildi (${schemaName}). Birkac saniye sonra tekrar deneyin.`);
  }
  return new Error(`OpenAI cagrisi basarisiz (${schemaName}): ${message}`);
}

/**
 * Yapilandirilmis JSON cagrisi. Model ciktisi Zod'dan gecmezse
 * hata mesajiyla birlikte bir kez daha denenir.
 */
export async function structuredCall<T>(options: StructuredCallOptions<T>): Promise<T> {
  const settings = await getSettings();
  const client = await getClient();
  const model = options.model ?? settings.openaiModel;

  const timeout = options.timeoutMs ?? DEFAULT_CALL_TIMEOUT_MS;
  let useReasoning = REASONING_MODELS.test(model);

  let lastError: string | null = null;
  /*
   * Responses API'de AKIL YURUTME jetonlari da max_output_tokens butcesinden
   * harcanir. Butce yetmezse yanit "incomplete" doner ve JSON yarida kesilir
   * ("Gecersiz JSON" hatasi). Bu durumda ikinci denemede butce buyutulur ve
   * akil yurutme bir kademe dusurulur — boylece cagri kendi kendini toparlar.
   */
  let budget: number = options.maxOutputTokens ?? 16_000;
  let effort: NonNullable<StructuredCallOptions<T>["reasoningEffort"]> = options.reasoningEffort ?? "low";

  for (let attempt = 1; attempt <= 2; attempt++) {
    const startedAt = Date.now();
    // Acik tip: "evolving let" cikarimi, asagidaki response.* kullanimlarinda
    // dairesel cikarim hatasina yol aciyor.
    let response: OpenAI.Responses.Response;
    try {
      response = await client.responses.create(
        {
          model,
          instructions: options.system,
          input:
            attempt === 1
              ? options.user
              : `${options.user}\n\nONCEKI CIKTI SU HATAYLA REDDEDILDI, DUZELTEREK TEKRAR URET: ${lastError}`,
          max_output_tokens: budget,
          text: {
            format: {
              type: "json_schema",
              name: options.schemaName,
              strict: true,
              schema: options.jsonSchema,
            },
          },
          ...(useReasoning ? { reasoning: { effort } } : {}),
        },
        { timeout }
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      // Model akil yurutme parametresini kabul etmiyorsa parametresiz tekrar dene
      if (useReasoning && /reasoning|unsupported parameter|unknown parameter/i.test(message)) {
        logger.warn({ model, schema: options.schemaName }, "Model reasoning parametresini kabul etmedi; parametresiz denenecek");
        useReasoning = false;
        attempt--;
        continue;
      }
      throw friendlyOpenAiError(err, options.schemaName);
    }
    const usage = response.usage;
    logger.info(
      {
        schema: options.schemaName,
        model,
        attempt,
        seconds: Math.round((Date.now() - startedAt) / 1000),
        status: response.status,
        budget,
        effort: useReasoning ? effort : "-",
        outputTokens: usage?.output_tokens,
        reasoningTokens: usage?.output_tokens_details?.reasoning_tokens,
      },
      "OpenAI cagrisi tamamlandi"
    );

    // Butce/durdurma nedeniyle YARIM kalan yanit: JSON'u ayristirmaya calismak
    // yaniltici "Gecersiz JSON" hatasi verir. Nedeni acikca bildir ve toparla.
    if (response.status === "incomplete") {
      const incompleteReason: string = response.incomplete_details?.reason ?? "bilinmiyor";
      lastError = `yanit tamamlanmadi (${incompleteReason})`;
      logger.warn({ schema: options.schemaName, attempt, incompleteReason, budget, effort }, "OpenAI yaniti yarim kaldi");
      if (incompleteReason === "max_output_tokens") {
        budget = Math.min(budget * 2, 64_000);
        if (useReasoning && effort === "high") effort = "medium";
        else if (useReasoning && effort === "medium") effort = "low";
        else if (useReasoning && effort === "low") effort = "minimal";
      }
      continue;
    }

    const raw = response.output_text ?? "";
    if (!raw.trim()) {
      lastError = "model bos yanit dondurdu";
      logger.warn({ schema: options.schemaName, attempt, status: response.status }, "OpenAI bos yanit dondurdu");
      continue;
    }
    try {
      const parsed = JSON.parse(raw) as unknown;
      const validated = options.zodSchema.safeParse(parsed);
      if (validated.success) return validated.data;
      lastError = validated.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
      logger.warn({ schema: options.schemaName, attempt, lastError }, "OpenAI ciktisi Zod dogrulamasindan gecemedi");
    } catch {
      lastError = `gecersiz JSON (${raw.length} karakter alindi)`;
      logger.warn({ schema: options.schemaName, attempt, rawLength: raw.length }, "OpenAI ciktisi JSON olarak ayristirilamadi");
      // Yarim kesilmis olabilir: butceyi buyut, akil yurutmeyi dusur
      budget = Math.min(budget * 2, 64_000);
      if (useReasoning && effort === "high") effort = "medium";
      else if (useReasoning && effort === "medium") effort = "low";
      else if (useReasoning && effort === "low") effort = "minimal";
    }
  }
  throw new Error(
    `OpenAI yapilandirilmis cikti uretemedi (${options.schemaName}): ${lastError}. Ayarlar'dan jeton butcesini artirabilir veya daha kisa bir hedef sure secebilirsiniz.`
  );
}

/** Serbest metin cagrisi (kisa yardimci uretimler icin). */
export async function textCall(system: string, user: string, maxOutputTokens = 8_000): Promise<string> {
  const settings = await getSettings();
  const client = await getClient();
  try {
    const response = await client.responses.create(
      {
        model: settings.openaiModel,
        instructions: system,
        input: user,
        max_output_tokens: maxOutputTokens,
        ...(REASONING_MODELS.test(settings.openaiModel) ? { reasoning: { effort: "low" as const } } : {}),
      },
      { timeout: DEFAULT_CALL_TIMEOUT_MS }
    );
    return (response.output_text ?? "").trim();
  } catch (err) {
    throw friendlyOpenAiError(err, "text_call");
  }
}

export type ImageAspect = "16:9" | "9:16";

/** gpt-image-1 ile gorsel uretir, PNG buffer dondurur. */
export async function generateImage(
  prompt: string,
  aspect: ImageAspect,
  quality: "low" | "medium" | "high" = "high"
): Promise<Buffer> {
  const client = await getClient();
  const size = aspect === "16:9" ? "1536x1024" : "1024x1536";
  try {
    const result = await client.images.generate(
      {
        model: "gpt-image-1",
        prompt,
        size: size as "1536x1024" | "1024x1536",
        quality,
      },
      { timeout: DEFAULT_CALL_TIMEOUT_MS }
    );
    const b64 = result.data?.[0]?.b64_json;
    if (!b64) throw new Error("Gorsel uretimi bos sonuc dondurdu");
    return Buffer.from(b64, "base64");
  } catch (err: unknown) {
    throw friendlyOpenAiError(err, "image_generation");
  }
}

/**
 * OpenAI TTS ile metinden ses uretir (mp3 buffer). Suno API anahtari yoksa
 * veya kullanici manuel ses yuklemediyse, "sarki sesi" icin tek alternatif
 * budur — melodi yerine ritmik/okunan bir seslendirme uretir (tekerleme /
 * saymaca gibi konusma-agirlikli icerikte dogal durur).
 * Tek cagrida 4096 karakter siniri var; uzun metin parcalara bolunup
 * sesler ffmpeg ile birlestirilir (bkz. concatAudioFiles).
 */
export async function synthesizeSpeech(
  text: string,
  opts?: { voice?: string; speed?: number; model?: string }
): Promise<Buffer> {
  const client = await getClient();
  try {
    const response = await client.audio.speech.create(
      {
        model: opts?.model ?? "gpt-4o-mini-tts",
        voice: opts?.voice ?? "shimmer",
        input: text,
        response_format: "mp3",
        speed: opts?.speed ?? 0.92,
      },
      { timeout: DEFAULT_CALL_TIMEOUT_MS }
    );
    const arrayBuffer = await response.arrayBuffer();
    return Buffer.from(arrayBuffer);
  } catch (err) {
    throw friendlyOpenAiError(err, "tts");
  }
}

/**
 * gpt-image-1 GORSEL DUZENLEME: mevcut bir referans gorseli KIMLIK KAYNAGI
 * olarak verir; model yuz/govde/oranlari o gorselden korur, sadece prompt'ta
 * istenen degisikligi (or. kiyafet) uygular. Metinden-uretime gore kimlik
 * sadakati kat kat daha yuksektir — tarz dolabi / kiyafet varyantlari icin
 * budur, sifirdan generateImage degil.
 */
export async function editImage(imagePath: string | string[], prompt: string, aspect: ImageAspect): Promise<Buffer> {
  const client = await getClient();
  const size = aspect === "16:9" ? "1536x1024" : "1024x1536";
  const paths = Array.isArray(imagePath) ? imagePath : [imagePath];
  try {
    const result = await client.images.edit(
      {
        model: "gpt-image-1",
        image: paths.length === 1 ? fs.createReadStream(paths[0]) : paths.map((p) => fs.createReadStream(p)),
        prompt,
        size: size as "1536x1024" | "1024x1536",
        quality: "high",
      },
      { timeout: DEFAULT_CALL_TIMEOUT_MS }
    );
    const b64 = result.data?.[0]?.b64_json;
    if (!b64) throw new Error("Gorsel duzenleme bos sonuc dondurdu");
    return Buffer.from(b64, "base64");
  } catch (err: unknown) {
    throw friendlyOpenAiError(err, "image_generation");
  }
}
