import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { loadSongSettings } from "@/server/services/song-settings-store";

export const runtime = "nodejs";

type Params = { params: Promise<{ id: string }> };

export async function GET(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const project = await prisma.project.findUniqueOrThrow({ where: { id } });
    if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");
    return loadSongSettings(id);
  });
}
