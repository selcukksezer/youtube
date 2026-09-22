import { z } from "zod";
import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { generateOpenAiSongAudio } from "@/server/services/song-tts";

export const runtime = "nodejs";
export const maxDuration = 300;

type Params = { params: Promise<{ id: string }> };

const bodySchema = z.object({
  lyrics: z.string().min(1),
  voice: z.string().optional(),
  speed: z.number().min(0.5).max(1.5).optional(),
});

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const project = await prisma.project.findUniqueOrThrow({ where: { id } });
    if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");

    const json = await request.json().catch(() => ({}));
    const body = bodySchema.parse(json);

    return generateOpenAiSongAudio(project, body.lyrics, { voice: body.voice, speed: body.speed });
  });
}
