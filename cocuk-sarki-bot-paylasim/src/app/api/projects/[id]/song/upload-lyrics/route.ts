import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { updateSongSettings } from "@/server/services/song-settings-store";
import { recordEvent } from "@/server/lib/logger";

export const runtime = "nodejs";

type Params = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const project = await prisma.project.findUniqueOrThrow({ where: { id } });
    if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");

    const formData = await request.formData();
    const textField = String(formData.get("lyrics") || "").trim();
    const file = formData.get("file");
    let lyrics = textField;

    if (file instanceof File && file.size > 0) {
      lyrics = (await file.text()).trim();
    }

    if (!lyrics) throw new Error("Soz metni bos — yapistirin veya .txt dosyasi yukleyin");

    const settings = await updateSongSettings(id, {
      formattedLyrics: lyrics,
      lyricsSource: "manual",
    });

    await recordEvent({ projectId: id, step: "song", message: `Sozler yuklendi (${lyrics.length} karakter)` });
    return settings;
  });
}
