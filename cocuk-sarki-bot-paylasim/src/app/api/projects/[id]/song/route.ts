import { handle } from "@/server/lib/api";
import { saveSongPackage, songPackageSchema } from "@/server/services/song";

export const runtime = "nodejs";

type Params = { params: Promise<{ id: string }> };

export async function PUT(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const body = songPackageSchema.parse(await request.json());
    return saveSongPackage(id, body);
  });
}
