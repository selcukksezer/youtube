import { handle } from "@/server/lib/api";
import { checkSessionStatusCached, isBrowserOpen } from "@/server/automation/browser";

export const runtime = "nodejs";

export async function GET() {
  return handle(async () => {
    const session = await checkSessionStatusCached();
    return { ...session, browserOpen: isBrowserOpen() };
  });
}
