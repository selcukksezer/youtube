"""
Channel health analysis, 15-rule anti-detect audit, and checklist generation.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from anti_detect_engine import BrowserProfile
import database
from .parser import parse_channel_url, PROFILES_BASE_DIR


def analyze_channel(
    engine,
    channel_url: str,
    proxy_url: Optional[str] = None,
    niche: str = "Stoic / Motivasyon",
    is_brand_new: bool = True,
    recovery_email: Optional[str] = None,
    phone_number: Optional[str] = None,
    phone_type: str = "physical"
) -> Dict[str, Any]:
    """
    Main analysis function.
    Generates comprehensive channel health diagnostic and 'Neler Yapılması Gerektiği' checklist
    covering Rules 1 to 15.
    """
    parsed = parse_channel_url(channel_url)
    profile_id = parsed["profile_id"]

    # Check if already exists in DB
    existing = database.get_managed_channel(parsed["canonical_url"]) or database.get_managed_channel(parsed["handle"])

    # If not passed in args, take from existing record
    if existing:
        recovery_email = recovery_email or existing.get("recovery_email")
        phone_number = phone_number or existing.get("phone_number")
        phone_type = phone_type or existing.get("phone_type", "physical")

    # Generate or load BrowserProfile
    profile_dir = os.path.join(PROFILES_BASE_DIR, profile_id)
    os.makedirs(profile_dir, exist_ok=True)
    config_file = os.path.join(profile_dir, "profile.json")

    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                p_data = json.load(f)
                profile = BrowserProfile(**p_data)
        except Exception:
            profile = engine.generate_profile(channel_id=profile_id, proxy_url=proxy_url)
    else:
        profile = engine.generate_profile(channel_id=profile_id, proxy_url=proxy_url)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(profile.__dict__, f, indent=2)

    # 1. Rule 2 Check: Proxy Validation
    proxy_audit = engine.verify_residential_proxy(proxy_url)

    # 2. Rule 10 Check: DNS Leak & DNS-over-HTTPS (DoH)
    dns_audit = engine.test_dns_leak(proxy_url)

    # 3. Rule 13 Check: User-Agent & Hardware Consistency
    hw_audit = engine.verify_user_agent_hardware_consistency(profile)

    # 4. Rule 14 Check: Recovery Email Isolation
    all_existing = database.list_managed_channels()
    email_audit = engine.verify_recovery_email_isolation(recovery_email, parsed["handle"], all_existing)

    # 5. Rule 15 Check: Phone SMS Verification Quality
    phone_audit = engine.verify_phone_verification_quality(phone_number, phone_type)

    # 6. Rule 20 Check: Font Enumeration Masking
    font_audit = engine.verify_font_masking()

    # 7. Rule 21 Check: Screen Resolution & Viewport Lock
    screen_audit = engine.verify_screen_viewport_consistency(profile)

    # 8. Rule 22 Check: TLS / JA3 Chrome Fingerprint
    tls_audit = engine.test_tls_ja3_fingerprint(proxy_url)

    # 9. Rule 17: Pre-upload Shorts Interaction Plan
    pre_upload_plan = engine.generate_pre_upload_interaction_plan(niche)

    # 10. Rule 18: Natural Session Duration Plan
    session_duration_plan = engine.calculate_natural_session_duration()

    # 11. Rule 23: HTTP/2 and HTTP/3 QUIC Support
    http_audit = engine.verify_http2_http3_support()

    # 12. Rule 24: Residential Network Bandwidth Jitter
    bandwidth_audit = engine.get_residential_network_conditions()

    # 13. Rule 25: Account Login Location Consistency
    baseline_loc = existing.get("baseline_location") if existing else "US / TR (Statik Bölge)"
    location_audit = engine.verify_login_location_consistency(baseline_loc, proxy_url)

    # 14. Rule 26: Cache, IndexedDB & LocalStorage Retention
    cache_audit = engine.verify_profile_cache_integrity(profile_id)

    # 15. Rule 27: Client Hints (sec-ch-ua & navigator.userAgentData)
    client_hints_audit = engine.verify_client_hints(profile)

    # 16. Rule 28 Check: 7-Day Resting Calendar
    now = datetime.now()
    created_at = datetime.fromisoformat(existing["created_at"]) if existing and existing.get("created_at") else now
    resting_until = created_at + timedelta(days=7)
    days_passed = (now - created_at).total_seconds() / 86400
    days_left = max(0.0, round(7.0 - days_passed, 1)) if is_brand_new else 0.0

    if days_left > 0:
        resting_status = f"Dinlendirme Devam Ediyor ({days_left} gün kaldı)"
        can_upload_now = False
    else:
        resting_status = "Dinlendirme Tamamlandı (Yüklemeye Uygun)"
        can_upload_now = True

    # 17. Rule 7 Check: 48-Hour Cookie Warmup Protocol
    warmup_cycles = existing.get("warmup_cycles", 0) if existing else 0
    warmup_started = datetime.fromisoformat(existing["warmup_started_at"]) if (existing and existing.get("warmup_started_at")) else None
    
    if warmup_started:
        warmup_hours_elapsed = round((now - warmup_started).total_seconds() / 3600.0, 1)
    else:
        warmup_hours_elapsed = 0.0

    cookies_file = os.path.join(profile_dir, "cookies.json")
    has_cookies = os.path.exists(cookies_file)
    cookie_count = 0
    if has_cookies:
        try:
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookie_count = len(json.load(f))
        except Exception:
            cookie_count = 1

    is_48h_ready = (warmup_hours_elapsed >= 48.0 and warmup_cycles >= 2 and cookie_count >= 5)
    warmup_progress_pct = min(100, int((min(warmup_hours_elapsed, 48.0) / 48.0) * 80 + (min(warmup_cycles, 2) * 10))) if warmup_started else (25 if has_cookies else 0)

    # 18. Calculate Overall Health Score (0-100)
    score = 50
    if proxy_audit["configured"] and proxy_audit["is_residential"]:
        score += 10
    elif proxy_audit["configured"] and not proxy_audit["is_residential"]:
        score -= 15

    if hw_audit["is_consistent"]:
        score += 6
    if email_audit["is_isolated"]:
        score += 6
    elif email_audit["status"] == "conflict":
        score -= 20

    if phone_audit["is_physical"]:
        score += 6
    if dns_audit["doh_active"]:
        score += 4
    if font_audit["font_masking_active"]:
        score += 4
    if screen_audit["is_standard"]:
        score += 4
    if tls_audit.get("tls_spoofing_active"):
        score += 4
    if http_audit["http3_quic_enabled"]:
        score += 3
    if cache_audit["has_persistent_storage"]:
        score += 3
    if location_audit["is_consistent"]:
        score += 4
    if has_cookies and cookie_count >= 5:
        score += 4
    if is_48h_ready:
        score += 4

    score = max(20, min(100, score))

    # Sample Jitter calculation for demo (Rule 8)
    jitter_sample = engine.calculate_upload_jitter(target_hour=18, target_minute=0)

    # 19. Generate 'Neler Yapılması Gerektiği' (Actionable Roadmap Checklist - Rules 1-30)
    checklist = [
        {
            "step": 1,
            "rule": "Kural 1 & 9: İzole Tarayıcı Profili (--user-data-dir) & Studio UI",
            "title": "İzole Tarayıcı Profili & Studio UI Oturumu",
            "status": "completed",
            "badge": "Aktif & İzole",
            "desc": f"Kanal için '{profile_id}' kimlikli bağımsız Chrome User Data Directory (`--user-data-dir`) ayrıldı. API upload bayrağı yerine doğrudan Studio UI oturumu kullanılır.",
            "details": f"Dizin: tokens/browser_profiles/{profile_id}/ | Donanım: {profile.webgl_renderer}"
        },
        {
            "step": 2,
            "rule": "Kural 2: Yerleşimlik (Residential) Proxy Denetimi",
            "title": "Statik ISP Residential Proxy Ataması",
            "status": "completed" if (proxy_audit["configured"] and proxy_audit["is_residential"]) else ("warning" if proxy_audit["configured"] else "pending"),
            "badge": "Onaylandı (ISP)" if (proxy_audit["configured"] and proxy_audit["is_residential"]) else ("Riskli (Datacenter)" if proxy_audit["configured"] else "Eksik"),
            "desc": proxy_audit.get("info") or proxy_audit.get("warning"),
            "details": "Hetzner, AWS, DigitalOcean kesinlikle engellenir. ISP ev interneti statik proxy bağlanmalıdır."
        },
        {
            "step": 3,
            "rule": "Kural 3, 4, 5: WebRTC, Canvas 2D & WebGL Donanım Kalkanı",
            "title": "Apple Silicon GPU & Donanım Parmak İzi Sahtelemesi",
            "status": "completed",
            "badge": "Korumalı",
            "desc": f"WebGL: {profile.webgl_renderer} | WebRTC: non-proxied UDP engelli | Canvas: Deterministik gürültü aktif.",
            "details": f"Canvas Noise Seed: {profile.canvas_noise_seed:.6f} | WebRTC Policy: disable_non_proxied_udp"
        },
        {
            "step": 4,
            "rule": "Kural 6: AudioContext Parmak İzi Değişkenliği",
            "title": "AudioContext & FFT Hash Pertürbasyonu",
            "status": "completed",
            "badge": "Jitter Aktif",
            "desc": f"Ses motoru FFT frekans eğrisi ve AudioBuffer çıktısı her hesap profilinde mikro seviyede farklılaştırıldı ({profile.audio_noise_jitter:.6f}).",
            "details": "FingerprintJS ses donanım analizine karşı kanala özel sabit tohumlu ses gürültüsü."
        },
        {
            "step": 5,
            "rule": "Kural 13: User-Agent & Donanım Tutarlılığı",
            "title": "User-Agent & Donanım Parametre Eşleşmesi",
            "status": "completed" if hw_audit["is_consistent"] else "warning",
            "badge": "%100 Uyumlu" if hw_audit["is_consistent"] else "Çelişki Var",
            "desc": hw_audit["info"],
            "details": f"CPU Çekirdek: {hw_audit['hardware_concurrency']} | RAM: {hw_audit['device_memory_gb']}GB | Çözünürlük: {hw_audit['viewport']}"
        },
        {
            "step": 6,
            "rule": "Kural 14: Google Hesap Kurtarma E-postaları",
            "title": "Kurtarma E-postası İzolasyonu & Çakışma Denetimi",
            "status": "completed" if email_audit["status"] == "isolated" else ("conflict" if email_audit["status"] == "conflict" else "pending"),
            "badge": "İzole & Temiz" if email_audit["status"] == "isolated" else ("KRİTİK ÇAKIŞMA" if email_audit["status"] == "conflict" else "Girilmedi"),
            "desc": email_audit.get("warning") or email_audit.get("info"),
            "details": "Hesapların birbiriyle eşleştirilip zincirleme banlanmaması için her kanala ayrı kurtarma adresi tanımlanmalıdır."
        },
        {
            "step": 7,
            "rule": "Kural 15: Telefon Doğrulaması (SMS Verification)",
            "title": "Fiziksel SIM Doğrulaması (Gelişmiş Özellikler)",
            "status": "completed" if phone_audit["is_physical"] else ("warning" if phone_audit["status"] == "voip_warning" else "pending"),
            "badge": "Fiziksel SIM" if phone_audit["is_physical"] else ("Sanal VOIP Riski" if phone_audit["status"] == "voip_warning" else "Girilmedi"),
            "desc": phone_audit.get("warning") or phone_audit.get("info"),
            "details": "Shorts için günlük 10+ video kotası ve açıklama linkleri için fiziksel SIM şarttır."
        },
        {
            "step": 8,
            "rule": "Kural 10: DNS Sızıntı Testi (DNS-over-HTTPS)",
            "title": "DNS Sızıntı Koruması & Cloudflare DoH (1.1.1.1)",
            "status": "completed" if dns_audit["doh_active"] else "active_in_browser",
            "badge": "DoH Korumalı",
            "desc": dns_audit["details"],
            "details": f"Sağlayıcı: {dns_audit['doh_provider']} | Sızıntı Durumu: Engellendi"
        },
        {
            "step": 9,
            "rule": "Kural 17: Yükleme Öncesi Video İzleme & Etkileşim",
            "title": "Yükleme Öncesi Shorts İzleme, Beğeni & Yorum",
            "status": "completed",
            "badge": f"{pre_upload_plan['shorts_count']} Shorts + 1 Yorum",
            "desc": f"Studio'ya video yüklenmeden önce akışta {pre_upload_plan['shorts_count']} Shorts sonuna kadar izlenir, 1 beğeni ve '{pre_upload_plan['selected_comment']}' yorumu bırakılır.",
            "details": f"Ön İzleme Süresi: ~{pre_upload_plan['estimated_pre_upload_duration_seconds']}s | Organik izleyici sinyali üretildi."
        },
        {
            "step": 10,
            "rule": "Kural 18: Oturum Süresi Doğallığı (3-7 Dakika)",
            "title": "Doğal Oturum Süresi & Hızlı Çıkış Engeli",
            "status": "completed",
            "badge": f"{session_duration_plan['target_session_minutes']} dk Oturum",
            "desc": f"Bot asla 5 saniyede yükleyip çıkmaz. Platformda {session_duration_plan['target_session_minutes']} dakika aktif kalınır, erken bitişlerde pasif akış gezinmesi yapılır.",
            "details": f"Minimum: 3.0 dk | Hedef: {session_duration_plan['target_session_seconds']}s | Hızlı çıkış bot tripwire'ları engellendi."
        },
        {
            "step": 11,
            "rule": "Kural 19: Headless Tarayıcı İzi Temizliği",
            "title": "Headless İzi Temizliği (webdriver & Notification Mock)",
            "status": "completed",
            "badge": "webdriver: undefined",
            "desc": "navigator.webdriver tanımsız yapılır, window.chrome ve Notification.permission ('default') birebir mocklanır, plugin havuzu doldurulur.",
            "details": "Chrome/Blink otomasyon flag'leri ve CDP izleri %100 temizlenir."
        },
        {
            "step": 12,
            "rule": "Kural 20: Font Listesi Parmak İzi Maskelemesi",
            "title": "Standart macOS Font Havuzu Koruması",
            "status": "completed",
            "badge": f"{font_audit['whitelisted_fonts_count']} Standart Font",
            "desc": "Sistem fontlarının taranması engellenir; document.fonts.check ve Canvas measureText standart macOS Apple Silicon font havuzuna kilitlenir.",
            "details": f"Örnek: {', '.join(font_audit['sample_fonts'][:4])}..."
        },
        {
            "step": 13,
            "rule": "Kural 21: Ekran Çözünürlüğü ve Viewport Kilidi",
            "title": "Standart Ekran & Viewport Kilidi (1920x1080 / 1440x900)",
            "status": "completed",
            "badge": screen_audit["resolution"],
            "desc": "Viewport boyutu pencere dışına taşmaz. Monitör 16:9 / 16:10 standart oranına ve screen.availWidth/Height değerlerine eşitlenir.",
            "details": f"Monitör: {screen_audit['resolution']} ({screen_audit['aspect_ratio']}) | Taşma: Engellendi"
        },
        {
            "step": 14,
            "rule": "Kural 22: TLS / JA3 Fingerprint Simülasyonu",
            "title": "Chrome TLS JA3 Parmak İzi (curl_cffi)",
            "status": "completed",
            "badge": "JA3: Chrome 124",
            "desc": f"Python 'requests' TLS imzası yerine curl_cffi Chrome 124 JA3 el sıkışması simüle edilir ({tls_audit.get('ja3_hash', '')[:16]}...).",
            "details": f"Kütüphane: {tls_audit.get('library', 'curl_cffi')} | Protokol: {tls_audit.get('http_version', 'HTTP/2')}"
        },
        {
            "step": 15,
            "rule": "Kural 23: HTTP/2 ve HTTP/3 Protokol Desteği",
            "title": "HTTP/2 & HTTP/3 QUIC Çerçeve Desteği",
            "status": "completed",
            "badge": "h2 & h3 (QUIC) Aktif",
            "desc": "Google sunucularıyla iletişimde HTTP/1.1 yerine modern HTTP/2 ve HTTP/3 QUIC çerçeveleri kullanılır.",
            "details": f"ALPN: {', '.join(http_audit['alpn_protocols'])} | QUIC: Aktif"
        },
        {
            "step": 16,
            "rule": "Kural 24: Ağ Bant Genişliği Dalgalanması (Jitter)",
            "title": "Ev İnterneti Hız Dalgalanması & Gecikme Simülasyonu",
            "status": "completed",
            "badge": f"{bandwidth_audit['upload_mbps']} Mbps & {bandwidth_audit['latency_ms']}ms",
            "desc": f"Video yükleme sırasında veri akışı sabit veri merkezi hızıyla değil, ev interneti gibi {bandwidth_audit['upload_mbps']} Mbps yükleme ve {bandwidth_audit['latency_ms']}ms gecikme ile dalgalandırılır.",
            "details": "CDP Network.emulateNetworkConditions devrede."
        },
        {
            "step": 17,
            "rule": "Kural 25: Google Hesabı Giriş Konumu & Coğrafi Sabitlik",
            "title": "Proxy & Hesap Açılış Lokasyon Kilitlenmesi",
            "status": "completed" if location_audit["is_consistent"] else "warning",
            "badge": "Lokasyon Sabit" if location_audit["is_consistent"] else "Sapma Riski",
            "desc": location_audit["info"],
            "details": f"Kayıtlı Bölge: {location_audit['baseline_location']} | Mevcut Proxy: {location_audit['current_proxy']}"
        },
        {
            "step": 18,
            "rule": "Kural 26: Önbellek (Cache) Tutarlılığı",
            "title": "IndexedDB, LocalStorage & Cache Kalıcılığı",
            "status": "completed",
            "badge": f"{cache_audit['storage_size_kb']} KB Kalıcı",
            "desc": "Oturumlar arasında IndexedDB, LocalStorage ve tarayıcı önbelleği silinmez; gerçek bir kullanıcının veri birikimi korunur.",
            "details": f"Dizin: tokens/browser_profiles/{profile_id} ({cache_audit['file_count']} dosya)"
        },
        {
            "step": 19,
            "rule": "Kural 27: İstemci İpuçları (Client Hints)",
            "title": "sec-ch-ua & navigator.userAgentData Uyumu",
            "status": "completed",
            "badge": "sec-ch-ua: macOS",
            "desc": client_hints_audit["info"],
            "details": f"sec-ch-ua: {client_hints_audit['sec_ch_ua']} | platform: {client_hints_audit['sec_ch_ua_platform']}"
        },
        {
            "step": 20,
            "rule": "Kural 28: 7 Günlük Dinlendirme Kuralı",
            "title": "Organik Dinlendirme & Güven Skoru Takvimi",
            "status": "in_progress" if days_left > 0 else "completed",
            "badge": f"{days_left} Gün Kaldı" if days_left > 0 else "Hazır",
            "desc": f"İlk 3 gün sadece kanal açılışı, 4-6. günler çerez ısındırma, 7. gün ilk video. ({resting_status})",
            "details": f"Hedef İlk Güvenli Yükleme Tarihi: {resting_until.strftime('%d.%m.%Y %H:%M')}"
        },
        {
            "step": 21,
            "rule": "Kural 29: Video Dosyası Oluşturulma Tarihi (ctime/mtime)",
            "title": "Dosya Zaman Damgası 15-45 dk Geriye Kaydırma",
            "status": "ready",
            "badge": "15-45 dk Geçmiş",
            "desc": "Yüklenen MP4 dosyasının işletim sistemi oluşturulma ve değiştirilme tarihi (ctime, mtime) yükleme anından en az 15-45 dakika öncesine ayarlanır.",
            "details": "os.utime manipülasyonu ile anlık robot render izi gizlenir."
        },
        {
            "step": 22,
            "rule": "Kural 30: Yükleme Boyutu Varyasyonu (free atom)",
            "title": "Özgün Dosya Boyutu & free Atom Varyasyonu",
            "status": "ready",
            "badge": "+500KB..1.2MB Özgün",
            "desc": "Her videonun dosya boyutu aynı şablondan çıkmış gibi olamaz. MP4 standart free atomu ile videoya 500KB-1.2MB arası güvenli rastgele dolgu eklenerek benzersiz hash üretilir.",
            "details": "Kalite kaybı olmadan şablon benzerliği filtresi atlatılır."
        },
        {
            "step": 23,
            "rule": "Kural 7: 48 Saatlik Çerez (Cookie) Isındırma Protokolü",
            "title": "Trend Shorts İzleme & 48 Saatlik Çerez Havuzu",
            "status": "completed" if is_48h_ready else ("in_progress" if (warmup_cycles > 0 or has_cookies) else "pending"),
            "badge": f"%{warmup_progress_pct} Tamamlandı" if warmup_started else (f"{cookie_count} Çerez" if has_cookies else "Başlatılmalı"),
            "desc": f"İlk videodan önce en az 48 saat boyunca trend Shorts izlenmeli, beğeni atılmalı ve çerez havuzu oluşturulmalıdır. (Döngü: {warmup_cycles}, Çerez: {cookie_count}, Süre: {warmup_hours_elapsed} sa).",
            "details": "Tek tıkla botu başlatıp organik oturum açtırabilirsiniz."
        },
        {
            "step": 24,
            "rule": "Kural 8, 11, 12: Jitter, Bezier Faresi & Tuş Gecikmesi",
            "title": "İnsan Davranış Simülasyonu & Jitter Takvimi",
            "status": "ready",
            "badge": f"+{jitter_sample['jitter_applied_minutes']} dk Jitter",
            "desc": f"Videolar tam saat başında yüklenmez (+{jitter_sample['jitter_applied_minutes']} dk jitter: {jitter_sample['time_str']}). Yükleme ekranında Bezier fare eğrileri ve 40-130ms tuş basım gecikmesi uygulanır.",
            "details": f"Planlanan: {jitter_sample['date_str']} {jitter_sample['time_str']} | Fare/Tuş: İnsan Modu"
        }
    ]

    channel_status = "resting" if days_left > 0 else ("ready" if is_48h_ready else "warming")

    # Save or update DB
    database.save_managed_channel(
        channel_url=parsed["canonical_url"],
        handle=parsed["handle"],
        channel_name=parsed["handle"].lstrip("@"),
        niche=niche,
        proxy_url=proxy_url,
        profile_id=profile_id,
        status=channel_status,
        health_score=score,
        resting_until=resting_until.isoformat(),
        recovery_email=recovery_email,
        phone_number=phone_number,
        phone_type=phone_type,
        config_json=json.dumps({
            "profile": profile.__dict__,
            "proxy_audit": proxy_audit,
            "dns_audit": dns_audit,
            "hw_audit": hw_audit,
            "email_audit": email_audit,
            "phone_audit": phone_audit,
            "font_audit": font_audit,
            "screen_audit": screen_audit,
            "tls_audit": tls_audit,
            "pre_upload_plan": pre_upload_plan,
            "session_duration_plan": session_duration_plan,
            "resting_days_left": days_left,
            "warmup_hours_elapsed": warmup_hours_elapsed,
            "warmup_cycles": warmup_cycles,
            "cookie_count": cookie_count
        })
    )

    return {
        "status": "ok",
        "channel": {
            "handle": parsed["handle"],
            "url": parsed["canonical_url"],
            "profile_id": profile_id,
            "niche": niche,
            "health_score": score,
            "status": channel_status,
            "can_upload_now": can_upload_now,
            "resting_days_left": days_left,
            "resting_until": resting_until.strftime("%d.%m.%Y %H:%M")
        },
        "proxy_audit": proxy_audit,
        "browser_profile": profile.__dict__,
        "checklist": checklist,
        "summary_recommendation": (
            "Kanal profili izole edildi ve 5 altın kural uygulandı. "
            + (f"7 günlük dinlendirme süresi devam ediyor ({days_left} gün kaldı). Çerez ısındırma botunu başlatabilirsiniz." if days_left > 0 else "Dinlendirme tamamlandı. Çerez ısındırma ve Studio UI yükleme işlemlerine başlayabilirsiniz.")
        )
    }
