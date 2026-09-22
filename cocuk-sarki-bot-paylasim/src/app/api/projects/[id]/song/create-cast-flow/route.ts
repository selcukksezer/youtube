import { handle } from "@/server/lib/api";
import { bulkCreateSongCastViaFlow } from "@/server/services/song-cast";

export const runtime = "nodejs";
export const maxDuration = 2400;

type Params = { params: Promise<{ id: string }> };

/** Flow ile AI kadrosunu sirayla olusturur. */
export async function POST(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    return bulkCreateSongCastViaFlow(id);
  });
}
