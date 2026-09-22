import { z } from "zod";
import { handle } from "@/server/lib/api";
import { runAutoCalibration } from "@/server/automation/calibration";

export const runtime = "nodejs";
export const maxDuration = 300;

const schema = z
  .object({
    editorUrl: z.string().url().optional(),
  })
  .optional();

/** Video editoru + karakterler sayfasinda oncelikli secicileri otomatik kalibre eder. */
export async function POST(request: Request) {
  return handle(async () => {
    const body = schema.parse(await request.json().catch(() => ({})));
    return runAutoCalibration({ editorUrl: body?.editorUrl });
  });
}
