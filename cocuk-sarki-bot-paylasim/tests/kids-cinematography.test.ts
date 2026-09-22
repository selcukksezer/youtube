import { describe, expect, it } from "vitest";
import { composeKidsScenePrompt } from "@/server/services/kids";
import { buildClipPrompt } from "@/server/services/prompt-builder";

const kidsProject = {
  templateType: "kids_animation",
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

const kidsCharacter = {
  baseAppearancePrompt: "A soft orange fox cub with big eyes.",
  baseWardrobePrompt: "blue scarf",
  baseEnvironmentPrompt: "Pixar short-film world",
  baseCameraPrompt: "Cinematic kids coverage",
  baseVoicePrompt: "warm child-friendly voice",
  negativePrompt: "no scary imagery",
  flowCharacterReference: "",
};

describe("Cocuk animasyonu sinematografi", () => {
  it("composeKidsScenePrompt kamera/isik/blokaj katmanlarini birlestirir", () => {
    const shot = composeKidsScenePrompt({
      index: 2,
      description: "Tilki bahcede topu arar",
      emotion: "merak",
      imagePrompt: "3D Pixar-style cinematic animation shot of a fox cub searching a garden",
      charactersInScene: ["Sunny"],
      hookNote: "Top nerede?",
      environment: "sunlit backyard with fence depth and flower beds",
      lighting: "warm 4800K key, soft fill, gentle rim",
      cameraShot: "wide establishing, 24mm, low angle, slow push-in",
      motionDetail: "leaves drifting, scarf flutter",
      blocking: "fox steps from left garden path toward the sandbox",
      secondBySecond:
        "0-1s: Sunny peeks past a flower bed; 1-2s: steps onto the path; 2-3s: leans to look under a bucket; 3-4s: lifts the bucket; 4-5s: eyes widen; 5-6s: points ahead; 6-7s: takes two eager steps; 7-8s: freezes mid-reach toward a mystery glow",
    });
    expect(shot).toContain("Environment: sunlit backyard");
    expect(shot).toContain("Lighting: warm 4800K");
    expect(shot).toContain("Camera: wide establishing");
    expect(shot).toContain("Blocking: fox steps");
    expect(shot).toContain("Secondary motion: leaves drifting");
    expect(shot).toContain("Serial continuity lock");
    expect(shot).toContain("Second-by-second action");
    expect(shot).toContain("0-1s: Sunny peeks");
    expect(shot).toContain("Identity lock");
  });

  it("composeKidsScenePrompt onceki klibin son saniyesini mikro-kopru olarak kilitler", () => {
    const shot = composeKidsScenePrompt(
      {
        index: 3,
        description: "Onceki jestten devam: ipi ceker",
        emotion: "kararli",
        imagePrompt: "3D Pixar-style cinematic animation shot fox pulls rope",
        charactersInScene: ["Sunny"],
        hookNote: "Sonraki basamak",
        environment: "icy ledge",
        lighting: "cool key",
        cameraShot: "medium 35mm",
        motionDetail: "spindrift",
        blocking: "pulls rope",
        secondBySecond: "0-1s: continues pull; 7-8s: plants boot",
      },
      "Sunny (hero): orange fox",
      8,
      "",
      "prev clip #2 | LAST 1–2s to CONTINUE (match-on-action into 0–1s): 6-7s: hand on rope; 7-8s: leans into pull"
    );
    expect(shot).toContain("MICRO-BRIDGE / MATCH-ON-ACTION");
    expect(shot).toContain("Carry-over locked:");
    expect(shot).toContain("7-8s: leans into pull");
    expect(shot).toContain("ONE story spine");
  });

  it("Flow promptu ayni oda/kamera kilidi KULLANMAZ; sahne plani ve cesitlilik ister", () => {
    const prompt = buildClipPrompt({
      project: kidsProject,
      character: kidsCharacter,
      clip: {
        dialogue: "Topum nerede acaba?",
        index: 2,
        sceneDescription: "Bahcede arama",
        voiceTone: "curious and hopeful",
        emotionLabel: "merakli",
        imagePrompt:
          "3D Pixar-style cinematic animation shot of a fox. Environment: garden. Camera: wide 24mm low angle. Second-by-second action (8s continuous take):\n0-1s: Sunny enters; 1-2s: looks left; 2-3s: kneels; 3-4s: lifts pot; 4-5s: gasps; 5-6s: points; 6-7s: steps; 7-8s: reaches",
      },
      isFirstClip: false,
    });
    expect(prompt).not.toContain("same room, chair, background");
    expect(prompt).toContain("SERIAL SHORT-FILM CONTINUITY");
    expect(prompt).toContain("ONE STORY SPINE");
    expect(prompt).toContain("DIRECT CONTINUATION");
    expect(prompt).toContain("Feature-film family animation coverage");
    expect(prompt).toContain("Acted theatrical 3D short-film performance");
    expect(prompt).toContain("Environment: garden");
    expect(prompt).toContain("professionally directed");
    expect(prompt).toContain("Follow the Second-by-second action timeline");
    expect(prompt).toContain("Directed continuous 8-second");
    expect(prompt).toContain("MATCH-ON-ACTION");
  });

  it("ilk sahnede film dunyasini kurar", () => {
    const prompt = buildClipPrompt({
      project: kidsProject,
      character: kidsCharacter,
      clip: {
        dialogue: "Merhaba!",
        index: 1,
        sceneDescription: "Acilis",
        voiceTone: "bright",
        emotionLabel: "neseli",
        imagePrompt: "3D Pixar-style cinematic animation shot opening wide on a cozy hill town",
      },
      isFirstClip: true,
    });
    expect(prompt).toContain("Opening beat of the film");
    expect(prompt).toContain("opening wide on a cozy hill town");
    expect(prompt).toContain("Second-by-second staging required");
  });
});
