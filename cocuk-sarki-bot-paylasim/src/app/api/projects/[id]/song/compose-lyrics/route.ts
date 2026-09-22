import { z } from "zod";
import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { composeLyricsForSuno } from "@/server/services/song";

export const runtime = "nodejs";
export const maxDuration = 600;

type Params = { params: Promise<{ id: string }> };

const schema = z.object({
  ageBand: z.string().optional(),
  targetDurationSeconds: z.number().int().min(30).max(1200).optional(),
  topic: z.string().max(2000).optional(),
  title: z.string().max(120).optional(),
  styleId: z.string().optional(),
});

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const project = await prisma.project.findUniqueOrThrow({ where: { id } });
    if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");
    const body = schema.parse(await request.json());
    const lyrics = await composeLyricsForSuno(id, body);
    return lyrics;
  });
}
