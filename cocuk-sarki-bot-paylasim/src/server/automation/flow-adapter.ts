import fs from "node:fs";
import path from "node:path";
import AdmZip from "adm-zip";
import type { Locator, Page } from "playwright";
import type { Project } from "@prisma/client";
import {
  buildLocator,
  getCandidatesFor,
  locatorFor,
  resolveSelector,
  saveCandidates,
  type SelectorCandidate,
} from "@/server/automation/selectors";
import { acquireProjectPage, checkSessionStatus, isSessionCheckOverridden, openFlowBrowser } from "@/server/automation/browser";
import { assertAutomationContinuing, interruptibleSleep } from "@/server/automation/abort";
import { getSettings } from "@/server/services/settings";
import { recordEvent } from "@/server/lib/logger";
import { nextAvailablePath, safeProjectPath } from "@/server/lib/paths";
import { isKidsContent } from "@/lib/templates";
import { ensureAnimatedCastLock, sanitizeKidsPromptForFlow } from "@/lib/flow-prompt-safety";
import {
  compactPromptForFlow,
  ensureNoOnscreenTextLock,
  FLOW_PROMPT_MAX,
} from "@/lib/flow-prompt-compact";
import {
  chipNeedsRepair,
  flowClipSeconds,
  flowDurationTabPattern,
  generationChipMismatchMessage,
  imageModelNamesMatch,
  isImageFlowModel,
  isImageOutputModeLabel,
  isStuckFlowResolvingText,
  isTrustedVideoOutputLabel,
  parseFlowSettingsChip,
} from "@/lib/flow-generation-settings";

/**
 * Flow sayfa adaptoru: prompt yazma, uretim baslatma, tamamlanma bekleme, indirme.
 * Tum secic erisimi selectors.ts uzerinden yapilir; bot tespiti asma,
 * sahte insan davranisi veya guvenlik kontrolu atlatma YOKTUR.
 */

export class ManualActionNeededError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ManualActionNeededError";
  }
}

export class FlowWindowClosedError extends Error {
  constructor() {
    super("Flow penceresi kapandi. Otomasyon tarayiciyi yeniden acacak.");
    this.name = "FlowWindowClosedError";
  }
}

export function isFlowWindowClosedError(err: unknown): boolean {
  if (err instanceof FlowWindowClosedError) return true;
  const message = err instanceof Error ? err.message : String(err);
  return /Flow penceresi kapandi|Target closed|has been closed|browser has been closed|Target page, context or browser has been closed|Protocol error.*closed/i.test(
    message
  );
}

export function assertFlowPageAlive(page: Page): void {
  if (page.isClosed()) throw new FlowWindowClosedError();
}

/**
 * Oturum boyunca kutuphaneye yuklenen referans dosya adlari.
 * 20+ klipten sonra ayni sheet'i tekrar upload etmek kutuphaneyi sisirir;
 * isim eslesmesi bozulur ve ayni karakter cifte eklenir.
 */
const libraryKnownByProject = new Map<string, Set<string>>();

function markLibraryKnown(projectId: string, imagePath: string): void {
  const key = path.basename(imagePath).toLowerCase();
  const set = libraryKnownByProject.get(projectId) ?? new Set<string>();
  set.add(key);
  libraryKnownByProject.set(projectId, set);
}

function isLibraryKnown(projectId: string, imagePath: string): boolean {
  return libraryKnownByProject.get(projectId)?.has(path.basename(imagePath).toLowerCase()) ?? false;
}

export function uniqueExistingImagePaths(imagePaths: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of imagePaths) {
    const trimmed = raw?.trim();
    if (!trimmed || !fs.existsSync(trimmed)) continue;
    const resolved = path.resolve(trimmed);
    const norm = resolved.toLowerCase();
    const base = path.basename(resolved).toLowerCase();
    if (seen.has(norm) || seen.has(`base:${base}`)) continue;
    seen.add(norm);
    seen.add(`base:${base}`);
    out.push(resolved);
  }
  return out;
}

const SELECTOR_LABELS: Record<string, string> = {
  promptInput: "Prompt kutusu",
  generateButton: "Generate (Uret) dugmesi",
  assetMenuButton: "Video kartinin menu dugmesi",
  downloadMenuItem: "Indir menu ogesi",
};

export class SelectorMissingError extends Error {
  constructor(key: string) {
    const label = SELECTOR_LABELS[key] ?? key;
    super(
      `"${label}" Flow sayfasinda bulunamadi. Kalibrasyon ekranindan bu ogeyi yeniden tanitin (Flow arayuzu degismis olabilir). Teknik anahtar: ${key}`
    );
    this.name = "SelectorMissingError";
  }
}

/** Aday locator'lar arasindan sayfada gorunur olan ilkini dondurur. */
async function firstUsable(candidates: Array<Locator | null>, timeoutMs = 1_500): Promise<Locator | null> {
  for (const candidate of candidates) {
    if (!candidate) continue;
    try {
      if ((await candidate.count()) === 0) continue;
      if (await candidate.isVisible({ timeout: timeoutMs })) return candidate;
    } catch {
      // bu aday kullanilamiyor, sonrakine gec
    }
  }
  return null;
}

/**
 * Prompt kutusunu arar (bulamazsa null doner, hata atmaz).
 * Once merkezi aday zinciri (kalibrasyon + yerlesik yedekler), sonra
 * ic cerceveler (iframe) taranir.
 */
/**
 * GORUNTU DUZENLEME kutusunun ipucu metni. Yuklenen/uretilen bir gorsel tam
 * ekran acildiginda Flow, VIDEO prompt kutusu yerine "Neyi degistirmek
 * istiyorsunuz?" yazan bir Nano Banana duzenleme kutusu gosterir. Bu kutu da
 * contenteditable oldugu icin genel adaylara yakalanir; prompt buraya
 * yazilirsa video yerine GORUNTU uretilir ve klip zaman asimina ugrar.
 */
const EDIT_BOX_HINT = /neyi de[gğ]i[sş]tirmek istiyorsun|what (do you want|would you like) to change/i;

/**
 * Adayin GERCEK video prompt kutusu olup olmadigini dogrular.
 * Flow sayfasinda birden fazla contenteditable bulunur (medya penceresi arama
 * alani, gizli z-index:-1 kutular, goruntu duzenleme). Yanlisina yazmak
 * "prompt yazilmadi / Generate basilmadi" hatasina yol acar.
 */
async function isVideoPromptBox(candidate: Locator): Promise<boolean> {
  try {
    // Gorunur olmali. Bos Flow promptu ~20px yukseklik + genis cubuk;
    // eski esik (24px) gercek kutuyu eleyip "editor acik degil" hatasi uretiyordu.
    if (!(await candidate.isVisible({ timeout: 400 }).catch(() => false))) return false;
    const box = await candidate.boundingBox().catch(() => null);
    if (!box || box.width < 120 || box.height < 14) return false;

    const meta = await candidate
      .evaluate((el) => {
        const style = window.getComputedStyle(el);
        const z = style.zIndex;
        const zNum = Number(z);
        return {
          zIndex: z,
          zIsNegative: Number.isFinite(zNum) && zNum < 0,
          pointerEvents: style.pointerEvents,
          ariaHidden: el.getAttribute("aria-hidden"),
          text: (el.textContent || "").replace(/\uFEFF/g, "").trim().slice(0, 120),
          placeholder: el.getAttribute("placeholder") || el.getAttribute("data-placeholder") || "",
          inDialog: !!el.closest("[role='dialog'], [aria-modal='true']"),
        };
      })
      .catch(() => null);
    if (!meta) return false;
    if (meta.inDialog) return false;
    if (meta.ariaHidden === "true") return false;
    if (meta.pointerEvents === "none") return false;
    // Yalnizca HESAPLANAN negatif z-index elenir. Flow gercek prompta
    // HTML zindex="-1" ozelligi koyuyor ama computed "auto" — onu ELEME.
    if (meta.zIsNegative) return false;
    if (EDIT_BOX_HINT.test(meta.text) || EDIT_BOX_HINT.test(meta.placeholder)) return false;
    return true;
  } catch {
    return false;
  }
}

/** Generate dugmesini iceren alt kompozisyon cubugu (prompt + gonder). */
function composerRoot(page: Page): Locator {
  return page
    .locator("div, form, section, footer")
    .filter({ has: page.locator("button").filter({ hasText: /arrow_forward/i }) })
    .filter({ has: page.locator("[contenteditable='true'], textarea") })
    .last();
}

/**
 * Video prompt kutusunu bulur. Oncelik:
 *  1) Generate (arrow_forward) dugmesinin yakinindaki contenteditable
 *  2) "Ne olusturmak istiyorsunuz?" ipucu tasiyan kutu
 *  3) Kalibre edilmis / genel adaylar (yalnizca isVideoPromptBox gecenler)
 */
async function findPromptInput(page: Page, _projectId?: string): Promise<Locator | null> {
  // Karakter editorunun prompt cubugu video kutusuna BENZER (arrow_forward +
  // contenteditable). Buraya yazmak klip yerine yeni karakter gorseli uretir.
  if (isCharactersPageUrl(page.url())) return null;

  // 1) En guvenilir: gonderme dugmesinin bulundugu kompozisyon cubugu
  const nearGenerate = composerRoot(page).locator("[contenteditable='true'], textarea").first();
  if (await isVideoPromptBox(nearGenerate)) return nearGenerate;

  // 2) Video promptunun yer tutucu metni (bos kutuda icerik olarak gelir)
  const byPlaceholder = page
    .locator("[contenteditable='true'], textarea")
    .filter({ hasText: /ne olu[sş]turmak istiyorsun|what do you want to create|generate a video/i })
    .first();
  if (await isVideoPromptBox(byPlaceholder)) return byPlaceholder;

  // 3) Kalibre edilmis secici — ama yalnizca gercekten kullanilabilirse
  //    (eski kalibrasyon z-index:-1 gizli kutuya takilabiliyordu)
  const resolved = await resolveSelector(page, "promptInput", { selfHeal: false, timeoutMs: 600 });
  if (resolved && (await isVideoPromptBox(resolved.locator))) return resolved.locator;

  // 4) Sayfadaki TUM contenteditable/textarea adaylarini tara; ilk uygun olan
  const all = page.locator("[contenteditable='true'], textarea");
  const count = await all.count().catch(() => 0);
  for (let i = 0; i < Math.min(count, 16); i++) {
    const candidate = all.nth(i);
    if (await isVideoPromptBox(candidate)) return candidate;
  }

  // 5) iframe yedegi
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    for (const pattern of ["textarea", "[contenteditable='true']"]) {
      const candidate = await firstUsable([frame.locator(pattern).first()], 600);
      if (candidate && (await isVideoPromptBox(candidate))) return candidate;
    }
  }
  return null;
}

/** Ayarlar paneli / menu / dialog aciksa Escape ile kapat (prompt yazmayi engeller). */
async function dismissOverlaysBlockingPrompt(page: Page, project: Project, context: string): Promise<void> {
  const settingsOpen = await page
    .getByRole("tab", { name: /^x[1-4]$/i })
    .first()
    .isVisible({ timeout: 300 })
    .catch(() => false);
  const dialogOpen = await page
    .locator("[role='dialog'], [aria-modal='true']")
    .first()
    .isVisible({ timeout: 300 })
    .catch(() => false);
  const menuOpen = await page
    .locator("[role='menu']")
    .first()
    .isVisible({ timeout: 300 })
    .catch(() => false);

  if (!settingsOpen && !dialogOpen && !menuOpen) return;

  await page.keyboard.press("Escape").catch(() => {});
  await page.waitForTimeout(500);
  // Hala ayarlar aciksa ozet dugmeye tekrar tiklayarak kapatmayi dene
  if (
    await page
      .getByRole("tab", { name: /^x[1-4]$/i })
      .first()
      .isVisible({ timeout: 300 })
      .catch(() => false)
  ) {
    const toggle = await locatorFor(page, "generationSettingsButton", { timeoutMs: 800 });
    if (toggle) await toggle.click().catch(() => {});
    await page.waitForTimeout(400);
  }
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Prompt yazmadan once acik panel/pencere kapatildi (${context})`,
  });
}

/**
 * Flow'un PROJE EDITORU ekraninda oldugundan emin olur.
 * Ana sayfa/proje listesi ekraninda prompt kutusu bulunmaz; bu durumda
 * projeye girmeyi dener, basaramazsa elle mudahale ister (bosuna yeniden
 * denemelerle vakit harcamaz).
 */
export async function ensureEditorReady(page: Page, project: Project): Promise<Locator> {
  // Karakterler sayfasinda kalinirsa klip promptu karakter editorune yazilir.
  if (isCharactersPageUrl(page.url())) {
    await returnToProjectEditor(page, project).catch(() => {});
  }
  // Yuklenen/uretilen gorselin actigi tam ekran duzenleme gorunumu varsa kapat
  await escapeAssetDetailView(page, project);

  let existing = await findPromptInput(page, project.id);
  if (existing) return existing;

  // Flow agir bir SPA: sayfa "yuklendi" gorunse de govde birkac saniye sonra
  // gelir. Pes etmeden once sabirla bekle (ozellikle tarayici yeni acildiginda).
  await page.waitForLoadState("networkidle", { timeout: 20_000 }).catch(() => {});
  const patienceDeadline = Date.now() + 25_000;
  while (Date.now() < patienceDeadline) {
    await escapeAssetDetailView(page, project);
    existing = await findPromptInput(page, project.id);
    if (existing) return existing;
    await page.waitForTimeout(2_000);
  }

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Prompt kutusu yok — Flow editoru acik degil gibi gorunuyor. Projeye girilmeye calisiliyor. Adres: ${page.url()}`,
  });

  const attempts: Array<{ label: string; run: () => Promise<boolean> }> = [];

  // En guvenilir kurtarma: projeye ozel adrese dogrudan git
  if (project.flowProjectUrl?.trim()) {
    const projectUrl = project.flowProjectUrl.trim();
    attempts.push({
      label: `proje adresine gidildi (${projectUrl})`,
      run: async () => {
        await page.goto(projectUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
        return true;
      },
    });
  }

  if (project.flowProjectName.trim()) {
    attempts.push({
      label: `"${project.flowProjectName}" projesine tiklandi`,
      run: async () => {
        const card = page.getByText(project.flowProjectName, { exact: false }).first();
        if (!(await card.isVisible({ timeout: 3_000 }).catch(() => false))) return false;
        await card.click();
        return true;
      },
    });
  }

  attempts.push({
    label: "Yeni proje dugmesine tiklandi",
    run: async () => {
      const button = await locatorFor(page, "newProjectButton");
      if (!button) return false;
      await button.click();
      return true;
    },
  });

  for (const attempt of attempts) {
    let clicked = false;
    try {
      clicked = await attempt.run();
    } catch {
      clicked = false;
    }
    if (!clicked) continue;

    await page.waitForLoadState("domcontentloaded").catch(() => {});
    await page.waitForTimeout(3_000);
    const input = await findPromptInput(page, project.id);
    if (input) {
      await recordEvent({ projectId: project.id, step: "flow", message: `Flow editoru acildi (${attempt.label})` });
      return input;
    }
  }

  const snapshot = await captureDebugSnapshot(page, project.slug, "editor-not-open");
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "error",
    message: "Flow editoru acilamadi; elle mudahale gerekiyor",
    screenshotPath: snapshot.screenshotPath,
    pageUrl: page.url(),
  });
  throw new ManualActionNeededError(
    `Flow editoru acik degil (su anki adres: ${page.url()}). Chrome penceresinde projenizi acin — prompt kutusunun gorundugu ekranda kalin — sonra "Devam Ettir"e basin. Kalici cozum: Proje Ayarlari > "Flow proje linki" alanina bu projenin Flow adresini yazin (or. .../tools/flow/project/XXXX); paralel calisma da bu linke dayanir.`
  );
}

/** Generate dugmesini bulur; kalibre edilmemisse yaygin adlarla arar. */
/**
 * Generate dugmesi. Kalibre secici oncelikli; bulunamazsa metin ve aria-label
 * ile aranir. Flow yeni arayuzde bu dugmeyi ikon-only (yazisiz, yuvarlak)
 * gosterebiliyor — o durumda yalniz erisilebilirlik adi kalir.
 */
async function resolveGenerateButton(page: Page): Promise<Locator | null> {
  const calibrated = await locatorFor(page, "generateButton");
  if (calibrated) return calibrated;

  const label = /^\s*(olu[sş]tur|[uü]ret|generate|create|g[oö]nder|send|submit)\s*$/i;
  const candidates: Locator[] = [
    page.getByText(/^\s*arrow_forward/).last(),
    page.locator("button").filter({ hasText: /^\s*arrow_forward/ }).last(),
    page.getByRole("button", { name: label }).last(),
    page.locator("button[aria-label]").filter({ hasText: /$^/ }).and(page.getByLabel(label)).last(),
    page.getByLabel(label).last(),
    page.locator('form button[type="submit"]').last(),
  ];
  for (const candidate of candidates) {
    if (!(await candidate.isVisible({ timeout: 700 }).catch(() => false))) continue;
    if (await candidate.isDisabled({ timeout: 500 }).catch(() => false)) continue;
    return candidate;
  }
  return null;
}

/** Indirme menu ogesini bulur. */
async function resolveDownloadMenuItem(page: Page): Promise<Locator | null> {
  return locatorFor(page, "downloadMenuItem");
}

/** Uretilen varligin menu dugmesini bulur. */
async function resolveAssetMenuButton(page: Page): Promise<Locator | null> {
  return locatorFor(page, "assetMenuButton");
}

/** Hata ayiklama: ekran goruntusu + HTML anlik goruntusu kaydeder. */
export async function captureDebugSnapshot(page: Page, projectSlug: string, label: string): Promise<{ screenshotPath: string; htmlPath: string }> {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const screenshotPath = nextAvailablePath(safeProjectPath(projectSlug, "screenshots", `${stamp}-${label}.png`));
  const htmlPath = nextAvailablePath(safeProjectPath(projectSlug, "screenshots", `${stamp}-${label}.html`));
  fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
  try {
    await page.screenshot({ path: screenshotPath, fullPage: false, timeout: 15_000 });
  } catch {
    // ekran goruntusu alinamasa da devam et
  }
  try {
    const html = await page.content();
    fs.writeFileSync(htmlPath, html, "utf8");
  } catch {
    // html alinamasa da devam et
  }
  return { screenshotPath, htmlPath };
}

/**
 * Flow'un acik ve oturumun hazir oldugunu garanti eder.
 *
 * projectId verilirse o projeye AYRILMIS sekme dondurulur (paralel calisma).
 * Verilmezse paylasilan ana sekme kullanilir — kalibrasyon, tekil karakter
 * uretimi gibi tek seferlik akislar icin.
 */
export async function ensureFlowReady(projectId?: string, flowProjectUrl?: string): Promise<Page> {
  const page = projectId ? await acquireProjectPage(projectId, flowProjectUrl) : await openFlowBrowser();
  const session = await checkSessionStatus(page);
  if (session.status === "needs_login") {
    throw new ManualActionNeededError("Google oturumu acik degil. Chrome penceresinde hesabiniza elle giris yapin, sonra devam edin.");
  }
  if (session.status === "needs_verification") {
    if (isSessionCheckOverridden()) {
      await recordEvent({
        projectId,
        step: "flow",
        level: "warning",
        message: `Dogrulama tespiti kullanici istegiyle atlandi (${session.detail.slice(0, 80)})`,
      });
    } else {
      throw new ManualActionNeededError(
        `${session.detail} Ekranda boyle bir dogrulama YOKSA bu bir yanlis alarmdir: panelde "Kontrolu atla" dugmesiyle devam edebilirsiniz.`
      );
    }
  }
  if (session.status === "closed") {
    throw new Error("Tarayici beklenmedik sekilde kapandi");
  }
  return page;
}

/**
 * Dogru Flow projesini acar.
 * 1) Projeye ozel link varsa DOGRUDAN oraya gidilir — en guvenilir yol ve
 *    paralel calismada her sekmenin kendi projesinde kalmasini garanti eder.
 * 2) Link yoksa proje ADIYLA listede aranir (eski davranis).
 */
export async function openFlowProject(page: Page, project: Project): Promise<void> {
  const projectUrl = project.flowProjectUrl?.trim();
  if (projectUrl) {
    const current = page.url();
    if (!current.startsWith(projectUrl)) {
      await page.goto(projectUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
      await recordEvent({ projectId: project.id, step: "flow", message: `Flow projesi adresinden acildi: ${projectUrl}` });
    }
    return;
  }

  if (!project.reuseFlowProject || !project.flowProjectName) return;

  // Proje adina gore listede ara
  const projectItem = page.getByText(project.flowProjectName, { exact: false }).first();
  if (await projectItem.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await projectItem.click();
    await page.waitForLoadState("domcontentloaded");
    await recordEvent({ projectId: project.id, step: "flow", message: `Flow projesi acildi: ${project.flowProjectName}` });
    return;
  }

  // Yeni proje dugmesi kalibre edildiyse yeni proje ac
  const newProjectButton = await locatorFor(page, "newProjectButton");
  if (newProjectButton && (await newProjectButton.isVisible({ timeout: 2_000 }).catch(() => false))) {
    await newProjectButton.click();
    await page.waitForLoadState("domcontentloaded");
    await recordEvent({ projectId: project.id, step: "flow", message: "Yeni Flow projesi olusturuldu" });
    return;
  }

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: "Flow projesi listede bulunamadi; mevcut acik sayfa kullanilacak",
  });
}

/** Menu tabanli secim: menuyu ac, metinle secenegi tikla. Secici yoksa atlanir (uyari). */
async function configureMenuOption(page: Page, project: Project, menuKey: string, optionText: string, label: string): Promise<void> {
  const menu = await locatorFor(page, menuKey);
  if (!menu) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `${label} menusu kalibre edilmemis; Flow'daki mevcut secim kullanilacak`,
    });
    return;
  }
  if (!(await menu.isVisible({ timeout: 3_000 }).catch(() => false))) {
    await recordEvent({ projectId: project.id, step: "flow", level: "warning", message: `${label} menusu gorunmuyor; atlandi` });
    return;
  }
  await menu.click();
  await page.waitForTimeout(400);
  const option = page.getByText(new RegExp(optionText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i")).first();
  if (await option.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await option.click();
    await recordEvent({ projectId: project.id, step: "flow", message: `${label} secildi: ${optionText}` });
  } else {
    await page.keyboard.press("Escape").catch(() => {});
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `${label} icin "${optionText}" secenegi bulunamadi; mevcut secim korundu`,
    });
  }
  await page.waitForTimeout(300);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Model adlarini gevsek karsilastirir. Flow arayuzu model adini "Veo 3.1 -
 * Fast" gibi TIRE ile yazarken proje ayarinda "Veo 3.1 Fast" (tiresiz)
 * tutulur; ayrica menu satirlarinin onunde ikon ligature metni ("volume_up")
 * dogrudan metne yapisik gelir ("volume_upVeo 3.1 - Fast"). Bu fonksiyon
 * bu farkliliklari yok sayarak karsilastirma yapar.
 */
function normalizeModelName(value: string): string {
  return value
    .replace(/volume_up|arrow_drop_down|arrow_drop_up/gi, " ")
    .toLowerCase()
    .replace(/[-_.]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function modelNamesMatch(uiText: string, target: string): boolean {
  const a = normalizeModelName(uiText);
  const b = normalizeModelName(target);
  if (!a || !b) return false;
  return a === b || a.includes(b) || b.includes(a);
}

/**
 * Model/en-boy orani/cikti sayisi kontrolleri, prompt cubugunun yanindaki
 * ozet dugmeye ("Video · 16:9 · x1" gibi) tiklanip acilan bir panelde
 * gorunur; panel kapaliyken sayfada hic yoktur. Panel zaten aciksa
 * (x1..x4 sekmelerinden biri gorunuyorsa) dokunulmaz.
 */
/** Ayarlar paneli acik mi? Flow bazen x1 sekmeleri yerine sure/oran sekmeleri gosterir. */
async function isGenerationSettingsPanelOpen(page: Page): Promise<boolean> {
  const probes = [
    page.getByRole("tab", { name: /^x[1-4]$/i }).first(),
    page.getByRole("tab", { name: /^(4|6|8|10)\s*(s|sn)$/i }).first(),
    page.getByRole("tab", { name: /16:9|9:16/ }).first(),
    page.getByRole("tab", { name: /videocam\s*video\s*$/i }).first(),
  ];
  for (const loc of probes) {
    if (await loc.isVisible({ timeout: 350 }).catch(() => false)) return true;
  }
  return false;
}

async function findGenerationSettingsChip(page: Page): Promise<Locator | null> {
  const fromConfig = await locatorFor(page, "generationSettingsButton", { timeoutMs: 1_500 });
  if (fromConfig && (await fromConfig.isVisible({ timeout: 400 }).catch(() => false))) return fromConfig;

  const fallbacks = [
    page.locator("button[aria-haspopup='menu']").filter({ hasText: /crop_(16_9|9_16)/ }).first(),
    page.locator("button").filter({ hasText: /720p.*crop_|crop_.*x[1-4]/i }).first(),
    page.getByRole("button", { name: /crop_(16_9|9_16)|720p/i }).first(),
  ];
  for (const loc of fallbacks) {
    if (await loc.isVisible({ timeout: 500 }).catch(() => false)) return loc;
  }
  return null;
}

async function openGenerationSettingsPanel(page: Page, project: Project): Promise<boolean> {
  if (await isGenerationSettingsPanelOpen(page)) return true;

  const toggle = await findGenerationSettingsChip(page);
  if (!toggle) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Uretim ayarlari paneli (model/oran/adet) bulunamadi; Flow'daki mevcut ayarlar kullanilacak",
    });
    return false;
  }
  await toggle.click().catch(() => {});
  await page.waitForTimeout(500);
  const nowOpen = await isGenerationSettingsPanelOpen(page);
  if (!nowOpen) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Uretim ayarlari paneli acilamadi; Flow'daki mevcut ayarlar kullanilacak",
    });
  }
  return nowOpen;
}

/** Model secimi: panel icindeki model dugmesini acar, listeden esleseni tiklar. */
async function selectModelInPanel(page: Page, project: Project): Promise<void> {
  const trigger = await locatorFor(page, "modelMenu", { timeoutMs: 2_000 });
  if (!trigger) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Model menusu bulunamadi; Flow'daki mevcut model kullanilacak",
    });
    return;
  }

  const currentText = (await trigger.textContent().catch(() => "")) ?? "";
  if (modelNamesMatch(currentText, project.flowModel)) {
    return; // zaten dogru model secili
  }

  await trigger.click().catch(() => {});
  await page.waitForTimeout(400);

  const items = page.getByRole("menuitem");
  const count = await items.count().catch(() => 0);
  let matched: Locator | null = null;
  const wantImage = isImageFlowModel(project.flowModel);
  for (let i = 0; i < count; i++) {
    const item = items.nth(i);
    const text = (await item.textContent().catch(() => "")) ?? "";
    if (!wantImage && isImageFlowModel(text)) continue;
    if (modelNamesMatch(text, project.flowModel)) {
      matched = item;
      break;
    }
  }

  if (matched) {
    await matched.click().catch(() => {});
    await recordEvent({ projectId: project.id, step: "flow", message: `Model secildi: ${project.flowModel}` });
  } else {
    await page.keyboard.press("Escape").catch(() => {});
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Model listesinde "${project.flowModel}" bulunamadi; mevcut secim korundu`,
    });
  }
  await page.waitForTimeout(300);
}

/**
 * Sekme tabanli tek tikla secim (en-boy orani / cikti sayisi). Bu kontroller
 * role="tab" ile isaretli oldugu icin metin aramasi ikon ligature'lariyla
 * (or. "crop_16_9") karismaz; kalibrasyon gerektirmez.
 */
async function selectSettingsTab(page: Page, project: Project, optionText: string, label: string): Promise<void> {
  const tab = page.getByRole("tab", { name: new RegExp(escapeRegExp(optionText), "i") }).first();
  if (await tab.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await tab.click().catch(() => {});
    await recordEvent({ projectId: project.id, step: "flow", message: `${label} secildi: ${optionText}` });
  } else {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `${label} icin "${optionText}" sekmesi bulunamadi; mevcut secim korundu`,
    });
  }
  await page.waitForTimeout(200);
}

function wantedClipSeconds(project: Project): number {
  return flowClipSeconds(project.flowModel, project.clipSeconds);
}

/**
 * Sure, en-boy gibi role="tab" (4s / 6s / 8s / 10s). Kalibrasyon gerekmez.
 * Veo Fast/Lite 10s destemez; 8s'ye cekilir. 9:16 short'ta Flow sikca 10s
 * birakir — o yuzden oran secildikten SONRA cagrilmali.
 */
async function selectDurationTab(page: Page, project: Project): Promise<boolean> {
  const seconds = wantedClipSeconds(project);
  const nameRe = flowDurationTabPattern(seconds);
  const candidates = [
    page.getByRole("tab", { name: nameRe }).first(),
    page.getByRole("radio", { name: nameRe }).first(),
    page.getByRole("button", { name: nameRe }).first(),
    page.getByText(nameRe).first(),
  ];

  for (const loc of candidates) {
    if (!(await loc.isVisible({ timeout: 1_200 }).catch(() => false))) continue;
    const selected =
      (await loc.getAttribute("aria-selected").catch(() => null)) === "true" ||
      (await loc.getAttribute("aria-checked").catch(() => null)) === "true";
    if (!selected) await loc.click().catch(() => {});
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: selected ? `Sure zaten ${seconds}s` : `Sure secildi: ${seconds}s`,
    });
    await page.waitForTimeout(200);
    return true;
  }

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Sure sekmesi (${seconds}s) bulunamadi; Flow'daki mevcut sure kullanilacak`,
  });
  return false;
}

async function applyAspectOutputsAndDuration(page: Page, project: Project): Promise<void> {
  await selectSettingsTab(page, project, project.aspectRatio, "En-boy orani");
  await selectSettingsTab(page, project, `x${project.outputsPerGeneration}`, "Cikti sayisi");
  const tabOk = await selectDurationTab(page, project);
  if (!tabOk) {
    const seconds = wantedClipSeconds(project);
    await configureMenuOption(page, project, "durationMenu", `${seconds}s`, "Sure");
  }
}

/** Ozet cubugu (10s + 9:16 gibi) proje ayariyla uyusmuyorsa paneli acip duzeltir. */
async function repairGenerationChipIfNeeded(page: Page, project: Project): Promise<void> {
  const label = await readOutputModeLabel(page);
  const chip = parseFlowSettingsChip(label);
  const wantSec = wantedClipSeconds(project);
  const repair = chipNeedsRepair(chip, {
    durationSec: wantSec,
    aspect: project.aspectRatio,
    outputs: project.outputsPerGeneration,
  });
  if (!repair.duration && !repair.aspect && !repair.outputs) return;

  const panelOpen = await openGenerationSettingsPanel(page, project);
  if (!panelOpen) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Uretim ozeti uyumsuz (${label.slice(0, 40) || "?"}; hedef ${project.aspectRatio} ${wantSec}s) ama panel acilamadi`,
    });
    return;
  }
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Uretim ozeti duzeltiliyor: "${label.slice(0, 48)}" → ${project.aspectRatio} ${wantSec}s`,
  });
  await applyAspectOutputsAndDuration(page, project);
  await dismissOverlaysBlockingPrompt(page, project, "sure/oran duzeltmesi sonrasi");
}

/** Generate oncesi: 10s short ozeti varsa tiklama. Promptu silmemek icin panel acilmaz. */
async function assertGenerationChipReady(page: Page, project: Project): Promise<void> {
  const label = await readOutputModeLabel(page);
  const chip = parseFlowSettingsChip(label);
  const wantSec = wantedClipSeconds(project);
  const repair = chipNeedsRepair(chip, {
    durationSec: wantSec,
    aspect: project.aspectRatio,
    outputs: project.outputsPerGeneration,
  });
  if (repair.duration || repair.aspect) {
    throw new Error(generationChipMismatchMessage(label, project.aspectRatio, wantSec));
  }
}

/**
 * Prompt cubugundaki GERCEK cikti turu etiketini okur.
 * Ayarlar ozeti ("Videocrop_16_9x1") YANILTICI — o her zaman "Video" diyebilir;
 * once "Metinden/Malzemelerden …" dugmesi aranir.
 */
async function readOutputModeLabel(page: Page): Promise<string> {
  const typeBtn = page
    .getByRole("button", {
      name: /(metinden (videoya|g[oö]r[uü]nt[uü]ye)|text to (video|image)|malzemelerden|ingredients to|frames to video|g[oö]r[uü]nt[uü]den video|nano\s*banana)/i,
    })
    .first();
  if (await typeBtn.isVisible({ timeout: 700 }).catch(() => false)) {
    return ((await typeBtn.textContent().catch(() => "")) ?? "").replace(/\s+/g, " ").trim();
  }

  const byText = page
    .locator("button")
    .filter({
      hasText:
        /metinden (videoya|g[oö]r[uü]nt[uü]ye)|text to (video|image)|malzemelerden (video|g[oö]r[uü]nt[uü])|ingredients to (video|image)|frames to video|nano\s*banana/i,
    })
    .first();
  if (await byText.isVisible({ timeout: 500 }).catch(() => false)) {
    return ((await byText.textContent().catch(() => "")) ?? "").replace(/\s+/g, " ").trim();
  }

  // Son care: ayarlar ozeti — yalnizca "Görüntü/Image" ise gorsel sinyali verir
  const settingsChip = page.locator("button[aria-haspopup='menu']").filter({ hasText: /crop_(16_9|9_16)/ }).first();
  if (await settingsChip.isVisible({ timeout: 400 }).catch(() => false)) {
    return ((await settingsChip.textContent().catch(() => "")) ?? "").replace(/\s+/g, " ").trim();
  }
  return "";
}

/**
 * Ciktinin VIDEO olacagini garanti eder.
 *
 * Referans gorsel eklendikten sonra Flow bazen GORUNTU / Nano Banana moduna
 * kayiyor; Generate o zaman jpeg uretir (mp4 yok). Prompt yazmadan VE Generate
 * basmadan hemen once cagrilmali.
 */
export async function ensureVideoOutputMode(
  page: Page,
  project: Project,
  opts?: { repairSettings?: boolean }
): Promise<void> {
  // Karakterler sayfasindaki prompt cubugu VIDEO uretmez; mod dogrulamasi
  // ancak proje editorunde anlamlidir.
  if (isCharactersPageUrl(page.url())) {
    await ensureProjectComposer(page, project).catch(() => {});
  }
  let label = await readOutputModeLabel(page);
  // "Metinden videoya" dugmesi yoksa ayarlar ozeti ("Video · 720pcrop…")
  // video kabul edilir. Onceki mantik repairSettings acikken ozeti zayif
  // sayip panel acamayinca "gorsel uretilebilir" diye yanlis alarm veriyordu.
  if (isTrustedVideoOutputLabel(label)) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Cikti turu video (${label.slice(0, 48) || "ok"})`,
    });
    if (opts?.repairSettings) await repairGenerationChipIfNeeded(page, project);
    return;
  }

  // 1) Cikti turu menusunden video / malzemelerden video sec
  const switched = await switchOutputType(page, project, "video");
  if (switched) {
    label = await readOutputModeLabel(page);
    if (isTrustedVideoOutputLabel(label)) {
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "warning",
        message: `Cikti turu menuden VIDEO yapildi → ${label.slice(0, 48) || "ok"}`,
      });
      if (opts?.repairSettings) await repairGenerationChipIfNeeded(page, project);
      return;
    }
  }

  // 2) Ayarlar panelindeki Video sekmesi
  if (!(await openGenerationSettingsPanel(page, project))) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Cikti turu dogrulanamadi (etiket: "${label.slice(0, 40) || "bos"}"); video yerine gorsel uretilebilir`,
    });
    return;
  }

  const videoTab = page.getByRole("tab", { name: /videocam\s*video\s*$/i }).first();
  if (!(await videoTab.isVisible({ timeout: 1_500 }).catch(() => false))) {
    await dismissOverlaysBlockingPrompt(page, project, "video modu (sekme yok)");
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Cikti turu dogrulanamadi (mevcut: "${label.slice(0, 40) || "bos"}"); video yerine gorsel uretilebilir`,
    });
    return;
  }

  const videoSelected =
    (await videoTab.getAttribute("aria-checked").catch(() => null)) === "true" ||
    (await videoTab.getAttribute("aria-selected").catch(() => null)) === "true";
  if (!videoSelected) {
    await videoTab.click().catch(() => {});
    await page.waitForTimeout(600);
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Cikti turu GORUNTU modundaydi; VIDEO sekmesine alindi",
    });
  }
  if (opts?.repairSettings) {
    await applyAspectOutputsAndDuration(page, project);
  }
  await dismissOverlaysBlockingPrompt(page, project, "video modu sonrasi");

  label = await readOutputModeLabel(page);
  if (isImageOutputModeLabel(label)) {
    throw new Error(
      `Flow hâlâ GÖRÜNTÜ modunda ("${label.slice(0, 60)}"). Generate video yerine jpeg üretir. Prompt çubuğundaki çıktı türünü elle "Malzemelerden video" / "Metinden videoya" yapıp Devam Ettir'e basın.`
    );
  }
}

/** Model / sure / oran / cikti sayisi / ses yapilandirmasi. */
export async function configureGeneration(page: Page, project: Project): Promise<void> {
  const panelOpen = await openGenerationSettingsPanel(page, project);
  if (panelOpen) {
    await selectModelInPanel(page, project);
    // Sure, orandan SONRA: 9:16'ya gecince Flow sikca 10s'ye doner.
    await applyAspectOutputsAndDuration(page, project);
  } else {
    const seconds = wantedClipSeconds(project);
    await configureMenuOption(page, project, "durationMenu", `${seconds}s`, "Sure");
  }

  const wantAudio = project.templateType === "kids_song" ? false : project.audioEnabled;
  await ensureFlowAudioMode(page, project, wantAudio);

  // Panel acik kalirsa prompt kutusuna tiklanamaz / yanlis contenteditable secilir
  await dismissOverlaysBlockingPrompt(page, project, "uretim ayarlari sonrasi");
  await repairGenerationChipIfNeeded(page, project);
}

/** Sarki kliplerinde Flow sesini kapat — ses yalnizca yuklenen MP3. */
export async function ensureFlowAudioMode(page: Page, project: Project, wantOn: boolean): Promise<void> {
  const flipped = await toggleVisibleAudioSwitch(page, project, wantOn);
  if (flipped) return;
  const opened = await openGenerationSettingsPanel(page, project);
  if (!opened) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Ses anahtari bulunamadi; indirilen klibe yine de master MP3 basilacak",
    });
    return;
  }
  await toggleVisibleAudioSwitch(page, project, wantOn);
}

async function toggleVisibleAudioSwitch(page: Page, project: Project, wantOn: boolean): Promise<boolean> {
  const fromConfig = await locatorFor(page, "audioToggle");
  const named = page.getByRole("switch", { name: /ses|audio|sound|music|m[uü]zik|voice/i });
  const all = page.locator('[role="switch"]');
  const candidates: Locator[] = [];
  if (fromConfig) candidates.push(fromConfig);
  if ((await named.count().catch(() => 0)) > 0) candidates.push(named.first());
  const n = await all.count().catch(() => 0);
  for (let i = 0; i < n; i++) candidates.push(all.nth(i));

  for (const sw of candidates) {
    if (!(await sw.isVisible({ timeout: 800 }).catch(() => false))) continue;
    const label = (
      `${(await sw.getAttribute("aria-label").catch(() => "")) || ""} ` +
      `${(await sw.evaluate((el) => (el.closest("label")?.textContent || el.parentElement?.textContent || "").slice(0, 80)).catch(() => "")) || ""}`
    ).toLowerCase();
    const looksAudio = /ses|audio|sound|music|m[uü]zik|voice/.test(label);
    if (!looksAudio && candidates.length > 2 && sw !== fromConfig && sw !== named.first()) continue;
    const checked = await sw.getAttribute("aria-checked").catch(() => null);
    const isOn = checked === "true";
    if (checked !== null && isOn !== wantOn) {
      await sw.click().catch(() => {});
      await page.waitForTimeout(250);
      await recordEvent({
        projectId: project.id,
        step: "flow",
        message: `Ses ${wantOn ? "acildi" : "kapatildi"} (Flow kendi sarki uretmesin)`,
      });
    } else if (checked !== null) {
      await recordEvent({
        projectId: project.id,
        step: "flow",
        message: `Ses zaten ${wantOn ? "acik" : "kapali"}`,
      });
    }
    return true;
  }
  return false;
}

/**
 * Prompt cubuguna eklenmis referans sayisini (kucuk onizleme sayisi) verir.
 * Gorsel gercekten "isteme eklendiginde" prompt kutusunun ustunde bir
 * onizleme belirir; basarinin tek kesin kaniti budur.
 */
export async function promptAttachmentCount(page: Page): Promise<number> {
  return page
    .evaluate(() => {
      // Once gonderme dugmesinden kompozisyon cubugunu bul (ilk contenteditable
      // gizli z-index:-1 kutu olabiliyor — ona guvenme)
      const send = Array.from(document.querySelectorAll("button")).find((b) =>
        /arrow_forward/i.test(b.textContent || "")
      );
      let node: HTMLElement | null = (send as HTMLElement | undefined)?.parentElement ?? null;
      for (let up = 0; up < 10 && node; up++) {
        const hasEditor = !!node.querySelector("[contenteditable='true'], textarea");
        if (hasEditor) {
          // Ikon / ok gorsellerini sayma; referans cip onizlemeleri daha buyuk
          const imgs = Array.from(node.querySelectorAll("img")).filter((img) => {
            const w = Math.max(img.naturalWidth || 0, img.width || 0, img.clientWidth || 0);
            const h = Math.max(img.naturalHeight || 0, img.height || 0, img.clientHeight || 0);
            return w >= 28 && h >= 28;
          });
          return imgs.length;
        }
        node = node.parentElement;
      }
      return 0;
    })
    .catch(() => 0);
}

/**
 * Prompt cubugundaki mevcut referans eklerini kaldirir.
 * Her klip kendi referansiyla uretilmelidir; onceki klipten kalan ek
 * temizlenmezse sonraki kliplere yanlis yuz/gorsel tasinir veya AYNI
 * karakter cift gorunur (ozellikle 15-20. klipten sonra).
 */
export async function clearPromptAttachments(page: Page, project: Project): Promise<number> {
  let removed = 0;
  for (let round = 0; round < 16; round++) {
    const before = await promptAttachmentCount(page);
    if (before === 0) break;

    const clicked = await page
      .evaluate(() => {
        const send = Array.from(document.querySelectorAll("button")).find((b) =>
          /arrow_forward/i.test(b.textContent || "")
        );
        let composer: HTMLElement | null = (send as HTMLElement | undefined)?.parentElement ?? null;
        for (let up = 0; up < 10 && composer; up++) {
          const hasEditor = !!composer.querySelector("[contenteditable='true'], textarea");
          if (hasEditor) break;
          composer = composer.parentElement;
        }
        if (!composer) {
          const editor = document.querySelector("[contenteditable='true'], textarea");
          composer = (editor as HTMLElement | null)?.parentElement ?? null;
          for (let up = 0; up < 8 && composer; up++) {
            const hasSend = Array.from(composer.querySelectorAll("button")).some((b) =>
              /arrow_forward/i.test(b.textContent || "")
            );
            if (hasSend) break;
            composer = composer.parentElement;
          }
        }
        if (!composer) return 0;

        const removers = Array.from(composer.querySelectorAll("button")).filter((b) => {
          const text = (b.textContent || "").trim();
          const label = b.getAttribute("aria-label") || "";
          if (/arrow_forward|add_2|add\b/i.test(`${text} ${label}`)) return false;
          return /close|cancel|clear|remove|kald[iı]r|\bsil\b|^\s*×\s*$|^\s*x\s*$/i.test(`${text} ${label}`);
        });
        // Her turda en fazla 2 kaldir — DOM yenilensin
        let n = 0;
        for (const btn of removers.slice(0, 2)) {
          try {
            btn.click();
            n++;
          } catch {
            /* ignore */
          }
        }
        return n;
      })
      .catch(() => 0);

    if (!clicked) {
      await page.keyboard.press("Escape").catch(() => {});
      await page.waitForTimeout(300);
      const still = await promptAttachmentCount(page);
      if (still === before) break;
      continue;
    }
    await page.waitForTimeout(500);
    const after = await promptAttachmentCount(page);
    if (after < before) removed += before - after;
    else if (after === before) break;
  }

  const leftover = await promptAttachmentCount(page).catch(() => 0);
  if (leftover > 0) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Prompt cubugunda ${leftover} eski referans temizlenemedi — cift karakter riski`,
    });
  } else if (removed > 0) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Prompt cubugundaki ${removed} eski referans eki temizlendi`,
    });
  }
  return removed;
}

/**
 * Kompozisyon cubugundaki "+" dugmesine basip MEDYA PENCERESINI acar.
 *
 * DIKKAT: Ust seritteki "Medya ekle" MENUSU ile karistirilmamalidir. O menu
 * dosyayi yalnizca proje kitapligina yukler; isteme (prompta) EKLEMEZ. Dogru
 * dugme, pencere acan olandir (aria-haspopup="dialog").
 */
async function openMediaDialog(page: Page, project: Project): Promise<boolean> {
  const dialog = page.locator("[role='dialog'], [aria-modal='true']").first();
  if (await dialog.isVisible({ timeout: 500 }).catch(() => false)) return true;

  /*
   * Adaylar SONUCA gore denenir: bir dugmenin "gorunur olmasi" dogru dugme
   * oldugunu kanitlamaz. Ust seritteki "Medya ekle" bir MENU acar; dogru dugme
   * PENCERE acandir. Bu yuzden her aday tiklanir ve pencere gercekten acildi mi
   * diye bakilir; acilmadiysa (menu acilmis olabilir) Escape ile kapatilip
   * sonraki aday denenir.
   */
  const structural: SelectorCandidate = { strategy: "css", value: "button[aria-haspopup='dialog']", roleName: "" };
  const chain = [structural, ...(await getCandidatesFor("uploadReferenceButton"))];

  for (const candidate of chain) {
    const locator = buildLocator(page, candidate);
    if (!(await locator.isVisible({ timeout: 600 }).catch(() => false))) continue;

    await locator.click().catch(() => {});
    await page.waitForTimeout(900);
    if (await dialog.isVisible({ timeout: 2_500 }).catch(() => false)) {
      // Calisan adayi kalici hale getir: bir sonraki klipte bosuna denenmesin
      await saveCandidates("uploadReferenceButton", [candidate, ...chain.filter((c) => c !== candidate)].slice(0, 8)).catch(() => {});
      return true;
    }
    // Yanlis dugme (or. kitaplik menusu) acilmis olabilir: kapat, sonrakini dene
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(400);
  }

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message:
      "Medya penceresi acilamadi. Kalibrasyon ekranindan 'Medya ekleme (+) dugmesi' olarak PROMPT KUTUSUNUN YANINDAKI + dugmesini tanitin (ust seritteki 'Medya ekle' DEGIL).",
  });
  return false;
}

/**
 * Yukleme sonrasi Flow bir medya secim penceresi acar ve gorselin prompta
 * eklenmesi icin onay bekler (Turkce arayuzde "Isleme ekle").
 * Bu adim atlanirsa pencere acik kalir, prompt kutusunu ve Generate'i engeller.
 */
async function confirmReferenceDialog(page: Page, project: Project): Promise<boolean> {
  // Onay dugmesi Turkce arayuzde "Isteme ekle"; aday zinciri (kalibrasyon +
  // yerlesik yazim varyantlari) selectors.ts icinde tanimli.
  const dialog = page.locator("[role='dialog'], [aria-modal='true']").first();

  // 1) Yukleme bitene ve onay dugmesi gorunene kadar sabirla bekle.
  //    Dugme gorunmuyorsa yeni yuklenen ogeyi secmek gerekebilir (ilk kucuk resim).
  let confirm: Locator | null = null;
  const deadline = Date.now() + 15_000;
  let triedSelectingItem = false;
  let dialogEverSeen = false;
  while (Date.now() < deadline) {
    confirm = await locatorFor(page, "referenceConfirmButton", { timeoutMs: 900 });
    if (confirm) break;

    const dialogVisible = await dialog.isVisible({ timeout: 400 }).catch(() => false);
    dialogEverSeen = dialogEverSeen || dialogVisible;
    if (!triedSelectingItem && dialogVisible) {
      const firstThumb = dialog.locator("img").first();
      if (await firstThumb.isVisible({ timeout: 400 }).catch(() => false)) {
        triedSelectingItem = true;
        await firstThumb.click().catch(() => {});
        await recordEvent({ projectId: project.id, step: "flow", message: "Medya penceresinde yuklenen gorsel secildi" });
      }
    }
    await page.waitForTimeout(1_000);
  }

  if (!confirm && !dialogEverSeen) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message:
        "Medya secim penceresi hic acilmadi: gorsel kitapliga yuklenmis ama ISTEME EKLENMEMIS olabilir. Referans onemliyse '+' dugmesini ve 'Isteme ekle' ogesini kalibre edin.",
    });
    return false;
  }

  // 2) Onayla ve pencerenin gercekten kapandigini dogrula (en fazla 2 deneme)
  if (confirm) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      await confirm.click().catch(() => {});
      await page.waitForTimeout(1_500);
      const stillOpen = await dialog.isVisible({ timeout: 700 }).catch(() => false);
      if (!stillOpen) {
        await recordEvent({
          projectId: project.id,
          step: "flow",
          message: "Referans gorsel isteme eklendi ('Isteme ekle' onaylandi, pencere kapandi)",
        });
        return true;
      }
      confirm = await locatorFor(page, "referenceConfirmButton", { timeoutMs: 900 });
      if (!confirm) break;
    }
  }

  // 3) Onaylanamadi: prompt kutusunu engellememesi icin pencereyi kapat
  if (await dialog.isVisible({ timeout: 500 }).catch(() => false)) {
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(600);
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message:
        "Medya penceresi onaylanamadi ve kapatildi — referans gorsel ISTEME EKLENMEDI. Kalibrasyon ekranindan 'Medya penceresi onay dugmesi (Isteme ekle)' ogesini pencere acikken tanitin.",
    });
  }
  return false;
}

/**
 * Birden fazla referans gorseli yukler (sirayla).
 * Her ekleme sonrasi cubuk sayisi dogrulanir; eksik kalanlar bir kez daha denenir.
 *
 * Tekil ekleme akisi: + dugmesi → medya penceresi → dosya yukle → liste ogesi
 * tikla → (gerekirse Isteme ekle) → cubuk onizleme sayisi artmali.
 */
export async function uploadReferenceImages(page: Page, project: Project, imagePaths: string[]): Promise<number> {
  const unique = uniqueExistingImagePaths(imagePaths);
  if (unique.length === 0) return 0;

  if (isCharactersPageUrl(page.url())) {
    await returnToProjectEditor(page, project).catch(() => {});
  }
  await ensureVideoOutputMode(page, project);

  await clearPromptAttachments(page, project);
  // Temizlik sonrasi cubukta cip kaldiysa yeniden dene — cift karakterin ana kaynagi
  if ((await promptAttachmentCount(page).catch(() => 0)) > 0) {
    await page.waitForTimeout(400);
    await clearPromptAttachments(page, project);
  }

  const failed: string[] = [];
  let uploaded = 0;
  for (const imagePath of unique) {
    // Coklu referansli klipler bu dongude 30+ sn gecirebilir; her adimda
    // heartbeat tazelenmezse reconcileOrphanJobs bu CANLI isi yetim sanabilir
    // (bkz. HEARTBEAT_STALE_MS aciklamasi). Ayrica "durdur" istegi de burada
    // daha hizli fark edilir.
    assertAutomationContinuing();
    const before = await promptAttachmentCount(page).catch(() => uploaded);
    const ok = await uploadReferenceImage(page, project, imagePath, { clearFirst: false });
    const after = await promptAttachmentCount(page).catch(() => before);
    if (after > before) {
      uploaded = after;
      markLibraryKnown(project.id, imagePath);
    } else if (ok) {
      // Sayac artmadi ama ok — yine de bilinen say; tekrar upload etme
      markLibraryKnown(project.id, imagePath);
    } else {
      failed.push(imagePath);
    }
  }

  if (failed.length > 0) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `${failed.length} referans eksik (${uploaded}/${unique.length}); yeniden deneniyor`,
    });
    for (const imagePath of failed) {
      assertAutomationContinuing();
      await page.waitForTimeout(800);
      const before = await promptAttachmentCount(page).catch(() => uploaded);
      const ok = await uploadReferenceImage(page, project, imagePath, { clearFirst: false });
      const after = await promptAttachmentCount(page).catch(() => before);
      if (ok || after > before) {
        uploaded = Math.max(uploaded, after);
        markLibraryKnown(project.id, imagePath);
      }
    }
  }

  const onBar = await promptAttachmentCount(page).catch(() => uploaded);
  await recordEvent({
    projectId: project.id,
    step: "flow",
    message:
      onBar >= unique.length
        ? `${onBar}/${unique.length} referans gorsel isteme eklendi`
        : `${onBar}/${unique.length} referans isteme eklendi (hedef ${unique.length}; bazilari Flow tarafinda tutunamadi)`,
    level: onBar >= unique.length ? "info" : "warning",
  });

  await returnToVideoComposer(page, project);
  return onBar;
}

export async function uploadReferenceImage(
  page: Page,
  project: Project,
  imagePath: string,
  options?: { clearFirst?: boolean }
): Promise<boolean> {
  if (!fs.existsSync(imagePath)) {
    await recordEvent({ projectId: project.id, step: "flow", level: "warning", message: `Referans gorsel bulunamadi: ${imagePath}` });
    return false;
  }

  const fileName = path.basename(imagePath);
  const shortName = fileName.replace(/\.[^.]+$/, "").slice(0, 24);
  if (options?.clearFirst !== false) {
    await clearPromptAttachments(page, project);
  }
  const attachmentsBefore = await promptAttachmentCount(page);

  const finishAttach = async (dialog: ReturnType<Page["locator"]>, how: string): Promise<boolean> => {
    if (await dialog.isVisible({ timeout: 700 }).catch(() => false)) {
      await confirmReferenceDialog(page, project);
    }
    for (let round = 0; round < 4; round++) {
      await escapeAssetDetailView(page, project, { mode: "soft" });
      await page.waitForTimeout(500);
    }
    if (!(await findPromptInput(page, project.id))) {
      await returnToVideoComposer(page, project);
    }
    const attachmentsAfter = await promptAttachmentCount(page);
    if (attachmentsAfter > attachmentsBefore) {
      markLibraryKnown(project.id, imagePath);
      await recordEvent({
        projectId: project.id,
        step: "flow",
        message: `Referans isteme eklendi (${fileName}) · ${how} · cubukta ${attachmentsAfter} ek`,
      });
      return true;
    }
    return false;
  };

  // Onceki kliplerde yuklendiyse TEKRAR upload etme — kutuphaneden adiyla sec
  const preferLibrary = isLibraryKnown(project.id, imagePath);
  if (preferLibrary && (await openMediaDialog(page, project))) {
    const dialog = page.locator("[role='dialog'], [aria-modal='true']").first();
    const item = dialog.getByText(new RegExp(escapeRegExp(shortName), "i")).first();
    if (await item.isVisible({ timeout: 3_500 }).catch(() => false)) {
      await item.click().catch(() => {});
      await page.waitForTimeout(1_000);
      if (await finishAttach(dialog, "kutuphaneden")) return true;
    } else {
      await page.keyboard.press("Escape").catch(() => {});
    }
  }

  // 1) Medya penceresini ac + dosya yukle (yalnizca ilk sefer / kutuphanede yoksa)
  if (!(await openMediaDialog(page, project))) return false;
  const dialog = page.locator("[role='dialog'], [aria-modal='true']").first();

  const dialogInput = dialog.locator("input[type='file']").first();
  const fileInput = (await dialogInput.count().catch(() => 0)) > 0 ? dialogInput : page.locator("input[type='file']").first();
  if ((await fileInput.count().catch(() => 0)) === 0) {
    await recordEvent({ projectId: project.id, step: "flow", level: "warning", message: "Medya penceresinde dosya alani bulunamadi" });
    await page.keyboard.press("Escape").catch(() => {});
    return false;
  }
  await fileInput.setInputFiles(imagePath).catch(async (err: Error) => {
    await recordEvent({ projectId: project.id, step: "flow", level: "warning", message: `Dosya yuklenemedi: ${err.message}` });
  });
  await page.waitForTimeout(2_800);
  markLibraryKnown(project.id, imagePath);
  await recordEvent({ projectId: project.id, step: "flow", message: `Referans gorsel yuklendi: ${fileName}` });

  // ADIYLA sec — kalabalik kutuphanede "ilk thumbnail" YASAK (yanlis/cift karakter)
  const item = dialog.getByText(new RegExp(escapeRegExp(shortName), "i")).first();
  if (await item.isVisible({ timeout: 4_000 }).catch(() => false)) {
    await item.click().catch(() => {});
    await page.waitForTimeout(1_200);
  } else {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Kutuphanede ad eslesmedi (${shortName}); rastgele thumbnail tiklanmayacak`,
    });
  }

  if (await finishAttach(dialog, "yukle+ad")) return true;

  // Ikinci sans: sadece ad ile tekrar (yeniden upload yok)
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Referans cubuga yapismadi (${fileName}); kutuphaneden ikinci deneme`,
  });
  if (await openMediaDialog(page, project)) {
    const dialog2 = page.locator("[role='dialog'], [aria-modal='true']").first();
    const item2 = dialog2.getByText(new RegExp(escapeRegExp(shortName), "i")).first();
    if (await item2.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await item2.click().catch(() => {});
      await page.waitForTimeout(1_200);
      if (await finishAttach(dialog2, "2. deneme")) return true;
    }
    if (await dialog2.isVisible({ timeout: 500 }).catch(() => false)) {
      await page.keyboard.press("Escape").catch(() => {});
    }
  }

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Referans gorsel isteme EKLENEMEDI (${fileName}); klip eksik referansla uretilebilir.`,
  });
  return false;
}

/**
 * Tam ekran gorsel duzenlemeden video prompt cubuguna doner.
 * Kutuphaneden SILMEZ; Bitti / geri / Escape dener. Son care: proje URL.
 */
export async function returnToVideoComposer(page: Page, project: Project): Promise<void> {
  // Karakterler sayfasi / karakter editoru video promptu degildir.
  // Burada Bitti/Escape'e basmak yarim kalan karakteri kapatir veya kaydeder.
  if (isCharactersPageUrl(page.url())) {
    await returnToProjectEditor(page, project).catch(() => {});
  }

  // Onceki "goruntu duzenleme kapat" adimi genel bir geri/close dugmesine
  // basip projeden TAMAMEN cikartmis olabilir (Flow ana sayfasina/baska
  // projeye suruklenir). Bitti/Escape ile bos yere ugrasmadan once, bilinen
  // proje adresi varsa dogrudan ona don — en hizli ve en guvenilir kurtarma.
  if (!isOnExpectedProjectPage(page, project) && project.flowProjectUrl?.trim()) {
    const driftedFrom = page.url();
    await page.goto(project.flowProjectUrl.trim(), { waitUntil: "domcontentloaded", timeout: 60_000 }).catch(() => {});
    await page.waitForTimeout(1_500);
    if (await findPromptInput(page, project.id)) {
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "warning",
        message: `Beklenmedik sayfaya suruklenmisti (${driftedFrom}); proje adresine geri donuldu`,
      });
      return;
    }
  }

  for (let attempt = 1; attempt <= 6; attempt++) {
    if (await findPromptInput(page, project.id)) {
      if (attempt > 1) {
        await recordEvent({
          projectId: project.id,
          step: "flow",
          message: `Video editorune donuldu (deneme ${attempt})`,
        });
      }
      return;
    }

    await escapeAssetDetailView(page, project, { mode: "soft" });

    // Bitti / Done (ikon + metin)
    const done = page.getByRole("button", { name: /bitti|done|check/i }).first();
    if (await done.isVisible({ timeout: 500 }).catch(() => false)) {
      await done.click().catch(() => {});
      await page.waitForTimeout(800);
    }

    const back = page.getByRole("button", { name: /arrow_back|geri|back/i }).first();
    if (await back.isVisible({ timeout: 400 }).catch(() => false)) {
      await back.click().catch(() => {});
      await page.waitForTimeout(700);
    }

    // Escape overlay'i kapatir; kutuphane silmez (cop dugmesi siler)
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(500);

    if (await findPromptInput(page, project.id)) {
      await recordEvent({
        projectId: project.id,
        step: "flow",
        message: `Video editorune donuldu (Escape/Bitti, deneme ${attempt})`,
      });
      return;
    }
  }

  // Son care: proje kokune git (referans cip'leri kaybolabilir; yeniden yuklenir).
  // Su anki adres artik /project/ icermiyorsa (Flow ana sayfasina tamamen
  // suruklenmis olabiliriz) bilinen proje adresine dus — regex'e guvenme.
  const url = page.url();
  const match = url.match(/^(.*\/project\/[0-9a-f][0-9a-f-]{7,})/i);
  const recoveryUrl = match?.[1] || project.flowProjectUrl?.trim() || null;
  if (recoveryUrl) {
    await page.goto(recoveryUrl, { waitUntil: "domcontentloaded" }).catch(() => {});
    await page.waitForTimeout(1_800);
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: match
        ? "Gorsel ekraninda takili kalindi; proje adresine donuldu (referanslar yeniden eklenebilir)"
        : `Flow ana sayfasina/beklenmedik adrese suruklenmisti (${url}); bilinen proje adresine donuldu`,
    });
  }

  if (!(await findPromptInput(page, project.id))) {
    throw new Error(
      recoveryUrl
        ? "Flow gorsel duzenleme ekraninda takili kaldi; video prompt kutusu yok. Chrome'da 'Bitti' ile video editorune donup Devam Ettir'e basin."
        : "Flow beklenmedik bir sayfaya suruklendi ve bu proje icin 'Flow proje linki' tanimli degil. Proje Ayarlari > 'Flow proje linki' alanini doldurun (Chrome'da projeyi acip adres cubugundaki linki kopyalayin), sonra Devam Ettir'e basin."
    );
  }
}

/**
 * Yuklenen gorsel bazen tam ekran GORUNTU DUZENLEME gorunumunde acilir
 * ("Neyi degistirmek istiyorsunuz?" kutusu + "Bitti" dugmesi). Bu gorunum
 * video prompt kutusunu ele gecirir: prompt goruntu duzenleyiciye yazilir,
 * video uretimi hic baslamaz ve klip zaman asimina ugrar. Tespit edilirse
 * "Bitti"/geri ile kapatilip editore donulur.
 *
 * @param options.mode
 *  - soft: sadece Bitti/geri — kutuphaneden SILMEZ, sayfa yenilemez (referans
 *    yukleme sirasinda zorunlu; aksi halde eklenen karakter silinir)
 *  - aggressive (varsayilan): takili kalmissa kutuphaneden sil / Escape / goto
 *    — prompt cubugunda zaten ek varsa otomatik soft'a duser (generate oncesi
 *    referanslari silmemek icin)
 */
export async function escapeAssetDetailView(
  page: Page,
  project: Project,
  options?: { mode?: "soft" | "aggressive" }
): Promise<void> {
  // Karakter editoru de "Bitti" + prompt cubugu gosterir; bunu goruntu
  // duzenleme sanip kapatmak kadro uretimini oldurur.
  if (isCharactersPageUrl(page.url())) return;

  const requested = options?.mode ?? "aggressive";
  // Isteme cubugunda referans varken kutuphaneden silmek cip'i de kaldirir.
  const attachmentCount = await promptAttachmentCount(page).catch(() => 0);
  const mode = requested === "soft" || attachmentCount > 0 ? "soft" : "aggressive";
  // YALNIZCA gercek goruntu duzenleme: "Neyi degistirmek..." metni VEYA
  // referans baslik input'u + Bitti. "Gecmisi gizle" TEK BASINA yetmez —
  // video editorunde de gorunur ve surekli soft-escape uretimi boguyor.
  const isEditViewOpen = async (): Promise<boolean> => {
    const editHint = page
      .getByText(/neyi de[gğ]i[sş]tirmek istiyorsun|what (do you want|would you like) to change/i)
      .first();
    if (await editHint.isVisible({ timeout: 400 }).catch(() => false)) return true;
    const uploadedRefTitle = page.locator("input[value*='reference-flow'], input[value*='-last.']").first();
    const doneButton = page.getByRole("button", { name: /bitti|done/i }).first();
    if (
      (await uploadedRefTitle.isVisible({ timeout: 300 }).catch(() => false)) &&
      (await doneButton.isVisible({ timeout: 300 }).catch(() => false))
    ) {
      return true;
    }
    return false;
  };

  if (!(await isEditViewOpen())) return;

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message:
      mode === "soft"
        ? `Goruntu duzenleme gorunumu acik; yumusak kapatma (referanslar korunacak${attachmentCount > 0 ? `, cubukta ${attachmentCount} ek` : ""})`
        : "Goruntu duzenleme gorunumu acik (yuklenen gorsel tam ekran acilmis); kapatilip video editorune donuluyor",
  });

  // soft: kutuphaneden ASLA silme — referans-flow / cast gorselleri isteme ekliyken
  // silinirse prompt cubugundaki cip de kaybolur (kullanicinin gordugu "ekle sonra sil").
  if (mode === "aggressive") {
    let deletedCount = 0;
    for (let round = 0; round < 15; round++) {
      if (!(await isEditViewOpen())) break;
      const uploadedRefTitle = page.locator("input[value*='reference-flow'], input[value*='-last.']").first();
      if (!(await uploadedRefTitle.isVisible({ timeout: 700 }).catch(() => false))) break;
      const trashButton = page.getByRole("button", { name: /delete|[cç][oö]p|\bsil\b/i }).first();
      if (!(await trashButton.isVisible({ timeout: 700 }).catch(() => false))) break;
      await trashButton.click().catch(() => {});
      await page.waitForTimeout(800);
      const confirm = page
        .locator("[role='dialog'], [aria-modal='true']")
        .first()
        .getByRole("button", { name: /sil|delete|evet|onayla|confirm/i })
        .first();
      if (await confirm.isVisible({ timeout: 1_200 }).catch(() => false)) {
        await confirm.click().catch(() => {});
      }
      deletedCount++;
      await page.waitForTimeout(1_400);
    }
    if (deletedCount > 0) {
      await recordEvent({
        projectId: project.id,
        step: "flow",
        message: `Takili kalan ${deletedCount} yuklenmis referans varligi Flow kitapligindan silindi (gorunum geri gelemesin diye)`,
      });
    }
  }

  // "Bitti / Done" dugmesi (ikon + metin)
  if (await isEditViewOpen()) {
    const doneButton = page.getByRole("button", { name: /bitti|done/i }).first();
    if (await doneButton.isVisible({ timeout: 700 }).catch(() => false)) {
      await doneButton.click().catch(() => {});
      await page.waitForTimeout(1_000);
    }
  }
  // Hala aciksa: geri + Escape (Escape kutuphaneden silmez; cop dugmesi siler)
  if (await isEditViewOpen()) {
    const back = page.getByRole("button", { name: /arrow_back|geri|back/i }).first();
    if (await back.isVisible({ timeout: 500 }).catch(() => false)) await back.click().catch(() => {});
    else await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(700);
  }
  if (await isEditViewOpen()) {
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(600);
  }
  // Aggressive son care: Flow proje adresine geri don (soft'ta YAPMA — ekler silinir)
  if (mode === "aggressive" && (await isEditViewOpen())) {
    const url = page.url();
    const match = url.match(/^(.*\/project\/[0-9a-f][0-9a-f-]{7,})/i);
    const recoveryUrl = match?.[1] || project.flowProjectUrl?.trim() || null;
    if (recoveryUrl) {
      await page.goto(recoveryUrl, { waitUntil: "domcontentloaded" }).catch(() => {});
      await page.waitForTimeout(1_500);
    }
  }
  await recordEvent({
    projectId: project.id,
    step: "flow",
    message: (await isEditViewOpen())
      ? "UYARI: goruntu duzenleme gorunumu kapatilamadi"
      : "Video editorune geri donuldu",
    level: (await isEditViewOpen()) ? "warning" : "info",
  });
}

/** Flow prompt kisaltmasi `src/lib/flow-prompt-compact.ts` icinde — yazi yasagi dusmez. */

export async function enterPrompt(page: Page, project: Project, prompt: string): Promise<void> {
  // Kayitli promptlar zaten FLOW_PROMPT_MAX ile finalize edilir; burada guvenlik
  // agi olarak tekrar compact uygulanir (eski kayitlar / manuel duzenleme).
  // Dil + diyalog + sureklilik bloklari oncelikli; sinematik detay butceye gore.
  const strippedAt =
    isKidsContent(project.templateType) && !project.useFlowCharacter
      ? prompt.replace(/^(?:@[^\n]+\r?\n+)+\s*/u, "")
      : prompt;
  const source = isKidsContent(project.templateType) ? sanitizeKidsPromptForFlow(strippedAt) : strippedAt;
  const compacted = compactPromptForFlow(source, project.speechLanguage || "Turkish", FLOW_PROMPT_MAX);
  const afterKids = isKidsContent(project.templateType)
    ? ensureAnimatedCastLock(sanitizeKidsPromptForFlow(compacted.text), FLOW_PROMPT_MAX)
    : compacted.text;
  const promptToWrite = ensureNoOnscreenTextLock(afterKids, FLOW_PROMPT_MAX);
  if (source !== prompt && isKidsContent(project.templateType)) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: "Prompt yayin-guvenli mascot diline cekildi (Flow cocuk-politika reddini onlemek icin)",
    });
  }
  if (compacted.truncated) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Prompt Flow icin kisaltildi (${prompt.trim().length} → ${promptToWrite.length} karakter); dil+diyalog+yazi yasagi korundu`,
    });
  }

  // Yuklenen gorselin actigi tam ekran duzenleme gorunumu varsa once kapat
  await returnToVideoComposer(page, project);
  await dismissOverlaysBlockingPrompt(page, project, "prompt oncesi");

  let input = (await findPromptInput(page, project.id)) ?? (await ensureEditorReady(page, project));

  const focusPrompt = async (target: Locator): Promise<boolean> => {
    // Flow gercek promptuna HTML zindex="-1" koyuyor; Playwright'in normal
    // click actionability kontrolu bazen 15sn asima ugruyor. Once koordinat /
    // force, sonra DOM focus — normal click en son (ve kisa timeout).
    try {
      const box = await target.boundingBox();
      if (box && box.width > 0 && box.height > 0) {
        await page.mouse.click(box.x + Math.min(40, box.width / 2), box.y + Math.max(4, box.height / 2));
        return true;
      }
    } catch {
      /* devam */
    }
    try {
      await target.click({ force: true, timeout: 2_500 });
      return true;
    } catch {
      /* devam */
    }
    try {
      await target.evaluate((el) => {
        (el as HTMLElement).focus();
        const range = document.createRange();
        range.selectNodeContents(el);
        range.collapse(false);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
      });
      return true;
    } catch {
      /* devam */
    }
    try {
      await target.click({ timeout: 2_000 });
      return true;
    } catch {
      return false;
    }
  };

  const writePrompt = async (target: Locator): Promise<void> => {
    const existingText =
      ((await target.innerText().catch(() => "")) || (await target.inputValue().catch(() => ""))).trim();
    // Yer tutucu metni "mevcut prompt" sanma; varsa once temizle
    const looksLikePlaceholder = /ne olu[sş]turmak istiyorsun|what do you want to create/i.test(existingText);
    if (existingText && !looksLikePlaceholder) {
      try {
        await target.fill(promptToWrite);
        return;
      } catch {
        /* klavye yolu */
      }
    }
    await page.keyboard.press("Control+a").catch(() => {});
    await page.keyboard.press("Delete").catch(() => {});
    await page.keyboard.insertText(promptToWrite);
  };

  const promptLooksWritten = async (): Promise<boolean> => {
    const text = await readPromptText(page, project.id);
    if (!text) return false;
    if (/ne olu[sş]turmak istiyorsun|what do you want to create/i.test(text) && text.length < 80) {
      return false;
    }
    // En azindan promptun basindan bir parca kutuda olmali
    const sample = promptToWrite.trim().slice(0, 40);
    return text.includes(sample) || text.length >= Math.min(40, promptToWrite.trim().length);
  };

  let written = false;
  for (let attempt = 1; attempt <= 3; attempt++) {
    await dismissOverlaysBlockingPrompt(page, project, `prompt deneme ${attempt}`);
    input = (await findPromptInput(page, project.id)) ?? input;
    const focused = await focusPrompt(input);
    if (!focused) {
      await page.waitForTimeout(500);
      continue;
    }
    await writePrompt(input);
    await page.waitForTimeout(400);
    if (await promptLooksWritten()) {
      written = true;
      break;
    }
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Prompt kutuya yazilamadi (deneme ${attempt}/3); yeniden deneniyor`,
    });
    await page.waitForTimeout(700);
  }

  if (!written) {
    const snapshot = await captureDebugSnapshot(page, project.slug, "prompt-write-failed");
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "error",
      message: "Prompt chat kutusuna yazilamadi (gizli/yanlis contenteditable veya panel engeli)",
      screenshotPath: snapshot.screenshotPath,
      pageUrl: page.url(),
    });
    throw new Error(
      "Prompt chat kutusuna yazilamadi. Chrome'da Flow proje editorunun acik oldugundan ve prompt cubugunun gorundugunden emin olun, sonra Devam Ettir'e basin."
    );
  }

  await recordEvent({
    projectId: project.id,
    step: "flow",
    message: `Prompt yazildi (${promptToWrite.trim().length} karakter)`,
  });
}

/** Prompt kutusuna odaklanip Enter gonderir (Flow'da uretimi baslatir). */
async function submitPromptWithEnter(page: Page, project: Project): Promise<boolean> {
  const input = await findPromptInput(page, project.id);
  if (!input) return false;
  await input.click().catch(() => {});
  // Imleci metnin sonuna al (ortada Enter satir bolebilir)
  await page.keyboard.press("Control+End").catch(() => {});
  await page.keyboard.press("Enter");
  return true;
}

/** Prompt kutusundaki guncel metni okur (bulunamazsa null). */
async function readPromptText(page: Page, projectId: string): Promise<string | null> {
  const input = await findPromptInput(page, projectId);
  if (!input) return null;
  const text = (await input.innerText().catch(() => "")) || (await input.inputValue().catch(() => ""));
  return text.trim();
}

/** Generate'e basar (auto modda) ve uretimin basladigini dogrular. */
/**
 * Video akisinda hicbir kalici pencere acik olmamalidir; acik kalan medya
 * secim penceresi vb. hem kartlari orter hem tiklamalari yutar. Kapatir.
 */
async function closeStrayDialog(page: Page, project: Project, context: string): Promise<void> {
  const dialog = page.locator("[role='dialog'], [aria-modal='true']").first();
  if (!(await dialog.isVisible({ timeout: 300 }).catch(() => false))) return;
  await page.keyboard.press("Escape").catch(() => {});
  await page.waitForTimeout(600);
  if (await dialog.isVisible({ timeout: 300 }).catch(() => false)) {
    // Escape yetmediyse pencere disina tikla
    await page.mouse.click(4, 300).catch(() => {});
    await page.waitForTimeout(500);
  }
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Acik kalan pencere kapatildi (${context})`,
  });
}

export async function startGeneration(
  page: Page,
  project: Project,
  mode: "auto" | "manual",
  opts?: { output?: "video" | "image" }
): Promise<void> {
  const output = opts?.output ?? "video";
  // Generate'e basmadan: tam ekran onizlemeden cik (mod degistirmez)
  await returnToVideoComposer(page, project);
  await closeStrayDialog(page, project, "uretim oncesi");

  if (output === "image") {
    let imageLabel = await readOutputModeLabel(page);
    if (!isImageOutputModeLabel(imageLabel)) {
      await switchOutputType(page, project, "image");
      imageLabel = await readOutputModeLabel(page);
    }
    if (!isImageOutputModeLabel(imageLabel)) {
      throw new Error(
        `Generate iptal: Flow gorsel modunda degil ("${imageLabel.slice(0, 50)}"). Cikti turunu Metinden goruntuye / Nano Banana yapin.`
      );
    }
  } else {
    await ensureVideoOutputMode(page, project);
    const videoLabel = await readOutputModeLabel(page);
    if (isImageOutputModeLabel(videoLabel)) {
      throw new Error(
        `Generate iptal: Flow GÖRÜNTÜ modunda ("${videoLabel.slice(0, 50)}"). Çıktı türünü video yapıp tekrar deneyin.`
      );
    }
    if (project.templateType === "kids_song") {
      await ensureFlowAudioMode(page, project, false);
    }
  }

  const modeLabel = await readOutputModeLabel(page);

  if (!(await findPromptInput(page, project.id))) {
    await returnToVideoComposer(page, project);
    if (!(await findPromptInput(page, project.id))) {
      throw new Error(
        output === "image"
          ? "Gorsel prompt kutusu bulunamadi; Generate'e basilmadi"
          : "Video prompt kutusu bulunamadi (yuklenen gorselin tam ekran duzenleme gorunumu acik olabilir); video yerine gorsel uretmemek icin Generate'e basilmadi"
      );
    }
  }

  const promptTextBefore = await readPromptText(page, project.id);
  if (!promptTextBefore || promptTextBefore.length < 8) {
    throw new Error("Generate iptal: prompt kutusu bos veya yazilamamis");
  }

  // 10s + 9:16 + Veo Fast sessizce video uretmez; gorsel modunda bu kontrol yok.
  if (output === "video") {
    await assertGenerationChipReady(page, project);
  }

  let enterAlreadyTried = mode !== "auto";
  let generateWasEnabled = true;

  const clickGenerate = async (): Promise<void> => {
    const button = await resolveGenerateButton(page);
    if (button) {
      generateWasEnabled = !(await button.isDisabled({ timeout: 800 }).catch(() => false));
      // Once normal tikla (force disabled dugmeye "basilmis gibi" gorunur ama Flow yutmaz)
      if (generateWasEnabled) {
        await button.click({ timeout: 5_000 }).catch(async () => {
          await button.click({ force: true }).catch(() => {});
        });
      } else {
        await recordEvent({
          projectId: project.id,
          step: "flow",
          level: "warning",
          message: "Generate dugmesi pasif; once Enter denenecek",
        });
        await submitPromptWithEnter(page, project);
        enterAlreadyTried = true;
        return;
      }
      await recordEvent({
        projectId: project.id,
        step: "flow",
        message: `Generate dugmesine basildi (modu: ${modeLabel.slice(0, 40) || "bilinmiyor"})`,
      });
    } else {
      // Dugme hic bulunamadiysa cogu zaman gercek sebep "kalibrasyon eskimis"
      // degil, "sayfa artik bu projenin editoru degil" (goruntu-kapatma
      // kurtarmasi genel bir geri dugmesine basip Flow ana sayfasina/baska
      // projeye suruklemis olabilir). Once buna gore duzelt, sonra tekrar dene.
      if (!isOnExpectedProjectPage(page, project)) {
        const driftedFrom = page.url();
        await returnToVideoComposer(page, project).catch(() => {});
        const retryButton = await resolveGenerateButton(page);
        if (retryButton && !(await retryButton.isDisabled({ timeout: 800 }).catch(() => false))) {
          await recordEvent({
            projectId: project.id,
            step: "flow",
            level: "warning",
            message: `Sayfa suruklenmisti (${driftedFrom}); proje editorune donuldu ve Generate tekrar denendi`,
          });
          await retryButton.click({ timeout: 5_000 }).catch(async () => {
            await retryButton.click({ force: true }).catch(() => {});
          });
          await recordEvent({
            projectId: project.id,
            step: "flow",
            message: `Generate dugmesine basildi (modu: ${modeLabel.slice(0, 40) || "bilinmiyor"})`,
          });
          return;
        }
      }
      if (!(await submitPromptWithEnter(page, project))) {
        if (!isOnExpectedProjectPage(page, project)) {
          throw new Error(
            `Flow, proje editorunden farkli bir sayfaya suruklenmis durumda (${page.url()}) ve otomatik geri donulemedi. Chrome penceresinde bu projenin editorunun (prompt kutusunun gorundugu ekran) acik oldugundan emin olup "Devam Ettir"e basin.`
          );
        }
        throw new SelectorMissingError("generateButton");
      }
      enterAlreadyTried = true;
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "warning",
        message: "Generate dugmesi bulunamadi; prompt kutusunda Enter ile gonderildi. Dugmeyi kalibre etmeniz onerilir.",
      });
    }
  };

  if (mode === "auto") {
    await clickGenerate();
  } else {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "YARI OTOMATIK MOD: Generate dugmesine Flow penceresinde ELLE basin. Uretim algilandiginda otomasyon devam edecek.",
    });
  }

  const settings = await getSettings();
  const startTimeout = mode === "auto" ? 45_000 : 180_000;
  const deadline = Date.now() + startTimeout;
  const enterFallbackAt = Date.now() + 6_000;
  const secondClickAt = Date.now() + 12_000;
  let secondClickDone = false;
  // Generate'e basinca Flow bazen kompozisyon cubugunu TAMAMEN kaldirip yeni
  // uretim kartini/onizlemesini gosteriyor (kutu "temizlenmiyor", YOK oluyor).
  // Bu durum onceden "goruntu duzenleme acik" sanilip Bitti/geri/Escape ile
  // KAPATILIYORDU — tam da baslamis uretimi kesintiye ugratiyordu. Proje
  // sayfasindan hic ayrilmadan, ust uste 2 kontrolde kutu tamamen kayipsa
  // (gecici bir render karesi degil) basarili sayilir.
  let missingInputStreak = 0;

  while (Date.now() < deadline) {
    const current = await readPromptText(page, project.id);
    if (current !== null && (current.length === 0 || !current.includes(promptTextBefore.slice(0, 25)))) {
      await recordEvent({ projectId: project.id, step: "flow", message: "Uretim basladi (prompt gonderildi, kutu temizlendi)" });
      return;
    }

    const progress = await locatorFor(page, "generationProgress", { selfHeal: false, timeoutMs: 700 });
    if (progress) {
      await recordEvent({ projectId: project.id, step: "flow", message: "Uretim basladi (ilerleme gostergesi gorundu)" });
      return;
    }

    if (current === null && isOnExpectedProjectPage(page, project)) {
      missingInputStreak++;
      if (missingInputStreak >= 2) {
        await recordEvent({
          projectId: project.id,
          step: "flow",
          message: "Uretim basladi (prompt cubugu kayboldu — Flow yeni uretim gorunumune gecti)",
        });
        return;
      }
    } else {
      missingInputStreak = 0;
    }

    // Kutu kayipsa VE beklenen proje sayfasindaysak bu, uretimin baslamis
    // olabilecegi belirsiz bir durumdur (missingInputStreak bunu yukarida
    // cozer). Bu durumda returnToVideoComposer/escape cagirmak, Flow'un yeni
    // uretim onizlemesini "goruntu duzenleme" sanip KAPATMASINA ve ana sayfaya
    // suruklenmesine sebep oluyordu. Sadece kutu HALA GORUNUYORSA (Generate
    // gercekten calismadi) veya beklenmedik bir sayfaya suruklendiysek
    // (kutu da yok, sayfa da yanlis) aktif kurtarmaya gecilir.
    const ambiguousMaybeGenerating = current === null && isOnExpectedProjectPage(page, project);
    if (!enterAlreadyTried && !ambiguousMaybeGenerating && Date.now() >= enterFallbackAt) {
      enterAlreadyTried = true;
      await returnToVideoComposer(page, project).catch(() => {});
      if (await submitPromptWithEnter(page, project)) {
        await recordEvent({
          projectId: project.id,
          step: "flow",
          level: "warning",
          message: "Generate tiklamasi uretimi baslatmadi; prompt kutusunda Enter ile gonderildi",
        });
      }
    }

    if (mode === "auto" && !secondClickDone && !ambiguousMaybeGenerating && Date.now() >= secondClickAt) {
      secondClickDone = true;
      await returnToVideoComposer(page, project).catch(() => {});
      await closeStrayDialog(page, project, "generate yeniden");
      await clickGenerate();
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "warning",
        message: "Generate ikinci kez denendi (ilk tiklama promptu gondermedi)",
      });
    }

    await interruptibleSleep(settings.pollIntervalMs);
  }

  // Gorsel modunda prompt kutusu bazen temizlenmiyor ve ilerleme cubugu hic
  // gorunmuyor; gercek dogrulama yeni karenin belirmesidir (waitForNewComposerImage).
  // Bu yuzden burada firlatmak yerine uyari birakilir.
  if (output === "image" && mode === "auto") {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Gorsel uretiminin basladigi dogrulanamadi; yeni kare beklenerek devam ediliyor",
    });
    return;
  }

  throw new Error(
    mode === "auto"
      ? "Uretimin basladigi dogrulanamadi (prompt kutusu temizlenmedi / ilerleme gorunmedi). Flow'da cikti turunun VIDEO oldugundan ve gorsel duzenleme ekraninda olmadiginizdan emin olun."
      : "Elle Generate beklenirken zaman asimi (180 sn). Otomasyonu duraklattiktan sonra tekrar deneyin."
  );
}

export interface CompletionSignals {
  completeIndicator: boolean;
  progressGone: boolean;
  generateEnabled: boolean;
  errorVisible: boolean;
  errorText: string;
}

/**
 * Bir secici anahtarinin sayfadaki eslesme SAYISINI olcer (adaylar arasi en
 * yuksek deger). Medya listesindeki kartlar (eski hatalar, eski videolar)
 * kalici oldugu icin "var/yok" yerine sayim kullanilir: uretim oncesine gore
 * sayi ARTARSA yeni bir kart olusmus demektir.
 */
export async function countSelectorMatches(page: Page, key: string): Promise<number> {
  const { getCandidatesFor } = await import("@/server/automation/selectors");
  const candidates = await getCandidatesFor(key);
  let max = 0;
  for (const candidate of candidates) {
    try {
      let count = 0;
      if (candidate.strategy === "text") count = await page.getByText(new RegExp(candidate.value, "i")).count();
      else if (candidate.strategy === "role" && candidate.roleName)
        count = await page
          .getByRole(candidate.value as Parameters<Page["getByRole"]>[0], { name: new RegExp(candidate.roleName, "i") })
          .count();
      else if (candidate.strategy === "css") count = await page.locator(candidate.value).count();
      max = Math.max(max, count);
    } catch {
      // gecersiz aday sayimi etkilemesin
    }
  }
  return max;
}

const FLOW_FAILURE_TEXT =
  /hay aksi|ba[sş]ar[iı]s[iı]z|hata olu[sş]tu|[uü]cret al[iı]nmaz|generation failed|something went wrong|won'?t be charged|politikalar[iı]m[iı]z[iı] ihlal|ihlal ediyor olabilir|may violate|violates? (our|the) polic|content polic|hatay[ıi].{0,48}ç[oö]z|ç[oö]z[uü]l[uü]yor|yeniden den[ie]n|tekrar den[ie]n/i;

/** Icerik politikasi reddi: ayni istemle tekrar denemek anlamsizdir. */
const POLICY_BLOCK_TEXT =
  /politikalar[iı]m[iı]z[iı] ihlal|ihlal ediyor olabilir|may violate|violates? (our|the) polic|content polic|tan[iı]nm[iı][sş] ki[sş]iler/i;

/**
 * Hata metnine gore dogru hata turunu uretir: politika reddi ayni promptla
 * cozulemez, bu yuzden yeniden deneme yerine elle mudahale istenir.
 */
function generationFailureError(errorText: string): Error {
  if (POLICY_BLOCK_TEXT.test(errorText)) {
    return new ManualActionNeededError(
      `Flow icerik politikasi bu istemi reddetti: "${errorText.slice(0, 140)}". Ayni promptla tekrar denemek sonuc vermez — klibin sahne tarifini yumusatin (kisiyi yatak/samimi sahneden cikarin veya kesiti kisisiz kurun), promptu yenileyip klibi tekrar kuyruga alin.`
    );
  }
  return new Error(`Flow uretim hatasi: ${errorText.slice(0, 200)}`);
}

/** Ekrandaki Flow hata karti metnini toplar (sayim artmasa bile). */
async function collectVisibleErrorText(page: Page): Promise<string> {
  try {
    const locators = page.getByText(FLOW_FAILURE_TEXT);
    const n = await locators.count();
    const chunks: string[] = [];
    for (let i = 0; i < Math.min(n, 4); i++) {
      const text = ((await locators.nth(i).textContent().catch(() => "")) ?? "").replace(/\s+/g, " ").trim();
      if (text) chunks.push(text.slice(0, 180));
    }
    return chunks.join(" | ");
  } catch {
    return "";
  }
}

/**
 * Sayfadaki video varliklarinin kimliklerini toplar.
 * Flow her medyaya sabit bir kimlik verir: .../media.getMediaUrlRedirect?name=<kimlik>
 * Uretim oncesi/sonrasi bu kumeleri kiyaslamak, "yeni video gercekten olustu mu"
 * sorusunun TEK kesin cevabidir (kart sayimi sanal listede yaniltir).
 */
export async function snapshotVideoAssetIds(page: Page): Promise<Set<string>> {
  const sources = await page
    .evaluate(() =>
      Array.from(document.querySelectorAll("video"))
        .map((v) => (v as HTMLVideoElement).getAttribute("src") || v.querySelector("source")?.getAttribute("src") || "")
        .filter(Boolean)
    )
    .catch(() => [] as string[]);

  const ids = new Set<string>();
  for (const src of sources) {
    const match = src.match(/name=([0-9a-fA-F-]{8,})/);
    if (match) ids.add(match[1]);
  }
  return ids;
}

/**
 * Uretim oncesinde olmayan bir video varligi arar.
 *
 * KAYDIRMA YAPILMAZ: sanal listede asagi/yukari kaydirmak, daha once hic
 * gorunmemis ESKI kartlari DOM'a sokar ve bunlar "yeni" sanilir. Bu yuzden
 * yalnizca o an gorunen kartlara bakilir ve aday, KENDI indirme dugmesi
 * bulunabiliyorsa kabul edilir — indirilecek kartla ayni sey oldugu boylece
 * garanti altina alinir.
 */
async function findNewVideoAssetId(page: Page, known: Set<string>): Promise<string | null> {
  const current = await snapshotVideoAssetIds(page);
  for (const id of current) {
    if (known.has(id)) continue;
    if (await cardDownloadButtonFor(page, id)) return id;
  }
  return null;
}

/**
 * Uretim tamamlanmasini coklu sinyalle bekler:
 * - YENI video varligi (kesin kanit; donus degeri bu varligin kimligidir)
 * - generationComplete gostergesi / kart sayisi artisi
 * - ilerleme gostergesinin kaybolmasi + Generate'in aktiflesmesi
 * - YENI hata karti (uretim oncesi sayima gore artis) -> hata
 * - uretim dongusu bitti + yeni video yok -> hizli hata (420 sn beklenmez)
 * - zaman asimi -> ekran goruntusu + HTML snapshot ile hata
 */
export async function waitForCompletion(page: Page, project: Project, knownAssetIds?: Set<string>): Promise<string | null> {
  const settings = await getSettings();
  const startedAt = Date.now();
  const deadline = startedAt + settings.generationTimeoutMs;
  // Bir video uretimi saniyeler icinde bitemez; erken "tamamlandi" kararlari
  // eski kartlardan kaynaklanir. Ilk 20 saniyede tamamlanma kabul edilmez.
  const minWaitUntil = startedAt + 20_000;
  /** Generate tekrar aktif + ilerleme yok = dongu bitti; yeni video bu surede gelmezse FAIL. */
  const CYCLE_END_GRACE_MS = 40_000;
  /** "Hatayi cozuyoruz" toast'i bu sureden uzun surerse takilmis sayilir. */
  const STUCK_RESOLVING_MAX_MS = 75_000;
  let progressSeen = false;
  let generateCycleEndedAt: number | null = null;

  // Eski kartlar (basarisiz VE tamamlanmis) listede kalicidir; yalnizca
  // SAYIM ARTISI yeni kart demektir.
  const staleErrorCount = await countSelectorMatches(page, "errorBanner");
  const staleCompleteCount = await countSelectorMatches(page, "generationComplete");
  // Politika reddi gibi ANINDA basarisizliklarda Flow ilerleme gostergesi hic
  // gostermez ve kart sayimi da (eski kart yenisiyle degistiginde) artmayabilir.
  // Bu yuzden gorunur hata METNI de baslangictakiyle kiyaslanir.
  const staleFailureText = await collectVisibleErrorText(page);
  if (staleErrorCount > 0 || staleCompleteCount > 0) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Not: onceki denemelerden kalan kartlar var (hata: ${staleErrorCount}, video: ${staleCompleteCount}); yalnizca YENI kartlar dikkate alinacak`,
    });
  }

  while (Date.now() < deadline) {
    assertAutomationContinuing();
    assertFlowPageAlive(page);

    // SPA bazen "son acik varlik" gorunumunu gecikmeli geri getirir; bu tam
    // ekran gorunum video kartlarini DOM'dan gizler ve tamamlanma hic
    // algilanamaz. Her turda kontrol edip kapat (temizken ~1 sn surer).
    // Uretim sirasinda soft: referans/son kare cip'lerini kutuphaneden silme.
    await escapeAssetDetailView(page, project, { mode: "soft" });
    // Ayni sekilde acik kalan medya secim penceresi de kartlari orter.
    await closeStrayDialog(page, project, "video bekleme");

    const elapsed = Date.now() - startedAt;
    const liveFailureText = await collectVisibleErrorText(page);
    if (elapsed >= 12_000 && liveFailureText && liveFailureText !== staleFailureText) {
      const snapshot = await captureDebugSnapshot(page, project.slug, "flow-stuck-resolving");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: isStuckFlowResolvingText(liveFailureText)
          ? `Flow hata-cozme / yeniden-deneme ekraninda takildi: ${liveFailureText.slice(0, 160)}`
          : `Yeni Flow hata metni belirdi (kart sayisi artmasa da): ${liveFailureText.slice(0, 160)}`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw generationFailureError(liveFailureText);
    }
    if (
      elapsed >= STUCK_RESOLVING_MAX_MS &&
      liveFailureText &&
      isStuckFlowResolvingText(liveFailureText)
    ) {
      const snapshot = await captureDebugSnapshot(page, project.slug, "flow-stuck-resolving");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: `Flow hata-cozme ekrani ${Math.round(STUCK_RESOLVING_MAX_MS / 1000)} sn'dir acik — takili kabul edilip yeniden denenecek`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw generationFailureError(liveFailureText);
    }

    const signals = await readCompletionSignals(page);

    const currentErrorCount = await countSelectorMatches(page, "errorBanner");
    if (currentErrorCount > staleErrorCount) {
      const banner = await locatorFor(page, "errorBanner", { selfHeal: false, timeoutMs: 700 });
      const errorText = banner ? ((await banner.textContent().catch(() => "")) ?? "") : "";
      const snapshot = await captureDebugSnapshot(page, project.slug, "flow-error");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: `Yeni Flow hata karti belirdi (${staleErrorCount} -> ${currentErrorCount}): ${errorText.slice(0, 160)}`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw generationFailureError(errorText || "yeni hata karti belirdi");
    }

    // "generationProgress" secicisi ancak GERCEK bir uretim sirasinda DOM'da
    // belirir; oto-kalibrasyon bos sayfada calistirilirsa hicbir zaman
    // ogrenilemez ve progressGone SUREKLI true kalir (55 sn'de yanlis
    // "baslamadi" hatasi). Generate dugmesinin PASIF (devre disi) olmasi da
    // Flow'un isini surdurdugunun guclu ve model-bagimsiz bir kanitidir —
    // asagidaki basarisizlik kontrolu de zaten buna guveniyor.
    if (!progressSeen && (!signals.progressGone || !signals.generateEnabled)) progressSeen = true;

    // Dongu bitti: ilerleme yok + Generate tekrar basilabilir. Yeni video bu
    // pencerede gelmezse saatlerce (veya 420 sn) "Uretim Bekleniyor"da kalma.
    const cycleIdle = progressSeen && signals.progressGone && signals.generateEnabled;
    if (cycleIdle) {
      if (generateCycleEndedAt == null) generateCycleEndedAt = Date.now();
    } else if (!signals.generateEnabled || !signals.progressGone) {
      generateCycleEndedAt = null;
    }

    // Generate kilitli kaldigi halde ilerleme bitmis + hata metni var:
    // eski kart sayaci artmasa da bu deneme olmustur — 420 sn beklemeyelim.
    if (
      knownAssetIds &&
      progressSeen &&
      signals.progressGone &&
      !signals.generateEnabled &&
      elapsed >= 90_000 &&
      liveFailureText
    ) {
      const snapshot = await captureDebugSnapshot(page, project.slug, "flow-error-generate-locked");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: `Uretim bitti gibi (ilerleme yok) ama Generate kilitli ve hata gorunuyor — erken kesildi: ${liveFailureText.slice(0, 140)}`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw generationFailureError(liveFailureText);
    }
    if (
      knownAssetIds &&
      progressSeen &&
      signals.progressGone &&
      !signals.generateEnabled &&
      elapsed >= 120_000
    ) {
      const stillNew = await findNewVideoAssetId(page, knownAssetIds);
      if (!stillNew) {
        const snapshot = await captureDebugSnapshot(page, project.slug, "flow-stuck-generate-locked");
        await recordEvent({
          projectId: project.id,
          step: "flow",
          level: "error",
          message: "Uretim 120 sn'dir Generate kilitli / ilerleme yok / yeni video yok — takili kabul, yeniden denenecek",
          screenshotPath: snapshot.screenshotPath,
          pageUrl: page.url(),
        });
        throw new Error("Uretim takildi (Generate kilitli, yeni video yok). Yeniden denenecek.");
      }
    }

    if (Date.now() >= minWaitUntil) {
      // Tamamlanma gostergesi: SAYIM ARTISI (yeni video karti belirdi).
      // Ilerleme bitti + Generate aktif TEK BASINA yetmez: Flow basarisiz
      // oldugunda da Generate geri gelir ve yanlis "tamamlandi" sanilir.
      const currentCompleteCount = await countSelectorMatches(page, "generationComplete");
      const newCardAppeared = currentCompleteCount > staleCompleteCount;

      // NOT: progressSeen SART DEGIL — politika reddi gibi durumlarda Flow
      // ilerleme gostergesi hic gostermeden dogrudan basarisiz karti basar.
      if (!newCardAppeared && signals.progressGone && signals.generateEnabled) {
        const errorText = await collectVisibleErrorText(page);
        if (errorText && errorText !== staleFailureText) {
          const snapshot = await captureDebugSnapshot(page, project.slug, "flow-error");
          await recordEvent({
            projectId: project.id,
            step: "flow",
            level: "error",
            message: `Flow uretimi basarisiz (yeni video yok, hata metni var): ${errorText.slice(0, 160)}`,
            screenshotPath: snapshot.screenshotPath,
            pageUrl: page.url(),
          });
          throw generationFailureError(errorText);
        }
      }

      // EN GUCLU KANIT: uretim oncesinde olmayan bir video varligi belirdi.
      // Bu kimlik indirme adimina verilir; boylece dogru kartin kendi
      // "Indir" dugmesine basilir (eski/proje geneli arsivi degil).
      if (knownAssetIds) {
        const newAssetId = await findNewVideoAssetId(page, knownAssetIds);
        if (newAssetId) {
          await recordEvent({
            projectId: project.id,
            step: "flow",
            message: `Uretim tamamlandi (yeni video varligi: ${newAssetId.slice(0, 8)})`,
          });
          return newAssetId;
        }
        // Kimlik kiyasi yapilabiliyorsa "video" CSS sayim artisi YETERLI DEGIL —
        // gorsel kart / eski onizleme yanlis tamamlanma uretiyordu (jpeg indirme).
        // Yalnizca ilerleme dongusu asagida kabul edilir.
      } else if (newCardAppeared) {
        await recordEvent({
          projectId: project.id,
          step: "flow",
          message: `Uretim tamamlandi (sinyaller: yeni video karti${progressSeen && signals.progressGone ? ", ilerleme bitti" : ""}${signals.generateEnabled ? ", Generate aktif" : ""})`,
        });
        return null;
      }

      // Dongu bitti, grace doldu, yeni video yok → HATA (eski hata karti
      // sayaci artmasa bile). Eskiden burada "tamamlandi varsay" yapiliyordu
      // ve yanlis/eski video inmeye veya 420 sn beklemeye yol aciyordu.
      if (
        knownAssetIds &&
        generateCycleEndedAt != null &&
        Date.now() - generateCycleEndedAt >= CYCLE_END_GRACE_MS
      ) {
        const errorText = await collectVisibleErrorText(page);
        const snapshot = await captureDebugSnapshot(page, project.slug, "flow-cycle-end-no-video");
        await recordEvent({
          projectId: project.id,
          step: "flow",
          level: "error",
          message: errorText
            ? `Uretim dongusu bitti, yeni video yok — hata/sessiz dusme (${Math.round(CYCLE_END_GRACE_MS / 1000)} sn grace): ${errorText.slice(0, 140)}`
            : `Uretim dongusu bitti ama ${Math.round(CYCLE_END_GRACE_MS / 1000)} sn icinde yeni video olusmadi — yeniden denenecek`,
          screenshotPath: snapshot.screenshotPath,
          pageUrl: page.url(),
        });
        throw generationFailureError(
          errorText || "Uretim dongusu bitti ama yeni video olusmadi (sessiz dusme). Yeniden denenecek."
        );
      }

      // Varlik kimligi yoksa: ilerleme dongusu + hata yok → tamamlandi varsay.
      if (!knownAssetIds && progressSeen && signals.progressGone && signals.generateEnabled) {
        const errorText = await collectVisibleErrorText(page);
        if (!errorText || errorText === staleFailureText) {
          await recordEvent({
            projectId: project.id,
            step: "flow",
            message: "Uretim tamamlandi (ilerleme dongusu bitti; kart sayimi sanal liste nedeniyle artmadi)",
          });
          return null;
        }
      }

      // Medya listesi SANALLASTIRILMIS: gorunur pencere doluyken yeni kart
      // eskisini DOM disina iter ve sayim hic artmaz. Bu durumda guvenilir
      // sinyal ILERLEME DONGUSUDUR — yalnizca varlik kimligi YOKKEN.
      if (!knownAssetIds && Date.now() - startedAt >= 150_000 && signals.progressGone && signals.generateEnabled) {
        const errorText = await collectVisibleErrorText(page);
        if (!errorText || errorText === staleFailureText) {
          await recordEvent({
            projectId: project.id,
            step: "flow",
            message: "Uretim tamamlandi varsayiliyor (150 sn gecti, hata izi yok, varlik kimligi kiyasi yapilamiyor)",
          });
          return null;
        }
      }
    }

    // 9:16 + 10s / sessiz red: ilerleme hic gelmez, 420 sn "Uretim Bekleniyor"da kalinmaz.
    if (elapsed >= 55_000 && !progressSeen && knownAssetIds) {
      const snapshot = await captureDebugSnapshot(page, project.slug, "flow-no-progress");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: `Uretim 55 sn'de ilerlemedi (yeni video yok). 9:16 short 10s veya yanlis modelde Flow sessizce duser.`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw new Error(
        "Uretim 55 saniyede baslamadi (ilerleme yok, yeni video yok). 9:16 short'ta sure 8s ve model Veo 3.1 Fast olmali; 10s'de Flow video uretmez."
      );
    }

    await interruptibleSleep(settings.pollIntervalMs);
  }

  const seconds = Math.round(settings.generationTimeoutMs / 1000);
  const detail = knownAssetIds
    ? " Sure boyunca YENI bir video varligi olusmadi: uretim ya hic baslamadi ya da video yerine baska bir cikti (or. gorsel) uretildi. Referans gorsel yuklendikten sonra cikti turunun 'Video' kaldigini kontrol edin."
    : "";
  const snapshot = await captureDebugSnapshot(page, project.slug, "generation-timeout");
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "error",
    message: `Uretim zaman asimi (${seconds} sn).${detail}`,
    screenshotPath: snapshot.screenshotPath,
    pageUrl: page.url(),
  });
  throw new Error(`Uretim zaman asimina ugradi (${seconds} saniye).${detail}`);
}

async function readCompletionSignals(page: Page): Promise<CompletionSignals> {
  const signals: CompletionSignals = {
    completeIndicator: false,
    progressGone: true,
    generateEnabled: false,
    errorVisible: false,
    errorText: "",
  };

  // Sinyal okumalarinda kendini onarma kapali: bir ogenin YOKLUGU da anlamli
  // bir bilgidir, bu yuzden yedek aday promosyonu yapilmamalidir.
  const signalOptions = { selfHeal: false, timeoutMs: 700 };

  const complete = await locatorFor(page, "generationComplete", signalOptions);
  signals.completeIndicator = complete !== null;

  const progress = await locatorFor(page, "generationProgress", signalOptions);
  signals.progressGone = progress === null;

  const generateButton = await locatorFor(page, "generateButton", signalOptions);
  if (generateButton) {
    signals.generateEnabled = await generateButton.isEnabled({ timeout: 700 }).catch(() => false);
  }

  // Hata tespiti burada YAPILMAZ: bayat kartlara takilmamak icin
  // waitForCompletion icindeki sayim bazli kontrol kullanilir.

  return signals;
}

/**
 * Belirli bir video varliginin KENDI kartindaki indirme dugmesini bulur.
 * Flow'un guncel arayuzunde her tamamlanmis klip kartinda dogrudan bir "Indir"
 * dugmesi vardir; uc nokta menusune gerek yoktur.
 *
 * Video, kart icinde derin bir zincirin (oynat dugmesi > baglanti > sarmalayici
 * div'ler) sonunda durur; kartin eylem cubugu bu zincirin ~15 kademe ustundedir.
 * Bu yuzden yukari dogru cikilir, ancak ata BIRDEN FAZLA video icermeye
 * baslarsa durulur: aksi halde komsu klibin dugmesine basilir ve yanlis
 * (eski) video inerdi.
 */
export async function cardDownloadButtonFor(page: Page, assetId: string): Promise<Locator | null> {
  const video = page.locator(`video[src*="${assetId}"]`).first();
  if ((await video.count().catch(() => 0)) === 0) return null;

  for (let up = 1; up <= 18; up++) {
    const ancestor = video.locator(`xpath=${Array(up).fill("..").join("/")}`);
    if ((await ancestor.count().catch(() => 0)) === 0) return null;
    // Kart sinirini astik mi? (ata artik birden fazla klip iceriyor)
    if ((await ancestor.locator("video").count().catch(() => 0)) > 1) return null;

    const button = ancestor.locator("button").filter({ hasText: /download|[iİ]ndir/i }).first();
    if (await button.isVisible({ timeout: 300 }).catch(() => false)) return button;
  }
  return null;
}

/** Ureyen videoyu indirir ve hedef yola kaydeder. */
export async function downloadClipVideo(
  page: Page,
  project: Project,
  targetPath: string,
  newAssetId?: string | null
): Promise<string> {
  // Kartin ve dugmelerin yerlesmesi icin kisa sure bekle
  await page.waitForTimeout(1_500);

  const downloadPromise = page.waitForEvent("download", { timeout: 120_000 });
  let clickedCardButton = false;

  // 1) TERCIH EDILEN YOL: yeni uretilen varligin KENDI kartindaki "Indir".
  //    Sayfa/proje seviyesindeki menuler ("Diger secenekler" -> "Projeyi
  //    indir") her seferinde AYNI eski arsivi verdigi icin once bu denenir.
  if (newAssetId) {
    const cardButton = await cardDownloadButtonFor(page, newAssetId);
    if (cardButton) {
      await cardButton.click({ timeout: 5_000 }).catch(() => {});
      clickedCardButton = true;
      await recordEvent({
        projectId: project.id,
        step: "download",
        message: `Yeni uretilen klibin kendi indirme dugmesine basildi (varlik: ${newAssetId.slice(0, 8)})`,
      });
    } else {
      await recordEvent({
        projectId: project.id,
        step: "download",
        level: "warning",
        message: `Yeni varligin karti bulunamadi (${newAssetId.slice(0, 8)}); menu yoluna dusuluyor`,
      });
    }
  }

  // 2) YEDEK YOL: kart dugmesi yoksa eski menu akisi (uc nokta -> Indir).
  if (!clickedCardButton) {
    const assetMenu = await resolveAssetMenuButton(page);
    if (!assetMenu) throw new SelectorMissingError("assetMenuButton");
    await assetMenu.click();
    await page.waitForTimeout(700);

    const downloadItem = await resolveDownloadMenuItem(page);
    if (!downloadItem) throw new SelectorMissingError("downloadMenuItem");
    await downloadItem.click();
  }

  // Kalite alt menusu: birkac saniye boyunca yokla; gorunuyorsa tikla.
  // Gorunmuyorsa indirme dogrudan baslamis demektir.
  const qualityDeadline = Date.now() + 6_000;
  while (Date.now() < qualityDeadline) {
    const videoItem = await locatorFor(page, "downloadVideoItem", { selfHeal: false, timeoutMs: 800 });
    if (videoItem) {
      await videoItem.click().catch(() => {});
      await recordEvent({ projectId: project.id, step: "download", message: "Indirme kalitesi secildi" });
      break;
    }
    await page.waitForTimeout(800);
  }

  const download = await downloadPromise;
  const suggested = download.suggestedFilename();

  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  const finalPath = nextAvailablePath(targetPath);
  await download.saveAs(finalPath);

  const failure = await download.failure();
  if (failure) throw new Error(`Indirme basarisiz: ${failure}`);

  // Flow videolari ZIP arsivi icinde teslim eder; icindeki MP4 cikarilir
  await extractVideoIfArchive(finalPath, project.id);

  await recordEvent({ projectId: project.id, step: "download", message: `Video indirildi: ${path.basename(finalPath)} (kaynak: ${suggested})` });
  return finalPath;
}

/* -------------------------------------------------------------------------
 * GORSEL MODU (Nano Banana 2)
 *
 * Flow, prompt cubugundaki cikti turu menusunden gorsel uretimine gecebilir
 * (Nano Banana 2). Karakter referans gorselleri icin bu mod video uretiminden
 * ustundur: dogrudan net bir kare verir, video kredisi harcamaz ve hareket
 * bulanikligi tasimaz. Tum Flow gorsel uretimlerinde Pro DEGIL, 2 kullanilir.
 * ------------------------------------------------------------------------- */

/** Flow'da gorsel uretilirken secilecek model (Nano Banana Pro DEGIL). */
export const FLOW_IMAGE_MODEL = "Nano Banana 2";

function isPreferredImageModel(label: string, wanted: string = FLOW_IMAGE_MODEL): boolean {
  return imageModelNamesMatch(label, wanted);
}

async function clickWantedImageModelOption(page: Page, wanted: string): Promise<boolean> {
  const items = page.getByRole("menuitem");
  const count = await items.count().catch(() => 0);
  for (let i = 0; i < count; i++) {
    const item = items.nth(i);
    const text = (await item.textContent().catch(() => "")) ?? "";
    if (imageModelNamesMatch(text, wanted)) {
      await item.click().catch(() => {});
      return true;
    }
  }
  const option = page.getByRole("option").filter({ hasText: new RegExp(escapeRegExp(wanted), "i") }).last();
  if (await option.isVisible({ timeout: 800 }).catch(() => false)) {
    await option.click().catch(() => {});
    return true;
  }
  const byText = page.getByText(new RegExp(escapeRegExp(wanted), "i")).last();
  if (await byText.isVisible({ timeout: 1_200 }).catch(() => false)) {
    await byText.click().catch(() => {});
    return true;
  }
  return false;
}

/**
 * Prompt cubugundaki cikti turunu degistirir (video <-> gorsel).
 * Menu veya secenek bulunamazsa false doner; cagiran taraf eski yonteme duser.
 */
export async function switchOutputType(page: Page, project: Project, target: "image" | "video"): Promise<boolean> {
  // Karakterler / tam ekran varlik alt sayfalarinda cikti turu menusu YOKTUR.
  // Guard olmadan menu "bulunamadi" sayilir ve cagiran taraf yanlis moda
  // (or. karakter icin video) duser — goruntu/video karismasinin ana nedeni.
  if (isCharactersPageUrl(page.url())) {
    await ensureProjectComposer(page, project).catch(() => {});
  }

  const menu = await locatorFor(page, "outputTypeMenu");
  if (!menu || !(await menu.isVisible({ timeout: 2_500 }).catch(() => false))) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message:
        target === "image"
          ? "Cikti turu menusu bulunamadi (kalibrasyon: 'Cikti turu menusu'). Gorsel moduna gecilemiyor."
          : "Cikti turu menusu bulunamadi; ozet Video ise mevcut video modu korunacak.",
    });
    return false;
  }
  await menu.click();
  await page.waitForTimeout(500);

  const optionKey = target === "image" ? "imageModeOption" : "videoModeOption";
  const option = await locatorFor(page, optionKey, { timeoutMs: 1_500 });
  if (!option) {
    await page.keyboard.press("Escape").catch(() => {});
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: `Cikti turu menusunde ${target === "image" ? "gorsel" : "video"} secenegi bulunamadi; mevcut mod korundu`,
    });
    return false;
  }
  await option.click();
  await page.waitForTimeout(700);
  await recordEvent({
    projectId: project.id,
    step: "flow",
    message: `Cikti turu degistirildi: ${target === "image" ? "gorsel uretimi (Nano Banana)" : "video uretimi (Veo)"}`,
  });
  return true;
}

/**
 * Gorsel modunda model menusunden istenen Nano Banana modelini secer.
 * Karakter uretimi varsayilan olarak Nano Banana 2 (Pro degil).
 * Menu yoksa Flow'un o anki gorsel modeli kullanilir.
 */
export async function selectImageModel(page: Page, project: Project, wantedModel = FLOW_IMAGE_MODEL): Promise<void> {
  const wanted = wantedModel.trim() || FLOW_IMAGE_MODEL;
  const menu = await locatorFor(page, "modelMenu");
  if (!menu || !(await menu.isVisible({ timeout: 2_000 }).catch(() => false))) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Model menusu bulunamadi; Flow'daki mevcut gorsel modeli kullanilacak",
    });
    return;
  }
  const currentText = ((await menu.textContent().catch(() => "")) ?? "").trim();
  if (isPreferredImageModel(currentText, wanted)) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Gorsel modeli zaten ${wanted}`,
    });
    return;
  }
  await menu.click();
  await page.waitForTimeout(400);
  if (await clickWantedImageModelOption(page, wanted)) {
    await page.waitForTimeout(300);
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Gorsel modeli secildi: ${wanted}`,
    });
    return;
  }
  await page.keyboard.press("Escape").catch(() => {});
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Model menusunde "${wanted}" bulunamadi; mevcut secim korundu`,
  });
}

/**
 * Prompt cubugunun bulundugu proje editorune doner.
 *
 * Karakterler sayfasi (.../project/<id>/characters) proje adresiyle AYNI
 * onekle basladigi icin openFlowProject orada hicbir sey yapmaz; o sayfada
 * prompt cubugu ve cikti turu menusu yoktur. Alt sayfa adresi kirpilip
 * editorun yuklenmesi beklenir.
 */
export async function ensureProjectComposer(page: Page, project: Project): Promise<void> {
  const url = page.url();
  const projectRoot = url.match(/^(.*\/project\/[0-9a-f][0-9a-f-]{7,})/i)?.[1];
  if (projectRoot && url.length > projectRoot.length && !url.startsWith(`${projectRoot}?`)) {
    await page.goto(projectRoot, { waitUntil: "domcontentloaded" }).catch(() => {});
    await page.waitForTimeout(1_800);
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Proje editorune donuldu (alt sayfadan cikildi: ${url.slice(projectRoot.length).slice(0, 32)})`,
    });
  }
  await ensureEditorReady(page, project);
}

/** Ayarlar panelindeki gorsel sekmesi (cikti turu menusu bulunamazsa yedek). */
async function clickImageTabInSettingsPanel(page: Page, project: Project): Promise<boolean> {
  if (!(await openGenerationSettingsPanel(page, project))) return false;
  const tabs = page.getByRole("tab");
  const count = await tabs.count().catch(() => 0);
  for (let i = 0; i < count; i++) {
    const tab = tabs.nth(i);
    const text = ((await tab.textContent().catch(() => "")) ?? "").trim();
    if (!text || /video|videocam/i.test(text)) continue;
    if (!/image|photo|resim|g[oö]r[uü]nt[uü]/i.test(text)) continue;
    if ((await tab.getAttribute("aria-checked").catch(() => null)) !== "true") {
      await tab.click().catch(() => {});
      await page.waitForTimeout(600);
    }
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Cikti turu ayarlar panelinden gorsel yapildi (${text.slice(0, 32)})`,
    });
    return true;
  }
  return false;
}

/**
 * Ciktinin GORSEL olacagini garanti eder: cikti turu menusu, olmazsa ayarlar
 * panelindeki gorsel sekmesi. Zaten gorsel modundaysa dokunmaz.
 */
export async function ensureImageOutputMode(page: Page, project: Project): Promise<boolean> {
  // Alt sayfada cikti turu etiketi okunamaz; once prompt cubuguna don.
  if (isCharactersPageUrl(page.url())) {
    await ensureProjectComposer(page, project).catch(() => {});
  }
  if (isImageOutputModeLabel(await readOutputModeLabel(page))) return true;
  if (await switchOutputType(page, project, "image")) {
    if (isImageOutputModeLabel(await readOutputModeLabel(page))) return true;
  }
  if (await clickImageTabInSettingsPanel(page, project)) {
    await dismissOverlaysBlockingPrompt(page, project, "gorsel sekmesi sonrasi");
    return isImageOutputModeLabel(await readOutputModeLabel(page));
  }
  return false;
}

/**
 * Iki kare arasinda kompozisyon cubugunu TEMIZ "metinden goruntuye" durumuna
 * dondurur.
 *
 * Flow, uretilen kareyi otomatik secip prompt cubugunu Nano Banana DUZENLEME
 * kutusuna ("Neyi degistirmek istiyorsun?") cevirebiliyor. O kutu yeni kare
 * uretmez; seri uretim ikinci karede takilir. Cikti turu menusunden gorsel
 * modunu yeniden secmek bu durumu sifirlar; olmazsa proje adresine donulur.
 */
export async function resetImageComposer(page: Page, project: Project, imageModel?: string): Promise<void> {
  await escapeAssetDetailView(page, project, { mode: "soft" });
  await page.keyboard.press("Escape").catch(() => {});
  await page.waitForTimeout(300);

  if (await findPromptInput(page, project.id)) {
    if (isImageOutputModeLabel(await readOutputModeLabel(page))) return;
  }

  // Cikti turunu yeniden sec: duzenleme kutusundan uretim kutusuna dondurur.
  await switchOutputType(page, project, "image").catch(() => {});
  await page.waitForTimeout(400);
  if ((await findPromptInput(page, project.id)) && isImageOutputModeLabel(await readOutputModeLabel(page))) return;

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: "Gorsel istem kutusu temiz degil (duzenleme moduna kaymis olabilir); proje editoru yeniden yukleniyor",
  });
  await ensureProjectComposer(page, project);
  if (!(await ensureImageOutputMode(page, project))) {
    throw new Error("Flow gorsel modu korunamadi; sonraki kare uretilemedi");
  }
  if (imageModel) await selectImageModel(page, project, imageModel);
}

/**
 * Gorsel slayt / Nano Banana: cikti turu + model + 16:9.
 * Karakter uretimindeki gorsel moda gecisten bagimsiz; istenen model adi verilir.
 */
export async function configureImageGeneration(page: Page, project: Project, imageModel: string): Promise<void> {
  // Karakterler gibi alt sayfalarda prompt cubugu yok; once editore don.
  await ensureProjectComposer(page, project);

  if (!(await ensureImageOutputMode(page, project))) {
    throw new Error(
      `Flow'da gorsel modu acilamadi (Metinden goruntuye / Nano Banana). Chrome'da projenin ANA editor sayfasinda olun (Karakterler / tam ekran gorsel sayfasi degil), sonra tekrar deneyin. Cozulmezse Ayarlar > Secici Kilavuzu'ndan "Cikti turu menusu" ve "Gorsel uretim modu" secicilerini kalibre edin. Simdiki adres: ${page.url()}`
    );
  }

  await selectImageModel(page, project, imageModel);
  const panelOpen = await openGenerationSettingsPanel(page, project);
  if (panelOpen) {
    await selectSettingsTab(page, project, project.aspectRatio || "16:9", "En-boy orani");
    await selectSettingsTab(page, project, "x1", "Cikti sayisi");
  }
  await dismissOverlaysBlockingPrompt(page, project, "gorsel ayarlari sonrasi");
}

/**
 * Gorsel uretiminin tamamlanmasini bekler.
 * Video beklemesinden farki: "generationComplete" secicisi video kartina
 * kalibre edilmis olabilir. Gorselde en guvenilir sinyal, varlik menusu
 * dugmesi (assetMenuButton) sayisinin ARTMASIDIR; video karti sayimi da
 * yedek sinyal olarak kabul edilir.
 */
export async function waitForImageCompletion(page: Page, project: Project): Promise<void> {
  const settings = await getSettings();
  const startedAt = Date.now();
  const deadline = startedAt + settings.generationTimeoutMs;
  // Gorsel uretimi videodan cok daha hizlidir; kisa bir asgari bekleme yeterli
  const minWaitUntil = startedAt + 5_000;

  const staleErrorCount = await countSelectorMatches(page, "errorBanner");
  const staleAssetCount = await countSelectorMatches(page, "assetMenuButton");
  const staleCompleteCount = await countSelectorMatches(page, "generationComplete");
  let progressSeen = false;

  while (Date.now() < deadline) {
    assertAutomationContinuing();
    assertFlowPageAlive(page);
    const currentErrorCount = await countSelectorMatches(page, "errorBanner");
    if (currentErrorCount > staleErrorCount) {
      const banner = await locatorFor(page, "errorBanner", { selfHeal: false, timeoutMs: 700 });
      const errorText = banner ? ((await banner.textContent().catch(() => "")) ?? "") : "";
      const snapshot = await captureDebugSnapshot(page, project.slug, "flow-image-error");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: `Gorsel uretiminde hata karti belirdi: ${errorText.slice(0, 160)}`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw generationFailureError(errorText || "hata karti belirdi");
    }

    const progress = await locatorFor(page, "generationProgress", { selfHeal: false, timeoutMs: 600 });
    if (progress) progressSeen = true;

    if (Date.now() >= minWaitUntil) {
      const assetCount = await countSelectorMatches(page, "assetMenuButton");
      const completeCount = await countSelectorMatches(page, "generationComplete");
      if (assetCount > staleAssetCount || completeCount > staleCompleteCount) {
        await recordEvent({ projectId: project.id, step: "flow", message: "Gorsel uretimi tamamlandi (yeni varlik karti belirdi)" });
        return;
      }
      // Ilerleme gorunup bittiyse ve yeni kart yoksa hata metni ariyoruz
      if (progressSeen && !progress) {
        const errorText = await collectVisibleErrorText(page);
        if (errorText) {
          const snapshot = await captureDebugSnapshot(page, project.slug, "flow-image-error");
          await recordEvent({
            projectId: project.id,
            step: "flow",
            level: "error",
            message: `Gorsel uretimi basarisiz gorunuyor: ${errorText.slice(0, 160)}`,
            screenshotPath: snapshot.screenshotPath,
            pageUrl: page.url(),
          });
          throw new Error(`Flow gorsel uretim hatasi: ${errorText.slice(0, 200)}`);
        }
      }
    }
    await interruptibleSleep(settings.pollIntervalMs);
  }

  const snapshot = await captureDebugSnapshot(page, project.slug, "image-generation-timeout");
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "error",
    message: `Gorsel uretimi zaman asimi (${Math.round(settings.generationTimeoutMs / 1000)} sn)`,
    screenshotPath: snapshot.screenshotPath,
    pageUrl: page.url(),
  });
  throw new Error(`Gorsel uretimi zaman asimina ugradi (${Math.round(settings.generationTimeoutMs / 1000)} saniye)`);
}

/** Ureyen gorseli indirir ve hedef yola kaydeder. */
export async function downloadImageAsset(page: Page, project: Project, targetPath: string): Promise<string> {
  await page.waitForTimeout(1_200);

  const assetMenu = await resolveAssetMenuButton(page);
  if (!assetMenu) throw new SelectorMissingError("assetMenuButton");
  await assetMenu.click();
  await page.waitForTimeout(700);

  const downloadItem = await resolveDownloadMenuItem(page);
  if (!downloadItem) throw new SelectorMissingError("downloadMenuItem");

  const downloadPromise = page.waitForEvent("download", { timeout: 120_000 });
  await downloadItem.click();

  // Boyut/kalite alt menusu acilirsa kisa sure yokla ve ilk uygun ogeyi tikla
  const subMenuDeadline = Date.now() + 4_000;
  while (Date.now() < subMenuDeadline) {
    const sizeItem = await locatorFor(page, "downloadVideoItem", { selfHeal: false, timeoutMs: 700 });
    if (sizeItem) {
      await sizeItem.click().catch(() => {});
      break;
    }
    await page.waitForTimeout(700);
  }

  const download = await downloadPromise;
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  const finalPath = nextAvailablePath(targetPath);
  await download.saveAs(finalPath);

  const failure = await download.failure();
  if (failure) throw new Error(`Gorsel indirme basarisiz: ${failure}`);

  await extractImageIfArchive(finalPath, project.id);
  await recordEvent({ projectId: project.id, step: "download", message: `Gorsel indirildi: ${path.basename(finalPath)}` });
  return finalPath;
}

/** Indirilen gorsel ZIP arsivindeyse icindeki en buyuk gorseli cikarir. */
async function extractImageIfArchive(filePath: string, projectId: string): Promise<void> {
  const header = Buffer.alloc(4);
  const fd = fs.openSync(filePath, "r");
  try {
    fs.readSync(fd, header, 0, 4, 0);
  } finally {
    fs.closeSync(fd);
  }
  const isZip = header[0] === 0x50 && header[1] === 0x4b && header[2] === 0x03 && header[3] === 0x04;
  if (!isZip) return;

  const zip = new AdmZip(filePath);
  const imageEntries = zip
    .getEntries()
    .filter((entry) => !entry.isDirectory && /\.(png|jpe?g|webp)$/i.test(entry.entryName))
    .sort((a, b) => b.header.size - a.header.size);

  if (imageEntries.length === 0) {
    const names = zip
      .getEntries()
      .map((entry) => entry.entryName)
      .slice(0, 10)
      .join(", ");
    throw new Error(`Indirilen ZIP icinde gorsel dosyasi yok (icerik: ${names})`);
  }

  const chosen = imageEntries[0];
  const data = chosen.getData();
  const tempPath = `${filePath}.extract`;
  fs.writeFileSync(tempPath, data);
  fs.rmSync(filePath);
  fs.renameSync(tempPath, filePath);
  await recordEvent({
    projectId,
    step: "download",
    message: `ZIP arsivi acildi; gorsel cikarildi: ${chosen.entryName} (${(data.length / 1024).toFixed(0)} KB)`,
  });
}

/* -------------------------------------------------------------------------
 * KARAKTERLER SAYFASI (.../project/<id>/characters)
 *
 * Flow 2026: tam sayfa karakter editoru (dialog degil).
 *  1) Sol menude Karakterler
 *  2) Bos kadroda prompt kutusu ZATEN acik ("Yeni karakter" dugmesi yok)
 *     — kadro varsa "Yeni karakter" / person_add
 *  3) Prompt cubuguna tarif yaz, Generate (arrow_forward)
 *  4) Gorsel gelince adi doldur, sag ustte Bitti / Done
 *
 * Genel medya prompt cubugu video uretir; @ad referansi icin dogru yer burasi.
 * ------------------------------------------------------------------------- */

function isCharactersPageUrl(url: string): boolean {
  return /\/project\/[0-9a-f][0-9a-f-]{7,}\/characters(?:\/|$|\?)/i.test(url);
}

/**
 * Su an bu projenin editorunde miyiz (Flow ana sayfasi / baska proje degil)?
 * "Goruntu duzenleme kapat" kurtarmalari bazen genel bir "geri" dugmesine
 * basip projeden tamamen cikartiyor (bkz. isOffProjectPage kullanim yerleri) —
 * bu kontrol o durumu netlestirir.
 */
function isOnExpectedProjectPage(page: Page, project: Project): boolean {
  const url = page.url();
  const expected = project.flowProjectUrl?.trim();
  if (expected) return url.startsWith(expected);
  return /\/project\/[0-9a-f][0-9a-f-]{7,}/i.test(url);
}

/** Acik diyalog / hata kartini kapatip Karakterler sayfasini temizler. */
export async function dismissFlowOverlays(page: Page): Promise<void> {
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(250);
  }
}

/** Acik projenin Karakterler sayfasina gider. */
export async function openCharactersPage(page: Page, project: Project, options?: { forceReload?: boolean }): Promise<boolean> {
  const url = page.url();
  const match = url.match(/^(.*\/project\/[0-9a-f][0-9a-f-]{7,})/i);
  if (match) {
    const target = `${match[1]}/characters`;
    if (options?.forceReload || !url.startsWith(target)) {
      await dismissFlowOverlays(page);
      await page.goto(target, { waitUntil: "domcontentloaded" }).catch(() => {});
      await page.waitForTimeout(1_800);
    }
    if (page.url().includes("/characters")) {
      // ADRES YETMIYOR: Flow /characters adresinde bile sol menude "Tum Medya"
      // sekmesinde kalabiliyor; o panelde karakter editoru yoktur.
      await activateCharactersTab(page);
      await waitForCharactersWorkspace(page);
      const snapshot = await captureDebugSnapshot(page, project.slug, "characters-page");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        message: "Karakterler sayfasi acildi",
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      return true;
    }
  }

  // Yedek: sol menude "Karakterler" sekmesi/baglantisi
  const navCandidates = [
    page.getByRole("link", { name: /karakterler|characters/i }).first(),
    page.getByRole("tab", { name: /karakterler|characters/i }).first(),
    page.getByRole("button", { name: /karakterler|characters/i }).first(),
  ];
  for (const nav of navCandidates) {
    if (await nav.isVisible({ timeout: 1_200 }).catch(() => false)) {
      await nav.click().catch(() => {});
      await page.waitForTimeout(1_800);
      if (page.url().includes("/characters") || (await findCharacterPromptInput(page)) || (await findNewCharacterButton(page))) {
        await waitForCharactersWorkspace(page);
        await recordEvent({ projectId: project.id, step: "flow", message: "Karakterler sayfasi acildi (menu uzerinden)" });
        return true;
      }
    }
  }

  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message:
      "Karakterler sayfasina gecilemedi: proje adresi cozumlenemedi ve menude 'Karakterler' baglantisi bulunamadi. Once Flow'da projeyi acin.",
  });
  return false;
}

/** Karakterler sayfasindan proje editorune geri doner. */
export async function returnToProjectEditor(page: Page, project: Project): Promise<void> {
  const url = page.url();
  if (!url.includes("/characters")) return;
  const target = url.replace(/\/characters.*$/, "");
  await page.goto(target, { waitUntil: "domcontentloaded" }).catch(() => {});
  await page.waitForTimeout(1_200);
  await recordEvent({ projectId: project.id, step: "flow", message: "Proje editorune geri donuldu" });
}

/** Sayfadaki tum gorsel adreslerinin anlik fotografini alir (oncesi/sonrasi kiyasi icin). */
export async function snapshotImageSources(page: Page): Promise<Set<string>> {
  const sources = await page
    .evaluate(() =>
      Array.from(document.querySelectorAll("img"))
        .map((img) => (img as HTMLImageElement).currentSrc || (img as HTMLImageElement).src)
        .filter(Boolean)
    )
    .catch(() => [] as string[]);
  return new Set(sources);
}

/**
 * Sol menudeki "Karakterler" sekmesini etkinlestirir.
 *
 * Flow'un medya kitapligi tek sayfada sekmelidir (Tum Medya / Karakterler /
 * Sahneler). /characters adresine gitmek sekmeyi HER ZAMAN degistirmiyor —
 * "Tum Medya" secili kalirsa karakter olusturma arayuzu hic gorunmez.
 */
async function activateCharactersTab(page: Page): Promise<boolean> {
  const label = /^\s*(karakterler|characters)\s*$/i;
  const candidates: Locator[] = [
    page.getByRole("tab", { name: label }).first(),
    page.getByRole("button", { name: label }).first(),
    page.getByRole("link", { name: label }).first(),
    page.getByRole("listitem").filter({ hasText: label }).first(),
    page.getByText(label).first(),
  ];
  for (const candidate of candidates) {
    if (!(await candidate.isVisible({ timeout: 800 }).catch(() => false))) continue;
    // Zaten secili ise tiklamaya gerek yok
    const selected = await candidate
      .evaluate((el) => {
        const node = el as HTMLElement;
        const aria = node.getAttribute("aria-selected") ?? node.getAttribute("aria-current");
        if (aria === "true" || aria === "page") return true;
        return /active|selected/i.test(node.className || "");
      })
      .catch(() => false);
    if (selected) return true;
    await candidate.click({ timeout: 3_000 }).catch(async () => {
      await candidate.click({ force: true }).catch(() => {});
    });
    await page.waitForTimeout(1_200);
    return true;
  }
  return false;
}

const CHAR_NEW_BUTTON = /yeni karakter|karakter olu[sş]tur|karakter ekle|new character|create character|add character|person_add/i;
const CHAR_PROMPT_HINT = /karakter|character|tarif|describe|tan[iı]mla|ne olu[sş]turmak|what do you want to create|tasarla/i;
const CHAR_EDIT_HINT = /neyi de[gğ]i[sş]tirmek istiyorsun|what (do you want|would you like) to change/i;
const CHAR_DONE = /^(bitti|done|kaydet|save|tamam)$/i;

/** Bos kadro (prompt acik) veya "Yeni karakter" dugmesi gelene kadar bekler. */
async function waitForCharactersWorkspace(page: Page, timeoutMs = 8_000): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await findCharacterPromptInput(page)) return true;
    if (await findNewCharacterButton(page)) return true;
    await page.waitForTimeout(400);
  }
  return false;
}

async function isUsableCharacterBox(candidate: Locator, allowEditHint: boolean): Promise<boolean> {
  try {
    if (!(await candidate.isVisible({ timeout: 400 }).catch(() => false))) return false;
    const box = await candidate.boundingBox().catch(() => null);
    if (!box || box.width < 120 || box.height < 14) return false;
    const meta = await candidate
      .evaluate((el) => {
        const style = window.getComputedStyle(el);
        const zNum = Number(style.zIndex);
        return {
          zIsNegative: Number.isFinite(zNum) && zNum < 0,
          pointerEvents: style.pointerEvents,
          ariaHidden: el.getAttribute("aria-hidden"),
          text: (el.textContent || "").replace(/\uFEFF/g, "").trim().slice(0, 160),
          placeholder: el.getAttribute("placeholder") || el.getAttribute("data-placeholder") || "",
        };
      })
      .catch(() => null);
    if (!meta) return false;
    if (meta.ariaHidden === "true" || meta.pointerEvents === "none" || meta.zIsNegative) return false;
    if (!allowEditHint && (CHAR_EDIT_HINT.test(meta.text) || CHAR_EDIT_HINT.test(meta.placeholder))) return false;
    return true;
  } catch {
    return false;
  }
}

/** Karakter editorundeki tarif / prompt cubugunu bulur (dialog sart degil). */
async function findCharacterPromptInput(page: Page, allowEditHint = false): Promise<Locator | null> {
  const nearGenerate = composerRoot(page).locator("[contenteditable='true'], textarea").first();
  if (await isUsableCharacterBox(nearGenerate, allowEditHint)) return nearGenerate;

  const byHint = page.locator("[contenteditable='true'], textarea").filter({ hasText: CHAR_PROMPT_HINT }).first();
  if (await isUsableCharacterBox(byHint, allowEditHint)) return byHint;

  const calibrated = await locatorFor(page, "characterDescriptionInput", { timeoutMs: 700 });
  if (calibrated && (await isUsableCharacterBox(calibrated, allowEditHint))) return calibrated;

  const all = page.locator("[contenteditable='true'], textarea, [role='textbox']");
  const count = await all.count().catch(() => 0);
  for (let i = 0; i < Math.min(count, 16); i++) {
    const candidate = all.nth(i);
    if (await isUsableCharacterBox(candidate, allowEditHint)) return candidate;
  }
  return null;
}

async function waitForCharacterPrompt(page: Page, timeoutMs = 10_000): Promise<Locator | null> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const input = await findCharacterPromptInput(page);
    if (input) return input;
    await page.waitForTimeout(400);
  }
  return null;
}

async function findNewCharacterButton(page: Page): Promise<Locator | null> {
  const calibrated = await locatorFor(page, "characterNewButton", { timeoutMs: 700 });
  if (calibrated) return calibrated;

  const candidates: Locator[] = [
    page.getByRole("button", { name: CHAR_NEW_BUTTON }).first(),
    page.getByRole("link", { name: CHAR_NEW_BUTTON }).first(),
    page.locator("button", { hasText: CHAR_NEW_BUTTON }).first(),
    page.locator("[role='button']", { hasText: CHAR_NEW_BUTTON }).first(),
    page.getByText(/person_add/i).first(),
  ];
  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 500 }).catch(() => false)) return candidate;
  }
  return null;
}

async function resolveNewCharacterButton(page: Page): Promise<Locator | null> {
  await activateCharactersTab(page);
  return findNewCharacterButton(page);
}

async function chooseCharacterImageModel(page: Page, project: Project, scope: Page | Locator): Promise<void> {
  const modelTrigger = scope.getByText(/nano ?banana/i).first();
  if (!(await modelTrigger.isVisible({ timeout: 800 }).catch(() => false))) return;
  const currentLabel = ((await modelTrigger.textContent().catch(() => "")) ?? "").trim();
  if (isPreferredImageModel(currentLabel)) return;
  await modelTrigger.click().catch(() => {});
  await page.waitForTimeout(400);
  if (await clickWantedImageModelOption(page, FLOW_IMAGE_MODEL)) {
    await page.waitForTimeout(300);
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Karakter modeli ${FLOW_IMAGE_MODEL} olarak secildi`,
    });
    return;
  }
  await page.keyboard.press("Escape").catch(() => {});
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Karakter model listesinde ${FLOW_IMAGE_MODEL} bulunamadi; Pro'ya dusulmedi`,
  });
}

async function fillCharacterPrompt(page: Page, input: Locator, description: string): Promise<boolean> {
  await input.click({ timeout: 3_000 }).catch(async () => {
    await input.click({ force: true }).catch(() => {});
  });
  const filled = await input
    .fill(description)
    .then(() => true)
    .catch(() => false);
  if (!filled) {
    await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A").catch(() => {});
    await page.keyboard.press("Delete").catch(() => {});
    await page.keyboard.insertText(description).catch(async () => {
      await page.keyboard.type(description, { delay: 1 }).catch(() => {});
    });
  }
  await page.waitForTimeout(350);
  const text = ((await input.innerText().catch(() => "")) || (await input.inputValue().catch(() => ""))).trim();
  const sample = description.trim().slice(0, 32);
  return Boolean(sample && text.includes(sample)) || text.length >= Math.min(24, description.trim().length);
}

async function resolveCharacterGenerateButton(page: Page): Promise<Locator | null> {
  const fromComposer = composerRoot(page).locator("button").filter({ hasText: /arrow_forward/i }).last();
  if (await fromComposer.isVisible({ timeout: 600 }).catch(() => false)) return fromComposer;

  const calibrated = await locatorFor(page, "characterGenerateButton", { timeoutMs: 700 });
  if (calibrated) return calibrated;

  const label = /olu[sş]tur|generate|create|[uü]ret|g[oö]nder|send/i;
  const candidates: Locator[] = [
    page.getByRole("button", { name: label }).last(),
    page.locator("button[type='submit']").last(),
  ];
  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 500 }).catch(() => false)) return candidate;
  }
  return null;
}

async function submitCharacterPrompt(page: Page, project: Project, input: Locator): Promise<boolean> {
  const deadline = Date.now() + 6_000;
  while (Date.now() < deadline) {
    const button = await resolveCharacterGenerateButton(page);
    if (button && !(await button.isDisabled({ timeout: 400 }).catch(() => true))) {
      await button.click({ timeout: 4_000 }).catch(async () => {
        await button.click({ force: true }).catch(() => {});
      });
      return true;
    }
    await page.waitForTimeout(300);
  }
  await input.click().catch(() => {});
  await page.keyboard.press("Control+End").catch(() => {});
  await page.keyboard.press("Enter").catch(() => {});
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: "Karakter Generate dugmesi bulunamadi; Enter ile gonderildi",
  });
  return true;
}

export type CreateFlowCharacterResult = {
  started: boolean;
  imageSourcesBefore: Set<string>;
};

/**
 * Karakterler sayfasinda yeni karakter uretimini baslatir.
 *
 * Bos kadroda prompt kutusu zaten aciktir ("Yeni karakter" aranmaz).
 * Kadro varsa once Yeni karakter / person_add, sonra tarif + Generate.
 * Gorsel kaynaklari Generate ONCESI cekilir ki onceki karakterin gec biten
 * karesi yeni karaktere yazilmasin.
 */
export async function createFlowCharacter(
  page: Page,
  project: Project,
  name: string,
  description: string
): Promise<CreateFlowCharacterResult> {
  const empty: CreateFlowCharacterResult = { started: false, imageSourcesBefore: new Set() };
  await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
  await activateCharactersTab(page);

  let input = await findCharacterPromptInput(page);
  if (!input) {
    const newButton = await resolveNewCharacterButton(page);
    if (newButton) {
      await newButton.click();
      await page.waitForTimeout(900);
    }
    input = await waitForCharacterPrompt(page, 10_000);
  }

  {
    const snapshot = await captureDebugSnapshot(page, project.slug, "characters-create-ui");
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: input ? "Karakter editoru acik" : "Karakter editoru acilamadi",
      screenshotPath: snapshot.screenshotPath,
      pageUrl: page.url(),
    });
  }

  if (!input) {
    const snapshot = await captureDebugSnapshot(page, project.slug, "characters-no-input");
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message:
        "Karakter tarif kutusu yok. Bos kadroda editor zaten acik olmali; kadro varsa 'Yeni karakter' (person_add) gerekir.",
      screenshotPath: snapshot.screenshotPath,
      pageUrl: page.url(),
    });
    return empty;
  }

  const scope = page.locator("[role='dialog'], [aria-modal='true']").first();
  const scoped = (await scope.isVisible({ timeout: 400 }).catch(() => false)) ? scope : page;
  await fillVisibleCharacterName(scoped, name);
  await chooseCharacterImageModel(page, project, scoped);

  if (!(await fillCharacterPrompt(page, input, description))) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Karakter tarifi kutuya yazilamadi",
    });
    return empty;
  }

  const imageSourcesBefore = await snapshotImageSources(page);
  const submitted = await submitCharacterPrompt(page, project, input);
  if (submitted) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      message: `Karakter olusturma baslatildi: ${name || "adsiz"}`,
    });
  }
  return { started: submitted, imageSourcesBefore };
}

async function fillVisibleCharacterName(scope: Page | Locator, name: string, loose = false): Promise<boolean> {
  if (!name.trim()) return false;
  const candidates: Locator[] = [
    scope.getByLabel(/^(ad|isim|name|character name|karakter ad[ıi])/i).first(),
    scope.getByPlaceholder(/^(ad|isim|name|character name|karakter ad[ıi])/i).first(),
  ];
  if (loose) {
    candidates.push(scope.getByPlaceholder(/ad|isim|name|karakter/i).first());
    candidates.push(scope.locator("input[type='text']:not([readonly])").last());
  }
  for (const field of candidates) {
    if (!(await field.isVisible({ timeout: 500 }).catch(() => false))) continue;
    await field.click().catch(() => {});
    await field.fill(name).catch(() => {});
    return true;
  }
  return false;
}

async function pickFirstCharacterVoice(page: Page): Promise<void> {
  const trigger = page.getByRole("button", { name: /ses se[cç]|select a voice|choose a voice|ses ekle/i }).first();
  if (!(await trigger.isVisible({ timeout: 700 }).catch(() => false))) return;
  await trigger.click().catch(() => {});
  await page.waitForTimeout(500);
  const option = page.getByRole("option").first();
  const item = page.getByRole("menuitem").first();
  if (await option.isVisible({ timeout: 800 }).catch(() => false)) await option.click().catch(() => {});
  else if (await item.isVisible({ timeout: 500 }).catch(() => false)) await item.click().catch(() => {});
  const add = page.getByRole("button", { name: /karaktere ekle|add to character/i }).first();
  if (await add.isVisible({ timeout: 800 }).catch(() => false)) await add.click().catch(() => {});
}

/**
 * Gorsel geldikten sonra adi yazar ve Bitti / Done ile Flow karakterini kaydeder.
 * Kayit olmadan @ad kliplerde calismaz.
 */
export async function finalizeFlowCharacter(page: Page, project: Project, name: string): Promise<void> {
  await fillVisibleCharacterName(page, name, true);
  await page.waitForTimeout(400);

  let done = page.getByRole("button", { name: CHAR_DONE }).first();
  if (!(await done.isVisible({ timeout: 1_200 }).catch(() => false))) {
    done = page.getByRole("button", { name: /bitti|done|kaydet|save/i }).first();
  }
  if (!(await done.isVisible({ timeout: 800 }).catch(() => false))) {
    await recordEvent({
      projectId: project.id,
      step: "flow",
      level: "warning",
      message: "Karakter 'Bitti' dugmesi gorunmedi; Flow kaydi atlanmis olabilir",
    });
    return;
  }

  if (await done.isDisabled({ timeout: 400 }).catch(() => false)) {
    await pickFirstCharacterVoice(page);
    await page.waitForTimeout(400);
  }

  await done.click({ timeout: 4_000 }).catch(async () => {
    await done.click({ force: true }).catch(() => {});
  });
  await page.waitForTimeout(1_200);
  await recordEvent({
    projectId: project.id,
    step: "flow",
    message: `Karakter Flow'a kaydedildi: ${name || "adsiz"}`,
  });
}

/**
 * Karakterler sayfasinda YENI bir karakter gorselinin belirmesini bekler.
 * Baslangictaki gorsel adresleriyle kiyaslar; yeni ve yeterince buyuk
 * (ikon olmayan) ilk gorseli dondurur.
 */
export async function waitForNewCharacterImage(
  page: Page,
  project: Project,
  before: Set<string>,
  opts?: { minWaitMs?: number }
): Promise<{ locator: Locator; src: string } | null> {
  const settings = await getSettings();
  const deadline = Date.now() + settings.generationTimeoutMs;
  const minWaitUntil = Date.now() + Math.max(0, opts?.minWaitMs ?? 3_500);
  const staleErrorCount = await countSelectorMatches(page, "errorBanner");

  while (Date.now() < deadline) {
    assertFlowPageAlive(page);
    const currentErrorCount = await countSelectorMatches(page, "errorBanner");
    if (currentErrorCount > staleErrorCount) {
      const banner = await locatorFor(page, "errorBanner", { selfHeal: false, timeoutMs: 700 });
      const errorText = banner ? ((await banner.textContent().catch(() => "")) ?? "") : "";
      const snapshot = await captureDebugSnapshot(page, project.slug, "character-generation-failed");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: `Karakter uretimi Flow tarafinda basarisiz: ${errorText.slice(0, 160) || "hata karti belirdi"}`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw new Error(`Flow karakter uretim hatasi: ${errorText.slice(0, 200) || "hata karti belirdi"}`);
    }

    const entries = await page
      .evaluate(() =>
        Array.from(document.querySelectorAll("img")).map((img, index) => {
          const el = img as HTMLImageElement;
          const rect = el.getBoundingClientRect();
          return { index, src: el.currentSrc || el.src, area: rect.width * rect.height };
        })
      )
      .catch(() => [] as Array<{ index: number; src: string; area: number }>);

    const fresh = entries
      .filter((e) => e.src && !before.has(e.src) && e.area > 8_000)
      .sort((a, b) => b.area - a.area);

    if (fresh.length > 0 && Date.now() >= minWaitUntil) {
      const chosen = fresh[0];
      await recordEvent({ projectId: project.id, step: "flow", message: "Yeni karakter gorseli algilandi" });
      return { locator: page.locator("img").nth(chosen.index), src: chosen.src };
    }
    await page.waitForTimeout(settings.pollIntervalMs);
  }

  const snapshot = await captureDebugSnapshot(page, project.slug, "character-page-timeout");
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Karakterler sayfasinda yeni gorsel algilanamadi (${Math.round(settings.generationTimeoutMs / 1000)} sn)`,
    screenshotPath: snapshot.screenshotPath,
    pageUrl: page.url(),
  });
  return null;
}

/**
 * Bir gorsel ogesini diske kaydeder: adres http(s) ise oturum cerezleriyle
 * indirir; olmazsa ogenin ekran goruntusunu alir.
 */
/**
 * Prompt cubugunda uretilen YENI gorseli bekler.
 *
 * Varlik menusu / indirme akisi gorsel modunda kirilgan oldugu icin (menu
 * seciciler video kartina kalibre olabiliyor) karakter sayfasindaki kanitlanmis
 * yontem kullanilir: uretim oncesi img adresleri fotograflanir, sonra listede
 * BELIREN yeni ve buyuk gorsel yakalanir.
 *
 * @param opts.onPoll her turda cagrilir; firlatirsa bekleme aninda kesilir
 *                    (uzun form iptali 7 dakika beklemesin diye).
 */
export async function waitForNewComposerImage(
  page: Page,
  project: Project,
  before: Set<string>,
  opts?: { timeoutMs?: number; onPoll?: () => void }
): Promise<{ locator: Locator; src: string }> {
  const settings = await getSettings();
  const timeoutMs = Math.max(20_000, Math.min(opts?.timeoutMs ?? 240_000, settings.generationTimeoutMs));
  const pollMs = Math.max(700, Math.min(settings.pollIntervalMs, 2_000));
  const deadline = Date.now() + timeoutMs;
  const staleErrorCount = await countSelectorMatches(page, "errorBanner");

  while (Date.now() < deadline) {
    assertFlowPageAlive(page);
    opts?.onPoll?.();

    const currentErrorCount = await countSelectorMatches(page, "errorBanner");
    if (currentErrorCount > staleErrorCount) {
      const banner = await locatorFor(page, "errorBanner", { selfHeal: false, timeoutMs: 700 });
      const errorText = ((banner ? await banner.textContent().catch(() => "") : "") ?? "").trim();
      const snapshot = await captureDebugSnapshot(page, project.slug, "flow-image-error");
      await recordEvent({
        projectId: project.id,
        step: "flow",
        level: "error",
        message: `Gorsel uretiminde hata karti: ${errorText.slice(0, 160) || "hata karti belirdi"}`,
        screenshotPath: snapshot.screenshotPath,
        pageUrl: page.url(),
      });
      throw generationFailureError(errorText || "hata karti belirdi");
    }

    const entries = await page
      .evaluate(() =>
        Array.from(document.querySelectorAll("img")).map((img, index) => {
          const el = img as HTMLImageElement;
          const rect = el.getBoundingClientRect();
          return { index, src: el.currentSrc || el.src, area: rect.width * rect.height };
        })
      )
      .catch(() => [] as Array<{ index: number; src: string; area: number }>);

    // Yeni kare bazen kucuk bir kart onizlemesi olarak belirir; esik dusuk
    // tutulur ama her zaman EN BUYUK yeni gorsel secilir.
    const fresh = entries
      .filter((e) => e.src && !before.has(e.src) && e.area > 2_500 && !/^data:image\/svg/i.test(e.src))
      .sort((a, b) => b.area - a.area);

    if (fresh.length > 0) {
      return { locator: page.locator("img").nth(fresh[0].index), src: fresh[0].src };
    }
    await page.waitForTimeout(pollMs);
  }

  const snapshot = await captureDebugSnapshot(page, project.slug, "flow-image-timeout");
  await recordEvent({
    projectId: project.id,
    step: "flow",
    level: "warning",
    message: `Yeni gorsel algilanamadi (${Math.round(timeoutMs / 1000)} sn)`,
    screenshotPath: snapshot.screenshotPath,
    pageUrl: page.url(),
  });
  throw new Error(`Flow gorsel uretimi zaman asimina ugradi (${Math.round(timeoutMs / 1000)} sn)`);
}

/**
 * Uretilen gorselin ham baytlari.
 *
 * Sira: kirpilmis boyut ekini atmis TAM BOY adres → adresin kendisi →
 * son care element ekran goruntusu. Google CDN adreslerinde "=s512" /
 * "=w400-h300" gibi ekler onizleme boyutunu zorlar; atilinca orijinal gelir.
 */
export async function fetchGeneratedImage(page: Page, locator: Locator, src: string): Promise<Buffer> {
  if (/^data:image\//i.test(src)) {
    const body = Buffer.from(src.slice(src.indexOf(",") + 1), "base64");
    if (body.length > 5_000) return body;
  }

  if (/^https?:/i.test(src)) {
    const candidates = [src.replace(/=[swh]\d+(-[a-z0-9]+)*$/i, ""), src].filter(
      (url, index, list) => url && list.indexOf(url) === index
    );
    let best: Buffer | null = null;
    for (const url of candidates) {
      try {
        const response = await page.request.get(url);
        if (!response.ok()) continue;
        const body = await response.body();
        if (body.length > 5_000 && (!best || body.length > best.length)) best = body;
      } catch {
        // sonraki adaya gec
      }
    }
    if (best) return best;
  }

  return locator.screenshot();
}

export async function saveImageFromElement(page: Page, locator: Locator, src: string, targetPath: string): Promise<string> {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  const finalPath = nextAvailablePath(targetPath);

  if (/^https?:/i.test(src)) {
    try {
      const response = await page.request.get(src);
      if (response.ok()) {
        const body = await response.body();
        if (body.length > 5_000) {
          fs.writeFileSync(finalPath, body);
          return finalPath;
        }
      }
    } catch {
      // indirme olmazsa ekran goruntusune dus
    }
  }
  await locator.screenshot({ path: finalPath });
  return finalPath;
}

/**
 * Indirilen dosya ZIP ise (Flow, videolari arsiv olarak verir) icindeki
 * en buyuk video dosyasini cikarip ayni yola yazar.
 */
async function extractVideoIfArchive(filePath: string, projectId: string): Promise<void> {
  const header = Buffer.alloc(4);
  const fd = fs.openSync(filePath, "r");
  try {
    fs.readSync(fd, header, 0, 4, 0);
  } finally {
    fs.closeSync(fd);
  }
  const isZip = header[0] === 0x50 && header[1] === 0x4b && header[2] === 0x03 && header[3] === 0x04;
  if (!isZip) return;

  const zip = new AdmZip(filePath);
  const videoEntries = zip
    .getEntries()
    .filter((entry) => !entry.isDirectory && /\.(mp4|mov|webm|m4v)$/i.test(entry.entryName))
    .sort((a, b) => b.header.size - a.header.size);

  if (videoEntries.length === 0) {
    const names = zip
      .getEntries()
      .map((entry) => entry.entryName)
      .slice(0, 10)
      .join(", ");
    throw new Error(`Indirilen ZIP icinde video dosyasi yok (icerik: ${names})`);
  }

  const chosen = videoEntries[0];
  const data = chosen.getData();
  const tempPath = `${filePath}.extract`;
  fs.writeFileSync(tempPath, data);
  fs.rmSync(filePath);
  fs.renameSync(tempPath, filePath);
  await recordEvent({
    projectId,
    step: "download",
    message: `ZIP arsivi acildi; video cikarildi: ${chosen.entryName} (${(data.length / (1024 * 1024)).toFixed(1)} MB)`,
  });
}
