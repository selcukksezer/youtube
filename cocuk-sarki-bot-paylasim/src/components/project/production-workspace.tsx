"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Clapperboard, Cpu, Megaphone, Pencil, Scissors, SlidersHorizontal, User, Wand2 } from "lucide-react";
import { api } from "@/lib/client-api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, PageHeader, ProjectStatusBadge } from "@/components/shared";
import type { EventData, ProjectData } from "@/components/project/types";
import { ClipsTab } from "@/components/project/clips-tab";
import { PromptsTab } from "@/components/project/prompts-tab";
import { AutomationTab } from "@/components/project/automation-tab";
import { RenderTab } from "@/components/project/render-tab";
import { SongCastPanel } from "@/components/project/song-cast-panel";
import { SongSourcePanel } from "@/components/project/song-source-panel";
import { RenameProjectDialog } from "@/components/project/rename-project-dialog";
import { projectWorkspaceHref, templateLabel } from "@/lib/templates";

export function ProductionWorkspace({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [project, setProject] = React.useState<ProjectData | null>(null);
  const [loadFailed, setLoadFailed] = React.useState(false);
  const [liveEvents, setLiveEvents] = React.useState<EventData[]>([]);
  const [tab, setTab] = React.useState("clips");
  const [renameOpen, setRenameOpen] = React.useState(false);

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
        }
      })
      .catch(() => {
        setLoadFailed(true);
        toast.error("Proje yuklenemedi");
      });
  }, [reload, router]);

  React.useEffect(() => {
    const source = new EventSource(`/api/projects/${projectId}/events`);
    // "job" olaylari uretim sirasinda pes pese gelir; her birinde tum proje
    // verisini (klipler + promptlar, yuzlerce KB) yeniden cekmek arayuzu
    // yavaslatir. 1 sn icinde tek yenilemeye indirgenir.
    let reloadTimer: ReturnType<typeof setTimeout> | null = null;
    const queueReload = () => {
      if (reloadTimer) return;
      reloadTimer = setTimeout(() => {
        reloadTimer = null;
        reload().catch(() => {});
      }, 1_000);
    };
    source.addEventListener("snapshot", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as { events: EventData[] };
      setLiveEvents(data.events);
    });
    source.addEventListener("event", (e) => {
      const event = JSON.parse((e as MessageEvent).data) as EventData;
      setLiveEvents((prev) => [...prev.slice(-199), event]);
    });
    source.addEventListener("clip", (e) => {
      const clip = JSON.parse((e as MessageEvent).data) as {
        id: string;
        status: string;
        attemptCount: number;
        errorMessage: string | null;
        videoPath: string | null;
      };
      setProject((prev) =>
        prev
          ? {
              ...prev,
              clips: prev.clips.map((c) =>
                c.id === clip.id
                  ? {
                      ...c,
                      status: clip.status,
                      attemptCount: clip.attemptCount,
                      errorMessage: clip.errorMessage,
                      videoPath: clip.videoPath ?? c.videoPath,
                    }
                  : c
              ),
            }
          : prev
      );
    });
    source.addEventListener("project", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as { status: string };
      setProject((prev) => (prev ? { ...prev, status: data.status } : prev));
    });
    source.addEventListener("job", queueReload);
    return () => {
      if (reloadTimer) clearTimeout(reloadTimer);
      source.close();
    };
  }, [projectId, reload]);

  if (!project) {
    if (loadFailed) {
      return (
        <EmptyState
          icon={<Scissors className="h-6 w-6" />}
          title="Proje bulunamadi"
          description="Uretim sayfasi yuklenemedi."
          action={
            <Button onClick={() => router.push("/cocuk-sarki")}>Projelere don</Button>
          }
        />
      );
    }
    return (
      <div>
        <Skeleton className="h-10 w-80 mb-6" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  const settingsHref = `${projectWorkspaceHref(project)}?tab=settings`;
  const publishHref = `${projectWorkspaceHref(project)}?tab=publish`;

  return (
    <div className="pb-16">
      <PageHeader
        eyebrow="Klip uretimi"
        title={
          <span className="inline-flex items-center gap-2 min-w-0">
            <span className="truncate">{project.name}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              title="Yeniden adlandir"
              onClick={() => setRenameOpen(true)}
            >
              <Pencil className="h-4 w-4" />
            </Button>
          </span>
        }
        description={`${templateLabel(project.templateType)} · ${project.clips.length} klip · Flow goruntu + yuklenen MP3 ses`}
        actions={
          <>
            <ProjectStatusBadge status={project.status} />
            <Button type="button" variant="outline" size="sm" onClick={() => setRenameOpen(true)}>
              <Pencil className="h-3.5 w-3.5" /> Adi degistir
            </Button>
            <Link href={publishHref}>
              <Button variant="outline" size="sm">
                <Megaphone className="h-3.5 w-3.5" /> Yayin
              </Button>
            </Link>
            <Link href={settingsHref}>
              <Button variant="outline" size="sm">
                <SlidersHorizontal className="h-3.5 w-3.5" /> Ayarlar
              </Button>
            </Link>
          </>
        }
      />

      <RenameProjectDialog
        open={renameOpen}
        projectId={project.id}
        currentName={project.name}
        onOpenChange={setRenameOpen}
        onRenamed={(name) => setProject((prev) => (prev ? { ...prev, name } : prev))}
      />

      <SongSourcePanel
        project={project}
        reload={reload}
        liveEvents={liveEvents}
        onPrepared={() => setTab("clips")}
        onGoAutomation={() => setTab("automation")}
      />

      <SongCastPanel project={project} reload={reload} liveEvents={liveEvents} variant="bar" />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap">
          <TabsTrigger value="clips">
            <Scissors className="h-3.5 w-3.5" /> Klipler ({project.clips.length})
          </TabsTrigger>
          <TabsTrigger value="prompts">
            <Wand2 className="h-3.5 w-3.5" /> Promptlar
          </TabsTrigger>
          <TabsTrigger value="characters">
            <User className="h-3.5 w-3.5" /> Karakterler
          </TabsTrigger>
          <TabsTrigger value="automation">
            <Cpu className="h-3.5 w-3.5" /> Otomasyon
          </TabsTrigger>
          <TabsTrigger value="render">
            <Clapperboard className="h-3.5 w-3.5" /> Render
          </TabsTrigger>
        </TabsList>

        <TabsContent value="clips">
          <ClipsTab project={project} reload={reload} />
        </TabsContent>
        <TabsContent value="prompts">
          <PromptsTab project={project} reload={reload} />
        </TabsContent>
        <TabsContent value="characters">
          <SongCastPanel project={project} reload={reload} liveEvents={liveEvents} variant="full" />
        </TabsContent>
        <TabsContent value="automation">
          <AutomationTab
            project={project}
            reload={reload}
            liveEvents={liveEvents}
            onOpenSettings={() => router.push(`${projectWorkspaceHref(project)}?tab=settings`)}
          />
        </TabsContent>
        <TabsContent value="render">
          <RenderTab project={project} reload={reload} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
