/** Cocuk sarki studyosu — Adim 3 baslik kartlari. */

export function isTurkishSpeech(lang: string | undefined) {
  return /turk/i.test(lang || "Turkish");
}

export function pickSongPosterTitle(
  title: { english: string; turkish: string },
  speechLanguage?: string
) {
  if (isTurkishSpeech(speechLanguage)) return title.turkish?.trim() || title.english;
  return title.english?.trim() || title.turkish;
}

export function songTitleIsSelected(
  title: { english: string; turkish: string },
  current: string | undefined
) {
  const active = (current || "").trim();
  if (!active) return false;
  return active === title.turkish.trim() || active === title.english.trim();
}
