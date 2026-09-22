import { z } from "zod";
import { handle } from "@/server/lib/api";
import { applyCharacterNote, generateCharacterImage, getOrCreateMainCharacter } from "@/server/services/character";
import { generateCharacterImageWithFlow } from "@/server/services/character-flow";

export const runtime = "nodejs";
export const maxDuration = 900;

type Params = { params: Promise<{ id: string }> };

const schema = z.object({
  customPrompt: z.string().optional(),
  notes: z.string().optional(),
  /** openai = gpt-image-1 (hizli), flow = kisa video uretip kare alir (klip estetigiyle ayni) */
  source: z.enum(["openai", "flow"]).default("openai"),
});

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const body = schema.parse(await request.json().catch(() => ({})));
    const main = await getOrCreateMainCharacter(id);
    const note = (body.notes || main.storyNote || "").trim();
    if (note) await applyCharacterNote(id, note);
    return body.source === "flow"
      ? generateCharacterImageWithFlow(id, body.customPrompt)
      : generateCharacterImage(id, body.customPrompt);
  });
}
