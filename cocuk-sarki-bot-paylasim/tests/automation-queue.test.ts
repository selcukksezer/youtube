import { describe, expect, it } from "vitest";
import { enqueueProjectWork } from "@/server/automation/abort";

describe("enqueueProjectWork", () => {
  it("ayni proje islerini siraya dizer", async () => {
    const order: number[] = [];
    const first = enqueueProjectWork("proj-a", async () => {
      await new Promise((r) => setTimeout(r, 40));
      order.push(1);
      return "one";
    });
    const second = enqueueProjectWork("proj-a", async () => {
      order.push(2);
      return "two";
    });
    await expect(Promise.all([first, second])).resolves.toEqual(["one", "two"]);
    expect(order).toEqual([1, 2]);
  });

  it("farkli projeleri paralel birakir", async () => {
    let aStarted = false;
    const a = enqueueProjectWork("proj-b", async () => {
      aStarted = true;
      await new Promise((r) => setTimeout(r, 50));
      return "a";
    });
    const b = enqueueProjectWork("proj-c", async () => {
      expect(aStarted).toBe(true);
      return "b";
    });
    await expect(Promise.all([a, b])).resolves.toEqual(["a", "b"]);
  });

  it("onceki is hata verse bile sonrakini calistirir", async () => {
    const failed = enqueueProjectWork("proj-d", async () => {
      throw new Error("boom");
    });
    const next = enqueueProjectWork("proj-d", async () => "ok");
    await expect(failed).rejects.toThrow("boom");
    await expect(next).resolves.toBe("ok");
  });
});
