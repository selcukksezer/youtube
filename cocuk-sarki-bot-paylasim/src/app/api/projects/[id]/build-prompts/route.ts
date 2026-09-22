import { handle } from "@/server/lib/api";
import { buildPromptsForProject } from "@/server/services/clips";

export const runtime = "nodejs";
export const maxDuration = 1200;

type Params = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    return buildPromptsForProject(id);
  });
}
