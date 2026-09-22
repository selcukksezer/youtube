import { z } from "zod";
import { prisma } from "@/server/db";
import { structuredCall } from "@/server/services/openai";
import { recordEvent } from "@/server/lib/logger";

const safetyResultSchema = z.object({
  safe: z.boolean(),
  flags: z.array(
    z.object({
      sceneIndex: z.number().int(),
      severity: z.enum(["low", "medium", "high"]),
      issue: z.string(),
      suggestion: z.string(),
    })
  ),
});

export type SafetyResult = z.infer<typeof safetyResultSchema>;

/** Cocuk sarki klip icerigi guvenlik taramasi. */
export async function runSafetyCheck(projectId: string): Promise<SafetyResult> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const clips = await prisma.clip.findMany({
    where: { projectId, languageVariant: "primary" },
    orderBy: { index: "asc" },
  });
  if (clips.length === 0) throw new Error("Taranacak klip yok");

  const content = clips
    .map(
      (c) =>
        `Klip ${c.index}:\nAciklama: ${c.sceneDescription}\nSozler: ${c.dialogue}\nGorsel prompt: ${c.imagePrompt}`
    )
    .join("\n\n");

  const result = await structuredCall<SafetyResult>({
    system: `Sen cocuk sarki videosu guvenlik denetcisisin. ${project.ageBand || "3-5"} yas bandi icin klip ve sozleri denetle.
Isaretlenecekler: dehset/korku ogeleri, siddet, kan, olum, tehlikeli davranis ozendirmesi, yasa uygun olmayan dil, reklam/marka.
safe=true yalnizca orta/yuksek onemli bulgu yoksa.`,
    user: content.slice(0, 60_000),
    schemaName: "safety_check",
    jsonSchema: {
      type: "object",
      additionalProperties: false,
      properties: {
        safe: { type: "boolean" },
        flags: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            properties: {
              sceneIndex: { type: "integer" },
              severity: { type: "string", enum: ["low", "medium", "high"] },
              issue: { type: "string" },
              suggestion: { type: "string" },
            },
            required: ["sceneIndex", "severity", "issue", "suggestion"],
          },
        },
      },
      required: ["safe", "flags"],
    },
    zodSchema: safetyResultSchema,
  });

  await recordEvent({
    projectId,
    step: "song",
    level: result.safe ? "info" : "warning",
    message: result.safe ? "Guvenlik taramasi temiz" : `Guvenlik taramasi ${result.flags.length} bulgu isaretledi`,
    detail: result.flags,
  });
  return result;
}
