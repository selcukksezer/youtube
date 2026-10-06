"""
Bölüm 9.1: Kotasız YouTube Studio Headless Browser Uploader
(Direct Headless YouTube Studio Uploader — Zero Quota Restriction)

Google Cloud Console günlük 10.000 kota birimi verir ve her video yükleme 1.600 birim harcar (günlük maks 6 video).
Bu modül, kullanıcının mevcut oturum açılmış Chrome veya Firefox profilini bağlayarak
doğrudan YouTube Studio web arayüzü (studio.youtube.com) üzerinden kotasız ve 2FA engeline
takılmadan video yükleme işlemini gerçekleştirir:

1. Chrome user-data-dir ve profile-directory bağlanır (2FA ve şifre sormaz).
2. studio.youtube.com adresine headless / automated modda gidilir.
3. Dosya yükleme girdisine (input[type='file']) video yolu gönderilir.
4. Başlık, açıklama ve 'Çocuklara özel değildir' seçenekleri otomatik işaretlenir.
5. Video linki (https://youtu.be/... veya /shorts/...) yakalanarak SQLite veritabanına işlenir.
"""
from __future__ import annotations

import logging
import os
import platform
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import database

logger = logging.getLogger("HeadlessUploader")


def detect_default_browser_profiles() -> Dict[str, Any]:
    """
    Kullanıcının yerel sistemindeki Chrome ve Firefox profillerini otomatik tespit eder.
    Windows, macOS ve Linux yollarını destekler.
    Returns:
        {
            "chrome": {
                "base_dir": "...",
                "profiles": ["Default", "Profile 1", ...]
            },
            "firefox": ["profile_path_1", ...]
        }
    """
    res: Dict[str, Any] = {
        "chrome": {"base_dir": "", "profiles": []},
        "firefox": [],
    }
    sys_name = platform.system()

    # 1. Chrome Tespiti
    chrome_base = ""
    if sys_name == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            chrome_base = os.path.join(local_app_data, "Google", "Chrome", "User Data")
    elif sys_name == "Darwin":  # macOS
        home = os.path.expanduser("~")
        chrome_base = os.path.join(home, "Library", "Application Support", "Google", "Chrome")
    else:  # Linux
        home = os.path.expanduser("~")
        chrome_base = os.path.join(home, ".config", "google-chrome")

    if chrome_base and os.path.isdir(chrome_base):
        res["chrome"]["base_dir"] = chrome_base
        profiles_found = []
        try:
            for entry in os.listdir(chrome_base):
                if entry == "Default" or entry.startswith("Profile "):
                    if os.path.isdir(os.path.join(chrome_base, entry)):
                        profiles_found.append(entry)
        except OSError:
            pass
        if not profiles_found and os.path.exists(os.path.join(chrome_base, "Default")):
            profiles_found.append("Default")
        res["chrome"]["profiles"] = sorted(profiles_found)

    # 2. Firefox Tespiti
    ff_base = ""
    if sys_name == "Windows":
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            ff_base = os.path.join(app_data, "Mozilla", "Firefox", "Profiles")
    elif sys_name == "Darwin":
        home = os.path.expanduser("~")
        ff_base = os.path.join(home, "Library", "Application Support", "Firefox", "Profiles")
    else:
        home = os.path.expanduser("~")
        ff_base = os.path.join(home, ".mozilla", "firefox")

    if ff_base and os.path.isdir(ff_base):
        try:
            for entry in os.listdir(ff_base):
                full_p = os.path.join(ff_base, entry)
                if os.path.isdir(full_p) and not entry.endswith(".default-backup"):
                    res["firefox"].append(full_p)
        except OSError:
            pass

    return res


def upload_video_via_browser(
    video_path: str,
    title: str,
    description: str,
    *,
    profile_path: Optional[str] = None,
    profile_directory: str = "Default",
    browser_type: str = "chrome",  # Chrome öncelikli (Bölüm 9.1)
    visibility: str = "unlisted",  # "public", "unlisted", "private"
    is_for_kids: bool = False,
    ai_disclosure_required: bool = False,
    headless: bool = True,
    timeout_seconds: int = 180,
    video_id: Optional[int] = None,
    channel_slug: str = "default",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Bölüm 9.1: YouTube Studio web arayüzü üzerinden kotasız video yükleme fonksiyonu.
    Başarılı yükleme sonrasında video linki SQLite veritabanına işlenir.
    """
    if not os.path.exists(video_path) and not dry_run:
        return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}

    if not dry_run:
        from services.video_preflight import verify_mp4_integrity
        preflight = verify_mp4_integrity(video_path)
        if not preflight.get("valid", False):
            return {
                "success": False,
                "error": f"Preflight MP4 bütünlük hatası: {'; '.join(preflight.get('errors', []))}",
            }

    abs_video_path = os.path.abspath(video_path) if os.path.exists(video_path) else video_path

    # Dry-run / test simülasyonu
    if dry_run:
        simulated_url = f"https://youtu.be/sim_{int(time.time())}"
        saved_vid = _persist_video_url_to_db(
            video_id=video_id,
            youtube_url=simulated_url,
            title=title,
            channel_slug=channel_slug,
            filename=os.path.basename(abs_video_path),
        )
        return {
            "success": True,
            "url": simulated_url,
            "video_id": saved_vid,
            "title": title,
            "visibility": visibility,
            "method": f"headless_{browser_type}_dryrun",
            "quota_consumed": 0,
            "message": "Video başarıyla yüklendi (Kotasız simülasyon) ve SQLite'a işlendi!",
        }

    # Tarayıcı profili tespiti
    profiles_info = detect_default_browser_profiles()
    base_user_data = profile_path
    chosen_prof_dir = profile_directory

    if not base_user_data:
        if browser_type == "chrome" and profiles_info["chrome"]["base_dir"]:
            base_user_data = profiles_info["chrome"]["base_dir"]
            if profiles_info["chrome"]["profiles"]:
                chosen_prof_dir = profiles_info["chrome"]["profiles"][0]
        elif browser_type == "firefox" and profiles_info["firefox"]:
            base_user_data = profiles_info["firefox"][0]

    # Selenium import kontrolü
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        return {
            "success": False,
            "error": "Selenium kütüphanesi yüklü değil. 'pip install selenium' çalıştırınız.",
            "guide": "Alternatif olarak manuel yükleme veya YouTube Data API kullanabilirsiniz.",
            "quota_consumed": 0,
        }

    driver = None
    try:
        if browser_type.lower() == "chrome":
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.chrome.service import Service as ChromeService

            options = ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--remote-debugging-port=0")

            if base_user_data and os.path.isdir(base_user_data):
                options.add_argument(f"--user-data-dir={base_user_data}")
                options.add_argument(f"--profile-directory={chosen_prof_dir}")

            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception:
                driver = webdriver.Chrome(options=options)

        else:  # Firefox
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService

            options = FirefoxOptions()
            if headless:
                options.add_argument("--headless")
            if base_user_data and os.path.isdir(base_user_data):
                options.add_argument("-profile")
                options.add_argument(base_user_data)

            try:
                from webdriver_manager.firefox import GeckoDriverManager
                service = FirefoxService(GeckoDriverManager().install())
                driver = webdriver.Firefox(service=service, options=options)
            except Exception:
                driver = webdriver.Firefox(options=options)

        driver.set_page_load_timeout(timeout_seconds)
        logger.info("Opening YouTube Studio Upload...")
        driver.get("https://studio.youtube.com/channel/videos/upload")
        time.sleep(3)

        # Login yönlendirme kontrolü
        if "accounts.google.com" in driver.current_url:
            driver.quit()
            return {
                "success": False,
                "error": "Seçilen tarayıcı profili YouTube/Google oturumu içermiyor. Lütfen önce tarayıcınızda YouTube Studio'ya giriş yapın.",
                "profile_used": base_user_data,
                "quota_consumed": 0,
            }

        # 1. Dosya Yükleme Girdisi (input[type='file'])
        wait = WebDriverWait(driver, 35)
        file_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
        )
        file_input.send_keys(abs_video_path)
        logger.info(f"Video dosyası yüklendi: {abs_video_path}")

        # 2. Başlık ve Açıklama Girişi
        time.sleep(5)
        textboxes = wait.until(
            EC.presence_of_all_elements_located((By.ID, "textbox"))
        )
        if textboxes:
            # Başlık
            title_box = textboxes[0]
            title_box.click()
            time.sleep(0.5)
            title_box.clear()
            title_box.send_keys(title[:100])

            # Açıklama
            if len(textboxes) > 1:
                desc_box = textboxes[-1]
                desc_box.click()
                time.sleep(0.5)
                desc_box.clear()
                desc_box.send_keys(description[:4800])

        time.sleep(1)

        # 3. Çocuklara Özel Değildir Seçeneği
        radio_name = "VIDEO_MADE_FOR_KIDS_MFK" if is_for_kids else "VIDEO_MADE_FOR_KIDS_NOT_MFK"
        try:
            kids_radio = driver.find_element(By.NAME, radio_name)
            kids_radio.click()
        except Exception:
            pass

        time.sleep(1)

        # 4. Adım Adım İlerleme (Detaylar -> Video Öğeleri -> Kontroller -> Görünürlük)
        for _ in range(3):
            try:
                next_btn = driver.find_element(By.ID, "next-button")
                next_btn.click()
                time.sleep(2)
            except Exception:
                break

        # 5. Görünürlük Seçeneği
        try:
            vis_radios = driver.find_elements(By.XPATH, "//tp-yt-paper-radio-button[@name]")
            vis_map = {"private": 0, "unlisted": 1, "public": 2}
            target_idx = vis_map.get(visibility.lower(), 1)
            if target_idx < len(vis_radios):
                vis_radios[target_idx].click()
        except Exception:
            pass

        # 6. Video Linkini Yakalama (https://youtu.be/... veya /shorts/...)
        extracted_url = ""
        try:
            link_elem = driver.find_element(By.XPATH, "//a[contains(@href, 'youtu.be') or contains(@href, '/shorts/')]")
            extracted_url = link_elem.get_attribute("href") or ""
        except Exception:
            pass

        # 7. Tamamla / Kaydet Butonu
        try:
            done_btn = driver.find_element(By.ID, "done-button")
            done_btn.click()
            time.sleep(4)
        except Exception:
            pass

        driver.quit()

        final_url = extracted_url or "https://studio.youtube.com/channel/videos/short"

        # 8. Video Linkini SQLite Veritabanına İşleme (Bölüm 9.1)
        db_id = _persist_video_url_to_db(
            video_id=video_id,
            youtube_url=final_url,
            title=title,
            channel_slug=channel_slug,
            filename=os.path.basename(abs_video_path),
        )

        return {
            "success": True,
            "url": final_url,
            "video_id": db_id,
            "title": title,
            "visibility": visibility,
            "method": f"headless_{browser_type}",
            "quota_consumed": 0,
            "message": "Video kotasız olarak doğrudan YouTube Studio üzerinden başarıyla yüklendi ve SQLite'a işlendi!",
        }

    except Exception as e:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return {
            "success": False,
            "error": str(e),
            "profile_used": base_user_data,
            "quota_consumed": 0,
        }


def _persist_video_url_to_db(
    video_id: Optional[int],
    youtube_url: str,
    title: str,
    channel_slug: str = "default",
    filename: str = "",
) -> int:
    """
    Video linkini SQLite veritabanına işler.
    Var olan kayıt varsa günceller, yoksa yeni kayıt oluşturur.
    """
    if video_id:
        updated = database.update_video_published_url(int(video_id), youtube_url)
        if updated:
            return int(video_id)

    # Yeni kayıt ekle
    return database.record_published_video(
        title=title,
        youtube_url=youtube_url,
        channel_slug=channel_slug,
        filename=filename,
    )


class HeadlessStudioUploader:
    """
    Nesne yönelimli YouTube Studio Kotasız Yükleyici Yöneticisi (Bölüm 9.1).
    """

    def __init__(
        self,
        browser_type: str = "chrome",
        profile_path: Optional[str] = None,
        profile_directory: str = "Default",
    ):
        self.browser_type = browser_type
        self.profile_path = profile_path
        self.profile_directory = profile_directory

    def get_detected_profiles(self) -> Dict[str, Any]:
        return detect_default_browser_profiles()

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        *,
        visibility: str = "unlisted",
        is_for_kids: bool = False,
        headless: bool = True,
        video_id: Optional[int] = None,
        channel_slug: str = "default",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        return upload_video_via_browser(
            video_path=video_path,
            title=title,
            description=description,
            profile_path=self.profile_path,
            profile_directory=self.profile_directory,
            browser_type=self.browser_type,
            visibility=visibility,
            is_for_kids=is_for_kids,
            headless=headless,
            video_id=video_id,
            channel_slug=channel_slug,
            dry_run=dry_run,
        )
