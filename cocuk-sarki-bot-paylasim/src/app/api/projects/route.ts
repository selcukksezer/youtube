import { handle } from "@/server/lib/api";
import { prisma } from "@/server/db";
import { createProject, createProjectSchema } from "@/server/services/projects";

export const runtime = "nodejs";

export async function GET() {
  return handle(async () => {
    const projects = await prisma.project.findMany({
      where: { templateType: "kids_song", parentProjectId: null },
      orderBy: { updatedAt: "desc" },
      include: {
        _count: { select: { clips: true } },
        clips: { where: { status: "completed" }, select: { id: true } },
        characters: { where: { role: "main" }, select: { name: true }, take: 1 },
      },
    });

    return projects.map((p) => ({
      id: p.id,
      name: p.name,
      slug: p.slug,
      title: p.title,
      genre: p.genre,
      templateType: p.templateType,
      status: p.status,
      targetDurationSeconds: p.targetDurationSeconds,
      clipCount: p._count.clips,
      completedClipCount: p.clips.length,
      createdAt: p.createdAt,
      updatedAt: p.updatedAt,
      mainCharacterName: p.characters[0]?.name ?? "",
    }));
  });
}

export async function POST(request: Request) {
  return handle(async () => {
    const body = createProjectSchema.parse(await request.json());
    return createProject(body);
  });
}
