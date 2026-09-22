import { handle } from "@/server/lib/api";
import { purgeLegacyProjects } from "@/server/services/projects";

export const runtime = "nodejs";

export async function POST() {
  return handle(async () => purgeLegacyProjects(true));
}
