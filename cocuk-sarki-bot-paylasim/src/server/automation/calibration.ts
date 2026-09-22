import type { Page } from "playwright";
import { prisma } from "@/server/db";
import { recordEvent } from "@/server/lib/logger";
import { checkSessionStatus, openDedicatedFlowPage, openFlowBrowser } from "@/server/automation/browser";
import {
  autoCalibrateAll,
  brokenSelectorReasons,
  buildLocator,
  CALIBRATION_CHARACTER_KEYS,
  CALIBRATION_CHAT_KEYS,
  CALIBRATION_COMPOSER_KEYS,
  CALIBRATION_SETTINGS_KEYS,
  calibrationPriority,
  ensureDefaultSelectors,
  locatorFor,
  parseCandidates,
  PROJECT_LEVEL_DOWNLOAD,
  purgeImplausibleStoredSelectors,
  saveCandidates,
  SEMANTIC_FALLBACKS,
  type AutoCalibrationResult,
  type FlowSelectorConfig,
  type SelectorCandidate,
  type SelectorTestResult,
  testAllSelectors,
} from "@/server/automation/selectors";

/**
 * Flow secici kalibrasyonu.
 *
 * Iki yol:
 * 1. OTO KALIBRASYON — acik Flow sayfasinda tum anahtarlar aday zinciriyle
 *    cozumlenir; bulunan ve kaydi olmayanlar birincil secici olarak yazilir.
 *    Otomasyon baslarken kritik seciciler eksikse kendiliginden de calisir.
 * 2. TIKLA-TANIT — kullanici Chrome'daki Flow penceresinde hedef ogeye
 *    tiklar; ogeden rol/etiket/metin cikarilir, aday zinciri kurulur, sayfada
 *    dogrulanir ve kaydedilir.
 */

/** Tiklanan ogeden cikarilan ham bilgi. */
export interface CapturedElementInfo {
  tag: string;
  id: string;
  testId: string;
  ariaLabel: string;
  role: string;
  accessibleName: string;
  placeholder: string;
  text: string;
  cssPath: string;
  editable: boolean;
}

const MAX_NAME_LEN = 40;

/** Uzun etiketlerde regex kismi eslesme yeter: en uzun kelime kullanilir. */
function compactLabel(raw: string): string {
  const cleaned = raw.replace(/\s+/g, " ").trim();
  if (cleaned.length <= MAX_NAME_LEN) return cleaned;
  let longest = "";
  for (const word of cleaned.split(" ")) {
    if (word.length > longest.length) longest = word;
  }
  return longest.slice(0, MAX_NAME_LEN);
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Oncelik sirasina gore (role > label > placeholder > text > testid > css)
 * dogrulanabilir aday listesi kurar. CSS her zaman son caredir.
 */
export function buildSelectorCandidates(key: string, info: CapturedElementInfo, required: boolean): SelectorCandidate[] {
  void required;
  const out: SelectorCandidate[] = [];
  const push = (candidate: SelectorCandidate) => {
    if (!candidate.value) return;
    if (out.some((c) => c.strategy === candidate.strategy && c.value === candidate.value && c.roleName === candidate.roleName)) return;
    out.push(candidate);
  };

  // Klip indirme anahtarlarinda proje-geneli ogeler ("Projeyi indir") zehirli:
  // her klip icin ayni arsivi indirir. Aday bile yapilmaz.
  const isDownloadKey = /^download/i.test(key);
  const banned = (label: string) => isDownloadKey && PROJECT_LEVEL_DOWNLOAD.test(label);

  // Yazi kutusunda icerikten turetilen ad (etiket degil, o anki metin)
  // kirilgandir: bir sonraki acilista metin degisir. ariaLabel ise kalicidir.
  const contentDerived = !info.ariaLabel && info.accessibleName === info.text;
  const roleName = info.ariaLabel || (info.editable && contentDerived ? "" : info.accessibleName);

  if (info.role.trim() && roleName.trim() && !banned(roleName)) {
    const candidate: SelectorCandidate = {
      strategy: "role",
      value: info.role.trim(),
      roleName: escapeRegex(compactLabel(roleName)),
    };
    if (brokenSelectorReasons(candidate).length === 0) push(candidate);
  }
  if (info.ariaLabel.trim() && !banned(info.ariaLabel)) {
    push({ strategy: "label", value: escapeRegex(compactLabel(info.ariaLabel)), roleName: "" });
  }
  if (info.placeholder.trim()) {
    push({ strategy: "placeholder", value: escapeRegex(compactLabel(info.placeholder)), roleName: "" });
  }
  if (info.text.trim() && !info.editable && !banned(info.text)) {
    push({ strategy: "text", value: escapeRegex(compactLabel(info.text)), roleName: "" });
  }
  if (info.testId.trim()) {
    push({ strategy: "testid", value: info.testId.trim(), roleName: "" });
  }
  push({ strategy: "css", value: info.cssPath.trim() || info.tag, roleName: "" });
  return out;
}

/** Aday listesinin ilkini birincil secici yapilandirmasina cevirir. */
export function pickBestSelector(key: string, info: CapturedElementInfo, required: boolean): FlowSelectorConfig {
  const [best] = buildSelectorCandidates(key, info, required);
  return {
    key,
    strategy: best?.strategy ?? "css",
    value: best?.value ?? (info.cssPath.trim() || info.tag),
    roleName: best?.roleName ?? "",
    description: "",
    required,
  };
}

/* -------------------------------------------------------------------------
 * OTO KALIBRASYON
 * ------------------------------------------------------------------------- */

/** Kullanicinin kalibrasyon icin actigi temiz Flow proje editoru. */
export const DEFAULT_CALIBRATION_EDITOR_URL =
  "https://labs.google/fx/tr/tools/flow/project/d25b011f-e596-4b39-99e1-f36e1339be8c";

export function flowEditorUrl(url: string): string {
  return url.trim().replace(/\/+$/, "").replace(/\/characters$/i, "");
}

export function flowCharactersUrl(url: string): string {
  return `${flowEditorUrl(url)}/characters`;
}

async function settingsPanelLooksOpen(page: Page): Promise<boolean> {
  const probes = [
    page.getByRole("tab", { name: /16:9|9:16/ }).first(),
    page.getByRole("tab", { name: /^(4|6|8|10)\s*(s|sn|saniye)/i }).first(),
    page.getByRole("tab", { name: /^x[1-4]$/i }).first(),
    page.getByRole("tab", { name: /videocam\s*video\s*$/i }).first(),
  ];
  for (const loc of probes) {
    if (await loc.isVisible({ timeout: 250 }).catch(() => false)) return true;
  }
  return false;
}

/** Video sekmesi secili olsun — gorsel/malzeme/kare modunda sure/ses kontrolleri yok. */
async function ensureVideoTabInSettings(page: Page): Promise<void> {
  const videoTab = page.getByRole("tab", { name: /videocam\s*video|videocamvideo/i }).first();
  if (!(await videoTab.isVisible({ timeout: 800 }).catch(() => false))) return;
  await videoTab.click().catch(() => {});
  await page.waitForTimeout(1_200);
  await page
    .getByRole("tab", { name: /^(4|6|8|10)\s*(s|sn|saniye)/i })
    .first()
    .waitFor({ state: "visible", timeout: 2_500 })
    .catch(() => {});
  await page.getByRole("switch").first().waitFor({ state: "visible", timeout: 800 }).catch(() => {});
}

async function openSettingsPanelForCalibration(page: Page, chipFound: boolean): Promise<boolean> {
  if (await settingsPanelLooksOpen(page)) {
    await ensureVideoTabInSettings(page);
    return true;
  }
  if (chipFound) {
    const chip = await locatorFor(page, "generationSettingsButton", { timeoutMs: 2_000 });
    if (chip) {
      await chip.click().catch(() => {});
    }
  } else {
    const fallback = page.locator("button[aria-haspopup='menu']").filter({ hasText: /crop_(16_9|9_16)|720p/ }).first();
    if (await fallback.isVisible({ timeout: 800 }).catch(() => false)) {
      await fallback.click().catch(() => {});
    }
  }
  const deadline = Date.now() + 5_000;
  while (Date.now() < deadline) {
    if (await settingsPanelLooksOpen(page)) {
      await ensureVideoTabInSettings(page);
      return true;
    }
    await page.waitForTimeout(250);
  }
  await recordEvent({
    step: "calibration",
    level: "warning",
    message: "Uretim ayarlari paneli kalibrasyon icin acilamadi; sure/ses secicileri eksik kalabilir",
  });
  return false;
}

async function recordSettingsDiagnostics(page: Page, missing: string[], panelOpen: boolean): Promise<void> {
  const summary = await page
    .evaluate(() => {
      const nodes = [...document.querySelectorAll('[role="tab"], [role="switch"], [role="radio"], [role="checkbox"], button')];
      return nodes
        .map((el) => {
          const role = el.getAttribute("role") || el.tagName.toLowerCase();
          const name = (el.getAttribute("aria-label") || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 56);
          return `${role}:${name}`;
        })
        .filter((row) => /tab:|switch:|radio:|(4|6|8|10)\s*(s|sn)|ses|audio|volume|crop_/i.test(row))
        .slice(0, 28)
        .join(" | ");
    })
    .catch(() => "");
  await recordEvent({
    step: "calibration",
    level: "warning",
    message: `Ayarlar paneli eksik seciciler: ${missing.join(", ")} (panel=${panelOpen ? "acik" : "kapali"}). Gorunen: ${(summary || "?").slice(0, 420)}`,
  });
}

async function gotoCalibrationPage(page: Page, url: string, label: string): Promise<void> {
  if (!page.url().startsWith(url)) {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
  }
  await page.waitForLoadState("networkidle", { timeout: 20_000 }).catch(() => {});
  await page.waitForTimeout(1_400);
  await recordEvent({
    step: "calibration",
    message: `Oto kalibrasyon sayfasi: ${label}`,
  });
}

/**
 * Ayarlar ekranindaki "Oto kalibre et": AYRI sekmede video editoru + karakterler.
 * Once chat (prompt + Generate), Generate'e BASILMAZ. Uretim sekmesine dokunmaz.
 */
export async function runAutoCalibration(opts?: { editorUrl?: string }): Promise<{ results: AutoCalibrationResult[]; pageUrl: string }> {
  await ensureDefaultSelectors();
  await purgeImplausibleStoredSelectors();

  const editorUrl = flowEditorUrl(opts?.editorUrl?.trim() || DEFAULT_CALIBRATION_EDITOR_URL);
  const charactersUrl = flowCharactersUrl(editorUrl);
  const page = await openDedicatedFlowPage(editorUrl);
  try {
    const session = await checkSessionStatus(page);
    if (session.status === "needs_login") {
      throw new Error("Google oturumu acik degil. Chrome penceresinde giris yapin, sonra tekrar deneyin.");
    }

    await gotoCalibrationPage(page, editorUrl, "video editoru / generate chat");
    await page
      .getByText(/ne olu[sş]turmak istiyorsun|what do you want to create|arrow_forward/i)
      .first()
      .waitFor({ state: "visible", timeout: 20_000 })
      .catch(() => {});

    const chat = await autoCalibrateAll(page, {
      keys: [...CALIBRATION_CHAT_KEYS],
      refreshFound: true,
    });

    const composer = await autoCalibrateAll(page, {
      keys: CALIBRATION_COMPOSER_KEYS.filter((key) => key !== "promptInput" && key !== "generateButton"),
      refreshFound: true,
    });

    const settingsChip = [...chat, ...composer].find((r) => r.key === "generationSettingsButton" && r.found);
    const panelOpen = await openSettingsPanelForCalibration(page, Boolean(settingsChip));
    const settings = await autoCalibrateAll(page, {
      keys: [...CALIBRATION_SETTINGS_KEYS],
      refreshFound: true,
    });
    const settingsMissing = settings.filter((r) => !r.found).map((r) => r.key);
    if (settingsMissing.length > 0) {
      await recordSettingsDiagnostics(page, settingsMissing, panelOpen);
    }
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(400);

    const done = new Set<string>([
      ...CALIBRATION_CHAT_KEYS,
      ...CALIBRATION_COMPOSER_KEYS,
      ...CALIBRATION_SETTINGS_KEYS,
      ...CALIBRATION_CHARACTER_KEYS,
    ]);
    const restKeys = (await prisma.flowSelector.findMany({ select: { key: true } }))
      .map((r) => r.key)
      .filter((key) => !done.has(key));
    const rest = restKeys.length > 0 ? await autoCalibrateAll(page, { keys: restKeys, refreshFound: false }) : [];

    await gotoCalibrationPage(page, charactersUrl, "karakterler");
    const characters = await autoCalibrateAll(page, {
      keys: [...CALIBRATION_CHARACTER_KEYS],
      refreshFound: true,
    });

    const results = [...chat, ...composer, ...settings, ...rest, ...characters];
    const p0Missing = results.filter((r) => r.priority === 0 && !r.found).map((r) => r.key);
    if (p0Missing.length > 0) {
      await recordEvent({
        step: "calibration",
        level: "warning",
        message: `Kritik chat secicileri bulunamadi: ${p0Missing.join(", ")}. Prompt cubugu gorunur mu?`,
      });
    } else {
      await recordEvent({
        step: "calibration",
        message: "Generate chat kalibrasyonu tamam: prompt kutusu + Generate kaydedildi (Generate'e basilmadi)",
      });
    }

    return { results, pageUrl: page.url() };
  } finally {
    await page.close().catch(() => {});
  }
}

/** Acik sayfada tum secicileri dener; sonuc raporunu dondurur (kayit yapmaz). */
export async function runSelectorTest(): Promise<{ results: SelectorTestResult[]; pageUrl: string }> {
  await ensureDefaultSelectors();
  const page = await openFlowBrowser();
  return { results: await testAllSelectors(page), pageUrl: page.url() };
}

const CRITICAL_KEYS = ["promptInput", "generateButton", "outputTypeMenu", "generationSettingsButton"] as const;

/**
 * Otomasyon basinda cagirilir: kritik seciciler kalibresizse acik editor
 * sayfasinda oto kalibrasyon kosar. Kayitli kalibrasyon varsa dokunmaz
 * (kendini onarma zaten calisiyor).
 */
export async function autoCalibrateMissingSelectors(page: Page, projectId?: string): Promise<AutoCalibrationResult[] | null> {
  const records = await prisma.flowSelector.findMany({ where: { key: { in: [...CRITICAL_KEYS] } } });
  const missing = CRITICAL_KEYS.filter((key) => {
    const record = records.find((r) => r.key === key);
    return !record || (!record.value.trim() && parseCandidates(record.candidates).length === 0);
  });
  if (missing.length === 0) return null;

  await recordEvent({
    projectId,
    step: "calibration",
    message: `Kalibrasyonsuz kritik seciciler (${missing.join(", ")}) icin otomatik kalibrasyon calisiyor…`,
  });
  return autoCalibrateAll(page);
}

/* -------------------------------------------------------------------------
 * TIKLA-TANIT
 * ------------------------------------------------------------------------- */

export interface ClickCalibrationOutcome {
  key: string;
  captured: CapturedElementInfo;
  saved: SelectorCandidate[];
  primary: SelectorCandidate;
}

let clickCalibrationBusy = false;

const CALIB_ATTR = "data-calib-target";

/**
 * Kullanicidan Chrome'daki Flow penceresinde hedef ogeye tiklamasini bekler,
 * ogeyi cozumler, adaylari sayfada dogrular ve kaydeder.
 */
export async function calibrateSelectorByClick(key: string, timeoutMs = 60_000): Promise<ClickCalibrationOutcome> {
  if (clickCalibrationBusy) {
    throw new Error("Baska bir kalibrasyon zaten bekliyor. Once onu tamamlayin veya suresinin dolmasini bekleyin.");
  }
  clickCalibrationBusy = true;
  try {
    await ensureDefaultSelectors();
    const record = await prisma.flowSelector.findUnique({ where: { key } });
    if (!record) throw new Error(`Bilinmeyen secici anahtari: ${key}`);

    const page = await openFlowBrowser();
    await page.bringToFront().catch(() => {});
    await recordEvent({
      step: "calibration",
      message: `Kalibrasyon basladi: ${record.description || key}. Flow uzerinde hedef elemana tiklayin.`,
    });

    await armClickCapture(page);

    const deadline = Date.now() + timeoutMs;
    let captured: CapturedElementInfo | null = null;
    while (Date.now() < deadline) {
      const state = await page
        .evaluate(() => {
          const w = window as unknown as { __calibDone?: { info?: unknown }; __calibCancel?: unknown };
          return { done: w.__calibDone ?? null, armed: typeof w.__calibCancel === "function" };
        })
        .catch(() => null);
      if (state?.done && typeof state.done === "object" && state.done.info) {
        captured = state.done.info as CapturedElementInfo;
        break;
      }
      // Sayfa yenilendiyse dinleyici kaybolur; yeniden kur
      if (state && !state.armed) await armClickCapture(page).catch(() => {});
      await new Promise((r) => setTimeout(r, 400));
    }

    await page
      .evaluate(() => {
        const w = window as unknown as { __calibCancel?: () => void; __calibDone?: unknown };
        w.__calibCancel?.();
        w.__calibCancel = undefined;
        w.__calibDone = undefined;
      })
      .catch(() => {});

    if (!captured) {
      throw new Error("Zaman asimi: 60 saniye icinde tiklama algilanmadi. Tekrar baslatip Chrome'daki Flow penceresinde hedef ogeye tiklayin.");
    }

    const candidates = buildSelectorCandidates(key, captured, record.required);
    const verified: SelectorCandidate[] = [];
    for (const candidate of candidates) {
      try {
        const locator = buildLocator(page, candidate);
        if ((await locator.count()) === 0) continue;
        const hitsTarget = await locator
          .evaluate((el, attr) => {
            const target = document.querySelector(`[${attr}]`);
            if (!target) return false;
            return el === target || el.contains(target) || target.contains(el);
          }, CALIB_ATTR)
          .catch(() => false);
        if (hitsTarget) verified.push(candidate);
      } catch {
        // gecersiz aday — atla
      }
    }

    await page
      .evaluate((attr) => {
        document.querySelectorAll(`[${attr}]`).forEach((el) => el.removeAttribute(attr));
      }, CALIB_ATTR)
      .catch(() => {});

    if (verified.length === 0) {
      throw new Error(
        "Tiklanan oge icin guvenilir secici uretilemedi (adaylar sayfada ilk eslesen olamadi). Dugmenin tam uzerine tiklamayi deneyin."
      );
    }

    await saveCandidates(key, verified);
    const primary = verified[0];
    await recordEvent({
      step: "calibration",
      detail: JSON.stringify({ denenenAdaylar: candidates.map((c) => `${c.strategy}=${verified.includes(c) ? 1 : 0}`) }),
      message: `Secici kaydedildi: ${key} -> ${primary.strategy}${primary.roleName ? `(${primary.roleName})` : `: ${primary.value.slice(0, 60)}`} — ${verified.length} dogrulanmis aday`,
    });

    return { key, captured, saved: verified, primary };
  } finally {
    clickCalibrationBusy = false;
  }
}

/** Sayfaya tek seferlik tiklama yakalayici kurar (capture fazi, Flow'a gitmez). */
async function armClickCapture(page: Page): Promise<void> {
  await page.evaluate((attr) => {
    const w = window as unknown as {
      __calibDone?: unknown;
      __calibCancel?: () => void;
    };
    w.__calibCancel?.();
    w.__calibDone = undefined;
    document.querySelectorAll(`[${attr}]`).forEach((el) => el.removeAttribute(attr));

    const implicitRole = (node: Element): string => {
      const explicit = node.getAttribute("role");
      if (explicit) return explicit;
      const tag = node.tagName.toLowerCase();
      if (tag === "button") return "button";
      if (tag === "a" && node.hasAttribute("href")) return "link";
      if (tag === "textarea") return "textbox";
      if (tag === "select") return "combobox";
      if (tag === "input") {
        const type = (node.getAttribute("type") || "text").toLowerCase();
        if (type === "button" || type === "submit") return "button";
        if (type === "checkbox") return "checkbox";
        if (type === "radio") return "radio";
        return "textbox";
      }
      if ((node as HTMLElement).isContentEditable) return "textbox";
      return "";
    };

    const stableCssPath = (node: Element): string => {
      if (node.id && !/^(radix-)?:?r/i.test(node.id)) return `#${CSS.escape(node.id)}`;
      const testid = node.getAttribute("data-testid");
      if (testid) return `[data-testid="${testid}"]`;
      const probes = [
        "textarea",
        "[contenteditable='true']",
        "button[type='submit']",
        "button[aria-haspopup='menu']",
        "button[aria-haspopup='dialog']",
        "input[type='file']",
      ];
      for (const probe of probes) {
        try {
          if (node.matches(probe) && document.querySelectorAll(probe).length === 1) return probe;
        } catch {
          /* gecersiz probe */
        }
      }
      const parts: string[] = [];
      let current: Element | null = node;
      let depth = 0;
      while (current && current !== document.body && depth < 4) {
        const parent: Element | null = current.parentElement;
        if (!parent) break;
        const tag = current.tagName.toLowerCase();
        const same = Array.from(parent.children).filter((c) => c.tagName === current!.tagName);
        parts.unshift(same.length > 1 ? `${tag}:nth-of-type(${same.indexOf(current) + 1})` : tag);
        current = parent;
        depth++;
      }
      return parts.join(" > ");
    };

    const handler = (ev: MouseEvent) => {
      ev.preventDefault();
      ev.stopPropagation();
      document.removeEventListener("click", handler, true);
      const raw = ev.target as Element | null;
      if (!raw) {
        w.__calibDone = { error: "hedef yok" };
        return;
      }
      const interactive =
        "button, a, [role='button'], [role='menuitem'], [role='tab'], [role='option'], [role='combobox'], [role='switch'], input, textarea, select, [contenteditable='true']";
      const el = (raw.closest(interactive) as Element | null) || raw;
      el.setAttribute(attr, "1");
      const text = ((el as HTMLElement).innerText || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 120);
      const ariaLabel = el.getAttribute("aria-label") || "";
      w.__calibDone = {
        info: {
          tag: el.tagName.toLowerCase(),
          id: el.id || "",
          testId: el.getAttribute("data-testid") || "",
          ariaLabel,
          role: implicitRole(el),
          accessibleName: ariaLabel || text,
          placeholder: el.getAttribute("placeholder") || el.getAttribute("data-placeholder") || "",
          text,
          cssPath: stableCssPath(el),
          editable:
            (el as HTMLElement).isContentEditable ||
            el.tagName.toLowerCase() === "textarea" ||
            (el.tagName.toLowerCase() === "input" && !["button", "submit", "checkbox", "radio", "file"].includes((el.getAttribute("type") || "text").toLowerCase())),
        },
      };
    };
    document.addEventListener("click", handler, true);
    w.__calibCancel = () => document.removeEventListener("click", handler, true);
  }, CALIB_ATTR);
}

/* -------------------------------------------------------------------------
 * DURUM LISTESI / SIFIRLAMA
 * ------------------------------------------------------------------------- */

export interface SelectorStateRow {
  key: string;
  description: string;
  required: boolean;
  strategy: string;
  value: string;
  roleName: string;
  candidateCount: number;
  fallbackCount: number;
  lastTestOk: boolean | null;
  lastTestAt: string | null;
  priority: number;
}

export async function listSelectorStates(): Promise<SelectorStateRow[]> {
  await ensureDefaultSelectors();
  const records = await prisma.flowSelector.findMany();
  return records
    .map((record) => ({
      key: record.key,
      description: record.description,
      required: record.required,
      strategy: record.strategy,
      value: record.value,
      roleName: record.roleName,
      candidateCount: parseCandidates(record.candidates).length,
      fallbackCount: (SEMANTIC_FALLBACKS[record.key] ?? []).length,
      lastTestOk: record.lastTestOk,
      lastTestAt: record.lastTestAt ? record.lastTestAt.toISOString() : null,
      priority: calibrationPriority(record.key),
    }))
    .sort((a, b) => a.priority - b.priority || a.key.localeCompare(b.key));
}

/** Kalibrasyonu siler; anahtar yerlesik yedeklerle calismaya doner. */
export async function resetSelector(key: string): Promise<{ key: string }> {
  await prisma.flowSelector.update({
    where: { key },
    data: { strategy: "css", value: "", roleName: "", candidates: "[]", lastTestOk: null, lastTestAt: null },
  });
  await recordEvent({
    step: "calibration",
    message: `Secici sifirlandi: ${key} — yerlesik yedek tarifler kullanilacak`,
  });
  return { key };
}
