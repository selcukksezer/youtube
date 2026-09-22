import { describe, expect, it } from "vitest";
import {
  stripGearLockBlocks,
  stripStoryGearFromDnaCard,
  prepareDnaCardForNewFilm,
  scrubCarriedOutfitFromText,
  needsThemeOutfitRefresh,
  storyThemeKey,
  assertKidsThemeLookReady,
} from "@/server/services/kids";
import { stripEmotionTonePhrase } from "@/server/services/character";

/**
 * "Bu ana karakterle yeni film": SADECE karakter kimligi (tur/yuz/govde) devralinir.
 * Eski filmin hikaye artiklari (tema prop kilidi, tema kostumu, sabit duygu) tasinmaz.
 */
describe("Yeni filme devir: hikaye artiklari temizlenir", () => {
  it("kostumden tema prop kilidi blogu cikarilir, kimlik metni kalir", () => {
    const wardrobe = [
      "Teal knit scarf with frayed edge, charcoal shorts, worn leather sandals.",
      "",
      "[STORY PROP / GEAR LOCK — NON-NEGOTIABLE ACROSS EVERY CLIP]",
      "• Dalış tüpü: matte teal aluminium tank with amber valve",
      "• Fener: brushed steel torch with orange grip",
    ].join("\n");

    const cleaned = stripGearLockBlocks(wardrobe);
    expect(cleaned).toContain("Teal knit scarf");
    expect(cleaned).not.toMatch(/STORY PROP \/ GEAR LOCK/i);
    expect(cleaned).not.toMatch(/Dalış tüpü/);
  });

  it("eski surumun dag ekipmani blogu da temizlenir", () => {
    const wardrobe = "Blue jacket.\n\n[EXPEDITION GEAR LOCK — NON-NEGOTIABLE]\n• Rope: signal-orange";
    expect(stripGearLockBlocks(wardrobe)).toBe("Blue jacket.");
  });

  it("DNA kartindan prop kilidi silinir, karakter kimligi korunur", () => {
    const dna = JSON.stringify({
      name: "Kırpık",
      species: "otter",
      colorPalette: ["#E85D04", "#023E8A"],
      outfitDetail: "teal scarf",
      storyGear: { themeKey: "deniz", items: [{ label: "Dalış tüpü", lock: "teal tank" }] },
      expeditionKit: { rope: "signal-orange" },
    });

    const parsed = JSON.parse(stripStoryGearFromDnaCard(dna)) as Record<string, unknown>;
    expect(parsed.name).toBe("Kırpık");
    expect(parsed.outfitDetail).toBe("teal scarf");
    expect(parsed.colorPalette).toEqual(["#E85D04", "#023E8A"]);
    expect(parsed.storyGear).toBeUndefined();
    expect(parsed.expeditionKit).toBeUndefined();
  });

  it("prop kilidi yoksa DNA karti aynen korunur", () => {
    const dna = JSON.stringify({ name: "Kiko", species: "otter" });
    expect(stripStoryGearFromDnaCard(dna)).toBe(dna);
    expect(stripStoryGearFromDnaCard("{}")).toBe("{}");
    expect(stripStoryGearFromDnaCard(null)).toBe("{}");
    // bozuk JSON: veri kaybetmemek icin oldugu gibi doner
    expect(stripStoryGearFromDnaCard("bozuk")).toBe("bozuk");
  });

  it("yeni film icin kimlik sheet'i yazilir, Everest/kostum ve prop silinir", () => {
    const dna = JSON.stringify({
      name: "Kırpık",
      species: "puff-sheep",
      bodyDetail: "Small and fluffy; 1:1.5 head-to-body; pearly blue eyes.",
      colorPalette: ["#F5F0EA", "#8EC5FF"],
      outfitDetail: "Sky-blue down jacket with micro-crampons",
      outfitThemeKey: "mountain||trail",
      imagePrompt:
        "3D Pixar-style animation. Tiny puff-sheep. Everest outfit: sky-blue down jacket with chevron quilting, snow goggles. Pearly blue eyes.",
      storyGear: { themeKey: "mountain||trail", items: [{ label: "Ip", lock: "rope" }] },
      signatureProp: "cloud-trimming safety scissors",
    });
    const parsed = JSON.parse(prepareDnaCardForNewFilm(dna)) as Record<string, unknown>;
    expect(parsed.name).toBe("Kırpık");
    expect(parsed.species).toBe("puff-sheep");
    expect(parsed.signatureProp).toBe("cloud-trimming safety scissors");
    expect(parsed.outfitDetail).toBe("");
    expect(parsed.outfitThemeKey).toBeUndefined();
    expect(parsed.storyGear).toBeUndefined();
    expect(String(parsed.imagePrompt)).not.toMatch(/Everest/i);
    expect(String(parsed.imagePrompt)).toMatch(/IDENTITY SHEET ONLY/i);
    expect(String(parsed.imagePrompt)).toContain("puff-sheep");
    expect(String(parsed.imagePrompt)).toContain("cloud-trimming safety scissors");
  });

  it("gorunum metninden Everest kostum cumleleri soyulur", () => {
    const text =
      "Tiny puff-sheep, pearly blue eyes. Everest outfit: sky-blue down jacket with chevron quilting, snow goggles on chest. Signature scissors.";
    const cleaned = scrubCarriedOutfitFromText(text);
    expect(cleaned).toContain("puff-sheep");
    expect(cleaned).toContain("scissors");
    expect(cleaned).not.toMatch(/Everest/i);
    expect(cleaned).not.toMatch(/snow goggles/i);
  });

  it("deniz temasında bayat dag kostumu yenileme ister", () => {
    const themeKey = storyThemeKey("custom:yat ve dalis", "yat dalis portal");
    expect(
      needsThemeOutfitRefresh(
        {
          outfitThemeKey: "",
          outfitDetail: "Sky-blue down jacket; micro-crampons; snow goggles",
          imagePrompt: "Everest outfit: sky-blue down jacket",
        },
        themeKey,
        "yat dalis portal deniz"
      )
    ).toBe(true);
    expect(
      needsThemeOutfitRefresh(
        {
          outfitThemeKey: themeKey,
          outfitDetail: "Mustard deck jacket over short wetsuit, life vest, deck shoes",
          imagePrompt: "Tiny puff-sheep in mustard deck jacket on a yacht",
        },
        themeKey,
        "yat dalis portal deniz"
      )
    ).toBe(false);
  });

  it("tema secilmeden Flow baslamasin", () => {
    expect(() =>
      assertKidsThemeLookReady({ moralLesson: "", topic: "", useReference: true }, { dnaCard: "{}", imageApproved: false })
    ).toThrow(/tema/i);

    const readyDna = JSON.stringify({
      name: "Kırpık",
      outfitThemeKey: storyThemeKey("custom:deniz", "yat"),
      outfitDetail: "deck jacket and life vest",
    });
    expect(() =>
      assertKidsThemeLookReady(
        { moralLesson: "custom:deniz", topic: "yat", useReference: true },
        { dnaCard: readyDna, imageApproved: true, referenceImagePath: "/tmp/ref.png" }
      )
    ).not.toThrow();
  });

  it("ses kimligi kalir, sabit duygu tonu cikarilir", () => {
    const voice = "warm mid-pitch female voice, emotional tone: mysterious, slightly tense, gesture level: subtle";
    const cleaned = stripEmotionTonePhrase(voice);
    expect(cleaned).toContain("warm mid-pitch female voice");
    expect(cleaned).toContain("gesture level: subtle");
    expect(cleaned).not.toMatch(/emotional tone/i);
  });

  it("duygu tonu yoksa ses metni degismez", () => {
    const voice = "warm, clear, age-safe kid-show host voice";
    expect(stripEmotionTonePhrase(voice)).toBe(voice);
    expect(stripEmotionTonePhrase("")).toBe("");
  });
});
