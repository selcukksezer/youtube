import fs from "node:fs";
import path from "node:path";
import { chromium, type BrowserContext, type Page } from "playwright";
import { getSettings } from "@/server/services/settings";
import { DEFAULT_CHROME_PROFILE_DIR } from "@/server/lib/paths";
import { recordEvent } from "@/server/lib/logger";
import { publishEvent } from "@/server/lib/events";

/**
 * Kalici profilli Chrome yonetimi.
 * - Google sifresi hicbir yerde saklanmaz/istenmez
 * - Kullanici ilk calistirmada acilan Chrome'da Google'a ELLE giris yapar
 * - Oturum, profil klasorunde kalici olarak saklanir
 *
 * PARALEL PROJE DESTEGI: tek Chrome penceresi (tek profil = tek Google oturumu)
 * icinde PROJE BASINA AYRI SEKME acilir. Ayri profil kullanmiyoruz: her profil
 * ayri Google girisi ister ve ayni hesabi cok oturumda surekli otomatize etmek
 * risklidir. Sekmeler ayni oturumu paylasir, birbirinden bagimsiz calisir.
 */

interface BrowserState {
  context: BrowserContext | null;
  /** Paylasilan ana sekme: kalibrasyon, oturum kontrolu, tek-proje akislari. */
  page: Page | null;
  /** projectId -> o projeye ayrilmis sekme (paralel otomasyon). */
  projectPages: Map<string, Page>;
  opening: Promise<Page> | null;
}

const globalForBrowser = globalThis as unknown as { flowBrowser?: BrowserState };
const state: BrowserState = globalForBrowser.flowBrowser ?? {
  context: null,
  page: null,
  projectPages: new Map<string, Page>(),
  opening: null,
};
if (!globalForBrowser.flowBrowser) globalForBrowser.flowBrowser = state;
// Eski surecten devralinan state'te alan eksik olabilir (sicak yeniden yukleme)
if (!state.projectPages) state.projectPages = new Map<string, Page>();

export function isBrowserOpen(): boolean {
  return !!state.context && !!state.page && !state.page.isClosed();
}

export function getPage(): Page | null {
  return isBrowserOpen() ? state.page : null;
}

/** Projeye ayrilmis sekme (yoksa null). Paralel calismada hata/ekran goruntusu icin. */
export function getProjectPage(projectId: string): Page | null {
  const page = state.projectPages.get(projectId);
  if (!page || page.isClosed()) return null;
  return page;
}

/** Su an sekmesi acik olan proje kimlikleri. */
export function openProjectPageIds(): string[] {
  return [...state.projectPages.entries()].filter(([, page]) => !page.isClosed()).map(([id]) => id);
}

/** Flow'u kalici profille acar (zaten aciksa mevcut sayfayi dondurur). */
export async function openFlowBrowser(): Promise<Page> {
  if (isBrowserOpen()) return state.page!;
  if (state.opening) return state.opening;

  state.opening = (async () => {
    const settings = await getSettings();
    const profileDir = settings.chromeProfileDir || DEFAULT_CHROME_PROFILE_DIR;
    if (!fs.existsSync(profileDir)) fs.mkdirSync(profileDir, { recursive: true });

    await recordEvent({ step: "browser", message: `Chrome aciliyor (profil: ${path.basename(profileDir)}, headless: ${settings.headless})` });

    /*
     * Ayni profil klasorunu kullanan eski Chrome sureci tam kapanmadan yenisi
     * acilirsa, yeni surec eskiye devredip aninda kapanir ("browser has been
     * closed" hatalari). Bu yuzden acilis dogrulanir ve gerekirse birkac
     * saniye beklenip yeniden denenir.
     */
    let lastError: unknown = null;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const context = await chromium.launchPersistentContext(profileDir, {
          headless: settings.headless,
          channel: "chrome",
          acceptDownloads: true,
          viewport: null,
          slowMo: settings.slowMoMs,
          args: [
            "--disable-blink-features=AutomationControlled",
            // Paralel projelerde yalnizca bir sekme onde olur; Chrome arka plan
            // sekmelerinde zamanlayicilari kisar ve Flow'un ilerleme arayuzu
            // donar/gec guncellenir. Bu bayraklar arka plan sekmelerini de tam
            // hizda calistirir.
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
          ],
        });

        const page = context.pages()[0] ?? (await context.newPage());
        page.setDefaultTimeout(15_000);

        // Acilisin kalici oldugunu dogrula (profil devri varsa hemen kapanir)
        await page.waitForTimeout(1_200);
        if (page.isClosed()) {
          await context.close().catch(() => {});
          throw new Error("Tarayici acilir acilmaz kapandi (profil baska bir Chrome tarafindan kullaniliyor olabilir)");
        }

        context.on("close", () => {
          state.context = null;
          state.page = null;
          state.projectPages.clear();
          invalidateSessionCache();
          publishEvent(null, { type: "system", payload: { browser: "closed" } });
        });

        await page.goto(settings.flowUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });

        state.context = context;
        state.page = page;
        invalidateSessionCache();
        publishEvent(null, { type: "system", payload: { browser: "open" } });
        await recordEvent({ step: "browser", message: "Flow sayfasi acildi", pageUrl: page.url() });
        return page;
      } catch (err) {
        lastError = err;
        state.context = null;
        state.page = null;
        if (attempt < 3) {
          await recordEvent({
            step: "browser",
            level: "warning",
            message: `Tarayici acilisi tutmadi (deneme ${attempt}/3); eski surecin kapanmasi icin 5 sn bekleniyor`,
          });
          await new Promise((resolve) => setTimeout(resolve, 5_000));
        }
      }
    }
    throw lastError instanceof Error ? lastError : new Error(String(lastError));
  })();

  try {
    return await state.opening;
  } finally {
    state.opening = null;
  }
}

/**
 * Bir projeye AYRILMIS sekmeyi dondurur; yoksa acar.
 *
 * Ilk proje paylasilan ana sekmeyi devralir (tek proje calisirken bugunku
 * davranis birebir korunur: fazladan sekme acilmaz). Ikinci ve sonraki
 * projeler kendi sekmelerinde acilir, boylece paralel otomasyon birbirinin
 * sayfasina dokunmaz.
 *
 * @param flowProjectUrl Bu projeye ozel Flow adresi; bos ise genel Flow adresi.
 */
export async function acquireProjectPage(projectId: string, flowProjectUrl?: string): Promise<Page> {
  const mainPage = await openFlowBrowser();
  const context = state.context;
  if (!context) throw new Error("Tarayici baglami acilamadi");

  const existing = state.projectPages.get(projectId);
  if (existing && !existing.isClosed()) return existing;

  const targetUrl = flowProjectUrl?.trim() || "";

  // Ana sekme henuz bir projeye baglanmadiysa onu kullan (tek proje = tek sekme)
  const mainTaken = [...state.projectPages.values()].some((page) => page === mainPage && !page.isClosed());
  if (!mainTaken) {
    state.projectPages.set(projectId, mainPage);
    if (targetUrl && !mainPage.url().startsWith(targetUrl)) {
      await mainPage.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 60_000 }).catch(async (err: Error) => {
        await recordEvent({
          projectId,
          step: "browser",
          level: "warning",
          message: `Proje adresi acilamadi (${targetUrl}): ${err.message}`,
        });
      });
    }
    return mainPage;
  }

  const settings = await getSettings();
  const page = await context.newPage();
  page.setDefaultTimeout(15_000);
  page.on("close", () => {
    if (state.projectPages.get(projectId) === page) state.projectPages.delete(projectId);
  });

  await page.goto(targetUrl || settings.flowUrl, { waitUntil: "domcontentloaded", timeout: 60_000 });
  state.projectPages.set(projectId, page);
  await recordEvent({
    projectId,
    step: "browser",
    message: `Bu proje icin ayri Flow sekmesi acildi (paralel uretim)${targetUrl ? "" : " — proje adresi bos, genel Flow adresi kullanildi"}`,
    pageUrl: page.url(),
  });
  return page;
}

/**
 * Kalibrasyon icin AYRI sekme. Ana sekme bir projenin uretimindeyse
 * (prompt/Generate chat) o sayfayi cekip uretimi iptal etmesin.
 */
export async function openDedicatedFlowPage(url: string): Promise<Page> {
  await openFlowBrowser();
  const context = state.context;
  if (!context) throw new Error("Tarayici baglami acilamadi");
  const page = await context.newPage();
  page.setDefaultTimeout(15_000);
  const target = url.trim();
  if (target) {
    await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60_000 });
  }
  await recordEvent({
    step: "calibration",
    message: "Kalibrasyon ayri sekmede acildi (uretim sekmesine dokunulmadi)",
    pageUrl: page.url(),
  });
  return page;
}

/** Proje sekmesini kapatir (is bitince cagrilir; ana sekme kapatilmaz). */
export async function releaseProjectPage(projectId: string): Promise<void> {
  const page = state.projectPages.get(projectId);
  state.projectPages.delete(projectId);
  if (!page || page.isClosed()) return;
  // Ana sekme paylasilan kaynaktir: sadece haritadan dusuruluyor, kapatilmiyor.
  if (page === state.page) return;
  await page.close().catch(() => {});
}

/** Tarayiciyi kapatir. */
export async function closeFlowBrowser(): Promise<void> {
  if (state.context) {
    try {
      await state.context.close();
    } catch {
      // zaten kapanmis olabilir
    }
  }
  state.context = null;
  state.page = null;
  state.projectPages.clear();
  invalidateSessionCache();
  publishEvent(null, { type: "system", payload: { browser: "closed" } });
  await recordEvent({ step: "browser", message: "Tarayici kapatildi" });
}

export type SessionStatus = "closed" | "ready" | "needs_login" | "needs_verification";

/**
 * Kullanici "bu bir yanlis alarm" dediginde guvenlik kontrolu atlanir.
 * Yalnizca calisan surec icin gecerlidir (kalici degil) ve YALNIZCA tespiti
 * atlar; hicbir dogrulamayi asma girisimi yapilmaz.
 */
const globalForOverride = globalThis as unknown as { flowSessionCheckOverride?: boolean };

export function setSessionCheckOverride(ignore: boolean): void {
  globalForOverride.flowSessionCheckOverride = ignore;
}

export function isSessionCheckOverridden(): boolean {
  return globalForOverride.flowSessionCheckOverride === true;
}

/**
 * Oturum durumu:
 * - needs_login: Google giris ekrani gorunuyor
 * - needs_verification: CAPTCHA / 2FA / hesap dogrulama ekrani gorunuyor (ASILMAZ, kullanici cozer)
 * - ready: Flow arayuzu kullanilabilir
 *
 * Tespit dar tutulur: "guvenlik", "dogrula" gibi tek kelimeler normal arayuz
 * metinlerinde (alt bilgi baglantilari, menuler) gecebildigi icin yalnizca
 * dogrulama ekranlarina ozgu adresler, reCAPTCHA cerceveleri ve tam ifadeler
 * dikkate alinir.
 */
export async function checkSessionStatus(targetPage?: Page | null): Promise<{ status: SessionStatus; detail: string; url?: string }> {
  const page = targetPage && !targetPage.isClosed() ? targetPage : getPage();
  if (!page) return { status: "closed", detail: "Tarayici kapali" };
  try {
    const url = page.url();

    // 1) Hesap dogrulama / challenge adresleri
    if (/accounts\.google\.com\/.*(challenge|speedbump|deniedsigninrejected)/i.test(url)) {
      return {
        status: "needs_verification",
        detail: "Google hesap dogrulama ekrani acik. Dogrulamayi Chrome penceresinde elle tamamlayin.",
        url,
      };
    }
    if (/accounts\.google\.com|ServiceLogin|\/signin(\/|$|\?)/i.test(url)) {
      return { status: "needs_login", detail: "Google giris ekrani acik. Acilan Chrome penceresinde hesabiniza elle giris yapin.", url };
    }

    // DOM yoklamalari otomasyonun kullandigi sekmeye CDP trafigi bindirir;
    // timeout kisa tutulur (yuklu DOM'da gorunurluk aninda döner).
    const PROBE_MS = 350;

    // 2) reCAPTCHA cercevesi / bot kontrolu
    const captcha = page.locator("iframe[src*='recaptcha'], iframe[title*='recaptcha'], .g-recaptcha, #captcha-form").first();
    if (await captcha.isVisible({ timeout: PROBE_MS }).catch(() => false)) {
      return { status: "needs_verification", detail: "CAPTCHA tespit edildi. Dogrulamayi Chrome penceresinde elle tamamlayin.", url };
    }

    // 3) Yalnizca dogrulama ekranlarina ozgu tam ifadeler
    const strongPhrase = page
      .getByText(
        /verify it'?s you|unusual traffic|confirm you'?re not a robot|2-step verification|kimli[gğ]inizi do[gğ]rula|robot olmad[iı][gğ][iı]n[iı]z[iı]|[iİ]ki a[sş]amal[iı] do[gğ]rulama/i
      )
      .first();
    if (await strongPhrase.isVisible({ timeout: PROBE_MS }).catch(() => false)) {
      const matched = (await strongPhrase.textContent().catch(() => "")) ?? "";
      return {
        status: "needs_verification",
        detail: `Dogrulama ekrani tespit edildi ("${matched.trim().slice(0, 60)}"). Dogrulamayi Chrome penceresinde elle tamamlayin.`,
        url,
      };
    }

    // 4) Belirgin bir giris dugmesi/baglantisi
    const signIn = page.getByRole("button", { name: /^\s*(sign in|oturum a[cç]|giri[sş] yap)\s*$/i }).first();
    const signInLink = page.getByRole("link", { name: /^\s*(sign in|oturum a[cç]|giri[sş] yap)\s*$/i }).first();
    if (
      (await signIn.isVisible({ timeout: PROBE_MS }).catch(() => false)) ||
      (await signInLink.isVisible({ timeout: PROBE_MS }).catch(() => false))
    ) {
      return { status: "needs_login", detail: "Oturum acilmamis gorunuyor. Chrome penceresinde Google hesabiniza giris yapin.", url };
    }

    return { status: "ready", detail: "Flow oturumu hazir", url };
  } catch (err) {
    return { status: "closed", detail: `Sayfa durumu okunamadi: ${err instanceof Error ? err.message : String(err)}` };
  }
}

/**
 * Durum panelleri icin ONBELLEKLI oturum kontrolu.
 *
 * /api/system/status ve /api/flow/session her SSE olayinda / sekme
 * yenilemesinde cagrilir; her cagri canli otomasyon sekmesine DOM yoklamasi
 * bindirirse hem arayuz hem otomasyon yavaslar. Sonuc kisa sure gecerli
 * sayilir; otomasyonun kendi cagrilari (ensureFlowReady) onbellek KULLANMAZ.
 */
const SESSION_CACHE_TTL_MS = 10_000;
let sessionCache: { at: number; value: { status: SessionStatus; detail: string; url?: string } } | null = null;

export async function checkSessionStatusCached(): Promise<{ status: SessionStatus; detail: string; url?: string }> {
  if (!isBrowserOpen()) {
    sessionCache = null;
    return { status: "closed", detail: "Tarayici kapali" };
  }
  if (sessionCache && Date.now() - sessionCache.at < SESSION_CACHE_TTL_MS) return sessionCache.value;
  const value = await checkSessionStatus();
  sessionCache = { at: Date.now(), value };
  return value;
}

export function invalidateSessionCache(): void {
  sessionCache = null;
}
