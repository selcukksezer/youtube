import { describe, expect, it } from "vitest";
import {
  inferKidsLocationMedium,
  kidsMediumPhysicsLock,
  composeKidsScenePrompt,
  type KidsScene,
} from "@/server/services/kids";

describe("Kids dunya medyumu / film gercekciligi", () => {
  it("yat/marina metnini DECK olarak tanir", () => {
    expect(inferKidsLocationMedium("On the yacht cockpit at the marina, Kirpik points at the logbook")).toBe("DECK");
  });

  it("sualti metnini UNDERWATER olarak tanir", () => {
    expect(inferKidsLocationMedium("Underwater near the portal, bubbles rise past the dive mask")).toBe("UNDERWATER");
  });

  it("guverte fizigi yuzmeyi yasaklar", () => {
    const lock = kidsMediumPhysicsLock("DECK");
    expect(lock).toMatch(/NO swimming/i);
    expect(lock).toMatch(/DECK/);
  });

  it("composeKidsScenePrompt medyum kilidi ve film craft ekler", () => {
    const scene: KidsScene = {
      index: 2,
      description: "Onceki guverte brifinginden devam: Kırpık palamara uzanır",
      emotion: "odakli",
      imagePrompt: "3D Pixar-style cinematic animation shot. On the yacht deck Kirpik reaches for a cleat.",
      charactersInScene: ["Kırpık"],
      hookNote: "devam",
      environment: "[DECK] Yacht cockpit, teak table, marina masts",
      lighting: "golden morning",
      cameraShot: "medium 35mm",
      blocking: "Kirpik plants hooves on non-skid deck",
      motionDetail: "halyard ticks, water glitter",
      secondBySecond: "0-1s: hoof on cleat; 1-2s: pulls line; 2-3s: nods; 3-4s: breath; 4-5s: glance; 5-6s: pull; 6-7s: hold; 7-8s: ready",
    };
    const prompt = composeKidsScenePrompt(scene, "Kırpık (hero): puff-sheep", 8, "", "prev medium: DECK");
    expect(prompt).toMatch(/WORLD MEDIUM LOCK \[DECK\]/);
    expect(prompt).toMatch(/FEATURE-FILM CRAFT CHECKLIST/);
    expect(prompt).toMatch(/NO swimming/i);
    expect(prompt).not.toMatch(/river raft/i);
  });
});
