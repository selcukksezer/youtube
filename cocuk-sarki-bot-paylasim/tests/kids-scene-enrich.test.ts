import { describe, expect, it } from "vitest";
import {
  applyDialoguePerformanceToImagePrompt,
  buildStoryWordVisualLock,
  composeKidsScenePrompt,
  composeSoloIntroOpeningPrompt,
  enrichKidsScene,
  extractKidsTimelineTail,
  extractStoryContentWords,
  formatKidsPreviousBridge,
  KIDS_SCENE_NO_TEXT_PHRASE,
  kidsTimelineCoversDuration,
} from "@/server/services/kids";
import { buildClipPrompt } from "@/server/services/prompt-builder";

describe("Uzun film sahne prompt zenginlestirme", () => {
  it("timeline kuyrugunu ve onceki kopru blogunu cikarir", () => {
    const timeline =
      "0-1s: steps; 1-2s: grips; 6-7s: hand on rope; 7-8s: leans into pull";
    expect(extractKidsTimelineTail(timeline, 2)).toContain("7-8s: leans into pull");
    expect(extractKidsTimelineTail(timeline, 2)).toContain("6-7s: hand on rope");
    const bridge = formatKidsPreviousBridge({
      index: 5,
      description: "Ip gerilir",
      emotion: "gergin",
      environment: "icy ledge with orange rope",
      hookNote: "Sonraki basamak",
      secondBySecond: timeline,
    });
    expect(bridge).toContain("prev clip #5");
    expect(bridge).toContain("match-on-action");
    expect(bridge).toContain("leans into pull");
  });

  it("eksik alanlari doldurur ve altyazi yasagini imagePrompt'a ekler", () => {
    const enriched = enrichKidsScene(
      {
        index: 37,
        description: "Ip gerilir, Sunny nefes nefese tutunur",
        emotion: "",
        imagePrompt: "fox holds orange rope on icy ledge",
        charactersInScene: ["Sunny"],
        hookNote: "",
        environment: "",
        lighting: "",
        cameraShot: "",
        motionDetail: "",
        blocking: "",
        secondBySecond: "",
      },
      8
    );

    expect(enriched.emotion).toBe("merakli");
    expect(enriched.imagePrompt).toMatch(/^3D Pixar-style cinematic animation shot/i);
    expect(enriched.imagePrompt).toContain(KIDS_SCENE_NO_TEXT_PHRASE);
    expect(enriched.environment.length).toBeGreaterThan(20);
    expect(enriched.lighting.length).toBeGreaterThan(10);
    expect(enriched.cameraShot.length).toBeGreaterThan(10);
    expect(enriched.blocking.length).toBeGreaterThan(10);
    expect(enriched.motionDetail.length).toBeGreaterThan(10);
    expect(kidsTimelineCoversDuration(enriched.secondBySecond, 8)).toBe(true);
    expect(enriched.secondBySecond).toContain("0-1s:");
    expect(enriched.secondBySecond).toContain("7-8s:");
  });

  it("composeKidsScenePrompt seyrek sahnelerde bile tum kilitleri yazar", () => {
    const shot = composeKidsScenePrompt(
      {
        index: 42,
        description: "Sonraki kaya basamagi",
        emotion: "gergin",
        imagePrompt: "climber steps up",
        charactersInScene: ["Sunny", "Topo"],
        hookNote: "Tutunabilecek mi?",
        environment: "",
        lighting: "",
        cameraShot: "",
        motionDetail: "",
        blocking: "",
        secondBySecond: "0-1s: steps",
      },
      "Sunny (hero): orange fox",
      8
    );

    expect(shot).toContain("ON-SCREEN TEXT BAN");
    expect(shot).toContain(KIDS_SCENE_NO_TEXT_PHRASE);
    expect(shot).toContain("CHARACTER FIDELITY LOCK");
    expect(shot).toContain("LOCOMOTION & REALISM LOCK");
    expect(shot).toContain("Environment:");
    expect(shot).toContain("Lighting:");
    expect(shot).toContain("Camera:");
    expect(shot).toContain("Blocking:");
    expect(shot).toContain("Secondary motion:");
    expect(shot).toContain("Second-by-second action");
    expect(shot).toContain("FINAL FRAME CHECK");
    expect(shot).toMatch(/whether the film has 8 or 60 takes|whether 8 or 60/i);  });

  it("Flow promptu cocuk sablonunda allowSubtitles acik olsa bile yazi yasagi yazar", () => {
    const prompt = buildClipPrompt({
      project: {
        templateType: "kids_animation",
        speechLanguage: "Türkçe",
        promptTemplate: "",
        useFlowCharacter: false,
        aspectRatio: "16:9",
        visualStyle: "",
        allowSubtitles: true,
        emotionCurve: "",
        clipSeconds: 8,
        useReference: true,
      },
      character: {
        baseAppearancePrompt: "orange fox",
        baseWardrobePrompt: "blue scarf",
        baseEnvironmentPrompt: "",
        baseCameraPrompt: "",
        baseVoicePrompt: "warm",
        negativePrompt: "",
        flowCharacterReference: "",
      },
      clip: {
        dialogue: "Hadi!",
        index: 50,
        sceneDescription: "Zirve",
        voiceTone: "excited",
        emotionLabel: "coskulu",
        imagePrompt: "3D Pixar-style cinematic animation shot of a fox on a peak",
      },
      isFirstClip: false,
    });

    expect(prompt).toContain("[NO ON-SCREEN TEXT — NON-NEGOTIABLE]");
    expect(prompt).toContain("first scene through last scene");
    expect(prompt).toContain("HARD BAN — NO TEXT IN FRAME");
    expect(prompt).toContain("[FINAL HARD LOCK — ON-SCREEN TEXT]");
    expect(prompt).not.toContain("REQUIRED: burn clean, readable closed captions");
  });

  it("diyalog performans kilidi acilis konusmasini imagePrompt'a yazar ve donuk poz yasagini koyar", () => {
    const withLock = applyDialoguePerformanceToImagePrompt(
      "3D Pixar-style cinematic animation shot. Fox stands on snow.",
      "Merhaba arkadaşlar ben Kırpık bugün dağ tırmanışı yapacağız zorlu ve heyecanlı olacak",
      "enerjik, samimi sunucu",
      8,
      "",
      "Türkçe"
    );
    expect(withLock).toContain("DIALOGUE-PERFORMANCE LOCK");
    expect(withLock).toContain("STORY-WORD VISUAL LOCK");
    expect(withLock).toContain("Merhaba");
    expect(withLock).toContain("Türkçe audio");
    expect(withLock).toContain("INTRO / ADDRESS");
    expect(withLock).toContain("ANTI-FREEZE");
    expect(withLock).toContain("SPEECH PACING");
    expect(withLock).toContain("entire 8s take");
    // yeniden uygulaninca cift kilit birikmesin
    const again = applyDialoguePerformanceToImagePrompt(withLock, "Merhaba tekrar", "neseli", 8, "", "Türkçe");
    expect(again.match(/DIALOGUE-PERFORMANCE LOCK/g)?.length).toBe(1);
    expect(again.match(/STORY-WORD VISUAL LOCK/g)?.length).toBe(1);
  });

  it("konusma dili secimine gore audio kilidi degisir", () => {
    const ar = applyDialoguePerformanceToImagePrompt(
      "3D Pixar-style cinematic animation shot.",
      "مرحبا اصدقائي",
      "enerjik",
      8,
      "",
      "العربية"
    );
    expect(ar).toContain("العربية audio");
    expect(ar).not.toContain("Turkish audio");
  });

  it("hikaye kelimelerini icerik listesine cikarir", () => {
    const words = extractStoryContentWords("Ip gerildi Batu kaski kontrol et ruzgar esti");
    expect(words).toEqual(expect.arrayContaining(["Ip", "gerildi", "Batu", "kaski", "kontrol", "ruzgar", "esti"]));
    expect(words).not.toContain("et");
    const lock = buildStoryWordVisualLock("Ip gerildi!", "Buzlucakta ruzgar", 8);
    expect(lock).toContain("STORY-WORD VISUAL LOCK");
    expect(lock).toContain("Ip");
    expect(lock).toContain("WORD→PICTURE");
  });

  it("solo acilis paneli yan kadroyu ezer ve SOLO kadro yazar", () => {
    const { sceneDescription, imagePrompt } = composeSoloIntroOpeningPrompt({
      heroName: "Kırpık",
      heroLook: "fluffy fox climber",
      dialogue: "Merhaba arkadaşlar ben Kırpık bugün dağ tırmanışı yapacağız",
      clipSeconds: 8,
    });
    expect(sceneDescription).toContain("SOLO");
    expect(sceneDescription).toContain("[Kadro: Kırpık]");
    expect(sceneDescription).not.toMatch(/Tona|Mete|Nima/);
    expect(imagePrompt).toContain("DIALOGUE-PERFORMANCE LOCK");
    expect(imagePrompt).toMatch(/solo|SOLO|no side/i);
  });

  it("Flow promptu acilis diyalogunda konusma performansini on plana alir", () => {
    const prompt = buildClipPrompt({
      project: {
        templateType: "kids_animation",
        speechLanguage: "Türkçe",
        promptTemplate: "",
        allowSubtitles: false,
        useFlowCharacter: false,
        clipSeconds: 8,
        emotionCurve: "{}",
        aspectRatio: "16:9",
        useReference: true,
        visualStyle: "pixar3d",
      },
      character: {
        name: "Kırpık",
        baseAppearancePrompt: "orange fox",
        baseWardrobePrompt: "climbing gear",
        baseEnvironmentPrompt: "",
        baseCameraPrompt: "",
        baseVoicePrompt: "",
        negativePrompt: "",
        flowCharacterReference: "",
      },
      clip: {
        dialogue:
          "Merhaba arkadaşlar ben Kırpık bugün arkadaşlarımızla birlikte dağ tırmanışı yapacağız",
        index: 1,
        sceneDescription: "Kırpık kameraya hitap eder",
        voiceTone: "samimi, enerjik",
        emotionLabel: "heyecanli",
        imagePrompt: "3D Pixar-style cinematic animation shot. Fox waves.",
      },
      isFirstClip: true,
    });

    expect(prompt).toContain("SPEAKING PERFORMANCE LOCK");
    expect(prompt).toContain("INTRO/ADDRESS");
    expect(prompt).toMatch(/never a frozen establishing portrait|ALIVE on camera/i);
    expect(prompt).toContain("STORY WORD → PICTURE LOCK");
    expect(prompt).toContain("STORY-WORD VISUAL LOCK");
    expect(prompt).toContain("MAXIMUM CLIP QUALITY");
  });
});
