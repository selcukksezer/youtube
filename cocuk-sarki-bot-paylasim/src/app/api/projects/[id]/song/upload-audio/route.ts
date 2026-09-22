import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { saveSongMasterAudio } from "@/server/services/song-audio";

export const runtime = "nodejs";
export const maxDuration = 120;

type Params = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const project = await prisma.project.findUniqueOrThrow({ where: { id } });
    if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");

    const formData = await request.formData();
    const file = formData.get("file");
    if (!(file instanceof File)) throw new Error("Dosya bulunamadi (form alani: file)");
    const lyrics = String(formData.get("lyrics") || "").trim();
    const buffer = Buffer.from(await file.arrayBuffer());

    const settings = await saveSongMasterAudio(project, buffer, file.name, {
      musicSource: "manual_upload",
      sunoStatus: "ready",
      formattedLyrics: lyrics || undefined,
      lyricsSource: lyrics ? "manual" : undefined,
    });

    return settings;
  });
}
