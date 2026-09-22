import { handle } from "@/server/lib/api";
import { createQuickSongProject } from "@/server/services/projects";

export const runtime = "nodejs";

export async function POST() {
  return handle(async () => {
    const project = await createQuickSongProject();
    return { id: project.id, slug: project.slug, name: project.name };
  });
}
