import fs from "node:fs";

export interface SongRefCharacter {
  id: string;
  name: string;
  referenceImagePath: string | null;
}

/** "Hep birlikte" turu sahne sinyalleri: kimin adi gecmese de kadro muhtemelen ekrandadir. */
const GROUP_SCENE_SIGNAL = /\b(arkada[sş](lar[ıi]?[mn]?[ıi]?z?)?|dostlar[ıi]?[mn]?[ıi]?z?|hepimiz|hepiniz|hepsi|beraber|birlikte|el\s*ele|hep\s*bir|ekip|tak[ıi]m)\b/iu;

/**
 * Bir klipte/sahnede GERCEKTEN yer almasi muhtemel destek kadrosunu belirler.
 *
 * Oncelik sirasi:
 * 1) Klibin metninde (soz + sahne aciklamasi) ADI GECEN karakterler — en
 *    guvenilir sinyal, SADECE bunlar donulur.
 * 2) Ad gecmiyorsa ama kadro kucukse (<=2 destek karakteri) veya metinde
 *    "arkadaşlar/beraber/birlikte" gibi bir grup sinyali varsa: tum destek
 *    kadrosu (guvenli varsayilan — kucuk kadrolarda genelde hep birlikte
 *    gorunurler; grup sinyali de aciyi ayni sekilde isaret eder).
 * 3) Hicbiri yoksa (tipik solo dize + buyuk kadro): BOS — yalniz sahne
 *    gereksiz sekilde tum kadronun tarifi/@etiketiyle kalabalik edilmez.
 */
export function resolveClipCastMembers<T extends { id: string; name: string }>(sceneText: string, others: T[]): T[] {
  const named = others.filter((m) => m.name.trim().length > 0);
  if (named.length === 0) return [];
  const haystack = sceneText.toLowerCase();
  const mentioned = named.filter((m) => {
    const n = m.name.trim().toLowerCase();
    return n.length >= 2 && haystack.includes(n);
  });
  if (mentioned.length > 0) return mentioned;
  if (named.length <= 2) return named;
  if (GROUP_SCENE_SIGNAL.test(sceneText)) return named;
  return [];
}

/**
 * Sarki klibi: once bu klibin soyleyeni, sonra sarkida gecen diger kadro.
 *
 * Flow karakteri (@ad) aciksa PNG YUKLENMEZ: gorseli isteme eklemek Flow'u
 * Karakterler / goruntu moduna kaydirir ve video yerine karakter karesi uretir.
 * Kadro o zaman prompttaki @ad ile baglanir.
 */
export function pickSongCastReferencePaths(
  cast: SongRefCharacter[],
  clipSinger: SongRefCharacter | null,
  useReference: boolean,
  useFlowCharacter = false
): string[] {
  if (useFlowCharacter) return [];
  if (!useReference) return [];
  const named = cast.filter((c) => c.name.trim());
  const ordered: SongRefCharacter[] = [];
  if (clipSinger?.name.trim()) ordered.push(clipSinger);
  for (const member of named) {
    if (ordered.some((c) => c.id === member.id)) continue;
    ordered.push(member);
  }
  const paths: string[] = [];
  for (const member of ordered) {
    const imagePath = member.referenceImagePath?.trim();
    if (!imagePath || !fs.existsSync(imagePath)) continue;
    if (paths.includes(imagePath)) continue;
    paths.push(imagePath);
  }
  return paths;
}

/** @deprecated tek gorsel — pickSongCastReferencePaths kullanin */
export function pickSongReferencePaths(
  characterImage: string | null,
  useReference: boolean,
  useFlowCharacter = false
): string[] {
  return pickSongCastReferencePaths(
    characterImage ? [{ id: "one", name: "lead", referenceImagePath: characterImage }] : [],
    characterImage ? { id: "one", name: "lead", referenceImagePath: characterImage } : null,
    useReference,
    useFlowCharacter
  );
}
