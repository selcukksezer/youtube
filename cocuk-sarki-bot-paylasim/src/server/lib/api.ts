import { NextResponse } from "next/server";
import { ZodError } from "zod";
import { logger } from "@/server/lib/logger";
import { maskSecrets } from "@/server/lib/mask";

/**
 * API yardimcilari: tutarli hata bicimi + gizli bilgi maskeleme.
 * Ham stack trace kullaniciya donmez; loglara yazilir.
 */

export function ok<T>(data: T, init?: ResponseInit): NextResponse {
  return NextResponse.json({ ok: true, data }, init);
}

export function fail(message: string, status = 400): NextResponse {
  return NextResponse.json({ ok: false, error: maskSecrets(message) }, { status });
}

/**
 * Kayit bulunamadi hatasi mi?
 * Prisma `findUniqueOrThrow` / `update` cagrilari silinmis kayitta P2025 firlatir.
 * Bu bir sunucu hatasi DEGIL — 404 olarak donmeli (or. silinmis bir projenin linki).
 */
function isRecordNotFound(err: unknown): boolean {
  return typeof err === "object" && err !== null && (err as { code?: string }).code === "P2025";
}

/** Route handler sarmalayici: hatalari yakalar, loglar, guvenli mesaj doner. */
export async function handle<T>(fn: () => Promise<T>): Promise<NextResponse> {
  try {
    const data = await fn();
    return ok(data);
  } catch (err) {
    if (err instanceof ZodError) {
      const message = err.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
      return fail(`Gecersiz istek: ${message}`, 422);
    }
    if (isRecordNotFound(err)) {
      return fail("Kayit bulunamadi (silinmis veya adres gecersiz)", 404);
    }
    const message = err instanceof Error ? err.message : String(err);
    logger.error({ err }, `API hatasi: ${message}`);
    return fail(message, 500);
  }
}
