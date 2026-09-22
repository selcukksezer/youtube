import { describe, expect, it } from "vitest";
import { formatSongClipBridge, songLipSyncLock } from "@/lib/song-prompt-craft";

const PREV_SHOT = [
  "Second-by-second action (0-8s): 0s: cold open, Sala mid-groove;",
  "3s: taps the cucumber prop; 6s: spins once on the boardwalk;",
  "7s-8s: last-syllable pose, hands still on the prop, soft handoff",
].join(" ");

const PREV_SHOT_TIMELINE = [
  "ACTION TIMELINE 0-8s (one continuous take):",
  "0s: exact match-on-action continuation of the previous clip's last frame",
  "1s: sung phrase 1 of the quoted line — Sala shows the cucumber",
  "6s: spin with arms wide, then point to the friends",
  "7-8s: last-syllable pose, then a soft handoff into the next clip",
  "",
  "SET (locked for the WHOLE song): a sunny boardwalk",
].join("\n");

describe("Klipler arasi kopma kilidi", () => {
  it("klip 1 cold open kurar ve onceki klipten bahsetmez", () => {
    const bridge = formatSongClipBridge({ clipIndex: 1, isFirstClip: true });
    expect(bridge).toMatch(/Cold open/i);
    expect(bridge).not.toMatch(/MATCH-ON-ACTION FROM CLIP/i);
    expect(bridge).toMatch(/no fade-in, no title card/i);
  });

  it("klip 2+ onceki klibin SOMUT bitisini prompta yazar", () => {
    const bridge = formatSongClipBridge({
      clipIndex: 4,
      isFirstClip: false,
      previousImagePrompt: PREV_SHOT,
      previousScene: "Sala boardwalk kenarinda arkadaslariyla zipliyor",
      previousEmotion: "neseli",
      previousVoiceTone: "bright and bouncy",
    });
    expect(bridge).toMatch(/MATCH-ON-ACTION FROM CLIP 3/);
    expect(bridge).toMatch(/Clip 3 ended on:/);
    expect(bridge).toMatch(/soft handoff/i);
    expect(bridge).toMatch(/Clip 3 beat:/);
    expect(bridge).toMatch(/neseli \/ bright and bouncy/);
  });

  it("kiyafet/mekan/isik degisimini ve yeniden tanisma acilisini yasaklar", () => {
    const bridge = formatSongClipBridge({ clipIndex: 2, isFirstClip: false, previousImagePrompt: PREV_SHOT });
    expect(bridge).toMatch(/FORBIDDEN AT THE CUT/);
    expect(bridge).toMatch(/new location/i);
    expect(bridge).toMatch(/changed or recoloured outfit/i);
    expect(bridge).toMatch(/re-introduction pose/i);
    expect(bridge).toMatch(/IDENTICAL: same location, camera side/);
  });

  it("sarki cekirdeginin ACTION TIMELINE bicimini de okur", () => {
    const bridge = formatSongClipBridge({
      clipIndex: 6,
      isFirstClip: false,
      previousImagePrompt: PREV_SHOT_TIMELINE,
    });
    expect(bridge).toMatch(/Clip 5 ended on:/);
    expect(bridge).toMatch(/handoff/i);
    expect(bridge).not.toMatch(/SET \(locked/);
    expect(bridge).not.toMatch(/ACTION TIMELINE/);
  });

  it("onceki veri eksikse bile kopma yasagi yazilir (cokmez)", () => {
    const bridge = formatSongClipBridge({ clipIndex: 5, isFirstClip: false });
    expect(bridge).toMatch(/MATCH-ON-ACTION FROM CLIP 4/);
    expect(bridge).toMatch(/FORBIDDEN AT THE CUT/);
    expect(bridge).not.toMatch(/ended on:/);
  });

  it("soz metnini TIRNAKLAMAZ (ekrana yazi riski)", () => {
    const bridge = formatSongClipBridge({
      clipIndex: 3,
      isFirstClip: false,
      previousImagePrompt: PREV_SHOT,
      previousScene: "sahne",
    });
    expect(bridge).not.toContain('"');
  });
});

describe("Dudak senkronu kilidi", () => {
  it("sozlu klipte hece-hece agiz kurallarini yazar", () => {
    const lock = songLipSyncLock({ seconds: 8, isFirstClip: true, singerName: "Sala", hasLyrics: true });
    expect(lock).toMatch(/MIME THE MASTER TRACK EXACTLY/);
    expect(lock).toContain("Sala");
    expect(lock).toMatch(/Each syllable gets its own visible mouth shape/i);
    expect(lock).toMatch(/last syllable inside the final second of this 8s clip/i);
    expect(lock).toMatch(/Turkish visemes/i);
  });

  it("klip 2+ agzin zaten cumle ortasinda oldugunu soyler", () => {
    const first = songLipSyncLock({ seconds: 8, isFirstClip: true, hasLyrics: true });
    const later = songLipSyncLock({ seconds: 8, isFirstClip: false, hasLyrics: true });
    expect(later).toMatch(/already mid-phrase from the previous clip/i);
    expect(first).not.toMatch(/already mid-phrase/i);
  });

  it("uydurma kelime, konusma ve seslendirmeyi yasaklar", () => {
    const lock = songLipSyncLock({ seconds: 8, isFirstClip: false, hasLyrics: true });
    expect(lock).toMatch(/extra or improvised words/i);
    expect(lock).toMatch(/speech, voice-over/i);
    expect(lock).toMatch(/rushing the line then standing mouth-closed/i);
    expect(lock).toMatch(/singing past its end/i);
  });

  it("sozsuz klipte agzi kapali tutar (rastgele ceneyi oynatmaz)", () => {
    const lock = songLipSyncLock({ seconds: 8, isFirstClip: false, singerName: "Sala", hasLyrics: false });
    expect(lock).toMatch(/INSTRUMENTAL SECONDS/);
    expect(lock).toMatch(/mouth stays closed/i);
    expect(lock).toMatch(/no random jaw flapping/i);
    expect(lock).not.toMatch(/Every sung syllable/i);
  });

  it("soz metnini TIRNAKLAMAZ", () => {
    const lock = songLipSyncLock({ seconds: 8, isFirstClip: false, singerName: "Sala", hasLyrics: true });
    expect(lock).not.toContain('"');
  });
});
