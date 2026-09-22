import { z } from "zod";
import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { pollMusicTask } from "@/server/services/suno";
import { loadSongSettings, updateSongSettings } from "@/server/services/song-settings-store";
import { importSongFromUrl } from "@/server/services/song-audio";

export const runtime = "nodejs";
export const maxDuration = 120;

type Params = { params: Promise<{ id: string }> };

const schema = z.object({
  taskId: z.string().optional(),
  selectedTrackIndex: z.number().int().min(0).optional(),
  download: z.boolean().optional(),
});

async function handleStatus(id: string, body: z.infer<typeof schema>) {
  const project = await prisma.project.findUniqueOrThrow({ where: { id } });
  if (project.templateType !== "kids_song") throw new Error("Yalnizca cocuk sarki projeleri");

  let settings = await loadSongSettings(id);
  const taskId = body.taskId || settings.sunoTaskId;
  if (!taskId) throw new Error("Suno taskId yok — once uretim baslatin");

  const poll = await pollMusicTask(taskId);
  const selectedTrackIndex = body.selectedTrackIndex ?? settings.selectedTrackIndex ?? 0;

  settings = await updateSongSettings(id, {
    sunoTaskId: taskId,
    sunoStatus: poll.status,
    sunoError: poll.error,
    sunoTracks: poll.tracks.map((t) => ({
      id: t.id,
      title: t.title,
      audioUrl: t.audioUrl,
      imageUrl: t.imageUrl,
      duration: t.duration,
      prompt: t.prompt,
      tags: t.tags,
    })),
    selectedTrackIndex,
    formattedLyrics: poll.tracks[selectedTrackIndex]?.prompt || settings.formattedLyrics,
    lyricsSource: poll.tracks[selectedTrackIndex]?.prompt ? "suno_prompt" : settings.lyricsSource,
  });

  if (body.download && poll.status === "ready") {
    const track = poll.tracks[selectedTrackIndex];
    if (!track?.audioUrl) throw new Error("Secilen parcanin audio URL'i yok");
    settings = await importSongFromUrl(project, track.audioUrl, {
      musicSource: "suno_api",
      sunoClipId: track.id,
      sunoStatus: "ready",
      formattedLyrics: track.prompt || settings.formattedLyrics,
      lyricsSource: "suno_prompt",
      selectedTrackIndex,
    });
  }

  return { settings, poll };
}

export async function GET(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const url = new URL(request.url);
    const body = schema.parse({
      taskId: url.searchParams.get("taskId") || undefined,
      selectedTrackIndex: url.searchParams.get("track") ? Number(url.searchParams.get("track")) : undefined,
      download: url.searchParams.get("download") === "1",
    });
    return handleStatus(id, body);
  });
}

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const body = schema.parse(await request.json().catch(() => ({})));
    return handleStatus(id, body);
  });
}
