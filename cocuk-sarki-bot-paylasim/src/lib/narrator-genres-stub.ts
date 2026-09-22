/** Legacy anlatici tur kontrolu — sarki-only uygulamada kullanilmaz. */
export function isNarratorHardConflictGenre(_genre: string | null | undefined): boolean {
  return false;
}

export type NarratorGenreId = "ozel";
export const NARRATOR_GENRES: Array<{ id: NarratorGenreId; label: string; tagline?: string }> = [];

export function resolveNarratorGenre(_genre?: string | null) {
  return { id: "ozel" as const, label: "" };
}

export function narratorGenreLabel(_id: NarratorGenreId, custom?: string): string {
  return custom?.trim() || "";
}

export function isNarratorDramaGenre(_genre?: string | null): boolean {
  return false;
}
