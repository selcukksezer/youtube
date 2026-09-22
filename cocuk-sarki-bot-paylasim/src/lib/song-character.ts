import { z } from "zod";
import { resolveSongVarietyPack } from "@/lib/song-variety";

/** Sarki yildizi (DNA karti) — karakter referans gorseli icin. */
export const dnaCardSchema = z.object({
  name: z.string().min(1),
  species: z.string(),
  personality: z.array(z.string()),
  catchphrase: z.string(),
  signatureGesture: z.string(),
  voiceDescription: z.string(),
  fears: z.string(),
  loves: z.string(),
  colorPalette: z.array(z.string()),
  imagePrompt: z.string().min(20),
  bodyDetail: z.string().default(""),
  outfitDetail: z.string().default(""),
  signatureProp: z.string().default(""),
  styleLabel: z.string().default(""),
  // AYIRT EDICI ALANLAR — kadro uyeleri birbirinin renk kopyasi olmasin.
  // Eski kayitlarda yok; varsayilanlar geriye donuk uyumlulugu korur.
  silhouette: z.string().default(""),
  heightBand: z.string().default(""),
  distinguishingMark: z.string().default(""),
  faceFeatures: z.string().default(""),
});

export type DnaCard = z.infer<typeof dnaCardSchema>;

export type SongCharacterProfileInput = {
  name: string;
  hair: string;
  faceFeatures: string;
  wardrobe: string;
  gestureLevel: string;
  voiceCharacter: string;
  emotionTone: string;
  storyNote: string;
  imagePrompt: string;
  baseAppearancePrompt: string;
  baseWardrobePrompt: string;
  baseVoicePrompt: string;
  negativePrompt: string;
  flowCharacterReference: string;
  referenceImagePath?: string | null;
};

export type SongProjectContext = {
  id?: string;
  visualStyle?: string;
  topic?: string;
  channelName?: string;
  createdAt?: Date | string | null;
  songSettings?: string | null;
  emotionCurve?: string | null;
};

const DEFAULT_PALETTE = ["#FFD166", "#06D6A0", "#EF476F", "#118AB2"];
const DEFAULT_PERSONALITY = ["cheerful", "playful", "energetic"];

export function isEmptyDnaCard(raw: string | null | undefined): boolean {
  if (!raw || raw.trim() === "" || raw.trim() === "{}") return true;
  try {
    const parsed = JSON.parse(raw) as Partial<DnaCard>;
    return !parsed.name?.trim() || !parsed.imagePrompt?.trim();
  } catch {
    return true;
  }
}

/** Karakter profilinden en az bir tanim alani dolu mu? */
export function characterReadyForSong(profile: SongCharacterProfileInput): boolean {
  const fields = [
    profile.name,
    profile.hair,
    profile.faceFeatures,
    profile.wardrobe,
    profile.storyNote,
    profile.imagePrompt,
    profile.baseAppearancePrompt,
    profile.flowCharacterReference,
  ];
  return fields.some((f) => f.trim().length > 0) || Boolean(profile.referenceImagePath);
}

function inferSpecies(profile: SongCharacterProfileInput): string {
  const hint = `${profile.storyNote} ${profile.faceFeatures} ${profile.hair}`.toLowerCase();
  const animals = [
    ["fox", "fennec fox mascot"],
    ["owl", "round owl mascot"],
    ["raccoon", "raccoon mascot"],
    ["penguin", "penguin mascot"],
    ["otter", "river otter mascot"],
    ["panda", "panda mascot"],
    ["chameleon", "chameleon mascot"],
    ["squirrel", "squirrel mascot"],
    ["hedgehog", "hedgehog mascot"],
    ["frog", "frog mascot"],
    ["koala", "koala mascot"],
    ["llama|alpaca", "llama mascot"],
    ["axolotl", "axolotl mascot"],
    ["bee", "round bee mascot"],
    ["turtle", "turtle mascot"],
    ["wolf", "friendly wolf-cub mascot"],
    ["mouse", "mouse mascot"],
    ["duck", "duck mascot"],
    ["capybara", "capybara mascot"],
    ["kiwi", "kiwi-bird mascot"],
    ["puffin", "puffin mascot"],
    ["sheep", "cloud-sheep mascot"],
    ["cat", "cartoon cat mascot"],
    ["dog", "cartoon dog mascot"],
    ["bear", "cartoon bear mascot"],
    ["bunny|rabbit", "cartoon bunny mascot"],
    ["bird", "cartoon bird mascot"],
    ["dragon", "friendly dragon mascot"],
    ["robot", "cute robot mascot"],
  ] as const;
  for (const [pattern, label] of animals) {
    if (new RegExp(pattern, "i").test(hint)) return label;
  }
  return "stylized 3D cartoon mascot performer";
}

function inferPersonality(profile: SongCharacterProfileInput): string[] {
  const traits: string[] = [];
  const tone = profile.emotionTone.toLowerCase();
  if (/joy|happy|cheer|nesel|mutlu|parlak/i.test(tone)) traits.push("cheerful");
  if (/play|oyun|fun|eglenc/i.test(tone)) traits.push("playful");
  if (/energetic|dance|dans|canli/i.test(`${tone} ${profile.gestureLevel}`)) traits.push("energetic");
  if (/curious|merak/i.test(tone)) traits.push("curious");
  if (/kind|nazik|sicak/i.test(tone)) traits.push("kind");
  return traits.length > 0 ? traits.slice(0, 4) : DEFAULT_PERSONALITY;
}

function inferCatchphrase(profile: SongCharacterProfileInput): string {
  const note = profile.storyNote.trim();
  if (note) {
    const first = note.split(/[.!?]/)[0]?.trim();
    if (first && first.length <= 40) return first;
  }
  const name = profile.name.trim() || "Hadi";
  return `${name} ile birlikte!`;
}

function styleLabelFor(project: SongProjectContext): { shot: string; id: string } {
  if (project.id) {
    const pack = resolveSongVarietyPack({ ...project, id: project.id });
    return { shot: pack.shotStylePhrase, id: pack.styleLabel };
  }
  const style = project.visualStyle?.trim() || "stylized3d";
  const shot = style === "pixar3d" ? "stylized 3D animation" : `${style} animation`;
  return { shot, id: style };
}

function buildImagePrompt(profile: SongCharacterProfileInput, project: SongProjectContext, name: string, species: string): string {
  if (profile.imagePrompt.trim().length >= 20) return profile.imagePrompt.trim();

  const { shot: styleLabel } = styleLabelFor(project);
  const appearance = profile.baseAppearancePrompt.trim() || [profile.hair, profile.faceFeatures].filter(Boolean).join(", ");
  const outfit = profile.baseWardrobePrompt.trim() || profile.wardrobe.trim();
  const parts = [
    `${styleLabel} music video hero character, ${name}, ${species}.`,
    appearance && `Appearance: ${appearance}.`,
    outfit && `Outfit: ${outfit}.`,
    "Full body visible, expressive friendly face, bright colorful kids MV look, clean studio lighting, no text, no watermark.",
  ].filter(Boolean);
  const prompt = parts.join(" ");
  return prompt.length >= 20 ? prompt : `${styleLabel} music video mascot ${name}, colorful outfit, full body, expressive face, kids pop MV.`;
}

/** CharacterProfile alanlarindan DNA karti uretir (sync/sarki uretimi icin). */
export function buildSongDnaCardFromProfile(profile: SongCharacterProfileInput, project: SongProjectContext = {}): DnaCard {
  const name =
    profile.name.trim() ||
    profile.flowCharacterReference.replace(/^@/, "").trim() ||
    "Sarki Yildizi";
  const species = inferSpecies(profile);
  const personality = inferPersonality(profile);
  const imagePrompt = buildImagePrompt(profile, project, name, species);

  return dnaCardSchema.parse({
    name,
    species,
    personality,
    catchphrase: inferCatchphrase(profile),
    signatureGesture: profile.gestureLevel.trim() || "rhythmic dance moves with upbeat hand gestures",
    voiceDescription: profile.baseVoicePrompt.trim() || profile.voiceCharacter.trim() || "bright cheerful singing voice for kids pop",
    fears: profile.negativePrompt.trim() || "dark scary imagery, loud shocks, violence",
    loves: project.topic?.trim() || "music, dancing, and playful discovery",
    colorPalette: DEFAULT_PALETTE,
    imagePrompt,
    bodyDetail: [profile.hair, profile.faceFeatures].filter(Boolean).join("; ") || profile.baseAppearancePrompt.trim(),
    outfitDetail: profile.baseWardrobePrompt.trim() || profile.wardrobe.trim(),
    signatureProp: "handheld star-shaped microphone",
    styleLabel: styleLabelFor(project).id,
    faceFeatures: profile.faceFeatures.trim(),
  });
}
