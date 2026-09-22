"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "sonner";
import { Clapperboard, FolderOpen, Megaphone, Music2, SlidersHorizontal, User, Wand2 } from "lucide-react";
import { postJson, api } from "@/lib/client-api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, PageHeader, ProjectStatusBadge } from "@/components/shared";
import { NewSongProjectButton } from "@/components/new-song-project-button";
import type { ProjectData } from "@/components/project/types";
import { PromptsTab } from "@/components/project/prompts-tab";
import { PublishTab } from "@/components/project/publish-tab";
import { SongStudioTab } from "@/components/project/song-studio-tab";
import { SongCharacterTab } from "@/components/project/song-character-tab";
import { SettingsTab } from "@/components/project/settings-tab";
import { projectWorkspaceHref, templateLabel } from "@/lib/templates";

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const [project, setProject] = React.useState<ProjectData | null>(null);
  const [loadFailed, setLoadFailed] = React.useState(false);
  const [tab, setTab] = React.useState("studio");

  const reload = React.useCallback(async () => {
    const data = await api<ProjectData>(`/api/projects/${projectId}`, { silent: true });
    setProject(data);
    return data;
  }, [projectId]);

  React.useEffect(() => {
    reload()
      .then((data) => {
        if (data.templateType !== "kids_song") {
          toast.error("Bu proje cocuk sarki degil");
          router.replace("/cocuk-sarki");
          return;
        }
        const paramsTab = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("tab") : null;
        const expectedPath = projectWorkspaceHref(data);
        if (expectedPath !== pathname) {
          router.replace(paramsTab ? `${expectedPath}?tab=${paramsTab}` : expectedPath);
          return;
        }
        const allowed = new Set(["studio", "character", "prompts", "publish", "settings"]);
        if (paramsTab && allowed.has(paramsTab)) setTab(paramsTab);
      })
      .catch(() => {
        setLoadFailed(true);
        toast.error("Proje yuklenemedi");
      });
  }, [reload, router, pathname]);

  if (!project) {
    if (loadFailed) {
      return (
        <div>
          <PageHeader eyebrow="Proje" title="Proje bulunamadi" />
          <EmptyState
            icon={<FolderOpen className="h-6 w-6" />}
            title="Bu proje artik yok"
            description="Proje silinmis veya adres gecersiz olabilir."
            action={
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button onClick={() => router.push("/cocuk-sarki")}>
                  <FolderOpen className="h-4 w-4" /> Projeler
                </Button>
                <NewSongProjectButton />
              </div>
            }
          />
        </div>
      );
    }
    return (
      <div>
        <Skeleton className="h-10 w-80 mb-6" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  const renderHref = `/cocuk-sarki/${project.id}/render`;

  return (
    <div className="pb-16">
      <PageHeader
        eyebrow={templateLabel(project.templateType)}
        title={project.name}
        description={`Studyo · ${project.flowModel} · ${project.clipSeconds}sn klip · ${project.aspectRatio}`}
        actions={
          <>
            <ProjectStatusBadge status={project.status} />
            {project.clips.length > 0 && (
              <Link href={renderHref}>
                <Button variant="default" size="sm">
                  <Clapperboard className="h-3.5 w-3.5" /> Uretim ({project.clips.length} klip)
                </Button>
              </Link>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => postJson(`/api/projects/${project.id}/open-folder`).then(() => toast.success("Klasor acildi"))}
            >
              <FolderOpen className="h-3.5 w-3.5" /> Klasoru Ac
            </Button>
          </>
        }
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap">
          <TabsTrigger value="studio">
            <Music2 className="h-3.5 w-3.5" /> Studyo
          </TabsTrigger>
          <TabsTrigger value="character">
            <User className="h-3.5 w-3.5" /> Karakter
          </TabsTrigger>
          <TabsTrigger value="prompts">
            <Wand2 className="h-3.5 w-3.5" /> Promptlar
          </TabsTrigger>
          <TabsTrigger value="publish">
            <Megaphone className="h-3.5 w-3.5" /> Yayin
          </TabsTrigger>
          <TabsTrigger value="settings">
            <SlidersHorizontal className="h-3.5 w-3.5" /> Ayarlar
          </TabsTrigger>
        </TabsList>

        <TabsContent value="studio">
          <SongStudioTab project={project} reload={reload} />
        </TabsContent>
        <TabsContent value="character">
          <SongCharacterTab project={project} reload={reload} />
        </TabsContent>
        <TabsContent value="prompts">
          <PromptsTab project={project} reload={reload} />
        </TabsContent>
        <TabsContent value="publish">
          <PublishTab project={project} reload={reload} />
        </TabsContent>
        <TabsContent value="settings">
          <SettingsTab project={project} reload={reload} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
