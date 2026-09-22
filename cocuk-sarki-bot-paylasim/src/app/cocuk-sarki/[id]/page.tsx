import { redirect } from "next/navigation";
import { ProjectWorkspace } from "@/components/project/project-workspace";

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string | string[] }>;
};

const KEEP_WORKSPACE_TABS = new Set(["settings", "publish"]);

/** Studyo sihirbazi atlanir — asil is uretim sayfasinda (MP3 + soz → klip). */
export default async function KidsSongWorkspacePage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const raw = (await searchParams).tab;
  const tab = Array.isArray(raw) ? raw[0] : raw;
  if (!tab || !KEEP_WORKSPACE_TABS.has(tab)) {
    redirect(`/cocuk-sarki/${id}/render`);
  }
  return <ProjectWorkspace projectId={id} />;
}
