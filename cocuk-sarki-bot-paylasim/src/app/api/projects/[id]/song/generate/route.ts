import { z } from "zod";
import { handle } from "@/server/lib/api";
import { generateSong, loadSongPackage } from "@/server/services/song";

export const runtime = "nodejs";
export const maxDuration = 600;

type Params = { params: Promise<{ id: string }> };

const schema = z.object({ title: z.string().optional() });

export async function GET(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    return loadSongPackage(id);
  });
}

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const body = schema.parse(await request.json().catch(() => ({})));
    return generateSong(id, body.title);
  });
}
