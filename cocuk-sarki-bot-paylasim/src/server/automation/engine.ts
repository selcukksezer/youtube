import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import type { Clip, Project } from "@prisma/client";
import { prisma } from "@/server/db";
import { publishEvent } from "@/server/lib/events";
import { recordEvent } from "@/server/lib/logger";
import { clipFileName, clipFrameFileName, ensureProjectDirs, safeProjectPath } from "@/server/lib/paths";
import { emptyDialogueHint, isKidsSong } from "@/lib/templates";
import { getSettings, parseModelSupportMatrix, resolveModelSupport, validateFlowConfig } from "@/server/services/settings";
import { flowClipSeconds } from "@/lib/flow-generation-settings";
import { extractLastFrame, validateVideoFile } from "@/server/services/ffmpeg";
import { stampClipWithMasterSlice, remuxExistingSongClipVideos } from "@/server/services/song-audio";
import {
  captureDebugSnapshot,
  configureGeneration,
  downloadClipVideo,
  ensureEditorReady,
  ensureFlowReady,
  ensureVideoOutputMode,
  enterPrompt,
  ensureFlowAudioMode,
  ManualActionNeededError,
  openFlowProject,
  snapshotVideoAssetIds,
  startGeneration,
  uploadReferenceImages,
  uniqueExistingImagePaths,
  waitForCompletion,
  isFlowWindowClosedError,
} from "@/server/automation/flow-adapter";
import { ensureDefaultSelectors, getSelectorConfig } from "@/server/automation/selectors";
import { autoCalibrateMissingSelectors } from "@/server/automation/calibration";
import { retryStrategyForAttempt, type ClipState, type JobState } from "@/server/automation/state-machine";
import { getProjectPage, openFlowBrowser, releaseProjectPage } from "@/server/automation/browser";
import { pickSongCastReferencePaths, resolveClipCastMembers } from "@/server/services/song-refs";
import {
  allControls,
  controlFor,
  dropControl,
  liveProjectIds,
  peekControl,
  runInProjectContext,
  assertAutomationContinuing,
  interruptibleSleep,
  AutomationStoppedError,
  ClipCancelledError,
  HEARTBEAT_STALE_MS,
} from "@/server/automation/abort";

/**
 * SQLite destekli otomasyon motoru — PROJE BASINA bir isci.
 * - Her projenin kendi is kilidi, kendi Chrome sekmesi ve kendi durdur/duraklat
 *   bayraklari vardir; birden fazla proje ayni anda uretim yapabilir
 *   (ust sinir: AppSettings.maxParallelProjects)
 * - Is durumu her adimda veritabanina yazilir -> uygulama kapansa bile kaldigi yerden devam
 * - Yeniden deneme merdiveni: ayni prompt -> sayfa yenile -> projeyi yeniden ac -> elle mudahale
 */

export interface EngineStatus {
  runningJobId: string | null;
  pauseRequested: boolean;
  stopRequested: boolean;
  loopAlive: boolean;
  /** Su an canli dongusu olan proje kimlikleri (paralel calisma gorunurlugu). */
  runningProjectIds: string[];
}

/**
 * projectId verilirse O projenin durumu; verilmezse genel ozet
 * (ilk canli is, panelin eski alanlariyla uyumlu kalir).
 */
export function engineStatus(projectId?: string): EngineStatus {
  const runningProjectIds = liveProjectIds();

  if (projectId) {
    const control = peekControl(projectId);
    const loopAlive = !!control?.runningJobId && Date.now() - (control.loopHeartbeatMs || 0) < HEARTBEAT_STALE_MS;
    return {
      runningJobId: control?.runningJobId ?? null,
      pauseRequested: control?.pauseRequested ?? false,
      stopRequested: control?.stopRequested ?? false,
      loopAlive,
      runningProjectIds,
    };
  }

  const first = allControls().find(({ control }) => !!control.runningJobId);
  const loopAlive = !!first && Date.now() - (first.control.loopHeartbeatMs || 0) < HEARTBEAT_STALE_MS;
  return {
    runningJobId: first?.control.runningJobId ?? null,
    pauseRequested: first?.control.pauseRequested ?? false,
    stopRequested: first?.control.stopRequested ?? false,
    loopAlive,
    runningProjectIds,
  };
}

function isMissingRecordError(err: unknown): boolean {
  return typeof err === "object" && err !== null && "code" in err && (err as { code: string }).code === "P2025";
}

/** Is durumunu yazar. Kayit silinmisse (proje silme) sessizce false doner. */
async function setJobState(
  jobId: string,
  state: JobState,
  extra?: { pausedReason?: string | null; errorMessage?: string | null }
): Promise<boolean> {
  try {
    const job = await prisma.automationJob.update({
      where: { id: jobId },
      data: {
        state,
        ...(extra?.pausedReason !== undefined ? { pausedReason: extra.pausedReason } : {}),
        ...(extra?.errorMessage !== undefined ? { errorMessage: extra.errorMessage } : {}),
        ...(state === "running" ? { startedAt: new Date() } : {}),
        ...(state === "completed" || state === "failed" || state === "stopped" ? { finishedAt: new Date() } : {}),
      },
    });
    publishEvent(job.projectId, {
      type: "job",
      payload: { id: job.id, state: job.state, pausedReason: job.pausedReason, currentClipId: job.currentClipId },
    });
    return true;
  } catch (err) {
    if (isMissingRecordError(err)) {
      console.warn(`[otomasyon] Is kaydi yok (silinmis olabilir): ${jobId} → ${state}`);
      return false;
    }
    throw err;
  }
}

async function setClipState(clip: Clip, state: ClipState, errorMessage?: string | null): Promise<Clip> {
  try {
    const updated = await prisma.clip.update({
      where: { id: clip.id },
      data: { status: state, ...(errorMessage !== undefined ? { errorMessage } : {}) },
    });
    publishEvent(clip.projectId, {
      type: "clip",
      payload: {
        id: updated.id,
        index: updated.index,
        status: updated.status,
        attemptCount: updated.attemptCount,
        errorMessage: updated.errorMessage,
        videoPath: updated.videoPath,
      },
    });
    return updated;
  } catch (err) {
    if (isMissingRecordError(err)) {
      console.warn(`[otomasyon] Klip kaydi yok (silinmis olabilir): ${clip.id} → ${state}`);
      return { ...clip, status: state, errorMessage: errorMessage ?? clip.errorMessage };
    }
    throw err;
  }
}

/** Duraklatma istegi varsa isi paused yapar ve devam/durdur bekler. */
async function waitWhilePaused(jobId: string, projectId: string): Promise<void> {
  const control = controlFor(projectId);
  if (!control.pauseRequested) return;
  await setJobState(jobId, "paused", { pausedReason: "Kullanici duraklatti" });
  await recordEvent({ projectId, jobId, step: "job", message: "Otomasyon duraklatildi" });
  while (control.pauseRequested && !control.stopRequested) {
    control.loopHeartbeatMs = Date.now();
    await new Promise<void>((resolve) => setTimeout(resolve, 1_000));
  }
  if (!control.stopRequested) {
    await setJobState(jobId, "running", { pausedReason: null });
    await recordEvent({ projectId, jobId, step: "job", message: "Otomasyon devam ediyor" });
  }
}

async function sleep(ms: number): Promise<void> {
  await interruptibleSleep(ms);
}

export class AutomationBusyError extends Error {
  constructor(message = "Bu projenin otomasyonu zaten calisiyor. Once onu durdurun veya bitmesini bekleyin.") {
    super(message);
    this.name = "AutomationBusyError";
  }
}

/** Otomasyonu baslatir (tamamlanmis klipler atlanir — kaldigi yerden devam). */
export async function startAutomation(projectId: string): Promise<{ jobId: string }> {
  // Yetim bellek kilidi varsa temizle
  await reconcileOrphanJobs(projectId, { force: true });
  const control = controlFor(projectId);
  if (control.runningJobId) throw new AutomationBusyError();

  let project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  if (project.templateType === "longform") {
    throw new Error("Gorsel slayt anlatilari Flow otomasyonu kullanmaz. Anlatici studyosundan gorselleri uretin.");
  }

  // Paralel calisma siniri: her proje ayri Chrome sekmesi + ayri Flow uretimi
  // demektir; sinirsiz acmak makineyi ve Google tarafindaki kotayi zorlar.
  const parallelLimit = Math.max(1, (await getSettings()).maxParallelProjects ?? 4);
  const alreadyRunning = liveProjectIds().filter((id) => id !== projectId);
  if (alreadyRunning.length >= parallelLimit) {
    throw new AutomationBusyError(
      `Ayni anda en fazla ${parallelLimit} proje calisabilir (su an ${alreadyRunning.length} calisiyor). Ayarlar > "Paralel proje sayisi" ile artirabilir veya calisan bir isi durdurabilirsiniz.`
    );
  }

  // Paralel guvenlik: iki is AYNI Flow projesinde calisamaz — ayni composer'a
  // yazip birbirlerinin videosunu indirirler. Link bos ise ikinci is genel Flow
  // sayfasina duser ve ayni riski dogurur.
  if (alreadyRunning.length > 0) {
    const normalize = (url: string): string => url.trim().replace(/\/+$/, "").toLowerCase();
    const myUrl = normalize(project.flowProjectUrl);
    if (!myUrl) {
      throw new AutomationBusyError(
        `Baska bir proje calisirken bu projeyi baslatmak icin "Flow proje linki" dolu olmali (Proje Ayarlari). Link olmadan iki is ayni Flow sayfasini paylasir ve klipler birbirine karisir.`
      );
    }
    const others = await prisma.project.findMany({
      where: { id: { in: alreadyRunning } },
      select: { id: true, name: true, flowProjectUrl: true },
    });
    const clash = others.find((other) => normalize(other.flowProjectUrl) === myUrl);
    if (clash) {
      throw new AutomationBusyError(
        `"${clash.name}" projesi ayni Flow adresinde calisiyor. Her projenin Flow linki FARKLI olmali; ayni adreste iki is birbirinin promptunu ve indirmesini bozar.`
      );
    }
  }

  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant: "primary" }, orderBy: { index: "asc" } });
  if (clips.length === 0) throw new Error("Proje icin klip bulunamadi. Once hikayeyi kliplere bolun.");
  // Dogru sira: sozler -> klipler -> karakterler -> promptlar -> OTOMASYON.
  // Bir kismi promptsuzsa otomasyon o klipte bos/hatali icerik uretir; hepsi
  // hazir olmadan baslamayiz (tek klip promptu yeterli sayilmazdi).
  const withoutPrompts = clips.filter((c) => !c.prompt.trim());
  if (withoutPrompts.length === clips.length) {
    throw new Error("Klip promptlari olusturulmamis. Once promptlari olusturun.");
  }
  if (withoutPrompts.length > 0) {
    throw new Error(
      `${withoutPrompts.length} klibin (${withoutPrompts.map((c) => c.index).join(", ")}) promptu yok. Otomasyon baslamadan once Promptlar sekmesinden "Tum Promptlari Olustur" ile hepsini tamamlayin.`
    );
  }

  // Konusma metni bos olan klipler sessiz/anlamsiz video uretir
  const emptyDialogue = clips.filter((c) => !c.dialogue.trim());
  if (emptyDialogue.length > 0) {
    throw new Error(
      project.templateType === "kids_animation" || project.templateType === "kids_song"
        ? `${emptyDialogue.length} sahnenin soz/diyalog metni bos. ${emptyDialogueHint(project.templateType)}`
        : `${emptyDialogue.length} klibin konusma metni bos. Klipler sekmesinden metinleri doldurun ve promptlari yeniden olusturun.`
    );
  }

  // Prompt, guncel diyalogu iceriyor mu? (Diyalog sonradan uretildiyse prompt eskimis olur)
  // Karsilastirma bosluk-duyarsiz: promptta soz tek satira normalize edilerek tirnaklanir,
  // diyalog ise DB'de satir sonlariyla durur — ham includes() yanlis alarm verir.
  const normWs = (s: string) => s.replace(/\s+/g, " ").trim();
  const stalePrompts = clips.filter(
    (c) => c.prompt.trim() && !normWs(c.prompt).includes(normWs(c.dialogue).slice(0, 30))
  );
  if (stalePrompts.length > 0) {
    throw new Error(
      `${stalePrompts.length} klibin promptu guncel diyalogu icermiyor (metin sonradan degismis). Promptlar sekmesinden "Tum Promptlari Olustur" ile yenileyin.`
    );
  }

  // Model destek dogrulamasi
  const settings = await getSettings();
  const matrix = parseModelSupportMatrix(settings);
  const supportedDurations = resolveModelSupport(matrix, project.flowModel)?.durations;
  const clampedSeconds = flowClipSeconds(project.flowModel, project.clipSeconds, supportedDurations);
  if (clampedSeconds !== project.clipSeconds) {
    const previous = project.clipSeconds;
    await prisma.project.update({ where: { id: projectId }, data: { clipSeconds: clampedSeconds } });
    project = { ...project, clipSeconds: clampedSeconds };
    await recordEvent({
      projectId,
      step: "job",
      level: "warning",
      message: `Klip suresi ${previous}s → ${clampedSeconds}s (${project.flowModel} 10s destemiyor; 9:16 short 8s kullanilacak)`,
    });
  }
  const validation = validateFlowConfig(matrix, {
    model: project.flowModel,
    clipSeconds: project.clipSeconds,
    aspectRatio: project.aspectRatio,
    useReference: project.useReference,
    useStartFrame: project.useStartFrame || project.usePrevLastFrame,
  });
  if (!validation.ok) {
    throw new Error(
      `Flow ayarlari gecersiz: ${validation.errors.join(" | ")}. Bu ayarlar projeye ozeldir; "Proje Ayarlari" sekmesinden duzeltin (Ayarlar ekranindaki varsayilanlar yalnizca yeni projeleri etkiler).`
    );
  }
  for (const warning of validation.warnings) {
    await recordEvent({ projectId, step: "job", level: "warning", message: warning });
  }

  // Karakter gorseli onay kontrolu (uretilmis ama onaysiz gorselle baslamayiz)
  const cast = await prisma.characterProfile.findMany({ where: { projectId } });
  const namedCast = cast.filter((c) => c.name.trim());
  if (project.useReference && namedCast.length > 0) {
    const unapproved = namedCast.filter((c) => c.referenceImagePath && !c.imageApproved);
    const missing = namedCast.filter((c) => !c.referenceImagePath);
    if (unapproved.length > 0) {
      throw new Error(
        `${unapproved.length} karakter gorseli henuz hazir degil. Uretim sayfasindaki Karakterler cubugundan Topluca uret.`
      );
    }
    if (missing.length > 0) {
      throw new Error(
        `${missing.length} karakterin Flow referansi yok (${missing.map((c) => c.name).join(", ")}). Ustteki Karakterler cubugundan Topluca uret — Flow acilip hepsi sirayla eklenecek.`
      );
    }
  } else if (project.useReference) {
    const character = namedCast.find((c) => c.role === "main");
    if (character?.referenceImagePath && !character.imageApproved) {
      throw new Error("Karakter gorseli henuz hazir degil. Karakterler cubugundan Topluca uret.");
    }
  }

  // Flow @karakter kullaniminda referans gorsel yuklenmez — Flow'un kendi
  // "Karakterler" ozelligindeki kayit (flowCharacterReference, or. "@Adi")
  // tek dayanaktir. Bu bossa prompttaki "@Adi" Flow'da hicbir seye baglanmaz.
  if (project.useFlowCharacter && namedCast.length > 0) {
    const missingFlowRef = namedCast.filter((c) => !c.flowCharacterReference.trim());
    if (missingFlowRef.length > 0) {
      throw new Error(
        `${missingFlowRef.length} karakterin Flow'da kaydi yok (${missingFlowRef.map((c) => c.name).join(", ")}). Karakterler cubugundan "Topluca uret" ile Flow'a ekleyin — aksi halde promptaki @mention Flow'da hicbir karaktere baglanmaz.`
      );
    }
  }

  await ensureDefaultSelectors();

  if (isKidsSong(project.templateType)) {
    const remuxed = await remuxExistingSongClipVideos(projectId, project.clipSeconds || 8);
    if (remuxed > 0) {
      await recordEvent({
        projectId,
        step: "song",
        message: `${remuxed} mevcut klibin Flow sesi silindi, yerine master MP3 dilimi basildi`,
      });
    }
  }

  // Generate dugmesi kalibresizse otomasyon DURMAZ: ilk klipte acik editor
  // sayfasinda oto kalibrasyon calisir; o da bulamazsa Enter ile gonderilir.
  if (project.generateButtonMode === "auto") {
    const config = await getSelectorConfig("generateButton");
    if (!config || !config.value) {
      await recordEvent({
        projectId,
        step: "calibration",
        level: "warning",
        message:
          "generateButton kalibrasyonu yok — ilk klipte otomatik kalibrasyon denenecek. Isterseniz Ayarlar > Flow Secici Kalibrasyonu'ndan 'Oto kalibre et' ile simdiden tanitabilirsiniz.",
      });
    }
  }

  // Eski yarim kalmis isleri kapat: panelde "calisan gorev" sayisini sismesin
  await prisma.automationJob.updateMany({
    where: { projectId, state: { in: ["pending", "running", "paused", "needs_manual_action"] } },
    data: { state: "stopped", finishedAt: new Date() },
  });

  // Kuyrukta bekleyen kliplerin sayaci temiz baslasin (kesintiden kalan
  // yuksek deneme sayilari aninda "maksimum deneme" hatasi uretmesin)
  await prisma.clip.updateMany({
    where: { projectId, languageVariant: "primary", status: "pending", attemptCount: { gt: 0 } },
    data: { attemptCount: 0 },
  });

  const job = await prisma.automationJob.create({
    data: { projectId, type: "flow_generation", state: "pending", mode: project.automationMode },
  });
  control.runningJobId = job.id;
  control.pauseRequested = false;
  control.stopRequested = false;
  control.cancelCurrentClip = false;
  control.loopHeartbeatMs = Date.now();

  await prisma.project.update({ where: { id: projectId }, data: { status: "automating" } });
  publishEvent(projectId, { type: "project", payload: { id: projectId, status: "automating" } });

  // Ana dongu arka planda calisir; API cagrisi hemen doner.
  // runInProjectContext: dongunun icindeki TUM async cagrilar (Playwright dahil)
  // bu projeye ait sayilir; assertAutomationContinuing dogru bayraklari okur.
  void runInProjectContext(projectId, () => runJobLoop(job.id, projectId)).catch(async (err) => {
    await recordEvent({ projectId, jobId: job.id, step: "job", level: "error", message: `Is dongusu beklenmedik hata: ${err instanceof Error ? err.message : String(err)}` });
    await setJobState(job.id, "failed", { errorMessage: err instanceof Error ? err.message : String(err) });
    control.runningJobId = null;
  });

  return { jobId: job.id };
}

export function pauseAutomation(projectId: string): void {
  controlFor(projectId).pauseRequested = true;
}

export function resumeAutomation(projectId: string): void {
  controlFor(projectId).pauseRequested = false;
}

const ACTIVE_JOB_STATES = ["pending", "running", "paused", "needs_manual_action"] as const;

/**
 * Bellekte dongu yokken DB'de "calisiyor" kalan yetim isleri kapatir.
 * Sunucu yeniden baslatildiginda panelde sahte Durdur/Duraklat gorunmesini onler.
 *
 * PARALEL GUVENLIK: canli dongusu olan projelere DOKUNMAZ. Panel her durum
 * sorgusunda bu fonksiyonu cagirdigi icin, aksi halde bir projenin sorgusu
 * digerlerinin calisan islerini durdururdu.
 */
const reconcileLastRunAt = new Map<string, number>();
const RECONCILE_THROTTLE_MS = 8_000;

export async function reconcileOrphanJobs(projectId?: string, opts?: { force?: boolean }): Promise<number> {
  // Panel her durum sorgusunda cagirir; her cagrida DB taramasi yapmak
  // sayfa gecislerini yavaslatir. Ayni kapsam icin 8 sn'de bir yeter.
  const throttleKey = projectId ?? "__global__";
  const lastRun = reconcileLastRunAt.get(throttleKey) ?? 0;
  if (!opts?.force && Date.now() - lastRun < RECONCILE_THROTTLE_MS) return 0;
  reconcileLastRunAt.set(throttleKey, Date.now());

  const live = new Set(liveProjectIds());

  // Kalinti bellek kilidi temizligi (dongu olmeden bayrak kalmis olabilir)
  for (const { projectId: id, control } of allControls()) {
    if (live.has(id)) continue;
    if (control.runningJobId) {
      control.runningJobId = null;
      control.stopRequested = false;
      control.pauseRequested = false;
      control.cancelCurrentClip = false;
    }
    if (id !== projectId) dropControl(id);
  }

  if (projectId && live.has(projectId)) return 0;

  const liveIds = [...live];
  const result = await prisma.automationJob.updateMany({
    where: {
      state: { in: [...ACTIVE_JOB_STATES] },
      ...(projectId ? { projectId } : liveIds.length > 0 ? { projectId: { notIn: liveIds } } : {}),
    },
    data: {
      state: "stopped",
      finishedAt: new Date(),
      pausedReason: "Onceki oturum sonlandi (sunucu yeniden baslatildi veya is koptu)",
    },
  });
  if (result.count > 0) {
    await recordEvent({
      projectId: projectId ?? undefined,
      step: "job",
      level: "warning",
      message: `${result.count} yetim otomasyon isi durduruldu (canli dongu yoktu)`,
    });
    if (projectId) {
      const project = await prisma.project.findUnique({ where: { id: projectId }, select: { status: true } });
      if (project?.status === "automating") {
        await prisma.project.update({ where: { id: projectId }, data: { status: "prompts_ready" } });
        publishEvent(projectId, { type: "project", payload: { id: projectId, status: "prompts_ready" } });
      }
    }
  }
  return result.count;
}

/**
 * Durdur: o projenin canli dongusunu keser VE DB'yi hemen "stopped" yapar
 * (yetim islerde de calisir). projectId verilmezse TUM projeler durdurulur.
 * Diger projelerin isleri etkilenmez.
 */
export async function stopAutomation(projectId?: string): Promise<{
  stopping: true;
  jobId: string | null;
  forced: boolean;
  stoppedCount: number;
}> {
  if (!projectId) {
    const ids = allControls().map((entry) => entry.projectId);
    let stoppedCount = 0;
    let jobId: string | null = null;
    for (const id of ids) {
      const result = await stopAutomation(id);
      stoppedCount += result.stoppedCount;
      jobId = jobId ?? result.jobId;
    }
    return { stopping: true, jobId, forced: ids.length === 0, stoppedCount };
  }

  const control = controlFor(projectId);
  const liveJobId = control.runningJobId;
  control.stopRequested = true;
  control.pauseRequested = false;
  control.cancelCurrentClip = true;

  // Canli donguye kisa sure tani; waitForCompletion assert ile cikmali
  if (liveJobId) {
    for (let i = 0; i < 50 && control.runningJobId === liveJobId; i++) {
      await new Promise<void>((resolve) => setTimeout(resolve, 100));
    }
    if (control.runningJobId === liveJobId) {
      control.runningJobId = null;
    }
  }

  let stoppedCount = 0;
  {
    const updated = await prisma.automationJob.updateMany({
      where: { projectId, state: { in: [...ACTIVE_JOB_STATES] } },
      data: { state: "stopped", finishedAt: new Date(), pausedReason: null, errorMessage: null },
    });
    stoppedCount = updated.count;
  }

  {
    // Yarida kalan klip durumlarini kuyruga geri al
    await prisma.clip.updateMany({
      where: {
        projectId,
        languageVariant: "primary",
        status: {
          in: [
            "preparing",
            "opening_flow",
            "waiting_for_login",
            "selecting_project",
            "uploading_reference",
            "configuring_model",
            "entering_prompt",
            "generating",
            "waiting_for_completion",
            "downloading",
            "validating_download",
            "extracting_last_frame",
            "retrying",
            "paused",
          ],
        },
      },
      data: { status: "pending", errorMessage: "Otomasyon durduruldu" },
    });

    const project = await prisma.project.findUnique({ where: { id: projectId }, select: { status: true } });
    if (project?.status === "automating") {
      await prisma.project.update({ where: { id: projectId }, data: { status: "prompts_ready" } });
      publishEvent(projectId, { type: "project", payload: { id: projectId, status: "prompts_ready" } });
    }

    // UI'nin job badge'ini yenilemesi icin
    publishEvent(projectId, {
      type: "job",
      payload: { id: liveJobId ?? "stopped", state: "stopped", pausedReason: null, currentClipId: null },
    });
  }

  await recordEvent({
    projectId,
    jobId: liveJobId ?? undefined,
    step: "job",
    message: liveJobId
      ? "Otomasyon durduruldu (canli is kesildi)"
      : control.busyOutsideJob
        ? "Durdur istegi alindi — karakter uretimi iptal ediliyor"
        : stoppedCount > 0
          ? `Otomasyon durduruldu (${stoppedCount} yetim/aktif is kapatildi)`
          : "Durdur istegi alindi (aktif is bulunamadi)",
  });

  // Sonraki baslatma icin bayraklari temizle (dongu finally de temizler).
  // ONEMLI: is disi uzun calisma (karakter kadrosu uretimi) suruyorsa bayragi
  // TEMIZLEMEYIZ — yoksa durdur sinyali o dongu okumadan silinir ve islem
  // durdurulamaz. Bayragi o is kendi finally blogunda temizler.
  if (!control.runningJobId && !control.busyOutsideJob) {
    control.stopRequested = false;
    control.pauseRequested = false;
    control.cancelCurrentClip = false;
    await releaseProjectPage(projectId);
  }

  return { stopping: true, jobId: liveJobId, forced: !liveJobId, stoppedCount };
}

export function cancelCurrentClip(projectId: string): void {
  controlFor(projectId).cancelCurrentClip = true;
}

function throwIfCancelled(): void {
  assertAutomationContinuing();
}

async function runJobLoop(jobId: string, projectId: string): Promise<void> {
  const settings = await getSettings();
  const control = controlFor(projectId);
  control.loopHeartbeatMs = Date.now();
  await setJobState(jobId, "running");
  await recordEvent({ projectId, jobId, step: "job", message: "Otomasyon basladi" });

  try {
    while (true) {
      control.loopHeartbeatMs = Date.now();
      const projectStillThere = await prisma.project.findUnique({ where: { id: projectId }, select: { id: true } });
      if (!projectStillThere) {
        console.warn(`[otomasyon] Proje silindi, is durduruluyor: ${projectId}`);
        break;
      }

      if (control.stopRequested) {
        await setJobState(jobId, "stopped");
        await recordEvent({ projectId, jobId, step: "job", message: "Otomasyon kullanici istegiyle durduruldu" });
        break;
      }
      await waitWhilePaused(jobId, projectId);
      if (control.stopRequested) continue;

      const nextClip = await prisma.clip.findFirst({
        where: { projectId, languageVariant: "primary", status: { notIn: ["completed", "needs_manual_action", "failed"] } },
        orderBy: { index: "asc" },
      });

      if (!nextClip) {
        const remaining = await prisma.clip.count({
          where: { projectId, languageVariant: "primary", status: { in: ["needs_manual_action", "failed"] } },
        });
        if (remaining > 0) {
          await setJobState(jobId, "needs_manual_action", {
            pausedReason: `${remaining} klip elle mudahale bekliyor (basarisiz/kalibrasyonluk). Panelden yeniden deneyin.`,
          });
          await recordEvent({ projectId, jobId, step: "job", level: "warning", message: `Is tamamlanamadi: ${remaining} klip elle mudahale bekliyor` });
        } else {
          const ok = await setJobState(jobId, "completed");
          if (ok) {
            try {
              await prisma.project.update({ where: { id: projectId }, data: { status: "clips_done" } });
              publishEvent(projectId, { type: "project", payload: { id: projectId, status: "clips_done" } });
              await recordEvent({ projectId, jobId, step: "job", message: "Tum klipler tamamlandi. FFmpeg birlestirmeye hazir." });
            } catch (err) {
              if (!isMissingRecordError(err)) throw err;
            }
          }
        }
        break;
      }

      try {
        await prisma.automationJob.update({ where: { id: jobId }, data: { currentClipId: nextClip.id } });
      } catch (err) {
        if (isMissingRecordError(err)) {
          console.warn(`[otomasyon] Is kaydi yok, dongu sonlandi: ${jobId}`);
          break;
        }
        throw err;
      }
      const result = await processClip(jobId, projectId, nextClip.id);

      if (result === "stopped") {
        await setJobState(jobId, "stopped");
        await recordEvent({ projectId, jobId, step: "job", message: "Otomasyon kullanici istegiyle durduruldu" });
        break;
      }

      if (result === "manual") {
        await setJobState(jobId, "needs_manual_action", { pausedReason: "Elle dogrulama/mudahale gerekiyor" });
        // Kullanici sorunu cozup devam edene kadar bekle
        control.pauseRequested = true;
        await waitWhilePaused(jobId, projectId);
        if (control.stopRequested) continue;
      }

      // Uretimler arasi bekleme (sabit asiri hizli bot davranisi olusturmamak icin)
      if (result === "completed" || result === "failed") {
        try {
          await sleep(settings.waitBetweenGenerationsMs);
        } catch (err) {
          if (err instanceof AutomationStoppedError) {
            await setJobState(jobId, "stopped");
            await recordEvent({ projectId, jobId, step: "job", message: "Otomasyon kullanici istegiyle durduruldu" });
            break;
          }
          if (!(err instanceof ClipCancelledError)) throw err;
        }
      }
    }
  } finally {
    control.runningJobId = null;
    control.pauseRequested = false;
    control.stopRequested = false;
    control.cancelCurrentClip = false;
    control.loopHeartbeatMs = 0;
    // Projeye ayrilmis Chrome sekmesini birak (ana sekme kapatilmaz)
    await releaseProjectPage(projectId).catch(() => {});
  }
}

type ClipResult = "completed" | "manual" | "failed" | "cancelled" | "stopped";

async function processClip(jobId: string, projectId: string, clipId: string): Promise<ClipResult> {
  const settings = await getSettings();
  const project = await prisma.project.findUniqueOrThrow({ where: { id: projectId } });
  let clip = await prisma.clip.findUniqueOrThrow({ where: { id: clipId } });
  const cast = await prisma.characterProfile.findMany({ where: { projectId } });
  const clipCharacter =
    (clip.characterId ? cast.find((c) => c.id === clip.characterId) : null) ??
    cast.find((c) => c.role === "main") ??
    cast[0] ??
    null;

  const attempt = clip.attemptCount + 1;
  try {
    clip = await prisma.clip.update({ where: { id: clip.id }, data: { attemptCount: attempt } });
  } catch (err) {
    if (isMissingRecordError(err)) return "cancelled";
    throw err;
  }
  const strategy = retryStrategyForAttempt(attempt, settings.maxRetries);

  if (strategy === "manual") {
    await setClipState(clip, "needs_manual_action", `Maksimum yeniden deneme (${settings.maxRetries}) asildi`);
    await recordEvent({ projectId, jobId, clipId, step: "clip", level: "error", message: `Klip ${clip.index}: maksimum deneme asildi, elle mudahale gerekiyor`, attempt });
    return "manual";
  }

  await recordEvent({ projectId, jobId, clipId, step: "clip", message: `Klip ${clip.index} isleniyor (deneme ${attempt}, strateji: ${strategy})`, attempt });

  try {
    clip = await setClipState(clip, "preparing");
    throwIfCancelled();

    // 1) Flow acik mi + oturum hazir mi (bu projeye AYRILMIS sekmede)
    clip = await setClipState(clip, "opening_flow");
    let page = await ensureFlowReady(projectId, project.flowProjectUrl).catch(async (err) => {
      if (err instanceof ManualActionNeededError) {
        await setClipState(clip, "waiting_for_login", err.message);
        throw err;
      }
      throw err;
    });

    // Yeniden deneme stratejileri
    if (strategy === "reload_page") {
      await recordEvent({ projectId, jobId, clipId, step: "clip", message: "Strateji: sayfa yenileniyor", attempt });
      await page.reload({ waitUntil: "domcontentloaded", timeout: 60_000 });
      await sleep(2_000);
    } else if (strategy === "reopen_project") {
      // Once bu projeye ozel adres; yoksa genel Flow adresi (proje adresi iceriyorsa).
      const projectUrl = project.flowProjectUrl.trim();
      const canReopen = projectUrl.length > 0 || project.flowProjectName.trim().length > 0 || /\/project/i.test(settings.flowUrl);
      if (canReopen) {
        const target = projectUrl || settings.flowUrl;
        await recordEvent({ projectId, jobId, clipId, step: "clip", message: `Strateji: proje adresi yeniden aciliyor (${target})`, attempt });
        await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60_000 });
      } else {
        await recordEvent({
          projectId,
          jobId,
          clipId,
          step: "clip",
          level: "warning",
          message:
            "Strateji: sayfa yenilendi (bu proje icin Flow adresi tanimli degil — Proje Ayarlari > 'Flow proje linki' alanini doldurmaniz onerilir)",
          attempt,
        });
        await page.reload({ waitUntil: "domcontentloaded", timeout: 60_000 });
      }
      await sleep(2_000);
    }
    page = await ensureFlowReady(projectId, project.flowProjectUrl);
    throwIfCancelled();

    // 2) Dogru Flow projesi + editor ekraninda oldugumuzu garanti et
    clip = await setClipState(clip, "selecting_project");
    if (clip.index === 1 || strategy === "reopen_project") {
      await openFlowProject(page, project);
    }
    await ensureEditorReady(page, project);
    await ensureVideoOutputMode(page, project);
    // Kritik seciciler (promptInput / generateButton) kalibresizse acik
    // editor sayfasinda kendiliginden kalibre et — tiklamalar isabetli olsun.
    if (clip.index === 1) {
      await autoCalibrateMissingSelectors(page, projectId).catch(() => {});
    }
    throwIfCancelled();

    // 3) Model/sure/oran ONCE — ayar degisimi composer'i sifirlayabilir;
    //    referanslar SONRA eklenmeli ki kaybolmasin.
    clip = await setClipState(clip, "configuring_model");
    if (clip.index === 1 || strategy === "reopen_project") {
      await configureGeneration(page, project);
    }
    throwIfCancelled();

    // 4) Referans gorseli / onceki son kare (cocuk: tum sabit kadro)
    clip = await setClipState(clip, "uploading_reference");
    const referencePaths = await resolveReferenceImages(project, clip, clipCharacter, cast);
    if (referencePaths.length > 0) {
      await uploadReferenceImages(page, project, referencePaths);
    }
    throwIfCancelled();

    // 5) Prompt (once ciktinin VIDEO oldugundan emin ol: referans yuklemesi
    //    Flow'u bazen goruntu moduna kaydiriyor ve video yerine gorsel uretiliyor)
    clip = await setClipState(clip, "entering_prompt");
    await ensureVideoOutputMode(page, project, { repairSettings: true });
    if (isKidsSong(project.templateType)) {
      await ensureFlowAudioMode(page, project, false);
    }
    await enterPrompt(page, project, clip.prompt);
    throwIfCancelled();

    // 6) Generate — startGeneration icinde video modu TEKRAR zorlanir
    // Uretim oncesi varlik kimlikleri: "yeni video gercekten olustu mu" ve
    // "hangi kartin indirilecegi" sorularinin tek kesin dayanagi.
    const knownAssetIds = await snapshotVideoAssetIds(page);
    clip = await setClipState(clip, "generating");
    await startGeneration(page, project, project.generateButtonMode === "manual" ? "manual" : "auto");
    throwIfCancelled();

    // 7) Tamamlanma bekle
    clip = await setClipState(clip, "waiting_for_completion");
    const newAssetId = await waitForCompletion(page, project, knownAssetIds);
    throwIfCancelled();

    // 8) Indir
    clip = await setClipState(clip, "downloading");
    ensureProjectDirs(project.slug);
    const targetPath = safeProjectPath(project.slug, "clips", clipFileName(clip.index, clip.id));
    const savedPath = await downloadClipVideo(page, project, targetPath, newAssetId);
    throwIfCancelled();

    // 8b) AYNI VIDEO KONTROLU: indirilen dosya baska bir klibin videosuyla
    // birebir ayniysa (proje geneli indirme, yanlis kart vb.) klip tamamlanmis
    // sayilamaz — dosya silinir ve klip yeniden denenir.
    const duplicateOf = await findDuplicateClipVideo(projectId, clip.id, savedPath);
    if (duplicateOf !== null) {
      fs.rmSync(savedPath, { force: true });
      throw new Error(
        `Indirilen video, klip ${duplicateOf} ile birebir ayni (yeni uretim degil, eski video inmis). Klip yeniden denenecek.`
      );
    }

    // 9) Dogrula (boyut + ffprobe)
    clip = await setClipState(clip, "validating_download");
    const validation = await validateVideoFile(savedPath);
    if (!validation.ok || !validation.info) {
      throw new Error(`Indirilen video dogrulanamadi: ${validation.error}`);
    }

    let stampedInfo = validation.info;
    if (isKidsSong(project.templateType)) {
      const clipCount = await prisma.clip.count({ where: { projectId, languageVariant: clip.languageVariant } });
      const stamped = await stampClipWithMasterSlice({
        projectId,
        clipIndex: clip.index,
        clipCount,
        clipSeconds: project.clipSeconds || 8,
        videoPath: savedPath,
      });
      if (!stamped) {
        throw new Error("Master parca yok — klip Flow sesiyle birakilmaz. Uretim sayfasindan WAV/FLAC veya MP3 yukleyin.");
      }
      const afterMux = await validateVideoFile(savedPath);
      if (!afterMux.ok || !afterMux.info) {
        throw new Error(`Ses dilimi basildiktan sonra video dogrulanamadi: ${afterMux.error}`);
      }
      stampedInfo = afterMux.info;
    }

    await prisma.generatedAsset.create({
      data: {
        projectId,
        clipId: clip.id,
        kind: "clip_video",
        path: savedPath,
        bytes: stampedInfo.sizeBytes,
        meta: JSON.stringify({ duration: stampedInfo.durationSeconds, codec: stampedInfo.videoCodec, audio: stampedInfo.audioCodec }),
      },
    });

    // 10) Son kare (sonraki klip icin gerekiyorsa)
    let lastFramePath: string | null = null;
    if (project.usePrevLastFrame || project.useStartFrame) {
      clip = await setClipState(clip, "extracting_last_frame");
      lastFramePath = safeProjectPath(project.slug, "frames", clipFrameFileName(clip.index, clip.id, "last"));
      await extractLastFrame(savedPath, lastFramePath);
      await prisma.generatedAsset.create({
        data: { projectId, clipId: clip.id, kind: "last_frame", path: lastFramePath, bytes: fs.statSync(lastFramePath).size },
      });
    }

    clip = await prisma.clip.update({
      where: { id: clip.id },
      data: {
        videoPath: savedPath,
        lastFramePath,
        actualDurationSeconds: stampedInfo.durationSeconds,
        errorMessage: null,
      },
    });
    clip = await setClipState(clip, "completed");
    await recordEvent({
      projectId,
      jobId,
      clipId,
      step: "clip",
      message: `Klip ${clip.index} tamamlandi (${stampedInfo.durationSeconds.toFixed(1)} sn, ${(stampedInfo.sizeBytes / (1024 * 1024)).toFixed(1)} MB)`,
      attempt,
    });
    return "completed";
  } catch (err) {
    if (err instanceof AutomationStoppedError) {
      await setClipState(clip, "paused", "Otomasyon durduruldu");
      await recordEvent({
        projectId,
        jobId,
        clipId,
        step: "clip",
        level: "warning",
        message: `Klip ${clip.index}: otomasyon durduruldu`,
        attempt,
      });
      return "stopped";
    }
    if (err instanceof ClipCancelledError) {
      await setClipState(clip, "paused", "Klip iptal edildi");
      await recordEvent({ projectId, jobId, clipId, step: "clip", level: "warning", message: `Klip ${clip.index} iptal edildi`, attempt });
      return "cancelled";
    }
    if (err instanceof ManualActionNeededError) {
      await setClipState(clip, "needs_manual_action", err.message);
      await recordEvent({ projectId, jobId, clipId, step: "clip", level: "warning", message: err.message, attempt });
      return "manual";
    }
    const message = err instanceof Error ? err.message : String(err);
    if (isFlowWindowClosedError(err)) {
      await recordEvent({
        projectId,
        jobId,
        clipId,
        step: "clip",
        level: "warning",
        message: `Klip ${clip.index}: Flow penceresi kapandi — Chrome yeniden acilacak`,
        attempt,
      });
      await openFlowBrowser().catch(() => {});
    }
    // Ekran goruntusu bu projenin KENDI sekmesinden alinmali (paralel calismada
    // ana sekme baska bir projeye ait olabilir).
    const page = getProjectPage(projectId);
    let screenshotPath: string | undefined;
    if (page) {
      const snapshot = await captureDebugSnapshot(page, project.slug, `clip-${clip.index}-error`);
      screenshotPath = snapshot.screenshotPath;
    }
    await setClipState(clip, "retrying", message);
    await recordEvent({
      projectId,
      jobId,
      clipId,
      step: "clip",
      level: "error",
      message: `Klip ${clip.index} hata (deneme ${attempt}): ${message}`,
      screenshotPath,
      attempt,
      detail: err instanceof Error ? { stack: err.stack?.slice(0, 2000) } : undefined,
    });
    return "failed";
  }
}

/**
 * Indirilen videonun ayni projedeki BASKA bir klibin videosuyla birebir ayni
 * olup olmadigini icerik ozetiyle (md5) kontrol eder. Ayniysa o klibin
 * sirasini dondurur; degilse null.
 *
 * Bu, "tamamlandi ama eski video indi" hatasina karsi son guvenlik agidir:
 * dosya adindaki zaman damgasi guvenilir degildir (Flow arsivi indirme aninda
 * olusturup o anin saatiyle adlandirir), icerik ozeti ise kesindir.
 */
async function findDuplicateClipVideo(projectId: string, clipId: string, videoPath: string): Promise<number | null> {
  if (!fs.existsSync(videoPath)) return null;
  const hashOf = (filePath: string): string =>
    crypto.createHash("md5").update(fs.readFileSync(filePath)).digest("hex");

  const newHash = hashOf(videoPath);
  const others = await prisma.clip.findMany({
    where: { projectId, id: { not: clipId }, videoPath: { not: null } },
    select: { index: true, videoPath: true },
    orderBy: { index: "asc" },
  });

  for (const other of others) {
    if (!other.videoPath || !fs.existsSync(other.videoPath)) continue;
    try {
      if (hashOf(other.videoPath) === newHash) return other.index;
    } catch {
      // okunamayan dosya kiyaslamayi durdurmasin
    }
  }
  return null;
}

/**
 * Sarki klibi: soyleyen once, sonra sarkida gecen tum kadro referans gorselleri.
 * Flow @karakter aciksa PNG yuklenmez — gorsel yuklemek video yerine karakter uretir.
 */
async function resolveReferenceImages(
  project: Project,
  clip: Clip,
  clipSinger: { id: string; name: string; referenceImagePath: string | null } | null,
  cast: { id: string; name: string; referenceImagePath: string | null }[]
): Promise<string[]> {
  // Bu sahnede GERCEKTEN gerekli kadro: soz/sahne metninde adi gecenler
  // (yoksa kucuk kadro/grup sinyaliyle hepsi, aksi halde bos). Boylece tek
  // kisilik dizelerde alakasiz arkadaslarin gorseli yuklenmez / @etiketlenmez.
  const others = cast.filter((c) => c.id !== clipSinger?.id);
  const sceneCast = resolveClipCastMembers(`${clip.dialogue} ${clip.sceneDescription} ${clip.imagePrompt}`, others);

  if (project.useFlowCharacter && isKidsSong(project.templateType)) {
    const names = [clipSinger?.name.trim(), ...sceneCast.map((c) => c.name.trim())].filter(Boolean);
    await recordEvent({
      projectId: project.id,
      clipId: clip.id,
      step: "flow",
      message: `Klip ${clip.index}: Flow @karakter (${names.join(", ") || "kadro"}) — gorsel yuklenmeyecek, video modu korunacak`,
    });
    return [];
  }
  const paths = pickSongCastReferencePaths(sceneCast, clipSinger, project.useReference, project.useFlowCharacter);
  if (paths.length > 0) {
    const names = [clipSinger?.name.trim(), ...sceneCast.map((c) => c.name.trim())].filter(Boolean);
    await recordEvent({
      projectId: project.id,
      clipId: clip.id,
      step: "flow",
      message: `Klip ${clip.index}: sarki kadro referanslari (${names.join(", ")} — ${paths.length} gorsel)`,
    });
  }
  return uniqueExistingImagePaths(paths);
}

/** Basarisiz/elle-mudahale klibini kuyruga geri alir. */
export async function retryClip(clipId: string): Promise<void> {
  const clip = await prisma.clip.findUniqueOrThrow({ where: { id: clipId } });

  // Tamamlanan klibi yeniden yap: eski video/kareyi sil ki motor yeniden uretsin
  if (clip.status === "completed") {
    for (const filePath of [clip.videoPath, clip.lastFramePath]) {
      if (filePath && fs.existsSync(filePath)) {
        try {
          fs.unlinkSync(filePath);
        } catch {
          // silinemedi; yine de yollari temizleyip yeniden uretimi dene
        }
      }
    }
  }

  await prisma.clip.update({
    where: { id: clipId },
    data: {
      status: "pending",
      attemptCount: 0,
      errorMessage: null,
      videoPath: null,
      lastFramePath: null,
      actualDurationSeconds: null,
    },
  });
  publishEvent(clip.projectId, {
    type: "clip",
    payload: {
      id: clipId,
      index: clip.index,
      status: "pending",
      attemptCount: 0,
      errorMessage: null,
      videoPath: null,
    },
  });
  await recordEvent({
    projectId: clip.projectId,
    clipId,
    step: "clip",
    message:
      clip.status === "completed"
        ? `Klip ${clip.index} yeniden yapilacak (eski video temizlendi)`
        : `Klip ${clip.index} yeniden kuyruga alindi`,
  });
}

/** Tum basarisiz klipleri kuyruga geri alir. */
export async function retryAllFailedClips(projectId: string): Promise<number> {
  const failed = await prisma.clip.findMany({
    where: { projectId, languageVariant: "primary", status: { in: ["failed", "needs_manual_action", "retrying", "paused"] } },
  });
  for (const clip of failed) {
    await prisma.clip.update({ where: { id: clip.id }, data: { status: "pending", attemptCount: 0, errorMessage: null } });
    publishEvent(projectId, { type: "clip", payload: { id: clip.id, index: clip.index, status: "pending", attemptCount: 0 } });
  }
  await recordEvent({ projectId, step: "clip", message: `${failed.length} basarisiz klip yeniden kuyruga alindi` });
  return failed.length;
}

/**
 * Projeyi bastan baslatmak icin sifirlar: tum kliplerin durumunu "draft"a
 * dondurur, deneme sayacini ve hata mesajlarini temizler. Istege bagli olarak
 * uretilmis video/kare dosyalarini da diskten siler.
 */
export async function resetAutomation(projectId: string, options?: { deleteVideos?: boolean }): Promise<{ resetCount: number }> {
  // Bu proje icin su an calisan bir is varsa once durdur (diger projeler etkilenmez).
  const control = controlFor(projectId);
  if (control.runningJobId) {
    const runningJobId = control.runningJobId;
    control.stopRequested = true;
    control.pauseRequested = false;
    for (let i = 0; i < 40 && control.runningJobId === runningJobId; i++) {
      await new Promise<void>((resolve) => setTimeout(resolve, 250));
    }
  }

  await prisma.automationJob.updateMany({
    where: { projectId, state: { in: ["pending", "running", "paused", "needs_manual_action"] } },
    data: { state: "stopped", finishedAt: new Date() },
  });

  const clips = await prisma.clip.findMany({ where: { projectId, languageVariant: "primary" } });
  if (options?.deleteVideos) {
    for (const clip of clips) {
      for (const filePath of [clip.videoPath, clip.lastFramePath]) {
        if (filePath && fs.existsSync(filePath)) {
          try {
            fs.unlinkSync(filePath);
          } catch {
            // dosya silinemedi, sifirlamayi durdurmaya deger degil
          }
        }
      }
    }
  }

  const result = await prisma.clip.updateMany({
    where: { projectId, languageVariant: "primary" },
    data: {
      status: "draft",
      attemptCount: 0,
      videoPath: null,
      lastFramePath: null,
      errorMessage: null,
      actualDurationSeconds: null,
    },
  });

  for (const clip of clips) {
    publishEvent(projectId, {
      type: "clip",
      payload: { id: clip.id, index: clip.index, status: "draft", attemptCount: 0, errorMessage: null, videoPath: null },
    });
  }

  await prisma.project.update({ where: { id: projectId }, data: { status: "prompts_ready" } });
  publishEvent(projectId, { type: "project", payload: { id: projectId, status: "prompts_ready" } });

  await recordEvent({
    projectId,
    step: "job",
    message: `Otomasyon sifirlandi: ${result.count} klip 'taslak' durumuna alindi${options?.deleteVideos ? "; video dosyalari silindi" : ""}. Baslatildiginda 1. klipten basiyacak.`,
  });

  return { resetCount: result.count };
}

/** Uygulama yeniden basladiginda yarim kalan isleri isaretler (instrumentation'dan cagrilir). */
export async function recoverInterruptedJobs(): Promise<void> {
  const interrupted = await prisma.automationJob.findMany({ where: { state: { in: ["running", "pending"] } } });
  for (const job of interrupted) {
    try {
      const updated = await prisma.automationJob.updateMany({
        where: { id: job.id },
        data: {
          state: "paused",
          pausedReason: "Uygulama yeniden basladi; tamamlanmis kliplerden devam etmek icin otomasyonu tekrar baslatin",
        },
      });
      if (updated.count === 0) continue;
      const projectExists = await prisma.project.findUnique({ where: { id: job.projectId }, select: { id: true } });
      if (!projectExists) continue;
      await recordEvent({
        projectId: job.projectId,
        jobId: job.id,
        step: "job",
        level: "warning",
        message: "Uygulama yeniden basladi: is duraklatildi. Otomasyonu baslattiginizda tamamlanmis klipler atlanacak.",
      });
    } catch (err) {
      console.warn(`[otomasyon] Kesinti kurtarma atlandi (${job.id}):`, err instanceof Error ? err.message : err);
    }
  }
  // Yarim kalan klip durumlarini toparla. Kesinti bizim yeniden baslatmamizdan
  // kaynaklandigi icin deneme sayaci da sifirlanir; aksi halde klip haksiz yere
  // "maksimum deneme asildi"ya duser.
  await prisma.clip.updateMany({
    where: { status: { notIn: ["draft", "pending", "completed", "failed", "needs_manual_action"] } },
    data: { status: "pending", attemptCount: 0 },
  });
}

/** Yari otomatik modda tek klip calistirir (kuyruk olmadan). */
export async function ensureBrowserForManualFlow(): Promise<void> {
  await openFlowBrowser();
}
