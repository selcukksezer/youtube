import { z } from "zod";
import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { SONG_STYLES } from "@/lib/song-catalog";
import { generateMusic } from "@/server/services/suno";
import { loadSongSettings, updateSongSettings } from "@/server/services/song-settings-store";
import { recordEvent } from "@/server/lib/logger";

export const runtime = "nodejs";
export const maxDuration = 120;

type Params = { params: Promise<{ id: string }> };

const schema = z.object({
  lyrics: z.string().optional(),
  title: z.string().optional(),
  styleId: z.string().optional(),
});

function stylePrompt(styleId: string | undefined, narrationStyle: string): string {
  const style = SONG_STYLES.find((s) => s.id === (styleId || narrationStyle));
  return style?.prompt || "bright cheerful kids pop, major key, catchy groove, warm vocal";
}

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const project = await prisma.project.findUniqueOrThrow({ where: { id } });
    if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");
    const body = schema.parse(await request.json().catch(() => ({})));
    const title = (body.title || project.title || project.name).slice(0, 80);
    const style = stylePrompt(body.styleId, project.narrationStyle);
    const existing = await loadSongSettings(id);
    const lyrics =
      body.lyrics?.trim() ||
      existing.formattedLyrics?.trim() ||
      project.openingHook?.trim() ||
      `${title} — cheerful kids song in ${project.speechLanguage}, age ${project.ageBand || "3-5"}`;

    const { taskId } = await generateMusic({
      title,
      style,
      lyrics,
      instrumental: false,
    });

    const settings = await updateSongSettings(id, {
      musicSource: "suno_api",
      sunoTaskId: taskId,
      sunoStatus: "generating",
      sunoError: undefined,
      sunoTracks: [],
      formattedLyrics: lyrics,
      lyricsSource: body.lyrics?.trim() || existing.formattedLyrics?.trim() ? "manual" : "suno_prompt",
    });

    await recordEvent({ projectId: id, step: "song", message: `Suno uretimi baslatildi (#${taskId.slice(0, 8)})` });
    return { taskId, settings };
  });
}
