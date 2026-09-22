import { describe, expect, it } from "vitest";
import {
  craftThumbnailOverlayText,
  enhanceThumbnailPrompt,
  forceShortCuriosityDescription,
  normalizePublishMeta,
  pickDiverseThumbnailCandidate,
  rankThumbnailClips,
  tightenCuriosityDescription,
} from "@/server/services/publish";

describe("Yayin meta normalize", () => {
  it("eksik baslik/etiket/thumbnail alanlarini tamamlar", () => {
    const meta = normalizePublishMeta(
      {
        titleVariants: ["Tilki zirvede"],
        primaryTitle: "",
        description: "Kisa.",
        tags: ["tilki"],
        hashtags: [],
        seoKeywords: { primary: "", secondary: [] },
        targetAudience: "",
        thumbnailPrompt: "",
        thumbnailText: "",
        thumbnailConcepts: [],
        chapters: [],
        pinnedComment: "",
        communityPost: "",
        shortsHooks: [],
        endScreenCta: "",
        postingStrategy: "",
        uploadChecklist: [],
        kidsSafetyNotes: "",
        contentWarnings: [],
        seriesHook: "",
      },
      { titleFallback: "Dag Macerasi", isKids: true, totalSeconds: 120 }
    );

    expect(meta.primaryTitle.length).toBeGreaterThan(3);
    expect(meta.titleVariants.length).toBeGreaterThanOrEqual(5);
    expect(meta.description.length).toBeGreaterThan(40);
    expect(meta.tags.length).toBeGreaterThanOrEqual(12);
    expect(meta.hashtags.length).toBeGreaterThanOrEqual(5);
    expect(meta.chapters[0]?.time).toBe("0:00");
    expect(meta.thumbnailConcepts.length).toBeGreaterThanOrEqual(3);
    expect(meta.thumbnailPrompt.length).toBeGreaterThan(20);
    expect(meta.uploadChecklist.length).toBeGreaterThanOrEqual(6);
    expect(meta.kidsSafetyNotes.length).toBeGreaterThan(10);
  });

  it("aciklama fallback film ozeti gibi degil merak on-bilgisi yazar", () => {
    const meta = normalizePublishMeta(
      {
        titleVariants: [],
        primaryTitle: "Karlı Zirve",
        description: "x",
        tags: [],
        hashtags: [],
        seoKeywords: { primary: "", secondary: [] },
        targetAudience: "",
        thumbnailPrompt: "enough characters here for thumb",
        thumbnailText: "Neler Oldu Neler?",
        thumbnailConcepts: [
          { name: "A", emotion: "e", hook: "h", prompt: "enough characters for a concept prompt xx" },
          { name: "B", emotion: "e", hook: "h", prompt: "enough characters for a concept prompt yy" },
          { name: "C", emotion: "e", hook: "h", prompt: "enough characters for a concept prompt zz" },
        ],
        chapters: [
          { time: "0:00", label: "Bas", beat: "" },
          { time: "1:00", label: "Orta", beat: "" },
          { time: "2:00", label: "Son", beat: "" },
        ],
        pinnedComment: "y".repeat(40),
        communityPost: "z".repeat(50),
        shortsHooks: ["a", "b", "c"],
        endScreenCta: "cta text here enough",
        postingStrategy: "strategy text here enough chars ok",
        uploadChecklist: ["1", "2", "3", "4", "5", "6"],
        kidsSafetyNotes: "",
        contentWarnings: [],
        seriesHook: "",
      },
      { titleFallback: "Karlı Zirve", isKids: true, totalSeconds: 90 }
    );
    expect(meta.description).toMatch(/değişiyor|İzle|merak|ne oluyor/i);
    expect(meta.description.length).toBeLessThan(450);
    expect(meta.description).not.toMatch(/Sonunda zirveye vardılar|hikayenin ozeti/i);
  });

  it("uzun aciklamayi kisa merak metnine sikiştirir", () => {
    const long = `Sis kısalıyor, rüzgârın tonu değişiyor: Üç küçük kâşif Everest'in buz köprülerinde adım ritmini bulabilecek mi? Bir ip, bir jumar ve çokça dostluk—gizemli geçitlerin sırrı burada açığa çıkıyor.
Gerçek bir tırmanışta olması gereken her şey bu çocuk animasyonunda: emniyet kemeri, karabina, sekizli düğüm, jumar, ara emniyet ve ekip içi komutlarla ilerleyen güvenli bir rota. Tona, Mete ve Nima; sisin ardındaki mavi buza giriş penceresini yakalayıp South Col'un altın ışığına ulaşmaya çalışırken, buz köprülerini test ediyor.
Eğer gerçekçi dağcılık ayrıntılarını içeren çocuk animasyonlarını seviyorsanız, bu gizem dolu yolculukta bize katılın ve yeni maceraları kaçırmamak için abone olmayı unutmayın.

#everest #çocuk`;
    const tight = forceShortCuriosityDescription(long, { title: "Karlı Zirve", hashtags: ["#macera"] });
    expect(tight.length).toBeLessThan(480);
    expect(tight).not.toMatch(/abone|emniyet kemeri|South Col/i);
    expect(tight.split(/(?<=[.!?…])\s+/).length).toBeLessThanOrEqual(4);
  });
});

describe("Kapak yazisi", () => {
  it("YouTube CTR: en fazla 3 kelime, kisa Turkce kanca", () => {
    expect(craftThumbnailOverlayText({ thumbnailText: "Neler Oldu?" })).toBe("Neler Oldu?");
    const long = craftThumbnailOverlayText({
      thumbnailText: "Bir tilki ve arkadaslari karli zirvede uzun macera",
      emotionLabel: "gergin",
    });
    expect(long.split(/\s+/).length).toBeLessThanOrEqual(3);
    expect(long.length).toBeLessThanOrEqual(22);
    expect(craftThumbnailOverlayText({ emotionLabel: "merak" })).toMatch(/Şimdi Ne|Bak Buna|Vay|Kaçırma|İzle/i);
  });

  it("Ingilizce kapak yazisini Turkce kancaya cevirir", () => {
    const text = craftThumbnailOverlayText({
      thumbnailText: "What Happened Next?",
      emotionLabel: "gergin",
    });
    expect(text).toMatch(/Neler Oldu|Sakın|Tutun|Ip Gerildi/i);
    expect(text).not.toMatch(/What|Happened|Next/i);
  });

  it("uzun basligi kapaga yapistirmez", () => {
    const text = craftThumbnailOverlayText({
      primaryTitle: "Kırpık ile arkadaşları Everest yolunda büyük macera yaşadı",
      emotionLabel: "heyecan",
    });
    expect(text.split(/\s+/).length).toBeLessThanOrEqual(3);
    expect(text).not.toMatch(/Everest|arkadaşları/i);
  });
});

describe("Thumbnail prompt guclendirme", () => {
  it("yazisiz profesyonel kilitleri ekler", () => {
    const prompt = enhanceThumbnailPrompt("orange fox on a snowy ridge gasping", {
      isKids: true,
      characterHint: "Sunny the fox with blue scarf",
    });
    expect(prompt).toContain("YouTube thumbnail");
    expect(prompt).toContain("NO text");
    expect(prompt).toContain("Pixar");
    expect(prompt).toContain("Sunny the fox");
    expect(prompt).toContain("orange fox on a snowy ridge");
  });
});

describe("Videodan thumbnail siralama", () => {
  it("yuksek merak + kanca + orta bolgeyi onde tutar", () => {
    const ranked = rankThumbnailClips([
      {
        index: 1,
        status: "completed",
        curiosityScore: 3,
        hasHook: false,
        emotionLabel: "sakin",
        videoPath: "C:\\fake\\a.mp4",
        lastFramePath: null,
        sceneImagePath: null,
        actualDurationSeconds: 8,
        estimatedDurationSeconds: 8,
      },
      {
        index: 5,
        status: "completed",
        curiosityScore: 9,
        hasHook: true,
        emotionLabel: "gergin",
        videoPath: "C:\\fake\\b.mp4",
        lastFramePath: null,
        sceneImagePath: null,
        actualDurationSeconds: 8,
        estimatedDurationSeconds: 8,
      },
      {
        index: 2,
        status: "draft",
        curiosityScore: 10,
        hasHook: true,
        emotionLabel: "heyecan",
        videoPath: "C:\\fake\\c.mp4",
        lastFramePath: null,
        sceneImagePath: null,
        actualDurationSeconds: 8,
        estimatedDurationSeconds: 8,
      },
    ]);
    expect(ranked[0]?.index).toBe(5);
    expect(ranked[0]?.reason).toMatch(/kanca|merak|duygu/i);
  });

  it("son kullanilan klipleri atlayip farkli kare orani secer", () => {
    const ranked = rankThumbnailClips([
      {
        index: 3,
        status: "completed",
        curiosityScore: 8,
        hasHook: true,
        emotionLabel: "gergin",
        videoPath: "a.mp4",
        lastFramePath: null,
        sceneImagePath: null,
        actualDurationSeconds: 8,
        estimatedDurationSeconds: 8,
      },
      {
        index: 7,
        status: "completed",
        curiosityScore: 8,
        hasHook: true,
        emotionLabel: "heyecan",
        videoPath: "b.mp4",
        lastFramePath: null,
        sceneImagePath: null,
        actualDurationSeconds: 8,
        estimatedDurationSeconds: 8,
      },
      {
        index: 10,
        status: "completed",
        curiosityScore: 7,
        hasHook: true,
        emotionLabel: "panik",
        videoPath: "c.mp4",
        lastFramePath: null,
        sceneImagePath: null,
        actualDurationSeconds: 8,
        estimatedDurationSeconds: 8,
      },
    ]);
    const first = pickDiverseThumbnailCandidate(ranked, [{ clipIndex: 3, atSec: 3.6 }]);
    expect(first.clip.index).not.toBe(3);
    expect(first.frameRatio).toBeGreaterThan(0.15);
    expect(first.frameRatio).toBeLessThan(0.85);
  });
});
