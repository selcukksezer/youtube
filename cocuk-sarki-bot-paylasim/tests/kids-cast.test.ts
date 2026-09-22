import { describe, expect, it } from "vitest";
import {
  composeKidsScenePrompt,
  formatKidsCastLine,
  matchCharactersByNames,
  parseKidsCastLine,
} from "@/server/services/kids";
import { buildClipPrompt } from "@/server/services/prompt-builder";

describe("Cocuk animasyonu sabit kadro", () => {
  it("Kadro satirini yazar ve okur", () => {
    expect(formatKidsCastLine(["Sunny", "Mavi"])).toBe("[Kadro: Sunny, Mavi]");
    expect(parseKidsCastLine("Bahcede arama\n[Kadro: Sunny, Mavi]")).toEqual(["Sunny", "Mavi"]);
    expect(parseKidsCastLine("Kadro yok")).toEqual([]);
  });

  it("isimleri buyuk/kucuk harf ve kismi eslesmeyle bulur", () => {
    const roster = [
      { id: "1", name: "Sunny", role: "main" },
      { id: "2", name: "Mavi Kus", role: "side" },
      { id: "3", name: "Topo", role: "side" },
    ];
    expect(matchCharactersByNames(["sunny", "Topo"], roster).map((p) => p.name)).toEqual(["Sunny", "Topo"]);
    expect(matchCharactersByNames(["Mavi"], roster).map((p) => p.name)).toEqual(["Mavi Kus"]);
  });

  it("composeKidsScenePrompt cast kilidini ekler", () => {
    const shot = composeKidsScenePrompt(
      {
        index: 1,
        description: "Iki arkadas",
        emotion: "neseli",
        imagePrompt: "3D Pixar-style cinematic animation shot of two friends",
        charactersInScene: ["Sunny", "Topo"],
        hookNote: "Ne olacak?",
        environment: "sunny meadow",
        lighting: "warm key",
        cameraShot: "medium two-shot 35mm",
        motionDetail: "grass sway",
        blocking: "they walk side by side",
        secondBySecond: "0-1s: Sunny and Topo enter; 1-2s: glance; 2-3s: smile; 3-4s: step; 4-5s: point; 5-6s: nod; 6-7s: jog; 7-8s: reach hillcrest",
      },
      "Sunny (hero): orange fox | Topo (friend): blue mole",
      8
    );
    expect(shot).toContain("On-screen cast locked");
    expect(shot).toContain("Sunny (hero): orange fox");
    expect(shot).toContain("Topo (friend): blue mole");
    expect(shot).toContain("Second-by-second action");
  });

  it("Flow promptu yan kadroyu kilitleyerek yazar", () => {
    const prompt = buildClipPrompt({
      project: {
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
      },
      character: {
        name: "Sunny",
        baseAppearancePrompt: "A soft orange fox cub with big eyes.",
        baseWardrobePrompt: "blue scarf",
        baseEnvironmentPrompt: "",
        baseCameraPrompt: "",
        baseVoicePrompt: "warm",
        negativePrompt: "no scary imagery",
        flowCharacterReference: "",
      },
      clip: {
        dialogue: "Hadi Topo, birlikte bakalim!",
        index: 2,
        sceneDescription: "Arama\n[Kadro: Sunny, Topo]",
        voiceTone: "excited",
        emotionLabel: "heyecanli",
        imagePrompt:
          "3D Pixar-style cinematic animation shot of fox and mole searching. Second-by-second action (8s continuous take):\n0-1s: Sunny and Topo enter; 7-8s: they point ahead",
      },
      supportingCast: [
        {
          name: "Sunny",
          role: "main",
          storyRole: "kahraman",
          baseAppearancePrompt: "A soft orange fox cub with big eyes.",
          baseWardrobePrompt: "blue scarf",
          flowCharacterReference: "",
        },
        {
          name: "Topo",
          role: "side",
          storyRole: "en iyi arkadas",
          baseAppearancePrompt: "A round blue mole with round glasses.",
          baseWardrobePrompt: "yellow vest",
          flowCharacterReference: "@Topo",
        },
      ],
      isFirstClip: false,
    });
    expect(prompt).toContain("Match the supplied character reference image(s) for the HERO");
    expect(prompt).toContain("EVEN WITH reference");
    expect(prompt).toContain("LOCOMOTION LOCK");
    expect(prompt).toContain("[IDENTITY LOCK — MAXIMUM CHARACTER CONSISTENCY]");
    expect(prompt).toContain("EVEN WITH references present");
    expect(prompt).not.toContain("@Topo also appears");
    expect(prompt).toContain("Topo (en iyi arkadas)");
    expect(prompt).toContain("yellow vest");
    expect(prompt).toContain("Do not redesign");
    expect(prompt).toContain("On-screen cast this take (LOCKED identities");
    expect(prompt).toContain("Sunny, Topo");
    // Ana kahraman supportingCast dongusunde tekrarlanmaz
    expect(prompt.match(/Also on screen with EXACT locked identity/g)?.length ?? 0).toBe(1);
    // useFlowCharacter kapaliyken yan kadro @ref'i kahramani ezmesin
    expect(prompt.startsWith("@Topo")).toBe(false);
  });
});
