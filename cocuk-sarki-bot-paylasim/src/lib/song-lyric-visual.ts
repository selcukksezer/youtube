/**
 * Şarkı klibi: duyulan her içerik kelimesi (söz + konuşma) ekranda ZORUNLU.
 * Sadece bilinen imge listesi değil — klibin sözündeki her içerik kelimesi
 * "SHOW: …" satırı alır (kelebek uçar = kelebek + uçuş).
 */

export type SongPictureBeat = {
  key: string;
  visible: string;
  kind: "noun" | "action" | "spoken" | "word";
  surface?: string;
};

const STOPWORDS = new Set(
  [
    "ve", "veya", "ile", "bir", "bu", "şu", "su", "o", "da", "de", "ta", "te",
    "mi", "mı", "mu", "mü", "en", "çok", "cok", "daha", "gibi", "için", "icin",
    "ama", "fakat", "ya", "ki", "ne", "ni", "hem", "her", "hiç", "hic", "az",
    "ben", "sen", "biz", "siz", "onlar", "benim", "senin", "onun",
    "olan", "olarak", "sonra", "önce", "once", "şimdi", "simdi", "gene", "yine",
    "la", "na", "oh", "ah", "ey", "yaa", "hmm",
    "minik", "küçük", "kucuk", "ufak", "iri", "büyük", "buyuk",
    "sevimli", "tatlı", "tatli", "sarı", "sari", "kırmızı", "kirmizi",
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "is", "it", "we", "you",
    "my", "our", "your", "for", "with", "at", "from",
  ].map((w) => w.toLocaleLowerCase("tr-TR"))
);

/** Bilinen imgeler — eşleşince İngilizce sahne cümlesi. */
const BEAT_RULES: Array<{ re: RegExp; key: string; visible: string; kind: Exclude<SongPictureBeat["kind"], "word"> }> = [
  { re: /\bkelebek(ler|i|lerim|leri)?\b/i, key: "butterfly", visible: "a colorful butterfly with beating wings, airborne and clearly flying through THIS frame (not a sticker, not off-screen)", kind: "noun" },
  { re: /\bbutterfl(y|ies)\b/i, key: "butterfly", visible: "a colorful butterfly with beating wings, airborne in THIS frame", kind: "noun" },
  { re: /\bku[sş](lar|u|um|lar[iı])?\b/i, key: "bird", visible: "a friendly cartoon bird clearly visible and moving in frame", kind: "noun" },
  { re: /\btav[sş]an(lar|i|ım)?\b/i, key: "rabbit", visible: "the rabbit character/prop fully visible as named", kind: "noun" },
  { re: /\btilki(ler|si)?\b/i, key: "fox", visible: "the fox character/prop fully visible as named", kind: "noun" },
  { re: /\bkirpi(ler|si)?\b/i, key: "hedgehog", visible: "the hedgehog character/prop fully visible as named", kind: "noun" },
  { re: /\bsincap(lar|i|ın|in)?\b/i, key: "squirrel", visible: "a cartoon squirrel fully visible, handling real hazelnuts if named — not empty paws", kind: "noun" },
  { re: /\bgeyik(ler|i)?\b/i, key: "deer", visible: "a friendly cartoon deer fully visible in this frame, running if the lyric says so", kind: "noun" },
  { re: /\bceylan(lar|i)?\b/i, key: "gazelle", visible: "a slim cartoon gazelle/antelope running visibly in this frame", kind: "noun" },
  { re: /\bkurba[gğ]a(lar|s[iı])?\b/i, key: "frog", visible: "a cartoon frog jumping into or beside visible water, splash readable", kind: "noun" },
  { re: /\bf[iı]nd[iı]k(lar|i)?\b/i, key: "hazelnut", visible: "visible hazelnuts being hidden or held — real nuts in frame, correct count", kind: "noun" },
  { re: /\b[cç]am\b/i, key: "pine", visible: "pine trees staged with needles, cones and bark — pine scent shown as those props", kind: "noun" },
  { re: /\bdal(lar|i|lardan)?\b/i, key: "branch", visible: "tree branches filling the frame as named, leaves attached", kind: "noun" },
  { re: /\b[cç]al[iı](n[iı]n|lar|n[iı]n)?\b/i, key: "bush", visible: "a visible bush/thicket a character can peek from behind", kind: "noun" },
  { re: /\bg[oö]lc[uü]k\b/i, key: "puddle", visible: "a readable puddle or tiny pool on the ground", kind: "noun" },
  { re: /\bg[oö]lge\b/i, key: "shade", visible: "visible cool blue shade under trees matching the lyric", kind: "noun" },
  { re: /\bay[iı](lar|s[iı])?\b/i, key: "bear", visible: "the bear character/prop visible as named", kind: "noun" },
  { re: /\bkedi(ler|si)?\b|\bpisi(?:k)?\b/i, key: "cat", visible: "the cat character/prop visible as named", kind: "noun" },
  { re: /\bk[oö]pek(ler|i)?\b/i, key: "dog", visible: "the dog character/prop visible as named", kind: "noun" },
  { re: /\bbal[iı][kğ]\w*/i, key: "fish", visible: "a clear LITTLE FISH in frame with the lead — swimming beside them, held gently, or pointed at; big enough to read scales and eyes, never a tiny speck in the background", kind: "noun" },
  { re: /\bfish(es)?\b/i, key: "fish", visible: "a clear little fish sharing the frame with the lead singer — swimming, held, or played with", kind: "noun" },
  { re: /\bardan?\b|\barbe(ler)?\b/i, key: "bee", visible: "a bee buzzing on screen as named", kind: "noun" },
  { re: /\borman(da|i|lar|ında|inda)?\b/i, key: "forest", visible: "a real forest set: trees, leaves, ground, sky between trunks", kind: "noun" },
  { re: /\ba[gğ]a[cç](lar|i|ın|in)?\b/i, key: "tree", visible: "trees with trunks, branches and leaves in frame", kind: "noun" },
  { re: /\byaprak(lar|i)?\b/i, key: "leaf", visible: "visible leaves moving on the beat", kind: "noun" },
  { re: /\b[cç]i[cç]ek(ler|i|lerim)?\b/i, key: "flower", visible: "visible flowers with petals (correct count if numbered)", kind: "noun" },
  { re: /\b[cç]imen(ler|lik)?\b/i, key: "grass", visible: "grass underfoot, not a void floor", kind: "noun" },
  { re: /\bg[oö]l(de|ü|u)?\b|\bnehir\b|\bdere\b/i, key: "water", visible: "visible water (lake/river/stream) matching the lyric", kind: "noun" },
  { re: /\bg[uü]ne[sş]\b/i, key: "sun", visible: "a readable sun or strong sunlight in the sky", kind: "noun" },
  { re: /\baydede\b|\b(the )?moon\b/i, key: "moon", visible: "a readable moon in the sky as named", kind: "noun" },
  { re: /\bya[gğ]mur\b/i, key: "rain", visible: "visible rain drops / wet surfaces matching the lyric", kind: "noun" },
  { re: /(?:^|[^\p{L}])kar(?:lar|[ıi])?(?=[^\p{L}]|$)/iu, key: "snow", visible: "visible snow matching the lyric", kind: "noun" },
  { re: /\br[uü]zgar\b|\besinti\b/i, key: "wind", visible: "visible wind: hair/fur/leaves/fabric blowing", kind: "noun" },
  { re: /\bg[oö]kku[sş]a[gğ][iı]\b/i, key: "rainbow", visible: "a rainbow arc clearly in the sky", kind: "noun" },
  { re: /\by[iı]ld[iı]z(lar|i)?\b/i, key: "star", visible: "visible stars matching the lyric", kind: "noun" },
  { re: /\bg[oö]ky[uü]z[uü]\b|\bg[oö]k(te)?\b/i, key: "sky", visible: "a readable sky (not a blank void)", kind: "noun" },
  { re: /\btren(ler|i)?\b|\bvagon(lar|u|u)?\b/i, key: "train", visible: "toy train / wagons with correct count, wheels visible", kind: "noun" },
  { re: /\baraba(lar|s[iı])?\b/i, key: "car", visible: "a car matching the lyric, wheels on the ground", kind: "noun" },
  { re: /\bbisiklet\b/i, key: "bike", visible: "a bicycle the singer can touch or ride as named", kind: "noun" },
  { re: /\bu[cç]ak\b|\buçak\b/i, key: "plane", visible: "a plane in the sky as named", kind: "noun" },
  { re: /\bgemi(ler|si)?\b|\btekne\b/i, key: "boat", visible: "a boat/ship on water as named", kind: "noun" },
  { re: /\bbalon(lar|u)?\b/i, key: "balloon", visible: "balloons with string and volume, correct count", kind: "noun" },
  { re: /\btop(lar|u)?\b/i, key: "ball", visible: "a ball the singer can touch or kick, on-screen", kind: "noun" },
  { re: /\bk[oö]p[uü]k\b|\bfoam\b/i, key: "foam", visible: "thick visible soap foam / bubbles on paws or props", kind: "noun" },
  { re: /\bel(ler|im|in)?\b/i, key: "hands", visible: "hands clearly acting the lyric (clap, hold, show)", kind: "noun" },
  { re: /\bayak(lar|i)?\b/i, key: "feet", visible: "feet planted and moving the named step (tap/stomp)", kind: "noun" },
  { re: /\bburun\b|\bnose\b/i, key: "nose", visible: "a readable nose-point or sniff beat matching the lyric", kind: "noun" },
  { re: /\bdost(lar|um|lar[iı]m)?\b|\barkada[sş](lar|im|ım)?\b/i, key: "friends", visible: "the named friends/cast actually sharing the frame", kind: "noun" },
  { re: /\bkafe\b|\bcafe\b|\bcaf[eé]\b/i, key: "cafe", visible: "a cafe interior: tables, window, counter — not a void", kind: "noun" },
  { re: /\bev(de|i)?\b|\boda(da)?\b/i, key: "home", visible: "a real interior with walls, floor, window — not a void", kind: "noun" },
  { re: /\bbah[cç]e\b|\bpark(ta)?\b/i, key: "garden", visible: "an outdoor garden/park with ground, plants, sky", kind: "noun" },
  { re: /\bk[iı]rm[iı]z[iı]\b|\bk[iı]rmizi\b/i, key: "red", visible: "the named object is clearly RED", kind: "noun" },
  { re: /\bmavi\b/i, key: "blue", visible: "the named object is clearly BLUE", kind: "noun" },
  { re: /\bye[sş]il\b/i, key: "green", visible: "the named object is clearly GREEN", kind: "noun" },
  { re: /\bsar[iı]\b/i, key: "yellow", visible: "the named object is clearly YELLOW", kind: "noun" },
  { re: /\bbeyaz\b|\bsiyah\b|\bpembe\b|\bturuncu\b/i, key: "color", visible: "the named color is visible on the named prop/costume", kind: "noun" },

  { re: /\bu[cç](ar|uyor|makta|sun|tu|mak|u[sş]|arak)\b|\bfly(ing|s)?\b/i, key: "flying", visible: "real flight in air: wings beating, body off the ground, path through THIS frame", kind: "action" },
  { re: /\bz[iı]pla(r|yor|mak|di)?\b|\bbounce\b/i, key: "jump", visible: "a readable jump/bounce with feet leaving the ground", kind: "action" },
  { re: /\bko[sş](ar|uyor|mak|tu)?\b/i, key: "run", visible: "running with planted-then-push steps, not sliding", kind: "action" },
  { re: /\by[uü]r[uü](r|yor|mek)?\b/i, key: "walk", visible: "a clear walk with weight transfer, planted feet", kind: "action" },
  { re: /\bdans(eder| ediyor|et)?\b|\bdance\b/i, key: "dance", visible: "clear dance groove matching the lyric beat", kind: "action" },
  { re: /\balk[iı][sş]\b|\bclap\b/i, key: "clap", visible: "hands clapping on the beat, palms contacting", kind: "action" },
  { re: /\bsay(ar|iyor|mak|al[iı]m)?\b|\bcount(ing)?\b/i, key: "count", visible: "counting by pointing to DISTINCT visible items in order — never empty air", kind: "action" },
  { re: /\bg[oö]ster(ir|iyor|elim)?\b|\bpoint(ing|s)?\b/i, key: "point", visible: "a clear point/show gesture aimed at the named prop", kind: "action" },
  { re: /\bg[uü]l(er|uyor|mek|d[uü])?\b|\bsmile\b/i, key: "smile", visible: "a readable smile matching the lyric moment", kind: "action" },
  { re: /\bsarla(n[iı]r|nmak)?\b|\bhug\b/i, key: "hug", visible: "a gentle hug/cuddle matching the lyric", kind: "action" },
  { re: /\bu[yü]u(r|yor|mak)?\b|\bsleep\b/i, key: "sleep", visible: "a sleep/rest pose matching the lyric (eyes, breath)", kind: "action" },
  { re: /\b[sş]ark[iı](s[oö]yle)?\b|\bsing\b/i, key: "sing", visible: "active singing visemes + body groove, not a frozen portrait", kind: "action" },
  { re: /\boyna(r|yor|mak)?\b/i, key: "play", visible: "playful physical play with the named prop/friend", kind: "action" },
  { re: /\bbak(ar|ıyor|iyor)\b/i, key: "look", visible: "a clear look/gaze at the named thing or friend", kind: "action" },

  { re: /\bmerhaba\b|\bselam\b|\bhello\b/i, key: "hello", visible: "a greeting beat: wave or welcome pose while mouthing those spoken words", kind: "spoken" },
  { re: /\bbak(ın|in|sana)\b|\bdinle(yin|n)?\b/i, key: "listen-look", visible: "spoken look/listen beat: singer turns to camera or a friend and gestures — not a generic dance", kind: "spoken" },
  { re: /\bhadi\b|\bhaydi\b/i, key: "come-on", visible: "an inviting 'hadi' gesture (come-on / let's-go) matching the spoken/sung cue", kind: "spoken" },
  { re: /\bsalla(r|mak|yin)?\b|\bwave\b/i, key: "wave", visible: "a clear hand-wave (el salla) to camera or friends", kind: "action" },
  { re: /\bg[uü]nayd[iı]n\b|\biyi geceler\b/i, key: "daypart", visible: "a spoken greeting matching morning/night with matching sky/light", kind: "spoken" },
];

export function tokenizeLyricWords(audioLine: string): string[] {
  return audioLine
    .replace(/["“”]/g, " ")
    .split(/[\s,./|!?…;:()[\]~]+/)
    .map((w) => w.trim())
    .filter(Boolean);
}

function norm(word: string): string {
  return word.toLocaleLowerCase("tr-TR");
}

export function isLyricStopword(word: string): boolean {
  const n = norm(word).replace(/['’]/g, "");
  if (!n) return true;
  if (/^\d+$/.test(n)) return false;
  return STOPWORDS.has(n);
}

/** Sözdeki içerik kelimeleri (sırayı korur, tekrarları düşürür). */
export function extractLyricContentWords(audioLine: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of tokenizeLyricWords(audioLine)) {
    const cleaned = raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
    if (cleaned.length < 2) continue;
    if (isLyricStopword(cleaned)) continue;
    const key = norm(cleaned);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(cleaned);
  }
  return out;
}

export function extractSongPictureBeats(audioLine: string): SongPictureBeat[] {
  const text = audioLine.replace(/\s+/g, " ").trim();
  if (!text) return [];
  const found = new Map<string, SongPictureBeat>();
  for (const rule of BEAT_RULES) {
    if (rule.re.test(text) && !found.has(rule.key)) {
      found.set(rule.key, { key: rule.key, visible: rule.visible, kind: rule.kind });
    }
  }
  return [...found.values()];
}

function knownVisibleForWord(word: string): string | null {
  const sample = ` ${word} `;
  for (const rule of BEAT_RULES) {
    if (rule.re.test(sample) || rule.re.test(word)) return rule.visible;
  }
  return null;
}

/**
 * Her içerik kelimesi için zorunlu SHOW satırı.
 * Bilinen imge varsa İngilizce sahne; yoksa kelimenin anlamını ekranda somutla.
 */
export function formatWordByWordVisualMap(audioLine: string): string {
  const words = extractLyricContentWords(audioLine);
  if (words.length === 0) return "";
  const lines = words.map((w, i) => {
    const known = knownVisibleForWord(w);
    const show = known
      ? known
      : `the meaning of the lyric word "${w}" as a REAL on-screen object, place, creature or action in THIS moment (not implied, not off-screen, not a later clip)`;
    return `${i + 1}. "${w}" → SHOW: ${show}`;
  });
  return `WORD-BY-WORD PICTURE MAP (every heard content word, in order — skip none):\n${lines.join("\n")}`;
}

export function extractCountedItems(audioLine: string): string[] {
  const tokens = tokenizeLyricWords(audioLine).map((w) => w.toLocaleLowerCase("tr-TR"));
  const text = audioLine.replace(/\s+/g, " ").trim();
  const out: string[] = [];
  const countable = tokens.some((t) =>
    /vagon|tren|balon|^top$|çiçek|cicek|elma|yıldız|yildiz|kuş|kus|kelebek/.test(t)
  );
  if (/\bsay|\bcount|\b1[-–]2[-–]3\b/i.test(text)) {
    out.push("count by tapping/pointing to DISTINCT visible items in lyric order — never mime empty air");
  }
  if (!countable) return out;
  const numMap: Array<[string[], string]> = [
    [["1"], "exactly 1 of the named item"],
    [["iki", "2"], "exactly 2 of the named items, both visible"],
    [["üç", "uc", "3"], "exactly 3 of the named items, counted in order"],
    [["dört", "dort", "4"], "exactly 4 of the named items"],
    [["beş", "bes", "5"], "exactly 5 of the named items"],
  ];
  for (const [keys, line] of numMap) {
    if (tokens.some((t) => keys.includes(t))) out.push(line);
  }
  return out;
}

export function isSpokenOrTalkSing(audioLine: string): boolean {
  return /\b(merhaba|selam|bakın|bakin|dinle|dinleyin|arkadaşlar|arkadaslar|hello|hey|günaydın|gunaydin|hadi|haydi)\b/i.test(audioLine);
}

function uniqueJoin(parts: string[]): string {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of parts) {
    const t = p.replace(/\s+/g, " ").trim();
    if (!t) continue;
    const k = t.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(t);
  }
  return out.join("; ");
}

export function mustShowFromAudio(audioLine: string): string {
  const beats = extractSongPictureBeats(audioLine);
  const counted = extractCountedItems(audioLine);
  const nouns = beats.filter((b) => b.kind !== "spoken").map((b) => b.visible);
  const leftovers = extractLyricContentWords(audioLine).filter((w) => !knownVisibleForWord(w));
  const leftoverLine =
    leftovers.length > 0
      ? `also stage these lyric words as visible things: ${leftovers.map((w) => `"${w}"`).join(", ")}`
      : "";
  return uniqueJoin([...nouns, ...counted, leftoverLine]);
}

export function lyricSyncFromAudio(audioLine: string): string {
  const compact = audioLine.replace(/\s+/g, " ").trim().slice(0, 200);
  const beats = extractSongPictureBeats(audioLine);
  const actions = beats.filter((b) => b.kind === "action" || b.kind === "spoken").map((b) => b.visible);
  const nouns = beats.filter((b) => b.kind === "noun").map((b) => b.visible);
  const spoken = isSpokenOrTalkSing(audioLine)
    ? "This clip includes SPOKEN / talk-sing in the song — mouth the exact words and act them; do not cover speech with a generic dance."
    : "";
  return uniqueJoin([
    `While the song audio says "${compact}", the picture illustrates THOSE words in the SAME moment, in lyric order`,
    ...actions,
    ...nouns.map((n) => `show ${n}`),
    spoken,
    "never mime empty air; every content word occupies real space in frame",
  ]);
}

export function mergeMustShowProps(aiText: string, audioLine: string): string {
  const extracted = mustShowFromAudio(audioLine);
  const ai = aiText.replace(/\s+/g, " ").trim();
  if (!extracted) return ai;
  if (!ai) return extracted;
  const missing = extracted
    .split(/;\s*/)
    .map((s) => s.trim())
    .filter(Boolean)
    .filter((part) => {
      const key = part.slice(0, 28).toLowerCase();
      return !ai.toLowerCase().includes(key.slice(0, 18));
    });
  if (missing.length === 0) return ai;
  return uniqueJoin([`MUST BE VISIBLE FROM THIS CLIP'S AUDIO: ${missing.join("; ")}`, ai]);
}

export function mergeLyricSyncAction(aiText: string, audioLine: string): string {
  const extracted = lyricSyncFromAudio(audioLine);
  const ai = aiText.replace(/\s+/g, " ").trim();
  if (!extracted) return ai;
  if (!ai) return extracted;
  const beats = extractSongPictureBeats(audioLine);
  if (ai.toLowerCase().includes("while") && beats.length > 0 && beats.every((b) => ai.toLowerCase().includes(b.key))) {
    return uniqueJoin([extracted, ai]);
  }
  return uniqueJoin([extracted, ai]);
}

/**
 * Şarkının geçtiği dünya — sözlerden tespit edilir ve TÜM film boyunca kilitlenir.
 * Kullanıcı kuralı: söz "ormanda" diyorsa video dağda/şehirde OLAMAZ.
 */
export type SongWorldLock = {
  key: string;
  /** İngilizce set tarifi (prompta girer). */
  positive: string;
  /** Bu dünyada asla görünmeyecekler (İngilizce). */
  never: string;
  /** Ortam metni bu regex'e takılırsa kilitli dünyayla çelişiyor demektir. */
  conflict: RegExp;
};

const WORLD_RULES: SongWorldLock[] = [
  {
    key: "forest",
    positive:
      "a sunny green FOREST — tall leafy trees with thick trunks, mossy ground with roots and fallen leaves, ferns and wildflowers, warm sun shafts between the trunks, glimpses of blue sky through the canopy",
    never:
      "mountain peaks, rocky cliffs, city streets or buildings, beach or ocean, desert, open snow fields, space, classrooms, bedrooms or any indoor room",
    conflict: /\b(mountain|cliff|alpine|city|street|skyline|beach|ocean|seaside|desert|space station|classroom|bedroom|kitchen)\b|da[gğ]lar|da[gğ]da|[sş]ehir|plaj|okyanus|[cç][oö]l\b/i,
  },
  {
    key: "sea",
    positive:
      "a bright SEASIDE — warm sandy beach, gentle rolling waves, blue sea to the horizon, seashells, dune grass and a clear sky",
    never: "forests, mountains, city streets, deserts, indoor rooms",
    conflict: /\b(forest|woodland|mountain|city|street|classroom|bedroom)\b|orman|da[gğ]da|[sş]ehir/i,
  },
  {
    key: "farm",
    positive:
      "a cheerful FARM — red wooden barn, fenced green fields, hay bales, a dirt path, farm animals in their pens under a sunny sky",
    never: "city streets, beaches, mountains, space, indoor classrooms",
    conflict: /\b(city|skyline|beach|ocean|mountain|space)\b|[sş]ehir|plaj|okyanus|da[gğ]da/i,
  },
  {
    key: "space",
    positive:
      "a friendly cartoon SPACE scene — deep starfield, colorful planets, a toy-like rocket, soft cosmic glow",
    never: "earthly cities, forests, beaches, everyday indoor rooms",
    conflict: /\b(forest|city|beach|classroom|bedroom|street)\b|orman|[sş]ehir|plaj/i,
  },
  {
    key: "garden",
    positive:
      "a sunny GARDEN / PARK — green lawn, flower beds, a big shade tree, colorful playground touches, butterflies in the air",
    never: "mountains, busy city traffic, beach, deserts, dark interiors",
    conflict: /\b(mountain|beach|ocean|desert|skyline)\b|da[gğ]da|plaj|okyanus|[cç][oö]l\b/i,
  },
  {
    key: "home",
    positive:
      "a cozy HOME interior — warm walls, wooden floor, soft rug, toys, and a bright window showing a sunny garden outside",
    never: "mountains, city streets, beach, deep forest sets",
    conflict: /\b(mountain|beach|ocean|street|skyline)\b|da[gğ]da|plaj|okyanus/i,
  },
];

/** Canli-cekim / sinematik: ayni dunya, ama FOTOGRAFIK gercek mekan yogunlugu. */
const WORLD_POSITIVE_LIVE: Record<string, string> = {
  forest:
    "a REAL sunlit FOREST — thick bark with lichen, mossy roots underfoot, wet leaf litter, ferns, insects in sun shafts, volumetric god-rays through canopy, true blue sky gaps, humid air haze, distant trees in soft optical bokeh",
  sea: "a REAL SEASIDE — wet packed sand with footprints, foam lace on rolling waves, salt spray glitter, shells and dune grass, horizon haze, harsh midday sun with sharp beach shadows",
  farm: "a REAL working FARM — weathered red barn wood, dusty dirt path, hay with seed flecks, fence posts with rusted wire, trampled grass, livestock smell-of-place clutter, hard sun and long barn shadows",
  space:
    "a REAL practical kids SPACE SET — dark stage sky with soft practical star lamps, large painted planet props with scuffed edges, a physical rocket mockup, theatrical haze, cinema key+rim — reads as filmed set, never CGI void",
  garden:
    "a REAL GARDEN / PARK — patchy lawn with soil showing, flower beds with mulch, tree bark and leaf shadow lace, gravel path grit, butterflies, playground wood grain, warm late-day sun",
  home: "a REAL HOME interior — scuffed wood floor, soft rug pile, fingerprint smudges on glass, cluttered toys, dust in a bright window shaft, real curtain fabric, garden visible through the glass",
};

/** Canli-cekim promptlari icin dunyanin fotografik pozitif tarifi. */
export function worldPositiveForLive(world: SongWorldLock): string {
  return WORLD_POSITIVE_LIVE[world.key] || world.positive;
}

const WORLD_DETECT: Array<[RegExp, string]> = [
  [/orman|forest|woodland/i, "forest"],
  [/deniz|okyanus|sahil|plaj|kumsal|dalga|\bsea\b|\bbeach\b/i, "sea"],
  [/[cç]iftlik|ah[iı]r|trakt[oö]r|\bfarm\b|\bbarn\b/i, "farm"],
  [/uzay|gezegen|roket|astronot|\bspace\b|\bplanet\b/i, "space"],
  [/bah[cç]e|park(ta|a)?\b|oyun park|\bgarden\b|\bplayground\b/i, "garden"],
  [/evde|odada|evimiz|odam[iı]z|\bbedroom\b|\bliving room\b/i, "home"],
];

/** Sözlerden (tüm şarkı + tema) dünyayı bulur; bulunamazsa null. */
export function detectSongWorld(textForWorld: string): SongWorldLock | null {
  const text = (textForWorld || "").replace(/\s+/g, " ").trim();
  if (!text) return null;
  for (const [re, key] of WORLD_DETECT) {
    if (re.test(text)) return WORLD_RULES.find((w) => w.key === key) ?? null;
  }
  return null;
}

/** AI ortam metni kilitli dünyayla çelişiyor mu? (orman kilidi + "mountain" = çelişki) */
export function environmentConflictsWorld(environment: string, world: SongWorldLock | null): boolean {
  if (!world) return false;
  const env = (environment || "").trim();
  if (!env) return false;
  return world.conflict.test(env);
}

/**
 * KAHRAMAN NESNE (hero prop): şarkı belirli bir nesne hakkındaysa
 * (salatalık, domates, balon...) o nesne filmin yıldızıdır — her klipte
 * görünür kalır, adının geçtiği satırlarda sahnenin merkezine alınır.
 */
export type HeroSubject = {
  /** Gruplama kökü (tr-küçük ilk 5 harf) — satırda geçiyor mu kontrolü için. */
  stem: string;
  /** Sözlerdeki en yalın yüzey biçimi (ör. "salatalık"). */
  surface: string;
  /** İngilizce etiket (ör. "cucumber"); sözlükte yoksa Türkçe yüzey. */
  label: string;
  /** Prompta girecek İngilizce tarif. */
  visible: string;
};

const HERO_LEXICON: Array<[RegExp, string]> = [
  [/^salatal/i, "cucumber"],
  [/^domat/i, "tomato"],
  [/^patat/i, "potato"],
  [/^havu[cç]/i, "carrot"],
  [/^biber/i, "pepper"],
  [/^patl[iı]c/i, "eggplant"],
  [/^elma/i, "apple"],
  [/^armut/i, "pear"],
  [/^muz/i, "banana"],
  [/^[cç]ilek/i, "strawberry"],
  [/^karpuz/i, "watermelon"],
  [/^kavun/i, "melon"],
  [/^[uü]z[uü]m/i, "grapes"],
  [/^portak/i, "orange fruit"],
  [/^limon/i, "lemon"],
  [/^mandal/i, "tangerine"],
  [/^kiraz/i, "cherry"],
  [/^[sş]eftal/i, "peach"],
  [/^kabak/i, "pumpkin"],
  [/^m[iı]s[iı]r/i, "corn cob"],
  [/^ekmek/i, "bread loaf"],
  [/^peynir/i, "cheese"],
  [/^yumurt/i, "egg"],
  [/^kurabiy/i, "cookie"],
  [/^pasta/i, "cake"],
  [/^dondurm/i, "ice cream"],
  [/^balon/i, "balloon"],
  [/^bal[iı][kğ]/i, "fish"],
  [/^kelebek/i, "butterfly"],
  [/^ku[sş]$/i, "bird"],
  [/^tav[sş]an/i, "rabbit"],
  [/^tilki/i, "fox"],
  [/^kirpi/i, "hedgehog"],
  [/^sincap/i, "squirrel"],
  [/^kurba[gğ]a/i, "frog"],
  [/^ay[iı]$/i, "bear"],
  [/^kedi/i, "cat"],
  [/^k[oö]pek/i, "dog"],
  [/^top$/i, "ball"],
  [/^tren/i, "toy train"],
  [/^araba/i, "toy car"],
  [/^u[cç]ak/i, "toy plane"],
  [/^gemi/i, "toy boat"],
  [/^bisiklet/i, "bicycle"],
  [/^davul/i, "drum"],
  [/^gitar/i, "guitar"],
  [/^y[iı]ld[iı]z/i, "star"],
  [/^[cç]i[cç]ek/i, "flower"],
  [/^[sş]emsiy/i, "umbrella"],
  [/^[sş]apka/i, "hat"],
  [/^ayakkab/i, "shoe"],
  [/^di[sş]$/i, "tooth"],
  [/^sabun/i, "soap bar"],
  [/^f[iı]r[cç]a/i, "brush"],
];

/** Baslik/sozden gelen kahraman icin daha somut "lead ile birlikte" tarifi. */
const HERO_VISIBLE: Record<string, string> = {
  fish: "the song's star LITTLE FISH — large in frame with the lead singer (swim beside, hold gently, or point at); readable eyes/scales, contact with water or paws; NEVER a tiny background speck",
  butterfly: "the song's star BUTTERFLY — large, airborne, circling or landing near the lead; never a sticker or off-screen",
  cucumber: "the song's star CUCUMBER — large, tactile, held or pointed at by the lead; real green skin and weight",
  tomato: "the song's star TOMATO — large, tactile, held or pointed at by the lead; real red skin and weight",
  balloon: "the song's star BALLOON — large, held by string in the lead's paw; volume and bounce readable",
};

function heroLabelFor(surface: string): string | null {
  for (const [re, label] of HERO_LEXICON) {
    if (re.test(surface)) return label;
  }
  const beats = extractSongPictureBeats(surface);
  const noun = beats.find((b) => b.kind === "noun");
  return noun ? noun.key : null;
}

function heroStemKey(word: string): string {
  const w = word.toLocaleLowerCase("tr-TR").replace(/[^\p{L}]/gu, "");
  return w.slice(0, 5) || w;
}

/** Ayni nesnenin cekimlerini birlestir: balık/balıklar/balığın → "fish". */
function heroGroupKey(word: string): { key: string; surface: string; label: string | null } {
  const lower = word.toLocaleLowerCase("tr-TR");
  const beats = extractSongPictureBeats(lower);
  const noun = beats.find((b) => b.kind === "noun" && b.key !== "forest" && b.key !== "garden" && b.key !== "home" && b.key !== "sky" && b.key !== "water");
  const label = heroLabelFor(lower);
  if (noun && !WORLD_DETECT.some(([re]) => re.test(lower))) {
    return { key: `beat:${noun.key}`, surface: lower, label: label || noun.key };
  }
  return { key: `stem:${heroStemKey(lower)}`, surface: lower, label };
}

function titleBoostsHero(title: string, surfaces: string[], beatOrStemKey: string): boolean {
  if (!title) return false;
  if (surfaces.some((s) => s.length >= 3 && title.includes(s))) return true;
  if (extractSongPictureBeats(title).some((b) => beatOrStemKey === `beat:${b.key}`)) return true;
  return false;
}

function buildHeroVisible(label: string): string {
  return (
    HERO_VISIBLE[label] ||
    `the song's star ${label.toUpperCase()} — large, tactile and instantly readable beside the lead singer (held, pointed at, or acted with); true material detail and a contact shadow; NEVER missing or a tiny background speck`
  );
}

/**
 * Sözlerin tamamından (başlık + konu dahil) şarkının yıldız nesnesini bulur.
 * Sıklık esaslıdır: en az 3 kez geçen (başlıkta geçiyorsa +3 sayılır) en
 * baskın SOMUT isim seçilir. Eylem/mekan kelimeleri aday olamaz.
 * Basliktaki nesne (ör. "Minik Balık") sozlerde az gecse bile guclu aday olur.
 */
export function detectHeroSubject(fullText: string, titleHint = ""): HeroSubject | null {
  const title = titleHint.toLocaleLowerCase("tr-TR");
  const groups = new Map<string, { count: number; surfaces: string[]; label: string | null }>();

  for (const raw of tokenizeLyricWords(fullText)) {
    const cleaned = raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
    if (!cleaned || isLyricStopword(cleaned)) continue;
    const lower = cleaned.toLocaleLowerCase("tr-TR");
    const inLexicon = HERO_LEXICON.some(([re]) => re.test(lower));
    if (!inLexicon && lower.length < 4) continue;
    // Eylem/konuşma kelimeleri kahraman nesne olamaz
    const beats = extractSongPictureBeats(lower);
    if (beats.some((b) => b.kind === "action" || b.kind === "spoken")) continue;
    // Mekan/dünya kelimeleri de olamaz (orman, deniz, bahçe... — onlar SET kilididir)
    if (WORLD_DETECT.some(([re]) => re.test(lower))) continue;
    // "dost/arkadas" gibi genel kadro kelimeleri kahraman degildir
    if (beats.some((b) => b.key === "friends" || b.key === "hands" || b.key === "feet" || b.key === "nose")) continue;

    const grouped = heroGroupKey(lower);
    const entry = groups.get(grouped.key) ?? { count: 0, surfaces: [], label: grouped.label };
    entry.count += 1;
    entry.surfaces.push(grouped.surface);
    if (!entry.label && grouped.label) entry.label = grouped.label;
    groups.set(grouped.key, entry);
  }

  // Baslikta gecen somut nesneyi en az bir kez gruba ekle (az sozlu sarkilar icin)
  for (const raw of tokenizeLyricWords(title)) {
    const cleaned = raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");
    if (!cleaned || isLyricStopword(cleaned)) continue;
    const lower = cleaned.toLocaleLowerCase("tr-TR");
    if (WORLD_DETECT.some(([re]) => re.test(lower))) continue;
    const grouped = heroGroupKey(lower);
    if (!grouped.label && !HERO_LEXICON.some(([re]) => re.test(lower))) continue;
    const entry = groups.get(grouped.key) ?? { count: 0, surfaces: [], label: grouped.label };
    if (!entry.surfaces.includes(lower)) entry.surfaces.push(lower);
    if (!entry.label && grouped.label) entry.label = grouped.label;
    groups.set(grouped.key, entry);
  }

  let best: { key: string; count: number; surface: string; label: string } | null = null;
  for (const [key, entry] of groups) {
    const surface = [...entry.surfaces].sort((a, b) => a.length - b.length)[0];
    const label = entry.label || heroLabelFor(surface) || surface;
    const bonus = titleBoostsHero(title, entry.surfaces, key) ? 3 : 0;
    const score = entry.count + bonus;
    // Baslikta gecen lexicon/beat nesnesi icin esik 2; aksi 3
    const need = bonus > 0 ? 2 : 3;
    if (score >= need && (!best || score > best.count)) {
      best = { key, count: score, surface, label };
    }
  }
  if (!best) return null;

  return {
    stem: best.key.startsWith("beat:") ? best.surface.slice(0, 5) : best.key.replace(/^stem:/, ""),
    surface: best.surface,
    label: best.label,
    visible: buildHeroVisible(best.label),
  };
}

/** Bu klibin sözü kahraman nesneyi adıyla anıyor mu? */
export function lyricsNameHero(lyrics: string, hero: HeroSubject | null): boolean {
  if (!hero) return false;
  const L = lyrics.toLocaleLowerCase("tr-TR");
  if (L.includes(hero.surface) || (hero.stem.length >= 3 && L.includes(hero.stem))) return true;
  // Cekim farklari: balığın / balıkları → beat eslesmesi
  return extractSongPictureBeats(lyrics).some((b) => b.key === hero.label || b.key === hero.surface);
}

/**
 * Tırnaksız sahneleme listesi: duyulan her içerik kelimesinin GÖRÜNÜR karşılığı,
 * İngilizce tek liste halinde. (Tırnaklı kelime listeleri Veo'da ekrana yazı
 * bastırabildiği için söz yalnızca BİR kez, en üstte tırnaklanır.)
 */
export function formatLyricStagingLine(audioLine: string, aiProps?: string): string {
  const beats = extractSongPictureBeats(audioLine);
  const counted = extractCountedItems(audioLine);
  const parts = beats.map((b) => b.visible.split(/[—(]/)[0].trim());
  const ai = (aiProps || "").replace(/\s+/g, " ").trim();
  const generic =
    "every other creature, object, place, color, number and action named in the sung line is also physically present and readable in this same clip — nothing named is skipped or delayed to a later clip";
  return uniqueJoin([...parts, ...counted, ai, generic]);
}

export function formatSongPictureConfirm(opts: {
  audioLine: string;
  singerName?: string;
  appearanceLock?: string;
  wardrobeLock?: string;
  supportingNames?: string[];
}): string {
  const audio = opts.audioLine.replace(/\s+/g, " ").trim();
  const beats = extractSongPictureBeats(audio);
  const must = mustShowFromAudio(audio);
  const wordMap = formatWordByWordVisualMap(audio);
  const spoken = beats.filter((b) => b.kind === "spoken");
  const support = (opts.supportingNames ?? []).map((n) => n.trim()).filter(Boolean);
  return [
    "[SONG PICTURE CONFIRM — AUDIO DRIVES FRAME]",
    `This clip's AUDIO (sung lyrics AND any spoken / talk-sing in the song) is exactly: "${audio}".`,
    "COMPREHENSIVE RULE: every content word that is HEARD must be SEEN in this same clip — animals, objects, places, colors, numbers, verbs. Skip none. Do not delay a named thing to a later clip.",
    wordMap,
    must ? `MUST BE VISIBLE IN THIS CLIP (non-negotiable): ${must}.` : "",
    spoken.length
      ? `SPOKEN / TALK-SING (not a generic dance): ${spoken.map((s) => s.visible).join("; ")}`
      : "",
    opts.singerName?.trim()
      ? `CONFIRM CAST: the performer on screen is ${opts.singerName.trim()} — same face, species, height, proportions and costume as every other clip of this song.`
      : "CONFIRM CAST: keep the locked lead singer 1:1 on-model.",
    opts.appearanceLock?.trim() ? `CONFIRM FACE/BODY: ${opts.appearanceLock.trim()}` : "",
    opts.wardrobeLock?.trim() ? `CONFIRM COSTUME: ${opts.wardrobeLock.trim()}` : "",
    support.length ? `Friends named in the song who belong on screen: ${support.join(", ")}.` : "",
    "FAIL the take if any heard content word is missing from the picture (example: 'kelebek uçar' without a butterfly flying).",
  ]
    .filter(Boolean)
    .join(" ");
}
