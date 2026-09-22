"use client";

import * as React from "react";
import { toast } from "sonner";
import { Check, CircleStop, Music2, Play, TriangleAlert, Upload, Wand2 } from "lucide-react";
import { api, mediaUrl, postJson } from "@/lib/client-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { EventData, ProjectData } from "@/components/project/types";
import { songHasMasterAudio, type SongSettings } from "@/lib/song-settings";
import { SONG_AUDIO_ACCEPT, isLosslessSongAudio, songAudioBadgeLabel } from "@/lib/song-audio-formats";

function jobIsActive(project: ProjectData): boolean {
  return project.jobs.some((j) => ["running", "paused", "needs_manual_action", "pending"].includes(j.state));
}

/** Kullanici Durdur'a bastiginda zinciri sessizce kesen isaret hatasi. */
class CancelledByUser extends Error {
  constructor() {
    super("Kullanici durdurdu");
    this.name = "CancelledByUser";
  }
}

function clipsAndPromptsReady(project: ProjectData): boolean {
  return project.clips.length > 0 && project.clips.every((c) => c.prompt.trim().length > 0);
}

export function SongSourcePanel({
  project,
  reload,
  liveEvents,
  onPrepared,
  onGoAutomation,
}: {
  project: ProjectData;
  reload: () => Promise<unknown>;
  liveEvents?: EventData[];
  onPrepared?: () => void;
  onGoAutomation?: () => void;
}) {
  const [songSettings, setSongSettings] = React.useState<SongSettings>({ selectedTrackIndex: 0 });
  const [lyrics, setLyrics] = React.useState("");
  const [pendingFile, setPendingFile] = React.useState<File | null>(null);
  const [busy, setBusy] = React.useState<string | null>(null);
  const [phase, setPhase] = React.useState<string | null>(null);
  const [expanded, setExpanded] = React.useState(project.clips.length === 0);
  const [stopping, setStopping] = React.useState(false);
  // Oto bitir cok adimli: iptal bayragi adimlar ARASINDA okunur, boylece
  // sunucu isi durdurulduktan sonra sonraki adim hic baslamaz.
  const cancelRef = React.useRef(false);

  const hasMasterAudio = songHasMasterAudio(songSettings);
  const hasClips = project.clips.length > 0;
  const canPrepare = (hasMasterAudio || Boolean(pendingFile)) && lyrics.trim().length > 0;
  const autoRunning = busy === "auto";
  const latestEvent = [...(liveEvents ?? [])]
    .reverse()
    .find((e) => ["song", "character", "prompts", "job", "clip"].includes(e.step));

  React.useEffect(() => {
    api<SongSettings>(`/api/projects/${project.id}/song/settings`, { silent: true })
      .then((data) => {
        setSongSettings(data);
        setLyrics(data.formattedLyrics || "");
        if (!songHasMasterAudio(data) || !(data.formattedLyrics || "").trim()) {
          setExpanded(true);
        }
      })
      .catch(() => {});
  }, [project.id]);

  async function run(action: string, fn: () => Promise<void>) {
    if (action === "auto") cancelRef.current = false;
    setBusy(action);
    try {
      await fn();
    } catch (err) {
      if (!(err instanceof CancelledByUser)) throw err;
    } finally {
      setBusy(null);
      setPhase(null);
    }
  }

  /** Adim sinirinda iptal kontrolu — kullanici Durdur'a bastiysa zinciri kes. */
  function assertNotCancelled() {
    if (cancelRef.current) throw new CancelledByUser();
  }

  /** TEK DUGME: hem cok adimli Oto bitir zincirini hem sunucudaki isi durdurur. */
  async function stopEverything() {
    cancelRef.current = true;
    setStopping(true);
    setPhase("Durduruluyor...");
    try {
      await postJson(`/api/projects/${project.id}/automation/stop`);
      await reload();
      toast.success("Islem durduruldu");
    } catch {
      toast.error("Durdurma istegi gonderilemedi");
    } finally {
      setStopping(false);
      setBusy(null);
      setPhase(null);
    }
  }

  async function saveLyrics(text: string) {
    const form = new FormData();
    form.append("lyrics", text.trim());
    const res = await fetch(`/api/projects/${project.id}/song/upload-lyrics`, { method: "POST", body: form });
    const envelope = (await res.json()) as { ok: boolean; data?: SongSettings; error?: string };
    if (!envelope.ok) throw new Error(envelope.error || "Soz kaydi basarisiz");
    setSongSettings(envelope.data!);
    setLyrics(text.trim());
  }

  async function uploadAudio(file: File) {
    const form = new FormData();
    form.append("file", file);
    if (lyrics.trim()) form.append("lyrics", lyrics.trim());
    const res = await fetch(`/api/projects/${project.id}/song/upload-audio`, { method: "POST", body: form });
    const envelope = (await res.json()) as { ok: boolean; data?: SongSettings; error?: string };
    if (!envelope.ok) throw new Error(envelope.error || "Yukleme basarisiz");
    setSongSettings(envelope.data!);
    if (envelope.data?.formattedLyrics) setLyrics(envelope.data.formattedLyrics);
    setPendingFile(null);
    await reload();
  }

  async function prepare() {
    if (lyrics.trim()) await saveLyrics(lyrics);
    const result = await postJson<{ clipCount: number; prompted: number }>(
      `/api/projects/${project.id}/song/prepare-production`,
      { formattedLyrics: lyrics.trim() || undefined }
    );
    await reload();
    toast.success(`${result.clipCount} klip + ${result.prompted} prompt hazir — ses yuklediginiz parca`);
    onPrepared?.();
  }

  async function autoFinish() {
    assertNotCancelled();
    if (pendingFile) {
      setPhase("Ses yukleniyor...");
      await uploadAudio(pendingFile);
    }
    assertNotCancelled();
    if (lyrics.trim()) await saveLyrics(lyrics);
    let data = (await reload()) as ProjectData;
    assertNotCancelled();

    const hasCompleted = data.clips.some((c) => c.status === "completed");
    if (!clipsAndPromptsReady(data)) {
      if (hasCompleted) {
        throw new Error(
          "Bazi klipler zaten uretilmis; sozleri yeniden bolemem. Promptlar sekmesinden eksikleri tamamlayin veya otomasyonu baslatin."
        );
      }
      setPhase("1/3 Sozler kliplere bolunuyor, promptlar yaziliyor (5–10 dk)...");
      const prepared = await postJson<{ clipCount: number; prompted: number }>(
        `/api/projects/${project.id}/song/prepare-production`,
        { formattedLyrics: lyrics.trim() || undefined }
      );
      toast.success(`${prepared.clipCount} klip + ${prepared.prompted} prompt hazir`);
      data = (await reload()) as ProjectData;
      onPrepared?.();
    }

    assertNotCancelled();
    setPhase("2/3 Karakterler Flow'da uretiliyor (eksikler otomatik tekrar denenecek)...");
    type CastResult = { created: number; total: number; failed: string[]; names: string[]; cancelled?: boolean };
    let cast: CastResult = { created: 0, total: 0, failed: [], names: [] };
    const CAST_ROUNDS = 3;
    for (let round = 1; round <= CAST_ROUNDS; round++) {
      assertNotCancelled();
      if (round > 1) {
        setPhase(`2/3 Kalan karakterler tekrar deneniyor (${round}/${CAST_ROUNDS})...`);
      }
      cast = await postJson<CastResult>(`/api/projects/${project.id}/song/create-cast-flow`);
      data = (await reload()) as ProjectData;
      if (cast.cancelled) throw new CancelledByUser();
      if (!cast.failed?.length) break;
    }
    if (cast.created > 0) {
      toast.success(`${cast.created} karakter Flow'da olusturuldu`);
    }
    if (cast.failed?.length) {
      toast.warning(
        `${cast.failed.length} karakter hâlâ eksik; otomasyon durdurulmuyor. Klipler devam eder, eksik @referans sonra tamamlanabilir.`
      );
    }

    if (jobIsActive(data)) {
      toast.success("Otomasyon zaten calisiyor");
      onGoAutomation?.();
      return;
    }

    assertNotCancelled();
    setPhase("3/3 Otomasyon basliyor — videolar sirayla uretilecek. Render size kaldi.");
    await postJson(`/api/projects/${project.id}/automation/start`);
    await reload();
    toast.success("Oto bitir: klipler + karakterler hazir, videolar sirayla uretiliyor. Render elle.");
    onGoAutomation?.();
  }

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2">
              <Music2 className="h-4 w-4 text-primary" />
              Master parca + sozler
            </CardTitle>
            <CardDescription className="mt-1">
              MP3 + soz kayitliysa Oto bitir sirayla: 1) sozleri kliplere boler ve prompt yazar, 2) tum karakterleri
              Flow&apos;da uretir (eksikleri kendisi tekrar dener), 3) klipleri sirayla baslatir. Render elle kalir.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 shrink-0 flex-wrap">
            {hasMasterAudio ? (
              <Badge variant="success">
                <Check className="h-3 w-3" />
                {songAudioBadgeLabel(songSettings.audioFileName || songSettings.audioPath, songSettings.audioDurationSeconds)}
                {isLosslessSongAudio(songSettings.audioFileName || songSettings.audioPath) ? " · kayipsiz" : ""}
              </Badge>
            ) : (
              <Badge variant="warning">Ses yok</Badge>
            )}
            {lyrics.trim() ? <Badge variant="success">Sozler var</Badge> : <Badge variant="warning">Soz yok</Badge>}
            {hasClips ? <Badge>{project.clips.length} klip</Badge> : null}
            {hasClips ? (
              <Button type="button" variant="ghost" size="sm" onClick={() => setExpanded((v) => !v)}>
                {expanded ? "Gizle" : "Duzenle"}
              </Button>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {hasMasterAudio && songSettings.audioPath ? (
          <audio src={mediaUrl(songSettings.audioPath)} controls className="w-full" />
        ) : (
          <div className="flex items-start gap-2.5 rounded-[12px] border border-warning/20 bg-warning-soft/70 p-3.5 text-[12px] leading-relaxed text-warning">
            <TriangleAlert className="mt-px h-4 w-4 shrink-0" />
            <p>
              Once sarkinin ses dosyasini yukleyin. <strong>WAV veya FLAC onerilir</strong> (kayipsiz). MP3 de olur ama
              zaten sikistirilmistir. Bu parca final videonun sesi olacak.
            </p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Button
            loading={autoRunning}
            disabled={!canPrepare || autoRunning || jobIsActive(project)}
            onClick={() => run("auto", autoFinish)}
          >
            <Play className="h-4 w-4" />
            {jobIsActive(project) ? "Otomasyon calisiyor" : autoRunning ? phase || "Oto bitir..." : "Oto bitir"}
          </Button>
          {(autoRunning || jobIsActive(project)) && (
            <Button variant="danger" loading={stopping} onClick={stopEverything}>
              <CircleStop className="h-4 w-4" />
              Durdur
            </Button>
          )}
          {!canPrepare ? (
            <span className="text-[12px] text-muted">Once ses ve sozleri kaydedin. Ses icin WAV/FLAC daha temiz.</span>
          ) : (
            <span className="text-[12px] text-muted">Sira: klip → karakter (otomatik tekrar) → videolar. Render degil.</span>
          )}
        </div>

        {autoRunning || phase ? (
          <div className="rounded-[12px] border border-primary/15 bg-primary-soft/50 p-3.5 text-[12px] leading-relaxed text-primary">
            {phase || "Calisiyor..."}
            {latestEvent?.message ? (
              <div className="mt-1 text-muted">{latestEvent.message}</div>
            ) : null}
          </div>
        ) : null}

        {expanded || !hasClips ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                type="file"
                accept={SONG_AUDIO_ACCEPT}
                className="h-10 max-w-sm flex-1 min-w-[240px] py-[7px]"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) setPendingFile(file);
                }}
              />
              <Button
                variant="outline"
                size="sm"
                loading={busy === "upload"}
                disabled={!pendingFile || autoRunning}
                onClick={() =>
                  run("upload", async () => {
                    await uploadAudio(pendingFile!);
                    toast.success(`Parca yuklendi · ${pendingFile!.name}`);
                  })
                }
              >
                <Upload className="h-4 w-4" />
                {hasMasterAudio ? "Ses degistir" : "Ses yukle"}
              </Button>
            </div>

            <Textarea
              className="min-h-[140px] font-mono text-[13px]"
              placeholder="Suno sozlerini buraya yapistirin..."
              value={lyrics}
              onChange={(e) => setLyrics(e.target.value)}
              disabled={autoRunning}
            />

            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                loading={busy === "lyrics"}
                disabled={!lyrics.trim() || autoRunning}
                onClick={() =>
                  run("lyrics", async () => {
                    await saveLyrics(lyrics);
                    toast.success("Sozler kaydedildi");
                  })
                }
              >
                Sozleri kaydet
              </Button>
              <Button
                variant="outline"
                loading={busy === "prepare"}
                disabled={!canPrepare || autoRunning}
                onClick={() => run("prepare", prepare)}
              >
                <Wand2 className="h-4 w-4" />
                {hasClips ? "Sadece klipleri yeniden planla" : "Sadece sozleri kliplere bol"}
              </Button>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
