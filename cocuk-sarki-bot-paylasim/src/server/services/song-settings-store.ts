import type { Project } from "@prisma/client";
import { prisma } from "@/server/db";
import {
  mergeSongSettings,
  parseSongSettings,
  serializeSongSettings,
  type SongSettings,
} from "@/lib/song-settings";

export function getSongSettings(project: Pick<Project, "songSettings">): SongSettings {
  return parseSongSettings(project.songSettings);
}

export async function updateSongSettings(projectId: string, patch: Partial<SongSettings>): Promise<SongSettings> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  const next = mergeSongSettings(getSongSettings(project), patch);
  await prisma.project.update({
    where: { id: projectId },
    data: { songSettings: serializeSongSettings(next) },
  });
  return next;
}

export async function loadSongSettings(projectId: string): Promise<SongSettings> {
  const project = await prisma.project.findUniqueOrThrow({
    where: { id: projectId },
    select: { songSettings: true },
  });
  return getSongSettings(project);
}
