import { handle } from "@/server/lib/api";
import { SONG_THEMES, SONG_STYLES } from "@/server/services/song";

export const runtime = "nodejs";

export async function GET() {
  return handle(async () => ({ themes: SONG_THEMES, styles: SONG_STYLES }));
}
