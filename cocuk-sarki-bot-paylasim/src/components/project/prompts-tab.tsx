"use client";

import * as React from "react";
import { toast } from "sonner";
import { RefreshCw, Save, Wand2 } from "lucide-react";
import { patchJson, postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared";
import type { ProjectData } from "@/components/project/types";

export function PromptsTab({ project, reload }: { project: ProjectData; reload: () => Promise<ProjectData> }) {
  const [busy, setBusy] = React.useState<string | null>(null);
  const [template, setTemplate] = React.useState(project.promptTemplate);
  const [showTemplate, setShowTemplate] = React.useState(false);
  const [selectedClipId, setSelectedClipId] = React.useState<string | null>(project.clips[0]?.id ?? null);

  React.useEffect(() => {
    setTemplate(project.promptTemplate);
  }, [project.promptTemplate]);

  React.useEffect(() => {
    if (!selectedClipId && project.clips.length > 0) setSelectedClipId(project.clips[0].id);
  }, [project.clips, selectedClipId]);

  const selectedClip = project.clips.find((c) => c.id === selectedClipId) ?? null;
  const templateDirty = template !== project.promptTemplate;
  const promptedCount = project.clips.filter((c) => c.prompt.trim().length > 0).length;
  const allReady = promptedCount === project.clips.length && project.clips.length > 0;

  async function saveTemplate() {
    setBusy("template");
    try {
      await patchJson(`/api/projects/${project.id}`, { promptTemplate: template });
      await reload();
      toast.success("Sablon kaydedildi. Topluca prompt olusturmayi unutmayin.");
    } finally {
      setBusy(null);
    }
  }

  async function buildAll() {
    setBusy("build");
    try {
      const clips = await postJson<unknown[]>(`/api/projects/${project.id}/build-prompts`);
      await reload();
      toast.success(`${clips.length} klip icin soz ve akis bazli detayli prompt olusturuldu`);
    } finally {
      setBusy(null);
    }
  }

  async function rebuildOne() {
    if (!selectedClip) return;
    setBusy("rebuild");
    try {
      await postJson(`/api/projects/${project.id}/clips/${selectedClip.id}/rebuild-prompt`);
      await reload();
      toast.success(`Klip ${selectedClip.index} promptu sozlere gore yenilendi`);
    } finally {
      setBusy(null);
    }
  }

  if (project.clips.length === 0) {
    return (
      <EmptyState
        icon={<Wand2 className="h-6 w-6" />}
        title="Once klipler gerekli"
        description="Once ustteki parca panelinden sozleri kliplere bolun. Ardindan gerekirse burada promptlari tek tek duzenleyin."
      />
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="gap-4 sm:!flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <CardTitle>Sozlere gore Flow promptlari</CardTitle>
            <CardDescription>
              Sozlere ve onceki sahnenin devamina gore her klip icin saniye-saniye yonetmen promptu yazilir: karakter kilidi,
              dis/set detayi, malzeme, isik, kamera ve lyric→ekran eslemesi. Flow yalnizca goruntu uretir; ses
              yuklediginiz master MP3&apos;te kalir.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Badge variant={allReady ? "success" : "warning"}>
              {promptedCount}/{project.clips.length} hazir
            </Badge>
            <Button onClick={buildAll} loading={busy === "build"}>
              <Wand2 className="h-4 w-4" /> Topluca prompt olustur
            </Button>
          </div>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr] gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Klipler</CardTitle>
            <CardDescription>Soz satirina gore secin</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1.5 max-h-[560px] overflow-y-auto pr-1">
            {project.clips.map((clip) => {
              const ready = clip.prompt.trim().length > 0;
              const lyric = clip.dialogue.replace(/\s+/g, " ").trim();
              const active = clip.id === selectedClipId;
              return (
                <button
                  key={clip.id}
                  type="button"
                  onClick={() => setSelectedClipId(clip.id)}
                  className={
                    active
                      ? "w-full rounded-[10px] border border-primary/40 bg-primary-soft px-3 py-2 text-left cursor-pointer"
                      : "w-full rounded-[10px] border border-transparent px-3 py-2 text-left hover:bg-surface-2 cursor-pointer"
                  }
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[12px] font-semibold tabular-nums">#{String(clip.index).padStart(3, "0")}</span>
                    <Badge variant={ready ? "success" : "warning"}>{ready ? "prompt var" : "bos"}</Badge>
                  </div>
                  <p className="mt-1 text-[11px] text-muted leading-snug line-clamp-2">
                    {lyric || clip.sceneDescription || "Soz yok"}
                  </p>
                </button>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <div>
                <CardTitle>
                  {selectedClip ? `Klip ${String(selectedClip.index).padStart(3, "0")} — detayli prompt` : "Prompt"}
                </CardTitle>
                <CardDescription>
                  {selectedClip?.dialogue
                    ? `Soz: “${selectedClip.dialogue.replace(/\s+/g, " ").trim().slice(0, 140)}”`
                    : "Bu klibin soz satiri bos"}
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={rebuildOne} loading={busy === "rebuild"} disabled={!selectedClip}>
                <RefreshCw className="h-3.5 w-3.5" /> Bu klibi yenile
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {selectedClip?.sceneDescription ? (
              <p className="text-[12px] text-muted leading-relaxed">
                <span className="font-medium text-foreground">Sahne akisi: </span>
                {selectedClip.sceneDescription}
              </p>
            ) : null}
            {selectedClip ? (
              selectedClip.prompt ? (
                <pre className="rounded-[10px] border border-border bg-surface-2 p-4 text-[11px] font-mono whitespace-pre-wrap break-words max-h-[520px] overflow-y-auto leading-relaxed">
                  {selectedClip.prompt}
                </pre>
              ) : (
                <p className="text-xs text-muted py-10 text-center">
                  Bu klip icin henuz prompt yok. &quot;Topluca prompt olustur&quot; ile tum sahneler soz ve akisa gore yazilir.
                </p>
              )
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div>
        <button
          type="button"
          className="text-[12px] text-muted hover:text-foreground"
          onClick={() => setShowTemplate((v) => !v)}
        >
          {showTemplate ? "Sablon editorunu gizle" : "Gelismis: prompt sablonunu duzenle"}
        </button>
      </div>

      {showTemplate ? (
        <Card>
          <CardHeader>
            <CardTitle>Prompt sablonu</CardTitle>
            <CardDescription>
              Bos birakirsaniz sarki klibi varsayilani kullanilir. Degiskenler:{" "}
              {"{{STYLE}} {{CHARACTER_REFERENCE}} {{SCENE_CONTINUITY}} {{CAMERA}} {{PERFORMANCE}} {{VOICE}} {{LANGUAGE}} {{DIALOGUE}} {{SUBTITLES}} {{SPEECH_FIDELITY}} {{NEGATIVE}} {{FLOW_CHARACTER}} {{SCENE_NOTES}} {{MUSIC}} {{LYRIC_VISUAL_LOCK}}"}.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              className="min-h-[280px] font-mono text-[11px]"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              placeholder="Varsayilan sablonu kullanmak icin bos birakin"
              spellCheck={false}
            />
            <Button onClick={saveTemplate} loading={busy === "template"} disabled={!templateDirty}>
              <Save className="h-4 w-4" /> Sablonu kaydet
            </Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
