import { describe, expect, it } from "vitest";
import { suggestedKidsSceneCount } from "@/components/project/kids-studio-tab";

describe("suggestedKidsSceneCount", () => {
  it("hedef sure / klip suresinden hesaplar", () => {
    expect(suggestedKidsSceneCount({ targetDurationSeconds: 180, clipSeconds: 8 })).toBe(23);
    expect(suggestedKidsSceneCount({ targetDurationSeconds: 60, clipSeconds: 8 })).toBe(8);
  });

  it("4-80 arasinda kirpar", () => {
    expect(suggestedKidsSceneCount({ targetDurationSeconds: 10, clipSeconds: 8 })).toBe(4);
    expect(suggestedKidsSceneCount({ targetDurationSeconds: 600, clipSeconds: 8 })).toBe(75);
    expect(suggestedKidsSceneCount({ targetDurationSeconds: 3600, clipSeconds: 8 })).toBe(80);
  });
});
