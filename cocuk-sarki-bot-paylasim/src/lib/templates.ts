export const TEMPLATE_TYPES = ["kids_song"] as const;
export type TemplateType = (typeof TEMPLATE_TYPES)[number];

export function isKidsSong(_templateType?: string): boolean {
  return true;
}

export function isKidsContent(templateType?: string): boolean {
  return !templateType || templateType === "kids_song" || templateType === "kids_animation";
}

export function isLongform(_templateType?: string): boolean {
  return false;
}

/** Ayarlar / yayin — eski calisma alani. */
export function projectWorkspaceHref(project: { id: string; templateType?: string }): string {
  return `/cocuk-sarki/${project.id}`;
}

/** Ana is: MP3 + soz → klipler → Flow → render. */
export function projectProductionHref(project: { id: string; templateType?: string }): string {
  return `/cocuk-sarki/${project.id}/render`;
}

export function isKidsSongSectionPath(pathname: string): boolean {
  return pathname === "/" || pathname.startsWith("/cocuk-sarki") || pathname.startsWith("/setup") || pathname.startsWith("/settings");
}

export function usesStudioWizard(_templateType?: string): boolean {
  return false;
}

export function templateLabel(_templateType?: string): string {
  return "Sarki Klibi";
}

export function templateLabelShort(_templateType?: string): string {
  return "Sarki";
}

export function emptyDialogueHint(_templateType?: string): string {
  return 'Ustteki parca panelinden MP3 ve sozleri kaydedip "Sozleri kliplere bol" calistirin. Promptlar sozlerden otomatik yazilir.';
}

export function emptyClipsHint(_templateType?: string): string {
  return "Yuklediginiz MP3 ve sozleri ustteki parca panelinden kliplere bolun. Suno API gerekmez — elinizdeki parca ses omurgasidir.";
}
