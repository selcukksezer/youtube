import { handle } from "@/server/lib/api";
import { listSelectorStates } from "@/server/automation/calibration";

export const runtime = "nodejs";

/** Tum Flow secicilerinin kalibrasyon durumu. */
export async function GET() {
  return handle(() => listSelectorStates());
}
