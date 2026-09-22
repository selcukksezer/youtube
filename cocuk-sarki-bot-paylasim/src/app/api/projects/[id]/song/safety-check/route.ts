import { handle } from "@/server/lib/api";
import { runSongSafetyCheck } from "@/server/services/song";

export const runtime = "nodejs";
export const maxDuration = 300;

type Params = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    return runSongSafetyCheck(id);
  });
}
