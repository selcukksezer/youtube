import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { pickCastReferencePaths } from "@/server/services/kids";

describe("Sabit kadro referans gorselleri", () => {
  it("sahnedeki kadronun referans yollarini ana once toplar", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cast-ref-"));
    const mainImg = path.join(dir, "main.png");
    const sideImg = path.join(dir, "side.png");
    fs.writeFileSync(mainImg, "x");
    fs.writeFileSync(sideImg, "y");

    const { paths, missingNames } = pickCastReferencePaths(
      [
        { id: "1", name: "Sunny", role: "main", referenceImagePath: mainImg },
        { id: "2", name: "Topo", role: "side", referenceImagePath: sideImg },
        { id: "3", name: "Mavi", role: "side", referenceImagePath: null },
      ],
      "Arama\n[Kadro: Sunny, Topo, Mavi]",
      "Sunny and Topo climb",
      3
    );

    expect(paths).toEqual([mainImg, sideImg]);
    expect(missingNames).toContain("Mavi");
  });
});
