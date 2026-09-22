import { handle } from "@/server/lib/api";
import { planSongCastFromProject } from "@/server/services/song-cast";

export const runtime = "nodejs";
export const maxDuration = 300;

type Params = { params: Promise<{ id: string }> };

/** Sarki sozlerinden AI ile sabit karakter kadrosu cikarir. */
export async function POST(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    return planSongCastFromProject(id);
  });
}
