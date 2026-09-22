import type { CharacterProfile, Project } from "@prisma/client";
import { prisma } from "@/server/db";
import {
  buildSongDnaCardFromProfile,
  characterReadyForSong,
  dnaCardSchema,
  isEmptyDnaCard,
  type DnaCard,
} from "@/lib/song-character";

export async function persistSongDnaCard(characterId: string, dna: DnaCard): Promise<CharacterProfile> {
  const validated = dnaCardSchema.parse(dna);
  return prisma.characterProfile.update({
    where: { id: characterId },
    data: { dnaCard: JSON.stringify(validated) },
  });
}

/** kids_song karakter profilinden DNA kartini olusturur veya mevcut olani dondurur. */
export async function ensureSongDnaCard(
  projectId: string
): Promise<{ project: Project; character: CharacterProfile; dna: DnaCard }> {
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType !== "kids_song") {
    throw new Error("Bu islem yalnizca cocuk sarki klibi sablonunda calisir");
  }

  const character = await prisma.characterProfile.findFirst({ where: { projectId, role: "main" } });
  if (!character) throw new Error("Ana karakter bulunamadi — once klipleri eslestirin (AI kadro olusturur)");

  if (!characterReadyForSong(character)) {
    throw new Error("Karakter profili yetersiz — once klipleri eslestirin");
  }

  if (!isEmptyDnaCard(character.dnaCard)) {
    try {
      const dna = dnaCardSchema.parse(JSON.parse(character.dnaCard));
      return { project, character, dna };
    } catch {
      /* yeniden uret */
    }
  }

  const dna = buildSongDnaCardFromProfile(character, {
    visualStyle: project.visualStyle,
    topic: project.topic,
    channelName: project.channelName,
  });
  const updated = await persistSongDnaCard(character.id, dna);
  return { project, character: updated, dna };
}

/** Karakter guncellendiginde kids_song DNA kartini profille senkronlar. */
export async function syncSongDnaCardForCharacter(characterId: string): Promise<void> {
  const character = await prisma.characterProfile.findUnique({ where: { id: characterId } });
  if (!character || character.role !== "main") return;

  const project = await prisma.project.findUnique({ where: { id: character.projectId } });
  if (!project || project.templateType !== "kids_song") return;
  if (!characterReadyForSong(character)) return;

  const dna = buildSongDnaCardFromProfile(character, {
    visualStyle: project.visualStyle,
    topic: project.topic,
    channelName: project.channelName,
  });
  await persistSongDnaCard(character.id, dna);
}
