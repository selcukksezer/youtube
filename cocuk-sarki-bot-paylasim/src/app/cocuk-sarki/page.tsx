"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Music2, Pencil, Trash2, Video } from "lucide-react";
import { api, del } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { EmptyState, PageHeader, ProjectStatusBadge } from "@/components/shared";
import { NewSongProjectButton } from "@/components/new-song-project-button";
import { RenameProjectDialog } from "@/components/project/rename-project-dialog";
import { formatDate, formatDuration } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";
import { projectProductionHref, templateLabel } from "@/lib/templates";
import { BRAND } from "@/lib/brand";

interface ProjectListItem {
  id: string;
  name: string;
  slug: string;
  title: string;
  genre: string;
  templateType: string;
  status: string;
  targetDurationSeconds: number;
  clipCount: number;
  completedClipCount: number;
  createdAt: string;
  updatedAt: string;
  mainCharacterName: string;
}

function ProjectCard({
  project,
  onDelete,
  onRename,
}: {
  project: ProjectListItem;
  onDelete: (p: ProjectListItem) => void;
  onRename: (p: ProjectListItem) => void;
}) {
  const router = useRouter();
  const progress = project.clipCount > 0 ? (project.completedClipCount / project.clipCount) * 100 : 0;

  return (
    <Card
      className="cursor-pointer hover:card-shadow-hover hover:-translate-y-0.5 hover:border-border-strong transition-all group"
      onClick={() => router.push(projectProductionHref(project))}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-primary-soft border border-primary/20 group-hover:brand-gradient group-hover:border-transparent transition-colors">
              <Music2 className="h-4 w-4 text-primary group-hover:text-white" />
            </div>
            <div className="min-w-0">
              <div className="text-[13.5px] font-semibold truncate">{project.name}</div>
              <div className="text-[11px] text-muted-2 truncate">
                {templateLabel(project.templateType)}
                {project.title ? ` · ${project.title}` : project.genre ? ` · ${project.genre}` : ""}
                {project.mainCharacterName ? ` · ${project.mainCharacterName}` : ""}
              </div>
            </div>
          </div>
          <ProjectStatusBadge status={project.status} />
        </div>

        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-[11px] text-muted">
            <span className="flex items-center gap-1">
              <Video className="h-3 w-3" />
              <span className="tabular-nums font-medium text-foreground">
                {project.completedClipCount}/{project.clipCount}
              </span>{" "}
              klip
            </span>
            <span>{formatDuration(project.targetDurationSeconds)} hedef</span>
          </div>
          <Progress value={progress} />
        </div>

        <div className="mt-3 pt-3 border-t border-border flex items-center justify-between gap-2">
          <span className="text-[11px] text-muted-2">{formatDate(project.updatedAt)}</span>
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              title="Yeniden adlandir"
              onClick={(e) => {
                e.stopPropagation();
                onRename(project);
              }}
            >
              <Pencil className="h-3.5 w-3.5" /> Adi degistir
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              title="Sil"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(project);
              }}
            >
              <Trash2 className="h-3.5 w-3.5 text-danger" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function KidsSongProjectsPage() {
  const [projects, setProjects] = React.useState<ProjectListItem[] | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<ProjectListItem | null>(null);
  const [renameTarget, setRenameTarget] = React.useState<ProjectListItem | null>(null);
  const [deleting, setDeleting] = React.useState(false);

  const load = React.useCallback(() => {
    api<ProjectListItem[]>("/api/projects").then(setProjects);
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  async function confirmDelete(deleteFiles: boolean) {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await del(`/api/projects/${deleteTarget.id}?deleteFiles=${deleteFiles}`);
      toast.success(`"${deleteTarget.name}" silindi`);
      setDeleteTarget(null);
      load();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow={BRAND.name}
        title="Projeler"
        description="Sarki klibi projeleri: MP3 + sozler kliplere bolunur, Flow goruntu uretir, render'da ses birlesir."
        actions={<NewSongProjectButton size="sm" />}
      />

      {!projects ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          icon={<Music2 className="h-6 w-6" />}
          title="Proje kutuphanesi bos"
          description="MP3 veya Suno.com indirmesi ile ilk cocuk sarki klibinizi olusturun."
          action={<NewSongProjectButton label="Ilk projeyi olustur" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} onDelete={setDeleteTarget} onRename={setRenameTarget} />
          ))}
        </div>
      )}

      <RenameProjectDialog
        open={!!renameTarget}
        projectId={renameTarget?.id ?? ""}
        currentName={renameTarget?.name ?? ""}
        onOpenChange={(open) => {
          if (!open) setRenameTarget(null);
        }}
        onRenamed={(name) => {
          setProjects((prev) => prev?.map((p) => (p.id === renameTarget?.id ? { ...p, name } : p)) ?? null);
          setRenameTarget(null);
        }}
      />

      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Projeyi sil</DialogTitle>
            <DialogDescription>
              &quot;{deleteTarget?.name}&quot; silinecek. Indirilen videolar ve uretilen dosyalar diskte{" "}
              {`projects/${deleteTarget?.slug}`} klasorunde duruyor.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Vazgec
            </Button>
            <Button variant="secondary" onClick={() => confirmDelete(false)} loading={deleting}>
              Sadece Kaydi Sil
            </Button>
            <Button variant="danger" onClick={() => confirmDelete(true)} loading={deleting}>
              <Trash2 className="h-4 w-4" /> Dosyalarla Birlikte Sil
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
