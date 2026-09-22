import { describe, expect, it } from "vitest";
import { buildClipPrompt, defaultStyleFor, VISUAL_STYLE_PRESETS } from "@/server/services/prompt-builder";

const baseProject = {
  templateType: "narrator",
  speechLanguage: "Türkçe",
  promptTemplate: "",
  useFlowCharacter: false,
  aspectRatio: "16:9",
  visualStyle: "",
  allowSubtitles: false,
  emotionCurve: "",
  clipSeconds: 8,
  useReference: true,
};

const baseCharacter = {
  baseAppearancePrompt: "A 20-year-old adult German woman with long blonde hair.",
  baseWardrobePrompt: "modern stylish outfit",
  baseEnvironmentPrompt: "modern living room. She is sitting on a sofa. Lighting: soft warm light",
  baseCameraPrompt: "Fixed tripod camera. Medium close-up.",
  baseVoicePrompt: "calm warm female voice",
  negativePrompt: "no jewelry",
  flowCharacterReference: "@Lena",
};

const baseClip = {
  dialogue: 'Merhaba. Bugun "tuhaf" bir sey anlatacagim.',
  index: 1,
  sceneDescription: "",
  voiceTone: "",
  imagePrompt: "",
  emotionLabel: "",
};

describe("Prompt olusturma", () => {
  it("diyalogu aynen icerir (cift tirnaklar tek tirnaga cevrilir)", () => {
    const prompt = buildClipPrompt({ project: baseProject, character: baseCharacter, clip: baseClip, isFirstClip: true });
    expect(prompt).toContain("Merhaba. Bugun 'tuhaf' bir sey anlatacagim.");
  });

  it("karakter kilidi metinlerini icerir", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, templateType: "kids_animation" },
      character: {
        ...baseCharacter,
        baseAppearancePrompt: "Tiny puff-sheep hero with long blonde hair.",
        baseWardrobePrompt: "modern stylish outfit",
        baseCameraPrompt: "Fixed tripod camera. Medium close-up.",
      },
      clip: baseClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("long blonde hair");
    expect(prompt).toContain("modern stylish outfit");
  });

  it("ilk klipte 'onceki klip' referansi olmaz, sonraki kliplerde film surekliligi olur", () => {
    const first = buildClipPrompt({ project: baseProject, character: baseCharacter, clip: baseClip, isFirstClip: true });
    const second = buildClipPrompt({
      project: baseProject,
      character: baseCharacter,
      clip: { ...baseClip, index: 2, sceneDescription: "A wet street at night" },
      isFirstClip: false,
      previousClip: { ...baseClip, index: 1, sceneDescription: "A doorway in the rain" },
    });
    expect(first).not.toContain("MATCH-ON-ACTION");
    expect(first).toContain("Opening cinema take");
    expect(second).toContain("MATCH-ON-ACTION");
    expect(second).not.toContain("same room, chair, background");
  });

  it("konusma dilini prompta yazar", () => {
    const prompt = buildClipPrompt({ project: baseProject, character: baseCharacter, clip: baseClip, isFirstClip: true });
    expect(prompt).toContain("Türkçe");
  });

  it("Flow karakter referansi acikken @ad ile baslar", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, templateType: "kids_animation", useFlowCharacter: true },
      character: {
        ...baseCharacter,
        baseAppearancePrompt: "Tiny puff-sheep hero",
        flowCharacterReference: "@Lena",
      },
      clip: baseClip,
      isFirstClip: true,
    });
    expect(prompt.startsWith("@Lena")).toBe(true);
  });

  it("anlatici film kliplerinde anlatıcı @ referansi prompta girmez", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, useFlowCharacter: true },
      character: baseCharacter,
      clip: { ...baseClip, sceneDescription: "A kitchen at night, broken plate on the floor" },
      isFirstClip: true,
    });
    expect(prompt).not.toMatch(/^@Lena/);
    expect(prompt).toContain("narrator woman is NOT in this shot");
    expect(prompt).toContain("broken plate");
  });

  it("kameradaki anlatici cekiminde ana karakter @ referansi kullanilir", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, useFlowCharacter: true },
      character: baseCharacter,
      clip: { ...baseClip, shotType: "narrator", sceneDescription: "Lived-in kitchen confession" },
      isFirstClip: true,
    });
    expect(prompt.startsWith("@Lena")).toBe(true);
    expect(prompt).toContain("NARRATOR ON CAMERA");
    expect(prompt).toContain("FEATURE-FILM DRAMA LOOK");
    expect(prompt).not.toContain("A female narrator voice-over");
  });

  it("useFlowCharacter kapaliyken yan karakter @ etiketleri prompta girmez (kahraman ezilmesin)", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, templateType: "kids_animation", useFlowCharacter: false },
      character: {
        ...baseCharacter,
        baseAppearancePrompt: "Tiny puff-sheep hero Kırpık",
        flowCharacterReference: "@Kırpık",
      },
      clip: {
        ...baseClip,
        dialogue: "Rota buradan kıvrılıyor.",
        sceneDescription: "Marina brifing. [Kadro: Kırpık, Ada, Rüzgar]",
        imagePrompt: "Kirpik on yacht deck with Ada",
      },
      supportingCast: [
        {
          name: "Ada",
          role: "side",
          storyRole: "arkadas",
          baseAppearancePrompt: "girl in wetsuit",
          baseWardrobePrompt: "mustard jacket",
          flowCharacterReference: "@Ada",
        },
        {
          name: "Rüzgar",
          role: "side",
          storyRole: "arkadas",
          baseAppearancePrompt: "boy in rash guard",
          baseWardrobePrompt: "lime shirt",
          flowCharacterReference: "@Rüzgar",
        },
      ],
      isFirstClip: true,
    });
    expect(prompt.startsWith("@Ada")).toBe(false);
    expect(prompt.startsWith("@Rüzgar")).toBe(false);
    expect(prompt).not.toMatch(/^@Ada/m);
    expect(prompt).not.toContain("@Ada also appears");
    expect(prompt).toContain("HERO VISIBILITY LOCK");
    expect(prompt).toContain("Tiny puff-sheep hero");
  });

  it("sinema anlatici klibine duygu + hareket yonergesi yazar (durgun video olmasin)", () => {
    const prompt = buildClipPrompt({
      project: baseProject,
      character: baseCharacter,
      clip: {
        ...baseClip,
        index: 3,
        sceneDescription: "Mert steps closer in the hallway; Elif freezes at the door frame",
        emotionLabel: "bastirilmis arzu / gerilim",
        voiceTone: "kisik, nefesi tutulmus",
      },
      isFirstClip: false,
      previousClip: { ...baseClip, index: 2, emotionLabel: "kiskanclik", voiceTone: "" },
    });
    expect(prompt).toContain("[PERFORMANCE — EMOTION IS MANDATORY]");
    expect(prompt).toContain("bastirilmis arzu / gerilim");
    expect(prompt).toContain("kisik, nefesi tutulmus");
    expect(prompt).toContain("Emotional hangover from the previous take: kiskanclik");
    expect(prompt).toContain("MOVEMENT EVERY SECOND");
    expect(prompt).toContain("no nudity, no sexual act");
  });

  it("anlatici promptu eski bloklari korur ve tam mekan katmanini ekler", () => {
    const prompt = buildClipPrompt({
      project: baseProject,
      character: baseCharacter,
      clip: {
        ...baseClip,
        sceneDescription: "Elif at the open street door",
        emotionLabel: "hasret",
        imagePrompt: [
          "[SHOT] Elif at the open street door",
          "[CAMERA] slow push-in",
          "[SETTING] threshold",
          "[ENVIRONMENT] Worn stairwell, terrazzo steps, rain visible through the street door.",
          "[BACKGROUND LAYERS] Foreground door frame, mid wet sidewalk, distant lit windows.",
          "[SET DRESSING] Rusted mailboxes, dripping umbrella.",
          "[ATMOSPHERE] Cold rain mist under sodium street light.",
        ].join("\n"),
      },
      isFirstClip: true,
    });
    expect(prompt).toContain("[STYLE]");
    expect(prompt).toContain("[SHOT]");
    expect(prompt).toContain("[WHO IS ON SCREEN]");
    expect(prompt).toContain("[SCENE CONTINUITY]");
    expect(prompt).toContain("[CAMERA]");
    expect(prompt).toContain("[PERFORMANCE — EMOTION IS MANDATORY]");
    expect(prompt).toContain("[AUDIO]");
    expect(prompt).toContain("[WORLD — FULL LOCATION]");
    expect(prompt).toContain("ADDED PRODUCTION-DESIGN LAYER");
    expect(prompt).toContain("terrazzo steps");
    expect(prompt).toContain("Foreground door frame");
    const continuityAt = prompt.indexOf("\n[SCENE CONTINUITY]");
    const worldAt = prompt.indexOf("\n[WORLD — FULL LOCATION]");
    expect(continuityAt).toBeGreaterThan(-1);
    expect(worldAt).toBeGreaterThan(continuityAt);
  });

  it("duygu etiketi yoksa da notr sahne yasagini yazar", () => {
    const prompt = buildClipPrompt({
      project: baseProject,
      character: baseCharacter,
      clip: { ...baseClip, sceneDescription: "A wet street at night" },
      isFirstClip: true,
    });
    expect(prompt).toContain("play its real emotion");
    expect(prompt).toContain("frozen tableau is FORBIDDEN");
  });

  it("useFlowCharacter acikken once ana kahraman @ sonra yan kadro", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, templateType: "kids_animation", useFlowCharacter: true },
      character: { ...baseCharacter, flowCharacterReference: "@Kırpık" },
      clip: baseClip,
      supportingCast: [
        {
          name: "Ada",
          role: "side",
          storyRole: "arkadas",
          baseAppearancePrompt: "girl",
          baseWardrobePrompt: "jacket",
          flowCharacterReference: "@Ada",
        },
      ],
      isFirstClip: true,
    });
    expect(prompt.startsWith("@Kırpık\n@Ada")).toBe(true);
  });

  it("ozel sablon degiskenleri isler ve eksik kilitleri ekler", () => {
    const prompt = buildClipPrompt({
      project: {
        ...baseProject,
        templateType: "kids_animation",
        promptTemplate: "DIL: {{LANGUAGE}}\nSOZ: {{DIALOGUE}}",
      },
      character: baseCharacter,
      clip: baseClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("DIL: Türkçe\nSOZ: Merhaba. Bugun 'tuhaf' bir sey anlatacagim.");
    expect(prompt).toContain("[SPEECH / LYRIC LOCK]");
    expect(prompt).toContain("SPEECH FIDELITY — NON-NEGOTIABLE");
    expect(prompt).toContain("[ON-SCREEN TEXT]");
    expect(prompt).toContain("HARD BAN — NO TEXT IN FRAME");
    expect(prompt).toContain("[FINAL HARD LOCK — ON-SCREEN TEXT]");
  });

  it("anlatici talking-head ozel sablonunu yok sayar", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, promptTemplate: "SADECE: {{DIALOGUE}}" },
      character: baseCharacter,
      clip: { ...baseClip, sceneDescription: "A dim kitchen, broken plate on tile" },
      isFirstClip: true,
    });
    expect(prompt).toContain("voice-over");
    expect(prompt).toContain("broken plate");
    expect(prompt).not.toBe("SADECE: Merhaba. Bugun 'tuhaf' bir sey anlatacagim.");
  });

  it("kisitlama blogunu her zaman icerir (varsayilan sablon)", () => {
    const prompt = buildClipPrompt({ project: baseProject, character: baseCharacter, clip: baseClip, isFirstClip: true });
    expect(prompt).toContain("Do not add, remove, paraphrase or translate the narration.");
    expect(prompt).toContain("Pace the exact narration across the FULL clip");
    expect(prompt).toContain("SPEECH PACING LOCK — 8s CLIP");
  });
});

describe("Gorsel stil secenegi", () => {
  it("anlatici sablonunda varsayilan stil gercekci canli cekimdir", () => {
    const prompt = buildClipPrompt({ project: baseProject, character: baseCharacter, clip: baseClip, isFirstClip: true });
    expect(prompt).toContain("Photorealistic LIVE-ACTION footage");
  });

  it("cocuk sablonunda varsayilan stil 3D Pixar tarzidir", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, templateType: "kids_animation" },
      character: baseCharacter,
      clip: baseClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("Feature-quality theatrical 3D CGI animation");
    expect(prompt).toContain("subsurface scattering");
  });

  it("on ayar kimligi kaydedildiyse tarife cevrilir", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, visualStyle: "anime" },
      character: baseCharacter,
      clip: baseClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("2D anime style");
    expect(prompt).not.toContain("Photorealistic live-action");
  });

  it("serbest metin stil aynen kullanilir", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, visualStyle: "Gritty handheld found-footage look" },
      character: baseCharacter,
      clip: baseClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("Gritty handheld found-footage look");
  });

  it("defaultStyleFor sablon turune gore dogru on ayari verir", () => {
    expect(defaultStyleFor("narrator")).toBe(VISUAL_STYLE_PRESETS.find((p) => p.id === "photorealistic")!.prompt);
    expect(defaultStyleFor("kids_animation")).toBe(VISUAL_STYLE_PRESETS.find((p) => p.id === "pixar3d")!.prompt);
    expect(defaultStyleFor("kids_song")).toBe(VISUAL_STYLE_PRESETS.find((p) => p.id === "pixar3d")!.prompt);
  });
});

describe("Altyazi secenegi", () => {
  it("kapaliyken her turlu ekran yazisini guclu dille yasaklar (varsayilan)", () => {
    const prompt = buildClipPrompt({ project: baseProject, character: baseCharacter, clip: baseClip, isFirstClip: true });
    expect(prompt).toContain("[ON-SCREEN TEXT]");
    expect(prompt).toContain("HARD BAN — NO TEXT IN FRAME");
    expect(prompt).toContain("no subtitles");
    expect(prompt).toContain("karaoke");
    expect(prompt).toContain("[FINAL HARD LOCK — ON-SCREEN TEXT]");
    expect(prompt).toContain("Negative constraints: no subtitles");
    expect(prompt).not.toContain("REQUIRED: burn clean");
  });

  it("allowSubtitles acik olsa bile gomulu altyazi istemez (dikey/yatay)", () => {
    const prompt = buildClipPrompt({
      project: { ...baseProject, allowSubtitles: true, aspectRatio: "16:9" },
      character: baseCharacter,
      clip: baseClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("HARD BAN — NO TEXT IN FRAME");
    expect(prompt).toContain("[FINAL HARD LOCK — ON-SCREEN TEXT]");
    expect(prompt).toContain("9:16");
    expect(prompt).toContain("16:9");
    expect(prompt).not.toContain("REQUIRED: burn clean");
  });

  it("uc sablonda da ekran yazisi yasaktir (ayar acik olsa bile)", () => {
    for (const templateType of ["narrator", "kids_animation", "kids_song"] as const) {
      const off = buildClipPrompt({
        project: { ...baseProject, templateType, aspectRatio: "9:16" },
        character: baseCharacter,
        clip: baseClip,
        isFirstClip: true,
      });
      expect(off).toContain("HARD BAN — NO TEXT IN FRAME");
      expect(off).toContain("[ON-SCREEN TEXT]");
      expect(off).toContain("[FINAL HARD LOCK — ON-SCREEN TEXT]");

      const on = buildClipPrompt({
        project: { ...baseProject, templateType, allowSubtitles: true, aspectRatio: "16:9" },
        character: baseCharacter,
        clip: baseClip,
        isFirstClip: true,
      });
      expect(on).toContain("HARD BAN — NO TEXT IN FRAME");
      expect(on).toContain("[NO ON-SCREEN TEXT — NON-NEGOTIABLE]");
      expect(on).toContain("first scene through last scene");
      expect(on).not.toContain("REQUIRED: burn clean");
    }
  });

  it("soz/sarki sadakati uc sablonda da zorunlu", () => {
    const narrator = buildClipPrompt({ project: baseProject, character: baseCharacter, clip: baseClip, isFirstClip: true });
    expect(narrator).toContain("NARRATION FIDELITY — NON-NEGOTIABLE");
    expect(narrator).toContain("word for word");
    expect(narrator).toContain("STORY-WORD VISUAL LOCK");

    const kids = buildClipPrompt({
      project: { ...baseProject, templateType: "kids_animation" },
      character: baseCharacter,
      clip: baseClip,
      isFirstClip: true,
    });
    expect(kids).toContain("SPEECH FIDELITY — NON-NEGOTIABLE");
    expect(kids).toContain("accurate syllable-sync");
    expect(kids).toContain("SPEECH PACING LOCK — 8s CLIP");
    expect(kids).toContain("first 3-5 seconds");

    const song = buildClipPrompt({
      project: { ...baseProject, templateType: "kids_song" },
      character: baseCharacter,
      clip: { ...baseClip, dialogue: "Alkış yap, merhaba!" },
      isFirstClip: true,
    });
    expect(song).toContain("LYRIC/AUDIO FIDELITY — NON-NEGOTIABLE");
    expect(song).toContain("true syllable-sync");
    expect(song).toContain("lyric-to-audio fidelity");
  });
});

describe("Cocuk sarki klibi promptu", () => {
  const songProject = { ...baseProject, templateType: "kids_song" };
  const songClip = {
    dialogue: "Alkış yap, alkış yap, merhaba!",
    index: 1,
    sceneDescription: "CHORUS · alkis ve ziplama. Parlak cimenlik.",
    voiceTone: "bright and bouncy, smiling tone",
    emotionLabel: "neseli",
    imagePrompt:
      "3D Pixar-style animation music video still of a fox clapping in a sunny meadow. Lighting: warm key light. Camera: medium shot, 50mm.",
  };

  it("sozlerin soylenmesini ister, konusulmasini degil", () => {
    const prompt = buildClipPrompt({
      project: songProject,
      character: baseCharacter,
      clip: songClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("SINGS");
    expect(prompt).toContain("Alkış yap, alkış yap, merhaba!");
    expect(prompt).toContain("they must be SUNG");
    expect(prompt).not.toContain("Do not add background music");
  });

  it("sozdeki nesne/sayiyi kadroya kilitler (bos havaya sayma yasak)", () => {
    const prompt = buildClipPrompt({
      project: songProject,
      character: baseCharacter,
      clip: {
        ...songClip,
        dialogue: "Kaç vagon saydın? Bir, iki, üç!",
        imagePrompt:
          "3D Pixar still of a zebra pointing at three wooden toy train wagons. MUST BE VISIBLE: exactly 3 wagons.",
      },
      isFirstClip: true,
    });
    expect(prompt).toContain("LYRIC VISUAL LOCK");
    expect(prompt).toContain("Kaç vagon saydın? Bir, iki, üç!");
    expect(prompt).toContain("never mime counting empty air");
    expect(prompt).toContain("physically visible");
  });

  it("secilen gorsel stile UYAR (canli cekim artik 3D'ye cevrilmez)", () => {
    // Eskiden cocuk sablonunda canli-cekim secimi sessizce 3D'ye cevriliyordu;
    // kullanicinin secimi uretimde gecersiz kaliyordu. Artik secilen aile
    // dunyanin tamamini baglar.
    const live = buildClipPrompt({
      project: { ...songProject, visualStyle: "cinematic" },
      character: baseCharacter,
      clip: songClip,
      isFirstClip: true,
    });
    expect(live).toContain("WORLD FAMILY LOCK — 100% LIVE-ACTION");
    expect(live).not.toContain("WORLD FAMILY LOCK — 100% STYLIZED 3D");
    expect(live).not.toContain("ukulele");
    expect(live).not.toContain("glockenspiel");

    const cgi = buildClipPrompt({
      project: { ...songProject, visualStyle: "pixar3d" },
      character: baseCharacter,
      clip: songClip,
      isFirstClip: true,
    });
    expect(cgi).toContain("WORLD FAMILY LOCK — 100% STYLIZED 3D ANIMATION");
    expect(cgi).not.toContain("WORLD FAMILY LOCK — 100% LIVE-ACTION");
  });

  it("oyunculuk, ikincil hareket ve dize tonu prompta girer", () => {
    const prompt = buildClipPrompt({
      project: songProject,
      character: baseCharacter,
      clip: songClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("Viseme timing matches every syllable");
    expect(prompt).toContain("Body stays ALIVE on the audible beat");
    expect(prompt).toContain("living background");
    expect(prompt).toContain("Delivery ENERGY only for this line (same singer): sung bright and bouncy, smiling tone");
    expect(prompt).toContain("Only this one singer");
    expect(prompt).toContain("SINGER VOICE IDENTITY LOCK");
    expect(prompt).toContain("LOCOMOTION LOCK");
    expect(prompt).toContain("ULTRA MUSIC-VIDEO PRODUCTION LOCK");
    expect(prompt).toContain("[MV CRAFT]");
    expect(prompt).toContain("LYRIC ↔ CLIP ↔ VIDEO SYNC LOCK");
    expect(prompt).toContain("LYRIC DRIVES PICTURE");
    expect(prompt).toContain("CHARACTER FIDELITY LOCK");
    expect(prompt).toContain("[CHARACTER FIDELITY — EVERY CLIP]");
    expect(prompt).toContain("[IDENTITY LOCK — MAXIMUM CHARACTER CONSISTENCY — EVERY CLIP]");
  });

  it("Ingilizce sahne notunu kullanir, Turkce koreografiyi prompta dokmez", () => {
    const prompt = buildClipPrompt({
      project: songProject,
      character: baseCharacter,
      clip: songClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("sunny meadow");
    expect(prompt).not.toContain("alkis ve ziplama");
  });

  it("sonraki kliplerde kanepe/oda kilidi yerine seri MV devamı kullanir", () => {
    const prompt = buildClipPrompt({
      project: songProject,
      character: baseCharacter,
      clip: { ...songClip, index: 2 },
      isFirstClip: false,
      previousClip: {
        ...songClip,
        index: 1,
        dialogue: "Onceki nakarat satiri",
        sceneDescription: "CHORUS · onceki sahne",
      },
    });
    expect(prompt).not.toContain("same room, chair, background");
    expect(prompt).toContain("SERIAL FAMILY MUSIC-VIDEO CONTINUITY");
    expect(prompt).toContain("DIRECT CONTINUATION / MATCH-ON-ACTION");
    expect(prompt).toContain("identical singing voice");
    expect(prompt).toContain("NO sliding");
  });

  it("altyazi kapaliyken ekran yazisini yasaklar", () => {
    const prompt = buildClipPrompt({
      project: songProject,
      character: baseCharacter,
      clip: songClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("HARD BAN — NO TEXT IN FRAME");
    expect(prompt).toContain("no subtitles");
    expect(prompt).toContain("[SABIT KURAL — ALTYAZI YOK]");
    expect(prompt).toContain("[SABIT KURAL SONU — ALTYAZI YOK]");
  });

  it("1. ve 1000. klip ayni altyazi yasagini tasir", () => {
    const first = buildClipPrompt({
      project: baseProject,
      character: baseCharacter,
      clip: { ...baseClip, index: 1 },
      isFirstClip: true,
    });
    const last = buildClipPrompt({
      project: baseProject,
      character: baseCharacter,
      clip: { ...baseClip, index: 1000, sceneDescription: "A hallway at night" },
      isFirstClip: false,
      previousClip: { ...baseClip, index: 999, sceneDescription: "A doorway" },
    });
    expect(first).toContain("[SABIT KURAL — ALTYAZI YOK]");
    expect(last).toContain("[SABIT KURAL — ALTYAZI YOK]");
    expect(first).toContain("clip 1 and clip 1000 get the same ban");
    expect(last).toContain("clip 1 and clip 1000 get the same ban");
    expect(first).toContain("[SABIT KURAL SONU — ALTYAZI YOK]");
    expect(last).toContain("[SABIT KURAL SONU — ALTYAZI YOK]");
  });

  it("ilk sarki klibi yayin-guvenli mascot kilidi tasir, toddler/kiss dili yok", () => {
    const prompt = buildClipPrompt({
      project: songProject,
      character: baseCharacter,
      clip: songClip,
      isFirstClip: true,
    });
    expect(prompt).toContain("[CAST LOCK — ANIMATED MASCOT]");
    expect(prompt).toMatch(/cartoon mascot/i);
    expect(prompt).not.toMatch(/\bchild\b|\bminor\b/i);
    expect(prompt).not.toMatch(/\btoddler/i);
    expect(prompt).not.toMatch(/\bkiss\b/i);
    expect(prompt).not.toMatch(/age-swap/i);
  });
});
