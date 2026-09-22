import { describe, expect, it } from "vitest";
import { authenticityHint, storyBriefBlock } from "@/server/services/kids";

describe("Hikaye on bilgisi / konu dogrulugu", () => {
  it("bos on bilgide blok uretmez", () => {
    expect(storyBriefBlock("")).toBe("");
    expect(storyBriefBlock(null)).toBe("");
  });

  it("on bilgiyi zorunlu incil olarak isaretler", () => {
    const block = storyBriefBlock("Kahraman ve arkadaslari kopruyu gecer.");
    expect(block).toContain("ZORUNLU HIKAYE INCILI");
    expect(block).toContain("kopruyu gecer");
  });

  it("dogruluk ipucu tema-agnostiktir: sabit bir konuya ait ekipman/rota dayatmaz", () => {
    const hint = authenticityHint();
    expect(hint).toContain("KONU DOGRULUGU");
    expect(hint).toMatch(/ARASTIR/i);
    // Kodda hicbir temaya (dag/deniz/uzay) ozel sabit rota veya ekipman listesi olmamali
    expect(hint).not.toMatch(/everest|khumbu|south\s*col|crampon|buz baltasi|dalis tupu/i);
  });

  it("secilmeyen tema/ekipmanin hikayeye girmesini yasaklar", () => {
    const block = storyBriefBlock("Kahraman denizde tup ile dalis yapar.");
    expect(block).toMatch(/GECMEYEN bir etkinlik, mekan veya ekipmani hikayeye SOKMA/i);
  });
});
