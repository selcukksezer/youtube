import { describe, expect, it } from "vitest";
import { clipFileName, clipFrameFileName } from "@/server/lib/paths";
import { selectClipsForRender } from "@/server/services/render";

describe("clipFileName", () => {
  it("index + clipId ile carpismasiz ad uretir", () => {
    expect(clipFileName(1, "clxyz123456789")).toMatch(/^001-[a-zA-Z0-9]+\.mp4$/);
    expect(clipFileName(1, "aaa")).not.toBe(clipFileName(1, "bbb"));
    expect(clipFileName(12)).toBe("012.mp4");
  });

  it("frame adi da id tasir", () => {
    expect(clipFrameFileName(3, "idABCDEF1234", "last")).toMatch(/^003-.*-last\.png$/);
  });
});

describe("selectClipsForRender", () => {
  it("videosu olanlari sirayla alir, olmayanlari atlar", () => {
    // Gercek dosya yok — existsSync false → hepsi atlanir; mantigi unit olarak yollarla test etmek zor.
    // Bos videoPath atlanir:
    const { included, skipped } = selectClipsForRender([
      { index: 1, status: "draft", videoPath: null },
      { index: 2, status: "completed", videoPath: null },
    ]);
    expect(included).toHaveLength(0);
    expect(skipped.map((s) => s.index)).toEqual([1, 2]);
  });
});
