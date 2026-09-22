import { describe, expect, it } from "vitest";
import {
  CHARACTER_CUTENESS_LOCK,
  CHARACTER_HEIGHT_BANDS,
  composeCharacterSheetPrompt,
  formatCastmateForbiddenLook,
  heightBandPhrase,
  spreadHeightBands,
} from "@/lib/song-character-sheet";
import { dnaCardSchema } from "@/lib/song-character";

const SHEET_LOCK = "ONE reference image = a clean 2-panel CHARACTER TURNAROUND SHEET only.";
const ART = "Theatrical glossy 3D CGI family animation, groomed fur strands.";

function dna(over: Record<string, unknown> = {}) {
  return dnaCardSchema.parse({
    name: "Pofuduk",
    species: "round hedgehog mascot",
    personality: ["shy", "kind"],
    catchphrase: "Hadi!",
    signatureGesture: "spins quills",
    voiceDescription: "soft high voice",
    fears: "loud shocks",
    loves: "berries",
    colorPalette: ["moss green", "cream", "coral"],
    imagePrompt: "A round hedgehog mascot performer with soft quills, full body, stylized 3D.",
    bodyDetail: "soft rounded quills, stubby paws",
    outfitDetail: "knitted vest, tiny boots",
    signatureProp: "acorn shaker",
    silhouette: "pear-shaped and round",
    heightBand: "short",
    distinguishingMark: "star-shaped cream patch over the left eye",
    faceFeatures: "big amber eyes, tiny pink nose",
    ...over,
  });
}

describe("Karakter kunyesi promptu", () => {
  it("ayirt edici alanlarin HEPSINI prompta yazar", () => {
    const prompt = composeCharacterSheetPrompt({
      name: "Pofuduk",
      dna: dna(),
      fallbackAppearance: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });

    expect(prompt).toContain("Pofuduk");
    expect(prompt).toContain("round hedgehog mascot");
    expect(prompt).toContain("pear-shaped and round");
    expect(prompt).toContain("star-shaped cream patch over the left eye");
    expect(prompt).toContain("big amber eyes");
    expect(prompt).toContain("knitted vest");
    expect(prompt).toContain("acorn shaker");
    expect(prompt).toContain("moss green");
    expect(prompt).toContain(SHEET_LOCK);
    expect(prompt).toContain(ART);
  });

  it("paletteki renkleri govde/ikincil/vurgu rolleriyle kilitler", () => {
    const prompt = composeCharacterSheetPrompt({
      name: "Pofuduk",
      dna: dna(),
      fallbackAppearance: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });
    expect(prompt).toMatch(/main body moss green/i);
    expect(prompt).toMatch(/secondary cream/i);
    expect(prompt).toMatch(/accent coral/i);
  });

  it("iki farkli kadro uyesi belirgin farkli prompt uretir", () => {
    const a = composeCharacterSheetPrompt({
      name: "Pofuduk",
      dna: dna(),
      fallbackAppearance: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });
    const b = composeCharacterSheetPrompt({
      name: "TikTik",
      dna: dna({
        name: "TikTik",
        species: "lanky heron mascot",
        imagePrompt: "A lanky heron mascot performer with long legs, full body, stylized 3D.",
        colorPalette: ["slate blue", "white", "amber"],
        silhouette: "tall with a long neck",
        heightBand: "tall",
        distinguishingMark: "one bent tail feather",
        faceFeatures: "narrow eyes, long beak",
        outfitDetail: "striped scarf, rubber boots",
        signatureProp: "tin whistle",
      }),
      fallbackAppearance: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });

    expect(a).not.toBe(b);
    expect(b).toContain("lanky heron mascot");
    expect(b).toContain("one bent tail feather");
    expect(b).not.toContain("hedgehog");
    expect(a).not.toContain("heron");
  });

  it("yeni tasarim kilidi her zaman vardir (onceki karta bakip kopyalamasin)", () => {
    const prompt = composeCharacterSheetPrompt({
      name: "Pofuduk",
      dna: dna(),
      fallbackAppearance: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });
    expect(prompt).toMatch(/NEW DESIGN/i);
    expect(prompt).toMatch(/Do not clone, recolor, or substitute/i);
  });

  it("sirinlik kilidi her karakter kunyesinde vardir ve kimligi ezmez", () => {
    const prompt = composeCharacterSheetPrompt({
      name: "Pofuduk",
      dna: dna(),
      fallbackAppearance: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });
    expect(prompt).toContain(CHARACTER_CUTENESS_LOCK);
    expect(prompt).toMatch(/CUTENESS LOCK/);
    expect(prompt).toMatch(/oversized glossy eyes/i);
    expect(prompt).toMatch(/plump round cheeks/i);
    expect(prompt).toMatch(/zero sharp claws/i);
    // Malzeme gercekligi: karakter "ucuz oyuncak render" gibi cikmasin
    expect(prompt).toMatch(/MATERIAL REALISM/);
    expect(prompt).toMatch(/groomed strand-by-strand/i);
    expect(prompt).toMatch(/subsurface scattering/i);
    // Kimlik alanlari korunur: sirinlik, kadroyu birbirine benzetmez
    expect(prompt).toMatch(/keep THIS character's own species, silhouette, height band/i);
    expect(prompt).toContain("star-shaped cream patch over the left eye");
  });

  it("kadro arkadaslarina benzememe kilidini ekler ve onlari cizdirmez", () => {
    const prompt = composeCharacterSheetPrompt({
      name: "Pofuduk",
      dna: dna(),
      fallbackAppearance: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
      castmates: [
        {
          name: "TikTik",
          species: "lanky heron mascot",
          mainColor: "slate blue",
          silhouette: "tall with a long neck",
          distinguishingMark: "one bent tail feather",
        },
        { name: "Dom Dom", species: "bouncy tomato mascot", mainColor: "warm red" },
      ],
    });
    expect(prompt).toContain("FORBIDDEN LOOKS");
    expect(prompt).toContain("DISTINCT FROM CASTMATES");
    expect(prompt).toContain("TikTik");
    expect(prompt).toMatch(/slate blue main body/i);
    expect(prompt).toContain("bouncy tomato mascot");
    expect(prompt).toContain("Do not draw those characters here.");
    expect(prompt).toMatch(/different SPECIES/i);
  });

  it("DNA yoksa yedek gorunum metnine duser (cokmez)", () => {
    const prompt = composeCharacterSheetPrompt({
      name: "Adsiz",
      dna: null,
      fallbackAppearance: "A friendly stylized 3D animal mascot performer",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });
    expect(prompt).toContain("A friendly stylized 3D animal mascot performer");
    expect(prompt).toContain(SHEET_LOCK);
  });

  it("bos alanlar icin bos satir yazmaz", () => {
    const prompt = composeCharacterSheetPrompt({
      name: "Sade",
      dna: dna({ distinguishingMark: "", signatureProp: "", outfitDetail: "" }),
      fallbackAppearance: "",
      wardrobe: "",
      artStyle: ART,
      sheetLock: SHEET_LOCK,
    });
    expect(prompt).not.toContain("UNMISTAKABLE MARK:");
    expect(prompt).not.toContain("SIGNATURE PROP:");
    expect(prompt).not.toContain("OUTFIT:");
  });
});

describe("Boy bandi dagitimi", () => {
  it("ayni boyu verilen kadroyu farkli bandlara dagitir", () => {
    expect(spreadHeightBands(["medium", "medium", "medium", "medium"])).toEqual([
      "medium",
      "tiny",
      "short",
      "tall",
    ]);
  });

  it("bos/gecersiz bandlari doldurur", () => {
    const out = spreadHeightBands(["", "dev", "tall"]);
    expect(new Set(out).size).toBe(3);
    expect(out).toContain("tall");
    for (const band of out) expect(CHARACTER_HEIGHT_BANDS).toContain(band);
  });

  it("zaten farkli olan bandlara dokunmaz", () => {
    expect(spreadHeightBands(["tiny", "tall"])).toEqual(["tiny", "tall"]);
  });

  it("4'ten fazla uyede cokmez", () => {
    const out = spreadHeightBands(new Array(6).fill("medium"));
    expect(out).toHaveLength(6);
    for (const band of out) expect(CHARACTER_HEIGHT_BANDS).toContain(band);
  });

  it("yasak gorunum satirina renk ve imza isaretini koyar", () => {
    expect(
      formatCastmateForbiddenLook({
        name: "Dom Dom",
        species: "bouncy tomato mascot",
        mainColor: "warm red",
        distinguishingMark: "leaf sprout tuft",
      })
    ).toMatch(/Dom Dom, bouncy tomato mascot, warm red main body, leaf sprout tuft/);
  });
});
