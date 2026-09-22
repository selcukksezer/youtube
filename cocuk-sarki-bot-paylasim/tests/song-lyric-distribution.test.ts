import { describe, expect, it } from "vitest";
import { distributeLyricLines, segmentLyricsForClips } from "@/server/services/song";
import { songClipAudioWindow, songClipCount } from "@/lib/song-clip-timeline";

function lines(n: number): string[] {
  return Array.from({ length: n }, (_, i) => `satir ${i + 1}`);
}

function weight(line: string): number {
  return Math.max(1, (line.toLocaleLowerCase("tr-TR").match(/[aeıioöuüâîû]/g) || []).length);
}

describe("Soz satirlarinin kliplere dengeli dagitimi", () => {
  it("84 satiri 20 klibe bosluk BIRAKMADAN dagitir (eski hata: son 3 klip bos)", () => {
    const out = distributeLyricLines(lines(84), 20);
    expect(out).toHaveLength(20);
    expect(out.every((slice) => slice.length > 0)).toBe(true);
    // tum satirlar tam bir kez kullanilir
    const flat = out.flat();
    expect(flat).toHaveLength(84);
    expect(new Set(flat).size).toBe(84);
  });

  it("satirlar tam bolunuyorsa esit dagitir", () => {
    const out = distributeLyricLines(lines(40), 10);
    expect(out.every((slice) => slice.length === 4)).toBe(true);
  });

  it("uzun ve kisa satirlar karisikken agirligi dengeler (ne tasma ne bosluk)", () => {
    const mixed = [
      "Bugun bahcede kocaman kirmizi domatesleri hep birlikte topluyoruz",
      "Hey!",
      "Hop!",
      "Minik ayaklar masanin ustunde tak tak tak diye zipliyor",
      "Dom dom domates",
      "Zip!",
      "Kirmizi domates hey hey hey hop hop hopla zipla",
      "Bir daha!",
    ];
    const out = distributeLyricLines(mixed, 4);
    expect(out).toHaveLength(4);
    expect(out.every((s) => s.length > 0)).toBe(true);
    const weights = out.map((s) => s.reduce((sum, l) => sum + weight(l), 0));
    const max = Math.max(...weights);
    const min = Math.min(...weights);
    // Eski satir-esasli dagitimda bu oran 5x'e cikiyordu
    expect(max / min).toBeLessThan(2.2);
  });

  it("satir sayisi klipten azken tekrarlari sona yigmaz, yayar", () => {
    const out = distributeLyricLines(["ilk soz", "orta soz", "son soz"], 6);
    expect(out).toHaveLength(6);
    expect(out.every((slice) => slice.length === 1)).toBe(true);
    // ilk klipler ilk sozu, son klipler son sozu alir
    expect(out[0]![0]).toBe("ilk soz");
    expect(out[5]![0]).toBe("son soz");
    // son satir 4 kez tekrar etmez
    const lastCount = out.filter((s) => s[0] === "son soz").length;
    expect(lastCount).toBeLessThanOrEqual(2);
  });

  it("az sayida uzun satiri cumlelere bolerek klip basina birim uretir", () => {
    const out = distributeLyricLines(["Hop hop hopla! Zip zip zipla! Dom dom domates!"], 3);
    expect(out).toHaveLength(3);
    const flat = out.flat();
    expect(new Set(flat).size).toBeGreaterThan(1);
  });

  it("hicbir klip penceresi klip suresini asmaz ve arada bosluk kalmaz", () => {
    for (const [dur, clipSeconds] of [
      [161.72, 8],
      [164.9, 8],
      [90, 8],
      [100, 6],
      [8.4, 8],
      [37.5, 4],
    ] as Array<[number, number]>) {
      const count = songClipCount(dur, clipSeconds);
      const windows = Array.from({ length: count }, (_, i) =>
        songClipAudioWindow({ index: i + 1, clipCount: count, clipSeconds, audioDurationSeconds: dur })
      );
      // 1) Hicbir pencere klip suresini asmaz -> panel uyarisi olusmaz
      for (const w of windows) {
        expect(w.durationSeconds).toBeLessThanOrEqual(clipSeconds + 0.001);
      }
      // 2) Pencereler ucu uca eklenir (bosluk/bindirme yok)
      expect(windows[0]!.startSeconds).toBeCloseTo(0, 5);
      for (let i = 1; i < windows.length; i++) {
        expect(windows[i]!.startSeconds).toBeCloseTo(windows[i - 1]!.endSeconds, 5);
      }
      // 3) Parcanin sonuna kadar kapsanir
      expect(windows[windows.length - 1]!.endSeconds).toBeCloseTo(dur, 5);
      // 4) Cok kisa artik klip olusmaz (Flow minimumu)
      const shortest = Math.min(...windows.map((w) => w.durationSeconds));
      if (count > 1) expect(shortest).toBeGreaterThan(clipSeconds / 2);
    }
  });

  it("161.7 sn / 8 sn -> 21 klip ve son klip 8 sn'yi asmaz (eski hata: 9.7 sn)", () => {
    const count = songClipCount(161.72, 8);
    expect(count).toBe(21);
    const last = songClipAudioWindow({ index: count, clipCount: count, clipSeconds: 8, audioDurationSeconds: 161.72 });
    expect(last.durationSeconds).toBeLessThanOrEqual(8);
    expect(last.endSeconds).toBeCloseTo(161.72, 5);
  });

  it("segmentLyricsForClips her klibe gercek soz verir", () => {
    const lyrics = [
      "[Verse]",
      ...Array.from({ length: 84 }, (_, i) => `Dom dom domates ${i + 1}`),
    ].join("\n");
    const clips = segmentLyricsForClips(lyrics, 20, "3-5");
    expect(clips).toHaveLength(20);
    expect(clips.every((c) => c.lyrics.trim().length > 0)).toBe(true);
    // son klip artik ilk kliplerle AYNI tekrar satiri olmasin
    expect(clips[19]!.lyrics).not.toBe(clips[18]!.lyrics);
    expect(clips[19]!.lyrics).toContain("84");
  });
});
