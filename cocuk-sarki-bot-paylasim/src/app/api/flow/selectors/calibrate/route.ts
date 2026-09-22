import { z } from "zod";
import { handle } from "@/server/lib/api";
import { calibrateSelectorByClick, resetSelector } from "@/server/automation/calibration";

export const runtime = "nodejs";
export const maxDuration = 300;

const schema = z.object({
  key: z.string().min(1),
  /** true: kalibrasyonu sil, yerlesik yedeklere don */
  reset: z.boolean().optional(),
});

/** Tikla-tanit kalibrasyonu baslatir (60 sn icinde Flow'da hedefe tiklanmali). */
export async function POST(request: Request) {
  return handle(async () => {
    const body = schema.parse(await request.json().catch(() => ({})));
    if (body.reset) return resetSelector(body.key);
    return calibrateSelectorByClick(body.key);
  });
}
