import { describe, expect, it } from "vitest";
import { LESSON_LIBRARY, lessonPromptBlock, lessonCurveHint, resolveLesson, isCustomLesson, customLessonText, formatCustomLesson } from "@/lib/kids-lessons";

describe("Cocuk animasyonu ders/macera kutuphanesi", () => {
  it("ahlaki ve macera temalari icerir", () => {
    expect(LESSON_LIBRARY.some((l) => l.kind === "moral")).toBe(true);
    expect(LESSON_LIBRARY.some((l) => l.kind === "adventure")).toBe(true);
    expect(LESSON_LIBRARY.find((l) => l.id === "treasure_hunt")?.kind).toBe("adventure");
    expect(LESSON_LIBRARY.find((l) => l.id === "bridge_crossing")?.label).toContain("kopru");
  });

  it("macera temasi prompt blogunda aksiyon yonergesi verir", () => {
    const block = lessonPromptBlock("treasure_hunt");
    expect(block).toContain("MACERA / AKSIYON");
    expect(block).toContain("Hazine");
    expect(block).toContain("siddet");
    expect(lessonCurveHint("treasure_hunt")).toContain("yola cikis");
  });

  it("ahlaki ders blogu dogru etiketlenir", () => {
    const block = lessonPromptBlock("helping");
    expect(block).toContain("AHLAKI DERS");
    expect(block).toContain("Yardimlasma");
    expect(resolveLesson("helping")?.kind).toBe("moral");
  });

  it("ozel tema prompt bloguna yazilir", () => {
    const block = lessonPromptBlock("custom:Everest tirmanisi, gercek rota ve ekipman");
    expect(block).toContain("OZEL TEMA");
    expect(block).toContain("Everest");
    expect(isCustomLesson("custom:Everest")).toBe(true);
    expect(customLessonText("custom:Everest tirmanisi")).toBe("Everest tirmanisi");
    expect(formatCustomLesson("  Ada  ")).toBe("custom:Ada");
    expect(lessonCurveHint("custom:ada macerasi")).toContain("yola cikis");
  });
});
