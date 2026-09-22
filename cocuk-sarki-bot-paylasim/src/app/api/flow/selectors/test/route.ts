import { handle } from "@/server/lib/api";
import { runSelectorTest } from "@/server/automation/calibration";

export const runtime = "nodejs";
export const maxDuration = 300;

/** Acik Flow sayfasinda tum secicileri dener; kayit yapmaz, rapor doner. */
export async function POST() {
  return handle(() => runSelectorTest());
}
