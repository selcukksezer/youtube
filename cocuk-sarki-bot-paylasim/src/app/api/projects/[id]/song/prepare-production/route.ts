import { z } from "zod";
import { handle } from "@/server/lib/api";
import { prepareSongProduction } from "@/server/services/song";

export const runtime = "nodejs";
export const maxDuration = 1200;

type Params = { params: Promise<{ id: string }> };

const schema = z.object({ formattedLyrics: z.string().optional() }).optional();

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const body = schema.parse(await request.json().catch(() => ({})));
    return prepareSongProduction(id, body?.formattedLyrics);
  });
}
