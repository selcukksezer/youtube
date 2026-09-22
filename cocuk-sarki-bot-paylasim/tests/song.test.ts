import { describe, expect, it } from "vitest";
import {
  composeShotPrompt,
  recommendedBpm,
  songClipCount,
  syllableBudgetForClip,
  syllableBudgetPerSecond,
  syllableFloorForClip,
  parseSongPackage,
  chunkSongVisualBatches,
  SONG_VISUALS_BATCH_SIZE,
  SONG_THEMES,
  SONG_STYLES,
  SONG_DURATION_PRESETS,
} from "@/server/services/song";
import { SONG_THEMES as CATALOG_THEMES, SONG_STYLES as CATALOG_STYLES } from "@/lib/song-catalog";
import { buildFullBodyPrompt } from "@/server/services/kids";
import { buildSongDnaCardFromProfile, characterReadyForSong } from "@/lib/song-character";
import { templateLabel, isKidsContent, isKidsSong, emptyClipsHint } from "@/lib/templates";
import { pickSongPosterTitle, songTitleIsSelected } from "@/lib/song-titles";

describe("Sarki klip matematiği", () => {
  it("30/60/90/180 saniyeyi 8 sn kliplere boler", () => {
    expect(songClipCount(30, 8)).toBe(4);
    expect(songClipCount(60, 8)).toBe(8);
    expect(songClipCount(90, 8)).toBe(11);
    expect(songClipCount(120, 8)).toBe(15);
    expect(songClipCount(180, 8)).toBe(23);
  });

  it("katalog sure presetleri songClipCount ile tutarli", () => {
    for (const preset of SONG_DURATION_PRESETS) {
      const count = songClipCount(preset.value, 8);
      expect(count).toBeGreaterThanOrEqual(4);
      expect(count).toBe(Math.max(4, Math.round(preset.value / 8)));
    }
  });

  it("uzun sure presetleri (5/10/15/20 dk) mevcut", () => {
    const values = SONG_DURATION_PRESETS.map((d) => d.value);
    expect(values).toEqual(expect.arrayContaining([300, 600, 900, 1200]));
  });

  it("sureye gore acilis/kapanis yay blueprint'i uretir", async () => {
    const { buildSongArcBlueprint, SONG_OPENING_CLOSING_CRAFT } = await import("@/lib/song-catalog");
    expect(SONG_OPENING_CLOSING_CRAFT).toMatch(/COLD OPEN|KAPANIS/i);

    const oneMin = buildSongArcBlueprint({ targetSeconds: 60, clipCount: 8, clipSeconds: 8 });
    expect(oneMin).toMatch(/KISA SINGLE|ACILIS|outro/i);

    const tenMin = buildSongArcBlueprint({ targetSeconds: 600, clipCount: 75, clipSeconds: 8 });
    expect(tenMin).toMatch(/UZUN SINGALONG|COLD OPEN|final chorus/i);

    const twentyMin = buildSongArcBlueprint({ targetSeconds: 1200, clipCount: 150, clipSeconds: 8 });
    expect(twentyMin).toMatch(/EPIC SINGALONG|Kapanis ZORUNLU|cold open/i);
  });

  it("en az 4 klip uretir", () => {
    expect(songClipCount(10, 8)).toBe(4);
  });

  it("gorsel plani 6'lik paketlere boler (uzun sarkida tek OpenAI cagrisini onler)", () => {
    const clips = Array.from({ length: 11 }, (_, i) => i + 1);
    const batches = chunkSongVisualBatches(clips, SONG_VISUALS_BATCH_SIZE);
    expect(SONG_VISUALS_BATCH_SIZE).toBe(6);
    expect(batches).toEqual([
      [1, 2, 3, 4, 5, 6],
      [7, 8, 9, 10, 11],
    ]);
    expect(chunkSongVisualBatches(clips.slice(0, 4))).toEqual([[1, 2, 3, 4]]);
  });

  it("1-3 yas daha yavas hece butcesi kullanir", () => {
    expect(syllableBudgetPerSecond("1-3")).toBeLessThan(syllableBudgetPerSecond("3-5"));
    expect(syllableBudgetPerSecond("3-5")).toBeLessThan(syllableBudgetPerSecond("6-8"));
    expect(syllableBudgetForClip("1-3", 8)).toBeLessThan(syllableBudgetForClip("6-8", 8));
  });

  it("hece butcesi klibi dolduracak kadar genis, alt sinir bos klibi engeller", () => {
    // 8 saniyeye iki dolu dize sigmali; eski 11-16 hecelik butce klipleri bos birakiyordu
    expect(syllableBudgetForClip("3-5", 8)).toBeGreaterThanOrEqual(20);
    expect(syllableBudgetForClip("6-8", 8)).toBeGreaterThanOrEqual(24);
    const floor = syllableFloorForClip("3-5", 8);
    expect(floor).toBeGreaterThan(10);
    expect(floor).toBeLessThan(syllableBudgetForClip("3-5", 8));
  });

  it("ninni ve 1-3 yas daha dusuk BPM onerir", () => {
    const lullaby = recommendedBpm("3-5", "lullaby");
    const pop = recommendedBpm("6-8", "kidspop");
    expect(lullaby.max).toBeLessThanOrEqual(100);
    expect(pop.min).toBeGreaterThanOrEqual(100);
  });

  it("yeni stiller katalog BPM araligini kullanir", () => {
    const electro = recommendedBpm("6-8", "electrokids");
    expect(electro.min).toBeGreaterThanOrEqual(110);
    const parade = recommendedBpm("3-5", "parade");
    expect(parade.min).toBeGreaterThanOrEqual(100);
  });
});

describe("Sarki temalari ve stiller", () => {
  it("her yas bandi icin en az bir tema vardir", () => {
    for (const band of ["1-3", "3-5", "6-8"]) {
      expect(SONG_THEMES.some((t) => t.ageBands.includes(band))).toBe(true);
    }
  });

  it("her temada ultra brief alanlari dolu", () => {
    for (const theme of SONG_THEMES) {
      expect(theme.propBank.trim().length).toBeGreaterThan(20);
      expect(theme.tagline.trim().length).toBeGreaterThan(8);
      expect(theme.hookAngle.trim().length).toBeGreaterThan(10);
      expect(theme.gameMechanic.trim().length).toBeGreaterThan(10);
      expect(theme.lyricSeedWords.trim().length).toBeGreaterThan(5);
      expect(theme.lyricSpark.trim().length).toBeGreaterThan(20);
      expect(theme.meaningPromise.trim().length).toBeGreaterThan(24);
      expect(theme.verseArc.trim().length).toBeGreaterThan(24);
      expect(theme.bpmGuide.trim().length).toBeGreaterThan(2);
    }
  });

  it("yeni anlam temalari katalogda", () => {
    for (const id of ["wonder", "kindness", "kitchen"]) {
      expect(SONG_THEMES.some((t) => t.id === id)).toBe(true);
    }
    expect(SONG_THEMES.length).toBeGreaterThanOrEqual(21);
  });

  it("12 muzik tarzi ve yeni id'ler mevcut", () => {
    expect(SONG_STYLES.length).toBe(12);
    for (const id of ["worldbounce", "electrokids", "softballad", "parade"]) {
      expect(SONG_STYLES.some((s) => s.id === id)).toBe(true);
    }
    for (const style of SONG_STYLES) {
      expect(style.tagline.trim().length).toBeGreaterThan(5);
      expect(style.groove.trim().length).toBeGreaterThan(5);
      expect(style.bpmRange.min).toBeLessThan(style.bpmRange.max);
      expect(style.mixColor.trim().length).toBeGreaterThan(5);
      expect(style.beatVisuals.trim().length).toBeGreaterThan(20);
    }
  });

  it("canli MV kilidi mevcut", async () => {
    const { SONG_MV_LIVELINESS_LOCK } = await import("@/lib/song-catalog");
    expect(SONG_MV_LIVELINESS_LOCK).toContain("LIVELY FAMILY MUSIC-VIDEO LOCK");
    expect(SONG_MV_LIVELINESS_LOCK).toMatch(/AUDIBLE|CONTINUOUS/i);
  });

  it("yaratici soz zanaati kilidi mevcut", async () => {
    const { SONG_LYRIC_CRAFT_LOCK } = await import("@/lib/song-catalog");
    expect(SONG_LYRIC_CRAFT_LOCK).toContain("YARATICI SOZ ZANAATI");
    expect(SONG_LYRIC_CRAFT_LOCK).toMatch(/ANLAM ONCE|meaningPromise|Hadi yapalim|Sticky hook|lyricSpark|SANATCI AGZI/i);
  });

  it("ses ve uretim kilitleri mevcut", async () => {
    const {
      SONG_VOICE_IDENTITY_LOCK,
      SONG_MV_PRODUCTION_LOCK,
      SONG_LYRIC_PICTURE_SYNC_LOCK,
      SONG_CHARACTER_FIDELITY_LOCK,
    } = await import("@/lib/song-catalog");
    expect(SONG_VOICE_IDENTITY_LOCK).toContain("SINGER VOICE IDENTITY LOCK");
    expect(SONG_MV_PRODUCTION_LOCK).toMatch(/NO sliding|ANTI-GLITCH|DENSE/i);
    expect(SONG_LYRIC_PICTURE_SYNC_LOCK).toContain("LYRIC ↔ CLIP ↔ VIDEO SYNC LOCK");
    expect(SONG_CHARACTER_FIDELITY_LOCK).toContain("CHARACTER FIDELITY LOCK");
    expect(SONG_CHARACTER_FIDELITY_LOCK).toMatch(/EVERY CLIP|morph|proportions/i);
  });

  it("song.ts katalog ile lib/song-catalog ayni kaynaktan gelir", () => {
    expect(SONG_THEMES).toBe(CATALOG_THEMES);
    expect(SONG_STYLES).toBe(CATALOG_STYLES);
  });

  it("bozuk JSON paketini null doner", () => {
    expect(parseSongPackage("")).toBeNull();
    expect(parseSongPackage("{not json")).toBeNull();
    expect(parseSongPackage(JSON.stringify({ title: "x" }))).toBeNull();
  });
});

describe("Sahne ve karakter detayi", () => {
  it("plan metni soz→gorsel sirali brief olarak toplanir", () => {
    const shot = composeShotPrompt({
      index: 1,
      section: "chorus",
      lyrics: "Köpük eller, mis kokar",
      syllableCount: 18,
      sceneDescription: "Banyoda kopuk oyunu",
      imagePrompt: "3D Pixar-style animation music video still of a fennec fox washing hands",
      choreography: "Elleri kalp yapip iki kez alkislar",
      voiceTone: "bright and bouncy",
      emotion: "neseli",
      environment: "turquoise tiled bathroom with grout lines and a steamy mirror",
      lighting: "warm 4200K key from the window, soft blue bounce",
      cameraShot: "medium shot, 40mm, slight low angle, slow push-in",
      motionDetail: "soap bubbles drifting, fur tufts bouncing",
      microExpression: "eyebrows lift on the rhyme, eye sparkle",
      mustShowProps: "thick white soap foam on both paws, turquoise ceramic sink with running water",
      lyricSyncAction: "As foam hands are sung, shows thick foam on both paws and sniffs the clean scent",
      hookNote: "Sepetin icinde ne var acaba?",
      curiosityScore: 8,
    });
    expect(shot).toContain("CLEAR MUSIC-VIDEO DIRECTOR BRIEF");
    expect(shot).toContain('HEARD THIS CLIP (sung + any spoken/talk-sing, exact): "Köpük eller, mis kokar"');
    expect(shot).toContain("AUDIO→PICTURE SYNC");
    expect(shot).toContain("WORD-BY-WORD PICTURE MAP");
    expect(shot).toMatch(/kelebek|foam|Köpük|kopuk/i);
    expect(shot).toContain("thick foam on both paws");
    expect(shot).toContain("MUST-SHOW PROPS");
    expect(shot).toContain("thick white soap foam");
    expect(shot).toContain("While singing:");
    expect(shot).toContain("SET / ENVIRONMENT: turquoise tiled bathroom");
    expect(shot).toContain("LIGHTING: warm 4200K key");
    expect(shot).toContain("CAMERA: medium shot, 40mm");
    expect(shot).toContain("SECONDARY MOTION: soap bubbles");
    expect(shot).toContain("FACE ACTING: eyebrows lift");
    expect(shot).toContain("ON-SCREEN MOVES");
    expect(shot).toContain("LYRIC ↔ CLIP ↔ VIDEO SYNC LOCK");
    expect(shot).toContain("CHARACTER FIDELITY LOCK");
    expect(shot).toContain("SINGER VOICE IDENTITY LOCK");
    expect(shot).toContain("ULTRA MUSIC-VIDEO PRODUCTION LOCK");
  });

  it("karakter referansi tam boy ve yakin plan yasakli olur", () => {
    const prompt = buildFullBodyPrompt({
      name: "Sunny",
      species: "Fennec Fox",
      personality: ["neseli"],
      catchphrase: "Hadi!",
      signatureGesture: "kulak oynatma",
      voiceDescription: "parlak mezzo",
      fears: "karanlik",
      loves: "kopuk",
      colorPalette: ["#F6E2B3"],
      imagePrompt: "3D Pixar-style animation of a fennec fox with oversized ears",
      bodyDetail: "small build, silky sand-colored fur",
      outfitDetail: "aqua denim jacket, corduroy shorts, red sneakers",
      signatureProp: "star-shaped microphone",
      styleLabel: "",
    });
    expect(prompt).toContain("2-panel character turnaround sheet");
    expect(prompt).toContain("full body head-to-toe");
    expect(prompt).toContain("NO close-up");
    expect(prompt).toContain("Outfit head-to-toe: aqua denim jacket");
    expect(prompt).toContain("Signature prop: star-shaped microphone");
    expect(prompt).toContain("CHARACTER BIBLE LABELS");
  });

  it("profilden DNA karti uretir", () => {
    expect(
      characterReadyForSong({
        name: "",
        hair: "",
        faceFeatures: "",
        wardrobe: "",
        gestureLevel: "",
        voiceCharacter: "",
        emotionTone: "",
        storyNote: "",
        imagePrompt: "",
        baseAppearancePrompt: "",
        baseWardrobePrompt: "",
        baseVoicePrompt: "",
        negativePrompt: "",
        flowCharacterReference: "",
      })
    ).toBe(false);

    const dna = buildSongDnaCardFromProfile(
      {
        name: "Yildiz",
        hair: "short brown hair",
        faceFeatures: "round friendly face",
        wardrobe: "colorful kids MV outfit",
        gestureLevel: "energetic dance gestures",
        voiceCharacter: "bright cheerful singing voice",
        emotionTone: "joyful",
        storyNote: "",
        imagePrompt: "",
        baseAppearancePrompt: "A 20-year-old adult with short brown hair, round friendly face.",
        baseWardrobePrompt: "colorful kids MV outfit",
        baseVoicePrompt: "bright cheerful singing voice, emotional tone: joyful",
        negativePrompt: "no scary imagery",
        flowCharacterReference: "@Yildiz",
      },
      { visualStyle: "pixar3d", topic: "sayma ve dans" }
    );
    expect(dna.name).toBe("Yildiz");
    expect(dna.imagePrompt.length).toBeGreaterThanOrEqual(20);
    expect(dna.personality.length).toBeGreaterThan(0);
    expect(dna.loves).toContain("sayma");
  });
});

describe("Sarki baslik poster adi", () => {
  const sample = { english: "Soap Cloud Parade", turkish: "Kopuk Bulutu" };

  it("Turkce soz dilinde Turkce poster adi secer", () => {
    expect(pickSongPosterTitle(sample, "Turkish")).toBe("Kopuk Bulutu");
    expect(pickSongPosterTitle(sample, "turkce")).toBe("Kopuk Bulutu");
  });

  it("Ingilizce soz dilinde Ingilizce poster adi secer", () => {
    expect(pickSongPosterTitle(sample, "English")).toBe("Soap Cloud Parade");
  });

  it("secili basligi TR veya EN eslesmesiyle tanir", () => {
    expect(songTitleIsSelected(sample, "Kopuk Bulutu")).toBe(true);
    expect(songTitleIsSelected(sample, "Soap Cloud Parade")).toBe(true);
    expect(songTitleIsSelected(sample, "Baska")).toBe(false);
  });
});

describe("Sablon etiketleri", () => {
  it("uc sablonu ayirir", () => {
    expect(templateLabel("kids_song")).toBe("Cocuk Sarki Klibi");
    expect(isKidsSong("kids_song")).toBe(true);
    expect(isKidsContent("kids_song")).toBe(true);
    expect(isKidsContent("narrator")).toBe(false);
    expect(emptyClipsHint("kids_song")).toContain("sarkiyi");
  });
});
