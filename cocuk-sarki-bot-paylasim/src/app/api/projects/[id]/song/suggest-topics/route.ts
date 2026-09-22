import { handle } from "@/server/lib/api";
import { suggestSongTopics } from "@/server/services/song";

export const runtime = "nodejs";
export const maxDuration = 180;

type Params = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    return suggestSongTopics(id);
  });
}
