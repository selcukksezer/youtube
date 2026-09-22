import { z } from "zod";
import { handle } from "@/server/lib/api";
import { buildSongClips, songPackageSchema } from "@/server/services/song";

export const runtime = "nodejs";
export const maxDuration = 120;

type Params = { params: Promise<{ id: string }> };

const schema = z.object({ song: songPackageSchema.optional() });

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const body = schema.parse(await request.json().catch(() => ({})));
    return buildSongClips(id, body.song);
  });
}
