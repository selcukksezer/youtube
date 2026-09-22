"use client";

import * as React from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Clapperboard,
  Film,
  Mic2,
  Music2,
  RefreshCw,
  Sparkles,
  XCircle,
} from "lucide-react";
import { api, postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useShellStatus } from "@/components/system-status-provider";
import { CheckRow, EmptyState, PageHeader, ProjectStatusBadge, StatCard } from "@/components/shared";
import { NewSongProjectButton } from "@/components/new-song-project-button";
import { formatDate } from "@/lib/utils";
import { projectProductionHref, templateLabel } from "@/lib/templates";
import { BRAND, NAV, PIPELINE_STEPS } from "@/lib/brand";
import { LiveEventLog } from "@/components/live-event-log";
import { toast } from "sonner";

interface SystemStatus {
  projectCount: number;
  runningJobs: number;
  completedClips: number;
  failedClips: number;
  recentProjects: Array<{ id: string; name: string; status: string; templateType: string; updatedAt: string }>;
  recentEvents: Array<{ id: number; level: string; step: string; message: string; createdAt: string }>;
  flowSession: { status: string; detail: string };
  browserOpen: boolean;
  openaiKeyPresent: boolean;
  sunoKeyPresent: boolean;
  sunoBaseUrl?: string;
  sunoDefaultModel?: string;
}

interface FfmpegChecks {
  ffmpeg: { ok: boolean; label: string; detail: string };
  ffprobe: { ok: boolean; label: string; detail: string };
}

interface PlaywrightChecks {
  playwright: { ok: boolean; label: string; detail: string };
  chrome: { ok: boolean; label: string; detail: string };
  profile: { ok: boolean; label: string; detail: string };
}

const STEP_ICONS = {
  music: Music2,
  lyrics: Mic2,
  character: Sparkles,
  render: Clapperboard,
} as const;

export default function DashboardPage() {
  const { tick } = useShellStatus();
  const [status, setStatus] = React.useState<SystemStatus | null>(null);
  const [ffmpeg, setFfmpeg] = React.useState<FfmpegChecks | null>(null);
  const [playwright, setPlaywright] = React.useState<PlaywrightChecks | null>(null);
  const [openaiTest, setOpenaiTest] = React.useState<string | null>(null);
  const [testingOpenai, setTestingOpenai] = React.useState(false);

  const load = React.useCallback(async () => {
    const [statusData, ffmpegData, playwrightData] = await Promise.all([
      api<SystemStatus>("/api/system/status", { silent: true }),
      api<FfmpegChecks>("/api/system/ffmpeg", { silent: true }),
      api<PlaywrightChecks>("/api/system/playwright", { silent: true }),
    ]);
    setStatus(statusData);
    setFfmpeg(ffmpegData);
    setPlaywright(playwrightData);
  }, []);

  React.useEffect(() => {
    load().catch(() => toast.error("Uretim merkezi verisi yuklenemedi"));
  }, [load, tick]);

  async function testOpenAi() {
    setTestingOpenai(true);
    try {
      const result = await postJson<{ ok: boolean; model: string; message: string }>("/api/settings/openai/test");
      setOpenaiTest(result.ok ? `Baglanti basarili (${result.model})` : result.message);
      if (result.ok) toast.success("OpenAI baglantisi basarili");
      else toast.error(result.message);
    } finally {
      setTestingOpenai(false);
    }
  }

  const flowBadge =
    status?.flowSession.status === "ready" ? (
      <Badge variant="success" dot>Oturum hazir</Badge>
    ) : status?.browserOpen ? (
      <Badge variant="warning" dot>Giris gerekli</Badge>
    ) : (
      <Badge dot>Tarayici kapali</Badge>
    );

  const songProjects = status?.recentProjects.filter((p) => p.templateType === "kids_song") ?? [];

  return (
    <div>
      <PageHeader
        eyebrow={BRAND.name}
        title={NAV.home.label}
        description={BRAND.tagline}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => load()}>
              <RefreshCw className="h-3.5 w-3.5" /> Yenile
            </Button>
            <NewSongProjectButton size="sm" />
          </>
        }
      />

      <div className="mb-6 overflow-hidden rounded-[18px] border border-border bg-surface p-5 sm:p-6 lg:p-8 card-shadow hairline-top">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 max-w-xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-primary-soft px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-primary">
              <Film className="h-3 w-3 shrink-0" />
              <span className="truncate">{BRAND.pipeline}</span>
            </div>
            <h2 className="mt-3 text-[20px] sm:text-[22px] font-semibold tracking-[-0.03em] text-foreground">
              Cocuk sarki klibi uretim hatti
            </h2>
            <p className="mt-2 text-[13px] text-muted leading-relaxed">
              Elinizdeki MP3 ve sozler kliplere bolunur. Flow yalnizca goruntu uretir; render&apos;da ses bu parcadan
              gelir. Suno API gerekmez.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2.5 sm:gap-3 w-full min-w-0 lg:max-w-[480px] shrink-0">
            {PIPELINE_STEPS.map((step) => {
              const Icon = STEP_ICONS[step.icon];
              return (
                <div
                  key={step.step}
                  className="min-w-0 rounded-[14px] border border-border/60 bg-surface-2 px-3.5 py-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex h-7 w-7 items-center justify-center rounded-[9px] bg-primary-soft text-primary">
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                    </span>
                    <span className="font-mono text-[10px] font-semibold text-muted-2">{step.step}</span>
                  </div>
                  <div className="mt-2 text-[11.5px] font-semibold leading-snug break-words">{step.title}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {!status ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[116px] rounded-[16px]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Aktif Proje" value={status.projectCount} icon={<Music2 className="h-[18px] w-[18px]" />} tone="primary" />
          <StatCard label="Calisan Render" value={status.runningJobs} icon={<Activity className="h-[18px] w-[18px]" />} tone={status.runningJobs > 0 ? "warning" : "default"} />
          <StatCard label="Tamamlanan Klip" value={status.completedClips} icon={<CheckCircle2 className="h-[18px] w-[18px]" />} tone="success" />
          <StatCard label="Basarisiz Klip" value={status.failedClips} icon={<XCircle className="h-[18px] w-[18px]" />} tone={status.failedClips > 0 ? "danger" : "default"} />
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader className="!flex-row items-center justify-between gap-4">
            <div>
              <CardTitle>Son Projeler</CardTitle>
              <CardDescription>En son guncellenen sarki klipleri</CardDescription>
            </div>
            {songProjects.length > 0 && (
              <Link href={NAV.projects.href}>
                <Button variant="ghost" size="sm">
                  Tumunu gor <ArrowRight className="h-3 w-3" />
                </Button>
              </Link>
            )}
          </CardHeader>
          <CardContent>
            {!status ? (
              <Skeleton className="h-40 rounded-[12px]" />
            ) : songProjects.length === 0 ? (
              <EmptyState
                icon={<Music2 className="h-6 w-6" />}
                title="Henuz proje yok"
                description="MP3 ve sozleri yukleyin; karakter referansi ve Flow ile muzik videosu klipleri olusturun."
                action={
                  <NewSongProjectButton size="sm" label="Ilk projeyi baslat" />
                }
              />
            ) : (
              <div className="space-y-1">
                {songProjects.map((project) => (
                  <Link
                    key={project.id}
                    href={projectProductionHref(project)}
                    className="group flex items-center justify-between gap-3 rounded-[12px] border border-transparent px-3 py-2.5 hover:border-border hover:bg-surface-2"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border border-border bg-surface-3 text-primary group-hover:border-primary/25 group-hover:bg-primary-soft">
                        <Music2 className="h-4 w-4" />
                      </span>
                      <div className="min-w-0">
                        <div className="text-[13px] font-medium truncate">{project.name}</div>
                        <div className="text-[11px] text-muted-2">
                          {templateLabel(project.templateType)} · {formatDate(project.updatedAt)}
                        </div>
                      </div>
                    </div>
                    <ProjectStatusBadge status={project.status} />
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Altyapi Durumu</CardTitle>
            <CardDescription>FFmpeg · Playwright · OpenAI · Suno · Flow</CardDescription>
          </CardHeader>
          <CardContent>
            {!ffmpeg || !playwright || !status ? (
              <Skeleton className="h-48 rounded-[12px]" />
            ) : (
              <div>
                <CheckRow ok={ffmpeg.ffmpeg.ok} label="FFmpeg" detail={ffmpeg.ffmpeg.detail} />
                <CheckRow ok={ffmpeg.ffprobe.ok} label="ffprobe" detail={ffmpeg.ffprobe.detail} />
                <CheckRow ok={playwright.playwright.ok} label="Playwright" detail={playwright.playwright.detail} />
                <CheckRow ok={playwright.chrome.ok} label="Google Chrome" detail={playwright.chrome.detail} />
                <div className="flex items-center justify-between py-3 border-b border-border">
                  <span className="text-[13px] font-medium">Flow Oturumu</span>
                  {flowBadge}
                </div>
                <div className="flex items-center justify-between gap-2 py-3 border-b border-border">
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium">OpenAI API</div>
                    {openaiTest ? (
                      <div className="text-[11px] text-muted mt-0.5 break-all">{openaiTest}</div>
                    ) : (
                      <div className="text-[11px] text-muted-2 mt-0.5">
                        {status.openaiKeyPresent ? "Anahtar ayarli" : "Ayarlar ekranindan ekleyin"}
                      </div>
                    )}
                  </div>
                  <Button variant="outline" size="sm" onClick={testOpenAi} loading={testingOpenai} disabled={!status.openaiKeyPresent}>
                    Test Et
                  </Button>
                </div>
                <div className="flex items-center justify-between gap-2 pt-3">
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium">Suno API</div>
                    <div className="text-[11px] text-muted-2 mt-0.5">
                      {status.sunoKeyPresent
                        ? `Anahtar ayarli · ${status.sunoDefaultModel || "V4_5"} · ${status.sunoBaseUrl || "kie.ai"}`
                        : "Anahtar yok — Ayarlar > Suno API"}
                    </div>
                  </div>
                  <Link href="/settings">
                    <Button variant="outline" size="sm">
                      {status.sunoKeyPresent ? "Duzenle" : "Ekle"}
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-4">
        <LiveEventLog description="Son otomasyon ve Flow adimlari — hata varsa burada gorunur" maxHeight="max-h-[320px]" />
      </div>
    </div>
  );
}
