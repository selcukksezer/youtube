import { describe, expect, it } from "vitest";
import {
  detectHeroSubject,
  detectSongWorld,
  environmentConflictsWorld,
  extractLyricContentWords,
  extractSongPictureBeats,
  formatLyricStagingLine,
  lyricsNameHero,
  mustShowFromAudio,
  worldPositiveForLive,
} from "@/lib/song-lyric-visual";
import { boostLiveActionShotPlan, buildLyricActionTimeline } from "@/lib/song-prompt-craft";
import { livePlaceAnchorLock } from "@/lib/visual-style-family";
import { composeShotPrompt } from "@/server/services/song";
import {
  compactPromptForFlow,
  stampNoOnscreenTextLock,
  FLOW_PROMPT_MAX,
} from "@/lib/flow-prompt-compact";
import { buildClipPrompt } from "@/server/services/prompt-builder";

const FOREST_LYRIC = "Ormanda dostlar var, kelebekler renk renk uçar";

function sampleClip(overrides: Partial<Parameters<typeof composeShotPrompt>[0]> = {}) {
  return {
    index: 3,
    section: "verse",
    lyrics: FOREST_LYRIC,
    syllableCount: 14,
    sceneDescription: "Kelebek ucusu",
    imagePrompt: "the fox friend twirls between mossy trunks while butterflies loop around her",
    choreography: "spin with arms wide, then point to the butterflies",
    voiceTone: "bright",
    emotion: "neseli",
    mustShowProps: "colorful butterflies airborne; forest clearing with mossy ground",
    lyricSyncAction: "eyes track the flying butterflies, arm sweeps to present the forest",
    hookNote: "",
    curiosityScore: 5,
    singerName: "Axo Işıl",
    environment: "forest clearing with ferns",
    ...overrides,
  } as Parameters<typeof composeShotPrompt>[0];
}

describe("Dunya kilidi (soz → set)", () => {
  it("ormanda gecen sarkiyi FOREST olarak kilitler", () => {
    const world = detectSongWorld("Ormanda dostlar var hadi say bir bir");
    expect(world?.key).toBe("forest");
    expect(world?.positive).toMatch(/FOREST/);
    expect(world?.never).toMatch(/mountain/i);
  });

  it("dag/sehir iceren ortam metnini celiski sayar", () => {
    const world = detectSongWorld("ormanda");
    expect(environmentConflictsWorld("mountain meadow at sunrise", world)).toBe(true);
    expect(environmentConflictsWorld("mossy forest clearing", world)).toBe(false);
  });

  it("canli-cekim orman pozitifi fotografik yogunluk tasir", () => {
    const world = detectSongWorld("Ormanda dostlar var");
    expect(world).toBeTruthy();
    const live = worldPositiveForLive(world!);
    expect(live).toMatch(/REAL sunlit FOREST/i);
    expect(live).toMatch(/god-rays|lichen|leaf litter/i);
    expect(livePlaceAnchorLock(live)).toMatch(/LIVE PLACE LOCK/);
    expect(livePlaceAnchorLock(live)).toMatch(/real ground/i);
  });

  it("boostLiveActionShotPlan SET'i live positive + PLACE LOCK ile guclendirir", () => {
    const base = composeShotPrompt(sampleClip(), 8, undefined, detectSongWorld(FOREST_LYRIC));
    const boosted = boostLiveActionShotPlan(base, FOREST_LYRIC, "orman sarkisi");
    expect(boosted).toMatch(/REAL sunlit FOREST/i);
    expect(boosted).toMatch(/LIVE PLACE LOCK/);
    expect(boosted).toMatch(/costumed mascot performers/i);
  });
});

describe("Soz → gorsel sahneleme (tirnaksiz)", () => {
  it("kelebek ucar icin kelebek + ucus cikarir", () => {
    const beats = extractSongPictureBeats(FOREST_LYRIC).map((b) => b.key);
    expect(beats).toEqual(expect.arrayContaining(["butterfly", "flying", "forest", "friends"]));
    expect(mustShowFromAudio(FOREST_LYRIC)).toMatch(/butterfly/i);
    expect(extractLyricContentWords(FOREST_LYRIC).length).toBeGreaterThan(2);
  });

  it("staging satiri Ingilizce ve tirnaksizdir", () => {
    const staging = formatLyricStagingLine(FOREST_LYRIC, "extra AI props");
    expect(staging).toMatch(/butterfly/i);
    expect(staging).toMatch(/forest/i);
    expect(staging).not.toContain('"');
  });

  it("saniye-saniye plan soz metnini alintilamaz", () => {
    const timeline = buildLyricActionTimeline({ lyrics: FOREST_LYRIC, seconds: 8, isFirstClip: false });
    expect(timeline).toMatch(/^0s: match-on-action from the previous clip/m);
    expect(timeline).toMatch(/butterfly|flying/i);
    expect(timeline).not.toContain('"');
    expect(timeline).toMatch(/7-8s:/);
  });
});

describe("Kahraman nesne (hero prop)", () => {
  const CUCUMBER_SONG = [
    "Bahçede uyandım, yeşil bir minik",
    "Salatalık büyüyor, uzun mu uzun",
    "Salatalığı sula, güneşe göster",
    "Salatalık dostumuz, hadi gel",
    "Dans et salatalıkla, gülümse",
  ].join("\n");

  it("salatalik sarkisinda kahraman nesneyi cucumber olarak bulur", () => {
    const hero = detectHeroSubject(CUCUMBER_SONG, "Salatalık Şarkısı");
    expect(hero).not.toBeNull();
    expect(hero!.label).toBe("cucumber");
    expect(lyricsNameHero("Salatalık büyüyor", hero)).toBe(true);
    expect(lyricsNameHero("Bahçede uyandım", hero)).toBe(false);
  });

  it("tekrar eden nesnesi olmayan sarkida kahraman dayatmaz", () => {
    expect(detectHeroSubject("Bahçede uyandım bugün hava çok güzel", "")).toBeNull();
  });

  it("mekan kelimesi (orman) kahraman nesne sayilmaz", () => {
    const hero = detectHeroSubject("Ormanda dostlar var\nOrmanda dostlar var\nOrmanda dostlar var", "Orman");
    expect(hero?.label ?? null).not.toBe("forest");
  });

  it("composeShotPrompt kahramani adli klipte merkeze, digerinde on planda tutar", () => {
    const hero = detectHeroSubject(CUCUMBER_SONG, "Salatalık Şarkısı");
    const named = composeShotPrompt(
      sampleClip({ lyrics: "Salatalık büyüyor, uzun mu uzun" }),
      8,
      undefined,
      null,
      hero
    );
    expect(named).toContain("HERO WITH LEAD");
    expect(named).toMatch(/CUCUMBER|cucumber/i);
    expect(named).toMatch(/center stage/i);
    expect(named).toMatch(/shares EVERY frame/i);

    const unnamed = composeShotPrompt(
      sampleClip({ lyrics: "Bahçede uyandım, hadi gel" }),
      8,
      undefined,
      null,
      hero
    );
    expect(unnamed).toContain("HERO WITH LEAD");
    expect(unnamed).toMatch(/never off-screen/i);
  });

  it("minik balik sarkisinda fish kahramani lead ile birlikte kilitlenir", () => {
    const song = [
      "Minik balık suda yüzer",
      "Balık balık hopla",
      "Minik balık dostum",
      "Balıklarla dans edelim",
    ].join("\n");
    const hero = detectHeroSubject(song, "Minik Balık");
    expect(hero).not.toBeNull();
    expect(hero!.label).toBe("fish");
    expect(lyricsNameHero("Balığın kuyruğu sallanır", hero)).toBe(true);

    const shot = composeShotPrompt(
      sampleClip({ lyrics: "Minik balık suda yüzer", singerName: "Luluma" }),
      8,
      undefined,
      detectSongWorld(song),
      hero
    );
    expect(shot).toMatch(/HERO WITH LEAD/);
    expect(shot).toMatch(/LITTLE FISH|fish/i);
    expect(shot).toMatch(/Luluma shares EVERY frame/i);
    expect(shot).toMatch(/STAGE EVERY SUNG WORD[\s\S]*fish/i);
  });

  it("baslikta balik geciyorsa az tekrarda bile kahraman olur", () => {
    const hero = detectHeroSubject("Suda yüzer hoplar\nHadi gel birlikte", "Minik Balık Şarkısı");
    expect(hero?.label).toBe("fish");
  });
});

describe("composeShotPrompt — temiz cekirdek", () => {
  it("soz yalnizca BIR kez tirnaklanir, dunya kilidi yazilir", () => {
    const shot = composeShotPrompt(sampleClip(), 8, undefined, detectSongWorld(FOREST_LYRIC));
    const quoteCount = (shot.match(/"/g) || []).length;
    expect(quoteCount).toBe(2);
    expect(shot).toContain("SONG LINE THIS CLIP");
    expect(shot).toContain(FOREST_LYRIC);
    expect(shot).toMatch(/NEVER show: .*mountain/i);
    expect(shot).toMatch(/STAGE EVERY SUNG WORD/);
    expect(shot).toMatch(/ACTION TIMELINE 0-8s/);
    expect(shot).not.toMatch(/WORD-BY-WORD/);
  });

  it("dunya ile celisen ortami dusurur", () => {
    const shot = composeShotPrompt(
      sampleClip({ environment: "mountain peak with snow" }),
      8,
      undefined,
      detectSongWorld(FOREST_LYRIC)
    );
    expect(shot).not.toMatch(/mountain peak with snow/);
    expect(shot).toMatch(/FOREST/);
  });
});

describe("buildClipPrompt — kids_song sifirdan mimari", () => {
  const ctx = {
    project: {
      templateType: "kids_song",
      speechLanguage: "Türkçe",
      promptTemplate: "",
      useFlowCharacter: true,
      aspectRatio: "16:9",
      visualStyle: "pixar3d",
      allowSubtitles: false,
      emotionCurve: "",
      clipSeconds: 8,
      useReference: true,
    },
    character: {
      name: "Axo Işıl",
      baseAppearancePrompt: "pink axolotl mascot, round face, frilly gills",
      baseWardrobePrompt: "yellow vest",
      baseEnvironmentPrompt: "forest path",
      baseCameraPrompt: "",
      baseVoicePrompt: "warm",
      negativePrompt: "",
      flowCharacterReference: "@Axo Işıl",
    },
    supportingCast: [
      {
        name: "Pıt Pıt Tavşan",
        role: "support",
        storyRole: "support",
        baseAppearancePrompt: "soft grey bunny with long ears",
        baseWardrobePrompt: "",
        flowCharacterReference: "@Pıt Pıt Tavşan",
      },
    ],
    clip: {
      dialogue: FOREST_LYRIC,
      index: 4,
      sceneDescription: "Kelebek",
      voiceTone: "bright",
      emotionLabel: "neseli",
      imagePrompt: composeShotPrompt(sampleClip({ index: 4 }), 8, undefined, detectSongWorld(FOREST_LYRIC)),
    },
    isFirstClip: false,
  } as unknown as Parameters<typeof buildClipPrompt>[0];

  it("kisa, bolumlu ve kesilmeden Flow'a sigar", () => {
    const prompt = buildClipPrompt(ctx);
    expect(prompt).toContain("[ANIMATED SONG FILM — CLIP 4");
    expect(prompt).toContain("[CAST — LOCKED EVERY FRAME]");
    expect(prompt).toContain("[STYLE]");
    expect(prompt).toContain("[PERFORMANCE — SHOT PLAN]");
    expect(prompt).toContain("[AUDIO]");
    expect(prompt).toContain("Axo Işıl");
    expect(prompt).toContain("Pıt Pıt Tavşan");
    expect(prompt).toMatch(/match-on-action/);

    const stamped = stampNoOnscreenTextLock(prompt);
    expect(stamped).toMatch(/\[SABIT KURAL — ALTYAZI YOK\]/);
    expect(stamped).toMatch(/\[SABIT KURAL SONU — ALTYAZI YOK\]/);
    expect(stamped).toMatch(/NO text at the TOP/i);
    expect(stamped).toMatch(/NO text at the BOTTOM/i);
    expect(stamped.length).toBeLessThan(FLOW_PROMPT_MAX);

    const { text, truncated } = compactPromptForFlow(stamped, "Türkçe", FLOW_PROMPT_MAX);
    expect(truncated).toBe(false);
    expect(text).toContain(FOREST_LYRIC);
    expect(text).toMatch(/NEVER show: .*mountain/i);
    // Soz iceren tek tirnakli blok kalmali — karaoke sinyali yok
    expect((text.match(/"/g) || []).length).toBeLessThanOrEqual(4);
  });

  it("eski dev bloklar ve tirnakli kelime haritasi artik yok", () => {
    const prompt = buildClipPrompt(ctx);
    expect(prompt).not.toMatch(/WORD-BY-WORD/);
    expect(prompt).not.toMatch(/SONG PICTURE CONFIRM/);
    expect(prompt).not.toMatch(/steam-sprite/i);
  });

  it("asiri uzun promptta bile sabit bloklar (soz, kadro, audio, yasak) dusmez", () => {
    const bloated = `${stampNoOnscreenTextLock(buildClipPrompt(ctx))}\n\n[STYLE]\n${"ultra detailed style words ".repeat(400)}`;
    const { text, truncated } = compactPromptForFlow(bloated, "Türkçe", 6500);
    expect(truncated).toBe(true);
    expect(text).toContain("[ANIMATED SONG FILM");
    expect(text).toContain("[CAST — LOCKED EVERY FRAME]");
    expect(text).toContain("[AUDIO]");
    expect(text).toContain("SONG LINE THIS CLIP");
    expect(text).toContain(FOREST_LYRIC);
    expect(text).toMatch(/\[SABIT KURAL — ALTYAZI YOK\]/);
    expect(text).toMatch(/\[SABIT KURAL SONU — ALTYAZI YOK\]/);
    expect(text.length).toBeLessThanOrEqual(6500);
  });
});
