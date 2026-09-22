import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { pickSongCastReferencePaths, resolveClipCastMembers } from "@/server/services/song-refs";

describe("pickSongCastReferencePaths", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "song-ref-"));
  const lead = path.join(dir, "lead.png");
  const pal = path.join(dir, "pal.png");
  fs.writeFileSync(lead, "a");
  fs.writeFileSync(pal, "b");
  const cast = [
    { id: "1", name: "Dom Dom", referenceImagePath: lead },
    { id: "2", name: "Pofuduk", referenceImagePath: pal },
  ];

  it("referans acikken soyleyeni once, sonra kadroyu verir", () => {
    expect(pickSongCastReferencePaths(cast, cast[0], true, false)).toEqual([lead, pal]);
  });

  it("Flow @karakter aciksa PNG yolu vermez (video yerine karakter yuklenmesin)", () => {
    expect(pickSongCastReferencePaths(cast, cast[0], true, true)).toEqual([]);
  });

  it("referans kapaliysa bos doner", () => {
    expect(pickSongCastReferencePaths(cast, cast[0], false, false)).toEqual([]);
  });
});

describe("resolveClipCastMembers", () => {
  const buyukKadro = [
    { id: "2", name: "Pıtpıt" },
    { id: "3", name: "Pofuduk" },
    { id: "4", name: "TıkTık" },
  ];

  it("metinde adi gecen karakteri bulur, digerlerini almaz", () => {
    const result = resolveClipCastMembers("Zıpla! Tak tak tak! TıkTık üç vuruş yapar.", buyukKadro);
    expect(result.map((c) => c.name)).toEqual(["TıkTık"]);
  });

  it("hic ad gecmiyorsa ve kadro genisse bos doner (solo sahne)", () => {
    const result = resolveClipCastMembers("Dom dom domates! Hey hey, domates!", buyukKadro);
    expect(result).toEqual([]);
  });

  it("grup sinyali varsa (arkadaslar/beraber) tum kadroyu doner", () => {
    const result = resolveClipCastMembers("Hep birlikte arkadaslarla dans ederiz", buyukKadro);
    expect(result.map((c) => c.name)).toEqual(["Pıtpıt", "Pofuduk", "TıkTık"]);
  });

  it("kucuk kadroda (<=2 destek) ad gecmese de hepsini doner", () => {
    const kucukKadro = [
      { id: "2", name: "Pıtpıt" },
      { id: "3", name: "Pofuduk" },
    ];
    const result = resolveClipCastMembers("Dom dom domates! Hey hey, domates!", kucukKadro);
    expect(result.map((c) => c.name)).toEqual(["Pıtpıt", "Pofuduk"]);
  });

  it("adsiz kadro girisini yok sayar", () => {
    const result = resolveClipCastMembers("herhangi bir metin", [{ id: "9", name: "" }]);
    expect(result).toEqual([]);
  });
});
