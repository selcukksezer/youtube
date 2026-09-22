import { describe, expect, it } from "vitest";
import {
  buildSongVarietyPackFromSeed,
  clipVarietyAccent,
  formatCastVarietyLock,
  formatLookPackLock,
  formatStyleOverlay,
  formatVisualsVarietyLock,
  hash32,
  resolveSongVarietyPack,
  stripGenericStudioLabels,
} from "@/lib/song-variety";
import { composeShotPrompt } from "@/server/services/song";

describe("Sarki look pack cesitliligi", () => {
  it("farkli proje id'leri farkli pack uretir", () => {
    const a = resolveSongVarietyPack({ id: "proj-alpha" });
    const b = resolveSongVarietyPack({ id: "proj-beta" });
    expect(a.packId).not.toBe(b.packId);
    expect(a.seed).not.toBe(b.seed);
  });

  it("ayni proje id'si ayni pack'i kilitler (sureklilik)", () => {
    const a = resolveSongVarietyPack({ id: "proj-stable", createdAt: "2026-01-01T00:00:00.000Z" });
    const b = resolveSongVarietyPack({ id: "proj-stable", createdAt: "2026-01-01T00:00:00.000Z" });
    expect(a.packId).toBe(b.packId);
    expect(a.seed).toBe(b.seed);
    expect(a.world.id).toBe(b.world.id);
  });

  it("emotionCurve'deki varietySeed pack'i ezer", () => {
    const seed = hash32("forced-seed");
    const pack = resolveSongVarietyPack({
      id: "ignored-id",
      emotionCurve: JSON.stringify({ kind: "song", varietySeed: seed }),
    });
    expect(pack.seed).toBe(seed);
    expect(pack.packId).toBe(buildSongVarietyPackFromSeed(seed).packId);
  });

  it("klip vurgusu kamerayi degistirir ama dunyayi degistirmez", () => {
    const pack = resolveSongVarietyPack({ id: "proj-film" });
    const c1 = clipVarietyAccent(pack, 1);
    const c2 = clipVarietyAccent(pack, 2);
    expect(c1.camera).not.toBe(c2.camera);
    expect(c1.choreo).not.toBe(c2.choreo);
    expect(clipVarietyAccent(pack, 1).camera).toBe(c1.camera);
  });

  it("jenerik Pixar etiketini strip eder", () => {
    expect(stripGenericStudioLabels("3D Pixar-style fox")).toMatch(/stylized 3D fox/i);
    expect(stripGenericStudioLabels("Pixar / DreamWorks lighting")).not.toMatch(/Pixar/);
  });

  it("composeShotPrompt pack'i brief'e yazar", () => {
    const pack = resolveSongVarietyPack({ id: "proj-shot" });
    const shot = composeShotPrompt(
      {
        index: 1,
        section: "chorus",
        lyrics: "Alkış yap merhaba",
        syllableCount: 8,
        sceneDescription: "Alkış",
        imagePrompt: "singer claps with both paws on the beat",
        choreography: "alkış",
        voiceTone: "bright",
        emotion: "neşeli",
        hookNote: "",
        curiosityScore: 5,
      },
      8,
      pack
    );
    // Look pack sahne planinda TEKRARLANMAZ — nihai promptun [STYLE] blogu
    // onu bir kez yazar (tekrar, 8k limitinde [STYLE]'in kesilmesine yol aciyordu).
    expect(shot).not.toContain("LOOK PACK");
    expect(shot.toLowerCase()).not.toContain("pixar-style");
  });

  it("cast ve visuals kilitleri Pixar kalibini yasaklar", () => {
    const pack = resolveSongVarietyPack({ id: "proj-locks" });
    const cast = formatCastVarietyLock(pack);
    const vis = formatVisualsVarietyLock(pack);
    expect(cast).toContain(pack.artDialect.prompt.slice(0, 28));
    expect(cast).toMatch(/do not write "Pixar-style"/i);
    expect(vis).toContain(pack.world.prompt.slice(0, 24));
    expect(vis).toMatch(/FORBIDDEN CLICHES/);
    expect(pack.characterRenderStyle).not.toMatch(/Pixar-style/);
  });

  it("karakterler hicbir lehcede kare kare/voksel olamaz (Minecraft yasagi)", () => {
    const pack = resolveSongVarietyPack({ id: "proj-smooth" });
    expect(pack.characterRenderStyle).toMatch(/never voxel/i);
    expect(pack.characterRenderStyle).toMatch(/Minecraft\/Lego-like/i);
    expect(formatVisualsVarietyLock(pack)).toMatch(/voxel\/Minecraft\/Lego-brick/i);
    expect(formatStyleOverlay(pack, 3)).toMatch(/never voxel/i);
    expect(formatLookPackLock(pack, 3)).toMatch(/never voxel/i);
  });

  it("hicbir sanat lehcesi karakteri tugla/minifigur olarak TARIF edemez", () => {
    for (let seed = 0; seed < 64; seed++) {
      const pack = buildSongVarietyPackFromSeed(seed);
      // Eski bozuk kaliplar (olumlu tarif) geri gelmesin; "never brick-built"
      // gibi yasak cumleleri serbesttir.
      expect(pack.artDialect.prompt).not.toMatch(/minifigure-adjacent/i);
      expect(pack.artDialect.prompt).not.toMatch(/studded brick architecture/i);
      expect(pack.artDialect.prompt).not.toMatch(/interlocking brick-toy/i);
      expect(pack.artDialect.prompt).not.toMatch(/characters?[^.]*brick-built(?![^.]*never)/i);
    }
  });

  it("Flow prompt STYLE bloguna proje look pack yazar", async () => {
    const { buildClipPrompt } = await import("@/server/services/prompt-builder");
    const pack = resolveSongVarietyPack({ id: "proj-style-overlay" });
    const prompt = buildClipPrompt({
      project: {
        id: "proj-style-overlay",
        templateType: "kids_song",
        speechLanguage: "Türkçe",
        promptTemplate: "",
        useFlowCharacter: false,
        aspectRatio: "16:9",
        visualStyle: "pixar3d",
        allowSubtitles: false,
        emotionCurve: JSON.stringify({ varietySeed: pack.seed }),
        clipSeconds: 8,
        useReference: true,
      },
      character: {
        baseAppearancePrompt: "round otter mascot with pebble necklace",
        baseWardrobePrompt: "blank teal vest",
        baseEnvironmentPrompt: "",
        baseCameraPrompt: "",
        baseVoicePrompt: "",
        negativePrompt: "",
        flowCharacterReference: "@Mavi",
        name: "Mavi",
      },
      clip: {
        dialogue: "Alkış yap merhaba",
        index: 1,
        sceneDescription: "alkış",
        voiceTone: "bright",
        imagePrompt: "While singing: Alkış yap merhaba. On-screen: claps both paws.",
        emotionLabel: "neşeli",
      },
      isFirstClip: true,
    });
    expect(prompt).toContain(`LOOK PACK ${pack.packId}`);
    expect(prompt).toContain(pack.world.prompt.slice(0, 28));
    expect(prompt).toContain(pack.artDialect.prompt.slice(0, 28));
    expect(prompt).not.toMatch(/Pixar \/ DreamWorks/);
  });
});
