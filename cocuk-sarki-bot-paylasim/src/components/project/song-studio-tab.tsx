"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowRight,
  Check,
  Clapperboard,
  FileText,
  Music2,
  Sparkles,
  Upload,
  Wand2,
} from "lucide-react";
import { api, mediaUrl, patchJson, postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { FormSection } from "@/components/shared";
import type { ProjectData } from "@/components/project/types";
import { cn } from "@/lib/utils";
import { formatElapsed, useElapsedSeconds } from "@/lib/use-elapsed";
import { SONG_DURATION_PRESETS, SONG_STYLES } from "@/lib/song-catalog";
import { songHasMasterAudio, type SongSettings } from "@/lib/song-settings";
import { SONG_AUDIO_ACCEPT } from "@/lib/song-audio-formats";

type AudioMode = "suno" | "upload";

interface SunoLyricsResult {
  title: string;
  titleTurkish: string;
  hookLine: string;
  formattedLyrics: string;
}

const LANGUAGES = [
  { label: "Türkçe", value: "Turkish" },
  { label: "İngilizce", value: "English" },
  { label: "Almanca", value: "German" },
  { label: "Fransızca", value: "French" },
  { label: "İspanyolca", value: "Spanish" },
] as const;

const AGE_OPTIONS = [
  { value: "1-3", label: "1–3 yaş" },
  { value: "3-5", label: "3–5 yaş" },
  { value: "6-8", label: "6–8 yaş" },
] as const;

const DURATIONS = [...SONG_DURATION_PRESETS, { label: "Özel süre", value: -1 as const }];
const FLOW_MODELS = ["Veo 3.1 Lite", "Veo 3.1 Fast", "Veo 3.1 Quality", "Gemini Omni Flash"];

export function SongStudioTab({ project, reload }: { project: ProjectData; reload: () => Promise<ProjectData> }) {
  const router = useRouter();
  const [audioMode, setAudioMode] = React.useState<AudioMode>("upload");
  const [songSettings, setSongSettings] = React.useState<SongSettings>({ selectedTrackIndex: 0 });
  const [busy, setBusy] = React.useState<string | null>(null);

  const [name, setName] = React.useState(project.name);
  const [title, setTitle] = React.useState(project.title || "");
  const [channelName, setChannelName] = React.useState(project.channelName || "");
  const [ageBand, setAgeBand] = React.useState(project.ageBand || "3-5");
  const [speechLanguage, setSpeechLanguage] = React.useState(project.speechLanguage || "Turkish");
  const [durationChoice, setDurationChoice] = React.useState(
    SONG_DURATION_PRESETS.some((p) => p.value === project.targetDurationSeconds)
      ? project.targetDurationSeconds
      : -1
  );
  const [customDuration, setCustomDuration] = React.useState(project.targetDurationSeconds || 90);
  const [styleId, setStyleId] = React.useState(project.narrationStyle || "kidspop");
  const [topic, setTopic] = React.useState(project.topic || "");
  const [flowModel, setFlowModel] = React.useState(project.flowModel || "Veo 3.1 Fast");
  const [clipSeconds, setClipSeconds] = React.useState(project.clipSeconds || 8);
  const [aspectRatio, setAspectRatio] = React.useState(project.aspectRatio || "16:9");

  const [lyricsDraft, setLyricsDraft] = React.useState("");
  const [lyricsDirty, setLyricsDirty] = React.useState(false);
  const [manualLyrics, setManualLyrics] = React.useState("");
  const [pendingAudioFile, setPendingAudioFile] = React.useState<File | null>(null);

  const elapsed = useElapsedSeconds(busy !== null);
  const hasMasterAudio = songHasMasterAudio(songSettings);
  const hasScenes = project.clips.length > 0;
  const durationSec = durationChoice === -1 ? customDuration : durationChoice;
  const renderHref = `/cocuk-sarki/${project.id}/render`;

  React.useEffect(() => {
    setName(project.name);
    setTitle(project.title || "");
    setChannelName(project.channelName || "");
    setAgeBand(project.ageBand || "3-5");
    setSpeechLanguage(project.speechLanguage || "Turkish");
    setStyleId(project.narrationStyle || "kidspop");
    setTopic(project.topic || "");
    setFlowModel(project.flowModel || "Veo 3.1 Fast");
    setClipSeconds(project.clipSeconds || 8);
    setAspectRatio(project.aspectRatio || "16:9");
  }, [project]);

  React.useEffect(() => {
    api<SongSettings>(`/api/projects/${project.id}/song/settings`, { silent: true })
      .then((data) => {
        setSongSettings(data);
        setLyricsDraft(data.formattedLyrics || "");
        setManualLyrics(data.formattedLyrics || "");
        if (data.musicSource === "manual_upload") setAudioMode("upload");
      })
      .catch(() => {});
  }, [project.id]);

  React.useEffect(() => {
    if (songSettings.sunoStatus !== "generating" || !songSettings.sunoTaskId) return;
    const interval = setInterval(() => {
      void postJson<{ settings: SongSettings }>(
        `/api/projects/${project.id}/song/suno/status`,
        {
          taskId: songSettings.sunoTaskId,
          selectedTrackIndex: songSettings.selectedTrackIndex ?? 0,
          download: false,
        },
        { silent: true }
      )
        .then(async (result) => {
          setSongSettings(result.settings);
          if (result.settings.sunoStatus === "ready") {
            toast.success("Parca hazir — indiriliyor...");
            const downloaded = await postJson<{ settings: SongSettings }>(
              `/api/projects/${project.id}/song/suno/status`,
              {
                taskId: result.settings.sunoTaskId,
                selectedTrackIndex: result.settings.selectedTrackIndex ?? 0,
                download: true,
              }
            );
            setSongSettings(downloaded.settings);
            setLyricsDraft(downloaded.settings.formattedLyrics || lyricsDraft);
            await reload();
            toast.success(`Sarki hazir · ${Math.round(downloaded.settings.audioDurationSeconds ?? 0)} sn`);
          }
          if (result.settings.sunoStatus === "failed") {
            toast.error(result.settings.sunoError || "Suno uretimi basarisiz");
          }
        })
        .catch(() => {});
    }, 4000);
    return () => clearInterval(interval);
  }, [project.id, songSettings.sunoStatus, songSettings.sunoTaskId, songSettings.selectedTrackIndex, lyricsDraft, reload]);

  async function run(action: string, fn: () => Promise<void>) {
    setBusy(action);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  }

  async function saveProjectSettings() {
    if (!name.trim()) {
      toast.error("Proje adi gerekli");
      return;
    }
    await patchJson(`/api/projects/${project.id}`, {
      name: name.trim(),
      title,
      channelName,
      ageBand,
      speechLanguage,
      storyLanguage: speechLanguage,
      speechPace: ageBand === "1-3" ? "slow" : "normal",
      targetDurationSeconds: durationSec,
      narrationStyle: styleId,
      topic,
      flowModel,
      clipSeconds,
      aspectRatio,
      audioEnabled: false,
    });
    await reload();
    toast.success("Proje ayarlari kaydedildi");
  }

  async function composeLyrics() {
    await saveProjectSettings();
    const result = await postJson<SunoLyricsResult>(`/api/projects/${project.id}/song/compose-lyrics`, {
      ageBand,
      targetDurationSeconds: durationSec,
      topic: topic.trim() || undefined,
      styleId,
      title: title.trim() || undefined,
    });
    setLyricsDraft(result.formattedLyrics);
    setLyricsDirty(false);
    await reload();
    toast.success(`Sozler hazir: "${result.titleTurkish || result.title}"`);
  }

  async function sunoGenerate() {
    if (!lyricsDraft.trim()) {
      toast.error("Once sozleri olusturun veya yapistirin");
      return;
    }
    const result = await postJson<{ settings: SongSettings }>(`/api/projects/${project.id}/song/suno/generate`, {
      lyrics: lyricsDraft.trim(),
      styleId,
      title: title.trim() || project.title || undefined,
    });
    setSongSettings(result.settings);
    toast.success("Suno seslendirme basladi");
  }

  async function uploadAudioWithLyrics(file: File, lyrics?: string) {
    const form = new FormData();
    form.append("file", file);
    if (lyrics?.trim()) form.append("lyrics", lyrics.trim());
    const res = await fetch(`/api/projects/${project.id}/song/upload-audio`, { method: "POST", body: form });
    const envelope = (await res.json()) as { ok: boolean; data?: SongSettings; error?: string };
    if (!envelope.ok) throw new Error(envelope.error || "Yukleme basarisiz");
    return envelope.data!;
  }

  async function saveLyricsOnly(text: string) {
    const form = new FormData();
    form.append("lyrics", text.trim());
    const res = await fetch(`/api/projects/${project.id}/song/upload-lyrics`, { method: "POST", body: form });
    const envelope = (await res.json()) as { ok: boolean; data?: SongSettings; error?: string };
    if (!envelope.ok) throw new Error(envelope.error || "Soz kaydi basarisiz");
    setSongSettings(envelope.data!);
    setLyricsDraft(text.trim());
    setManualLyrics(text.trim());
  }

  async function syncClipsAndGo() {
    const lyrics = lyricsDirty ? lyricsDraft : manualLyrics || lyricsDraft;
    if (lyrics.trim()) await saveLyricsOnly(lyrics);
    const result = await postJson<{ clipCount: number }>(`/api/projects/${project.id}/song/sync-clips`, {
      formattedLyrics: lyrics.trim() || undefined,
    });
    setLyricsDirty(false);
    await reload();
    toast.success(`${result.clipCount} klip hazir — uretim sayfasina yonlendiriliyor`);
    router.push(renderHref);
  }

  const audioTabs: { id: AudioMode; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: "suno", label: "Suno ile uret", icon: Sparkles },
    { id: "upload", label: "Dosya yukle", icon: Upload },
  ];

  return (
    <div className="space-y-4 max-w-4xl">
      <FormSection step={1} title="Proje kimligi" description="Kanal, yas bandi ve dil">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Proje adi *</Label>
            <Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)} placeholder="or. Kopuk Bulutu Sarkisi" />
          </div>
          <div>
            <Label>Poster basligi (istege bagli)</Label>
            <Input className="mt-1" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="YouTube basligi" />
          </div>
          <div>
            <Label>Kanal adi</Label>
            <Input className="mt-1" value={channelName} onChange={(e) => setChannelName(e.target.value)} placeholder="or. Minik Dostlar" />
          </div>
          <div>
            <Label>Yas bandi</Label>
            <Select value={ageBand} onValueChange={setAgeBand}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AGE_OPTIONS.map((a) => (
                  <SelectItem key={a.value} value={a.value}>
                    {a.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Sarki dili</Label>
            <Select value={speechLanguage} onValueChange={setSpeechLanguage}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LANGUAGES.map((l) => (
                  <SelectItem key={l.value} value={l.value}>
                    {l.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Hedef sure (tahmini)</Label>
            <Select value={String(durationChoice)} onValueChange={(v) => setDurationChoice(Number(v))}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DURATIONS.map((d) => (
                  <SelectItem key={d.value} value={String(d.value)}>
                    {d.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {durationChoice === -1 && (
              <Input
                className="mt-2"
                type="number"
                min={20}
                max={3600}
                value={customDuration}
                onChange={(e) => setCustomDuration(Number(e.target.value) || 90)}
              />
            )}
          </div>
        </div>
      </FormSection>

      <FormSection step={2} title="Muzik tarzi" description="Suno seslendirme stili — tema sozlerden otomatik uretilir">
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-72 overflow-y-auto pr-1">
            {SONG_STYLES.map((style) => (
              <button
                key={style.id}
                type="button"
                onClick={() => setStyleId(style.id)}
                className={cn(
                  "rounded-[12px] border p-3 text-left transition-colors",
                  styleId === style.id
                    ? "border-primary bg-primary-soft/40 ring-1 ring-primary/30"
                    : "border-border bg-surface hover:border-primary/40"
                )}
              >
                <div className="text-[12px] font-semibold">{style.label}</div>
                <p className="mt-0.5 text-[10.5px] text-muted leading-snug">{style.tagline}</p>
              </button>
            ))}
          </div>
          <div>
            <Label>Konu notu (istege bagli)</Label>
            <Input className="mt-1" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="or. mavi kedi, kopuk bulutu" />
          </div>
        </div>
      </FormSection>

      <FormSection step={3} title="Flow uretim" description="Goruntu klipleri — ses kapali, Suno parcasi renderda eklenir">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label>Flow modeli</Label>
            <Select value={flowModel} onValueChange={setFlowModel}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FLOW_MODELS.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Klip suresi</Label>
            <Select value={String(clipSeconds)} onValueChange={(v) => setClipSeconds(Number(v))}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[4, 6, 8, 10].map((s) => (
                  <SelectItem key={s} value={String(s)}>
                    {s} sn
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>En-boy orani</Label>
            <Select value={aspectRatio} onValueChange={setAspectRatio}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="16:9">16:9</SelectItem>
                <SelectItem value="9:16">9:16</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <p className="mt-3 text-[11px] text-muted">
          ~{Math.max(4, Math.round(durationSec / clipSeconds))} klip · ses Flow&apos;da kapali
        </p>
      </FormSection>

      <div className="flex justify-end">
        <Button variant="outline" size="sm" loading={busy === "save"} onClick={() => run("save", saveProjectSettings)}>
          Proje ayarlarini kaydet
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {audioTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <Button
              key={tab.id}
              type="button"
              variant={audioMode === tab.id ? "default" : "outline"}
              size="sm"
              onClick={() => setAudioMode(tab.id)}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              {tab.id === "upload" && hasMasterAudio && <Check className="h-3 w-3 ml-0.5" />}
            </Button>
          );
        })}
      </div>

      {audioMode === "suno" && (
        <Card className="border-primary/20">
          <CardHeader>
            <CardTitle>Suno ile sarki uret</CardTitle>
            <CardDescription>
              Yas, sure ve tarzi secin → sozler otomatik yazilir → Suno seslendirir. Tema ve klip promptlari sozlerden
              uretilir.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button loading={busy === "compose"} onClick={() => run("compose", composeLyrics)}>
                <FileText className="h-4 w-4" /> 1. Sozleri olustur
              </Button>
              <Button
                variant="secondary"
                loading={busy === "suno"}
                disabled={!lyricsDraft.trim()}
                onClick={() => run("suno", sunoGenerate)}
              >
                <Music2 className="h-4 w-4" /> 2. Suno ile seslendir
              </Button>
              {songSettings.sunoStatus === "generating" && (
                <Badge variant="warning">Suno calisiyor · {formatElapsed(elapsed)}</Badge>
              )}
            </div>
            <div>
              <Label>Sarki sozleri</Label>
              <Textarea
                className="mt-1 min-h-[220px] font-mono text-[13px] bg-surface-2"
                value={lyricsDraft}
                onChange={(e) => {
                  setLyricsDraft(e.target.value);
                  setLyricsDirty(true);
                }}
                placeholder="Sozleri olustur dedikten sonra burada gorunur."
              />
            </div>
            {(songSettings.sunoTracks?.length ?? 0) > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {songSettings.sunoTracks!.map((track, i) => (
                  <button
                    key={track.id || i}
                    type="button"
                    onClick={() => setSongSettings((s) => ({ ...s, selectedTrackIndex: i }))}
                    className={cn(
                      "rounded-[10px] border p-3 text-left text-[11px]",
                      (songSettings.selectedTrackIndex ?? 0) === i ? "border-primary bg-primary-soft/40" : "border-border"
                    )}
                  >
                    {track.title || `Varyant ${i + 1}`}
                    {track.duration ? ` · ${Math.round(track.duration)} sn` : ""}
                  </button>
                ))}
              </div>
            )}
            {hasMasterAudio && songSettings.audioPath && (
              <div className="rounded-[12px] border border-success/40 bg-success-soft/30 p-4 space-y-2">
                <Badge variant="success">Master parca hazir · {Math.round(songSettings.audioDurationSeconds ?? 0)} sn</Badge>
                <audio src={mediaUrl(songSettings.audioPath)} controls className="w-full" />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {audioMode === "upload" && (
        <Card className="border-primary/20">
          <CardHeader>
            <CardTitle>MP3 + soz yukle</CardTitle>
            <CardDescription>Suno.com veya baska kaynaktan indirdiginiz parca ve sozler.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              type="file"
              accept={SONG_AUDIO_ACCEPT}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) setPendingAudioFile(file);
              }}
            />
            <Textarea
              className="min-h-[180px] font-mono text-[13px]"
              placeholder="Sarki sozleri..."
              value={manualLyrics}
              onChange={(e) => setManualLyrics(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                loading={busy === "saveLyrics"}
                disabled={!manualLyrics.trim()}
                onClick={() => run("saveLyrics", async () => {
                  await saveLyricsOnly(manualLyrics);
                  toast.success("Sozler kaydedildi");
                })}
              >
                Sozleri kaydet
              </Button>
              <Button
                loading={busy === "uploadAll"}
                disabled={!pendingAudioFile}
                onClick={() =>
                  run("uploadAll", async () => {
                    const settings = await uploadAudioWithLyrics(pendingAudioFile!, manualLyrics);
                    setSongSettings(settings);
                    setLyricsDraft(settings.formattedLyrics || manualLyrics);
                    setPendingAudioFile(null);
                    await reload();
                    toast.success(`Parca yuklendi · ${Math.round(settings.audioDurationSeconds ?? 0)} sn`);
                  })
                }
              >
                <Upload className="h-4 w-4" /> MP3 + sozleri yukle
              </Button>
            </div>
            {hasMasterAudio && songSettings.audioPath && (
              <audio src={mediaUrl(songSettings.audioPath)} controls className="w-full" />
            )}
          </CardContent>
        </Card>
      )}

      <Card className="border-primary/30 bg-primary-soft/20">
        <CardHeader>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Wand2 className="h-4 w-4 text-primary" />
                Sozlerden klip plani
              </CardTitle>
              <CardDescription className="mt-1">
                Master parca + sozler hazir olunca klipleri olusturur; tema ve detayli promptlar sozlerden uretilir.
              </CardDescription>
            </div>
            {hasScenes && (
              <Link href={renderHref}>
                <Button variant="outline" size="sm">
                  <Clapperboard className="h-4 w-4" /> Uretim sayfasi
                  <ArrowRight className="h-3 w-3" />
                </Button>
              </Link>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {!hasMasterAudio && (
            <p className="text-sm text-warning rounded-[10px] border border-warning/30 bg-warning-soft p-3">
              Once Suno veya MP3 yukleme ile master parcayi ekleyin.
            </p>
          )}
          <Button loading={busy === "sync"} disabled={!hasMasterAudio} onClick={() => run("sync", syncClipsAndGo)}>
            <Wand2 className="h-4 w-4" /> Klipleri eslestir ve uretime git
          </Button>
          {hasScenes && (
            <p className="text-[11px] text-muted">
              {project.clips.length} klip hazir — Flow otomasyonu ve render icin{" "}
              <Link href={renderHref} className="text-primary underline">
                uretim sayfasina
              </Link>{" "}
              gidin.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
