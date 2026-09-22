import { z } from "zod";
import { handle } from "@/server/lib/api";
import { renderProject, getLatestRenderReport, listFinalRenders } from "@/server/services/render";
import { FfmpegCancelledError } from "@/server/services/ffmpeg";
import { RenderCancelledError } from "@/server/services/render-jobs";

export const runtime = "nodejs";
export const maxDuration = 1800;

type Params = { params: Promise<{ id: string }> };

const renderSchema = z.object({
  mode: z.enum(["direct", "reencode", "auto"]).default("auto"),
  audioFadeMs: z.number().int().min(0).max(300).default(0),
  trimSilence: z.boolean().default(false),
  trimBlack: z.boolean().default(false),
  outputResolution: z.enum(["source", "1080", "1440", "2160"]).default("source"),
});

function isCancelError(err: unknown): boolean {
  return err instanceof FfmpegCancelledError || err instanceof RenderCancelledError;
}

export async function POST(request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const body = renderSchema.parse(await request.json().catch(() => ({})));
    try {
      return await renderProject(id, body);
    } catch (err) {
      if (isCancelError(err)) {
        return {
          cancelled: true as const,
          message: "Birlestirme iptal edildi",
          jobId: err instanceof RenderCancelledError ? err.jobId : undefined,
        };
      }
      throw err;
    }
  });
}

export async function GET(_request: Request, { params }: Params) {
  return handle(async () => {
    const { id } = await params;
    const [report, finals] = await Promise.all([getLatestRenderReport(id), listFinalRenders(id)]);
    return { report, finals };
  });
}
