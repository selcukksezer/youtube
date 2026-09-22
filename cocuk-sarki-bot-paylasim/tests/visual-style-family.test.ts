import { describe, expect, it } from "vitest";
import {
  convertShotPlanToLiveAction,
  LIVE_ACTION_SONG_REALISM,
  visualStyleFamilyOf,
  worldFamilyLock,
} from "@/lib/visual-style-family";

describe("Gorsel stil ailesi cozumu", () => {
  it("preset id'leri kesin eslesir", () => {
    expect(visualStyleFamilyOf("kids_song", "photorealistic")).toBe("live-action");
    expect(visualStyleFamilyOf("kids_song", "cinematic")).toBe("live-action");
    expect(visualStyleFamilyOf("kids_song", "documentary")).toBe("live-action");
    expect(visualStyleFamilyOf("kids_song", "pixar3d")).toBe("cgi3d");
    expect(visualStyleFamilyOf("kids_song", "anime")).toBe("anime2d");
  });

  it("Turkce serbest metin 'gercekci canli cekim' canli-cekim sayilir", () => {
    expect(visualStyleFamilyOf("kids_song", "gerçekçi canlı çekim")).toBe("live-action");
    expect(visualStyleFamilyOf("kids_song", "gercekci canli cekim")).toBe("live-action");
    expect(visualStyleFamilyOf("kids_animation", "canlı çekim gibi olsun")).toBe("live-action");
  });

  it("serbest 3D/anime metinleri dogru aileye gider", () => {
    expect(visualStyleFamilyOf("kids_song", "3d pixar tarzi animasyon")).toBe("cgi3d");
    expect(visualStyleFamilyOf("kids_song", "anime tarzi")).toBe("anime2d");
  });

  it("bos stilde cocuk 3D, anlatici canli cekim varsayar", () => {
    expect(visualStyleFamilyOf("kids_song", "")).toBe("cgi3d");
    expect(visualStyleFamilyOf("kids_animation", null)).toBe("cgi3d");
    expect(visualStyleFamilyOf("narrator", "")).toBe("live-action");
  });
});

describe("Dunya ailesi kilidi", () => {
  it("canli cekim kilidi CGI/karikatur karisimini yasaklar", () => {
    const lock = worldFamilyLock("live-action");
    expect(lock).toMatch(/100% LIVE-ACTION/i);
    expect(lock).toMatch(/EVERY character/);
    expect(lock).toMatch(/BANNED.*3D CGI/i);
    expect(lock).toMatch(/real costumed mascot performers/i);
  });

  it("3D kilidi canli cekim/fotograf karisimini yasaklar", () => {
    const lock = worldFamilyLock("cgi3d");
    expect(lock).toMatch(/100% STYLIZED 3D ANIMATION/i);
    expect(lock).toMatch(/BANNED.*live-action footage/i);
    expect(lock).toMatch(/photographic humans/i);
    // Arka planlar da kahraman kadar islenmeli (duz karton panel yasagi)
    expect(lock).toMatch(/backgrounds get the same modelling, texturing and lighting care/i);
  });

  it("anime kilidi 3D ve fotografi yasaklar", () => {
    const lock = worldFamilyLock("anime2d");
    expect(lock).toMatch(/100% 2D ANIME/i);
    expect(lock).toMatch(/BANNED.*live-action/i);
  });

  it("sarki icin kisa canli-cekim fizik kilidi golge/yansima/kumas icerir", () => {
    expect(LIVE_ACTION_SONG_REALISM).toMatch(/shadow/i);
    expect(LIVE_ACTION_SONG_REALISM).toMatch(/reflection/i);
    expect(LIVE_ACTION_SONG_REALISM).toMatch(/fabric/i);
    expect(LIVE_ACTION_SONG_REALISM).toMatch(/lyric places/i);
  });

  it("canli cekim kilidi soz mekanlarini gercek cografiya olarak vurgular", () => {
    const lock = worldFamilyLock("live-action");
    expect(lock).toMatch(/PERFORM ON the real geography/i);
    expect(lock).toMatch(/Lyric places/i);
  });
});

describe("Sahne planinin canli-cekime cevrimi", () => {
  it("3D/CGI ifadelerini canli-cekim diline cevirir", () => {
    const converted = convertShotPlanToLiveAction(
      "gloss cgi 3D animated music-video shot, stylized 3D mascot rendered with CGI lighting"
    );
    expect(converted).not.toMatch(/\b3d\b/i);
    expect(converted).not.toMatch(/\bcgi\b/i);
    expect(converted).toMatch(/live-action music-video shot/i);
    expect(converted).toMatch(/photographed/i);
  });

  it("canli-cekim disi kelimelere dokunmaz", () => {
    const text = "While singing: 'hop hop'. Camera pushes in as the mascot claps.";
    expect(convertShotPlanToLiveAction(text)).toBe(text);
  });
});
