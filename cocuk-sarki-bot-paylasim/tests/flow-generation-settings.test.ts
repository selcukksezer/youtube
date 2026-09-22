import { describe, expect, it } from "vitest";
import {
  chipNeedsRepair,
  defaultDurationsForFlowModel,
  flowClipSeconds,
  preferredNarratorClipSeconds,
  flowDurationTabPattern,
  isImageFlowModel,
  imageModelNamesMatch,
  isImageOutputModeLabel,
  isStuckFlowResolvingText,
  isTrustedVideoOutputLabel,
  isVideoOutputModeLabel,
  parseFlowSettingsChip,
} from "@/lib/flow-generation-settings";

describe("Cikti turu ayrimi (goruntu / video karismasi)", () => {
  it("video etiketlerini goruntu sanmaz", () => {
    for (const label of [
      "Metinden videoya",
      "Text to video",
      "Malzemelerden video",
      "Ingredients to video",
      "Frames to video",
      "Görüntüden videoya",
      "Videocrop_16_9x1",
      "Video · 720pcrop_16_9x1",
    ]) {
      expect(isImageOutputModeLabel(label)).toBe(false);
      expect(isVideoOutputModeLabel(label)).toBe(true);
    }
  });

  it("'Görüntüden videoya' referans modunu VIDEO sayar (klibi bloke etmez)", () => {
    expect(isVideoOutputModeLabel("Görüntüden videoya")).toBe(true);
    expect(isImageOutputModeLabel("Görüntüden videoya")).toBe(false);
    expect(isVideoOutputModeLabel("Malzemelerden videoya")).toBe(true);
  });

  it("goruntu etiketlerini video sanmaz", () => {
    for (const label of [
      "Metinden görüntüye",
      "Text to image",
      "Nano Banana 2",
      "Nano Banana Pro",
      "Malzemelerden görüntü",
      "Ingredients to image",
      "Görüntücrop_16_9x1",
    ]) {
      expect(isImageOutputModeLabel(label)).toBe(true);
      expect(isVideoOutputModeLabel(label)).toBe(false);
    }
  });

  it("bos etiket hicbir moda kanit sayilmaz (alt sayfada okunamaz)", () => {
    expect(isImageOutputModeLabel("")).toBe(false);
    expect(isVideoOutputModeLabel("")).toBe(false);
  });

  it("iki mod ayni anda dogru olamaz", () => {
    for (const label of ["Metinden videoya", "Nano Banana 2", "Videocrop_16_9x1", "Text to image", ""]) {
      expect(isImageOutputModeLabel(label) && isVideoOutputModeLabel(label)).toBe(false);
    }
  });
});

describe("flowClipSeconds", () => {
  it("Veo Fast/Lite icin 10 sn'yi 8 sn'ye ceker", () => {
    expect(flowClipSeconds("Veo 3.1 Fast", 10)).toBe(8);
    expect(flowClipSeconds("Veo 3.1 - Fast", 10)).toBe(8);
    expect(flowClipSeconds("Veo 3.1 Lite", 10)).toBe(8);
  });

  it("proje 8 sn ise oldugu gibi birakir", () => {
    expect(flowClipSeconds("Veo 3.1 Fast", 8)).toBe(8);
    expect(flowClipSeconds("Veo 3.1 Fast", 6)).toBe(6);
  });

  it("Quality ve Omni 10 sn kabul eder", () => {
    expect(flowClipSeconds("Veo 3.1 Quality", 10)).toBe(10);
    expect(flowClipSeconds("Gemini Omni Flash", 10)).toBe(10);
  });

  it("sinema anlatici 8 sn varsayilani model izin veriyorsa 10 sn olur", () => {
    expect(preferredNarratorClipSeconds("Gemini Omni Flash", 8)).toBe(10);
    expect(preferredNarratorClipSeconds("Veo 3.1 Quality", 0)).toBe(10);
    expect(preferredNarratorClipSeconds("Veo 3.1 Fast", 8)).toBe(8);
    expect(preferredNarratorClipSeconds("Veo 3.1 Quality", 6)).toBe(6);
  });

  it("destek listesi verilirse ona uyar", () => {
    expect(flowClipSeconds("Ozel", 10, [4, 6, 8])).toBe(8);
    expect(flowClipSeconds("Ozel", 10, [4, 6, 8, 10])).toBe(10);
  });
});

describe("defaultDurationsForFlowModel", () => {
  it("Fast/Lite 10 icermez", () => {
    expect(defaultDurationsForFlowModel("Veo 3.1 Fast")).toEqual([4, 6, 8]);
    expect(defaultDurationsForFlowModel("Veo 3.1 Lite")).toEqual([4, 6, 8]);
  });
});

describe("parseFlowSettingsChip", () => {
  it("Video · 10scrop_9_16x1 ozetini okur", () => {
    const chip = parseFlowSettingsChip("Video · 10scrop_9_16x1");
    expect(chip.durationSec).toBe(10);
    expect(chip.aspect).toBe("9:16");
    expect(chip.outputs).toBe(1);
    expect(chip.looksLikeSettingsChip).toBe(true);
  });

  it("Videocrop_9_16x1 (suresiz eski ozet) oranini okur", () => {
    const chip = parseFlowSettingsChip("Videocrop_9_16x1");
    expect(chip.durationSec).toBeNull();
    expect(chip.aspect).toBe("9:16");
    expect(chip.outputs).toBe(1);
    expect(chip.looksLikeSettingsChip).toBe(true);
  });

  it("16:9 ozetini okur", () => {
    const chip = parseFlowSettingsChip("Videocrop_16_9x1");
    expect(chip.aspect).toBe("16:9");
  });

  it("Metinden videoya etiketini ayarlar ozeti saymaz", () => {
    const chip = parseFlowSettingsChip("Metinden videoya");
    expect(chip.looksLikeSettingsChip).toBe(false);
    expect(chip.aspect).toBeNull();
  });

  it("yalnizca 8s sure sekmesi ozet cubugu degildir", () => {
    expect(parseFlowSettingsChip("8s").looksLikeSettingsChip).toBe(false);
    expect(parseFlowSettingsChip("8 saniye").looksLikeSettingsChip).toBe(false);
  });
});

describe("chipNeedsRepair", () => {
  it("10s short + 8s hedefinde sureyi bozuk sayar", () => {
    const chip = parseFlowSettingsChip("Video · 10scrop_9_16x1");
    const repair = chipNeedsRepair(chip, { durationSec: 8, aspect: "9:16", outputs: 1 });
    expect(repair.duration).toBe(true);
    expect(repair.aspect).toBe(false);
    expect(repair.outputs).toBe(false);
  });

  it("oran 16:9 kalmissa short icin bozuk sayar", () => {
    const chip = parseFlowSettingsChip("Videocrop_16_9x1");
    const repair = chipNeedsRepair(chip, { durationSec: 8, aspect: "9:16" });
    expect(repair.aspect).toBe(true);
  });
});

describe("flowDurationTabPattern", () => {
  it("8s, 8 s, 8sn ve 8 sn eslesir; 10s eslesmez", () => {
    const re = flowDurationTabPattern(8);
    expect(re.test("8s")).toBe(true);
    expect(re.test("8 s")).toBe(true);
    expect(re.test("8sn")).toBe(true);
    expect(re.test("8 sn")).toBe(true);
    expect(re.test("10s")).toBe(false);
    expect(re.test("16:9")).toBe(false);
  });
});

describe("isTrustedVideoOutputLabel", () => {
  it("Video ayarlar ozetini video kabul eder (yanlis alarm cikmasin)", () => {
    expect(isTrustedVideoOutputLabel("Video · 720pcrop_16_9x1")).toBe(true);
    expect(isTrustedVideoOutputLabel("Videocrop_16_9x1")).toBe(true);
    expect(isTrustedVideoOutputLabel("Metinden videoya")).toBe(true);
  });

  it("goruntu etiketine guvenmez", () => {
    expect(isTrustedVideoOutputLabel("Nano Banana 2")).toBe(false);
    expect(isTrustedVideoOutputLabel("Görüntücrop_16_9x1")).toBe(false);
    expect(isTrustedVideoOutputLabel("")).toBe(false);
  });
});

describe("isImageFlowModel", () => {
  it("Nano Banana gorsel, Veo video", () => {
    expect(isImageFlowModel("Nano Banana 2")).toBe(true);
    expect(isImageFlowModel("Nano Banana Pro")).toBe(true);
    expect(isImageFlowModel("Veo 3.1 Fast")).toBe(false);
  });
});

describe("imageModelNamesMatch", () => {
  it("Pro ile 2 karismaz", () => {
    expect(imageModelNamesMatch("Nano Banana Pro", "Nano Banana Pro")).toBe(true);
    expect(imageModelNamesMatch("Nano Banana 2", "Nano Banana 2")).toBe(true);
    expect(imageModelNamesMatch("Nano Banana Pro", "Nano Banana 2")).toBe(false);
    expect(imageModelNamesMatch("Nano Banana 2", "Nano Banana Pro")).toBe(false);
  });
});

describe("isStuckFlowResolvingText", () => {
  it("Flow'un takili hata-cozme metnini yakalar", () => {
    expect(isStuckFlowResolvingText("Hatayı çözüyoruz, lütfen bekleyin")).toBe(true);
    expect(isStuckFlowResolvingText("Hatayı böyle çöz")).toBe(true);
    expect(isStuckFlowResolvingText("Yeniden deneniyor")).toBe(true);
    expect(isStuckFlowResolvingText("Uretim tamamlandi")).toBe(false);
  });
});
