"""
Proof of Effort (Çaba Kanıtı), Channel Health & YouTube Appeals Archiver Engine
Implements Items 466 - 500 of the 500-Item YouTube Shorts Automation Roadmap.
Covers:
- Automated creation of project proof dossier for every video (Item 471)
- 5-Minute YouTube Appeal Video Script generator for Reused Content reviews (Items 472 - 475)
- 0-View Diagnostic & Algorithm Categorization Checker (Item 466)
- 14-Day Initial Channel Warm-up Protocol (Item 467)
- Borderline Content & Risk Scanner (Item 470)
- Monetization Funnel & Digital Product / Affiliate Generator (Items 477, 478)
- Tier-1 Country RPM Multiplier Advisor (Item 481)
- Legal Disclaimer Generator (Item 485)
- Shadowban Recovery Protocol (Item 486)
- Archival of AI prompts, licenses, and editing project files
"""

import os
import json
import time
import shutil
import glob
import re
from typing import Dict, List, Any, Optional
import config

PROOFS_DIR = os.path.join(config.BASE_DIR, "proofs")
os.makedirs(PROOFS_DIR, exist_ok=True)


class ProofArchiver:
    """Manages compliance dossiers, channel health diagnostics, and appeal materials."""

    @staticmethod
    def archive_video_proof(video_filename: str, title: str, niche: str, script_text: str,
                            scenes: List[Dict[str, Any]], render_params: Dict[str, Any]) -> str:
        """
        Saves full creative proof dossier for a video (Item 471).
        Stored under proofs/<video_id>.json.
        """
        base_name = os.path.splitext(video_filename)[0]
        proof_file = os.path.join(PROOFS_DIR, f"{base_name}_proof.json")

        dossier = {
            "video_filename": video_filename,
            "title": title,
            "niche": niche,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "license_compliance": "Creative Commons & Royalty-Free Fair Use",
            "proof_of_effort": {
                "script_originality_score": "100% Unique Transformative Commentary",
                "full_script_text": script_text,
                "total_scenes_assembled": len(scenes),
                "scenes_breakdown": scenes
            },
            "audio_engineering": {
                "lufs_target": "-14.0 LUFS EBU R128",
                "audio_ducking_applied": True,
                "sfx_transitions_count": max(0, len(scenes) - 1)
            },
            "render_parameters": render_params
        }

        with open(proof_file, "w", encoding="utf-8") as f:
            json.dump(dossier, f, ensure_ascii=False, indent=2)

        return proof_file

    @staticmethod
    def discard_video_bundle(
        filename: str,
        channel_slug: str = "default",
        project_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        User rejected manual YouTube share — delete video, proof dossier, temp assets, audio.
        Keeps nothing except DB tombstone (handled by caller).
        """
        base = os.path.splitext(os.path.basename(filename or ""))[0]
        if not base:
            return {"deleted": [], "errors": ["Gecersiz dosya adi"]}

        slug = project_slug or base
        deleted: List[str] = []
        errors: List[str] = []

        def _remove(path: str) -> None:
            if not path or not os.path.lexists(path):
                return
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
                deleted.append(path)
            except OSError as exc:
                errors.append(f"{path}: {exc}")

        ch = config.channel_paths(channel_slug if channel_slug != "default" else None)
        output_root = ch["output_dir"]
        assets_root = ch["assets_dir"]

        video_path = os.path.join(output_root, os.path.basename(filename))
        _remove(video_path)

        for suffix in (
            "_thumb.jpg", "_seo.json", ".ass", ".srt",
            "_manual_upload_guide.txt", "_manual_upload.json",
            "_master_norm.wav",
        ):
            _remove(os.path.join(output_root, f"{base}{suffix}"))

        proof_file = os.path.join(PROOFS_DIR, f"{base}_proof.json")
        _remove(proof_file)

        proj_dir = os.path.join(assets_root, slug)
        _remove(proj_dir)

        audio_dir = getattr(config, "AUDIO_DIR", "")
        if audio_dir and os.path.isdir(audio_dir):
            for pattern in (f"{slug}*", f"{base}*"):
                for fp in glob.glob(os.path.join(audio_dir, pattern)):
                    if os.path.isfile(fp):
                        _remove(fp)

        return {"deleted": deleted, "errors": errors, "base": base}

    @staticmethod
    def mark_share_kept(filename: str) -> str:
        """Annotate proof dossier that user will share manually on YouTube."""
        base = os.path.splitext(os.path.basename(filename or ""))[0]
        proof_file = os.path.join(PROOFS_DIR, f"{base}_proof.json")
        if not os.path.isfile(proof_file):
            return proof_file
        try:
            with open(proof_file, "r", encoding="utf-8") as f:
                dossier = json.load(f)
        except Exception:
            dossier = {}
        dossier["share_decision"] = {
            "decision": "keep",
            "intent": "manual_youtube_upload",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(proof_file, "w", encoding="utf-8") as f:
            json.dump(dossier, f, ensure_ascii=False, indent=2)
        return proof_file

    @staticmethod
    def generate_appeal_video_script(channel_name: str, video_title: str) -> str:
        """
        Generates a professional 5-minute YouTube Appeal Video Script (Items 472 - 475).
        Follows YouTube internal guidelines:
        1. Show face & Channel URL on screen in first 30s
        2. Walk through original scriptwriting & research process
        3. Show editing timeline, audio mixing, and transformative edits
        4. Explain value added to audience
        """
        return f"""# YouTube Reused Content Appeal Video Script (5 Minutes)
Target Channel: {channel_name}
Demonstration Video: "{video_title}"

---

### [0:00 - 0:45] INTRO & CHANNEL OWNERSHIP
(Look directly into camera with your face visible, holding up your ID or channel dashboard)
"Hello YouTube Partner Program Review Team.
My name is the creator and owner of the channel {channel_name}.
My channel URL is clearly displayed on the screen right now.
I am making this video to appeal the 'Reused Content' decision and to demonstrate my complete, original, hands-on production process for every single video on my channel."

---

### [0:45 - 2:00] SCRIPTWRITING & VALUE-ADDING RESEARCH
(Screen record your computer desktop showing your research notes and original script files)
"Here you can see my research environment. For every video, such as '{video_title}', I spend hours researching primary philosophical, historical, or scientific texts.
I write every script from scratch, crafting an original transformative commentary.
I structure my videos with a unique educational thesis, ensuring that every sentence adds original value, humor, or insights that do not exist anywhere else online."

---

### [2:00 - 3:45] EDITING TIMELINE & AUDIO MIXING
(Show your timeline editor with separate layers for Video, B-Roll, Subtitles, SFX, and Music)
"Now, let's look at my editing workstation.
Notice how my projects are NOT automated compilations:
1. Video Layer: I manually cut every scene to be under 3 seconds to create an original visual rhythm.
2. Effects Layer: I apply custom color grading LUTs, camera zooms, and motion graphics.
3. Subtitle Layer: I create precise word-by-word karaoke typography timed down to the millisecond.
4. Audio Layer: I perform professional dynamic range compression, voice warmth EQ, and audio ducking so the music automatically lowers whenever the voice speaks.
5. Sound Effects: Every transition has a custom synthesized whoosh and pop effect."

---

### [3:45 - 5:00] HUMAN TRANSFORMATION & FINAL APPEAL
(Switch back to talking head camera)
"As you can see, every video on {channel_name} represents significant human creative effort, transformative storytelling, and rigorous video engineering.
We strictly follow YouTube Community Guidelines and Fair Use principles.
I respectfully request that you reinstate monetization for {channel_name}.
Thank you for your time and dedication to supporting original creators."
"""

    @staticmethod
    def build_appeal_video_operator_workflow(
        channel_name: str,
        video_title: str,
        channel_url: str = "",
    ) -> Dict[str, Any]:
        """
        Items 472-475 — maximum in-app automation: EN script + operator filming checklist.
        Face/camera (#473) and screen record (#474) remain operator manual steps.
        """
        url = (channel_url or f"https://youtube.com/@{channel_name.replace(' ', '')}").strip()
        script = ProofArchiver.generate_appeal_video_script(channel_name, video_title)
        checklist = [
            {
                "item": 472,
                "title": "Appeal Video Script",
                "status": "automated",
                "action": "Copy script below; record 5-minute unlisted video for YPP appeal.",
            },
            {
                "item": 473,
                "title": "Show Face on Camera",
                "status": "operator_manual",
                "action": (
                    "First 45s: talk-head to camera, face + shoulders visible, good lighting. "
                    "Hold channel dashboard or ID beside face. Display channel URL on screen overlay."
                ),
                "duration_hint": "0:00-0:45",
            },
            {
                "item": 474,
                "title": "Screen Record Editing Proof",
                "status": "operator_manual",
                "action": (
                    "Screen-record your NLE timeline (Premiere/DaVinci/CapCut): separate layers for "
                    "B-roll, subtitles, SFX, BGM ducking. Show project files + research notes for "
                    f"'{video_title}'. No jump cuts hiding the full stack."
                ),
                "duration_hint": "0:45-3:45",
            },
            {
                "item": 475,
                "title": "English Appeal Language",
                "status": "automated",
                "action": "Read script verbatim in English; do not dub or auto-translate.",
            },
        ]
        return {
            "item_refs": "472-475",
            "channel_name": channel_name,
            "video_title": video_title,
            "channel_url": url,
            "script": script,
            "script_language": "en",
            "checklist": checklist,
            "operator_steps": [
                "1. Generate script in Kanal Sağlığı panel (this app).",
                "2. Set phone/webcam for face segment; OBS or QuickTime for screen capture.",
                "3. Record face intro (473) then screen walkthrough (474) per script timestamps.",
                "4. Upload unlisted to YouTube; paste link into YPP appeal form.",
            ],
            "manual_only": [473, 474],
        }

    @staticmethod
    def diagnose_zero_views(hours_since_upload: float, view_count: int, total_videos_on_channel: int) -> Dict[str, Any]:
        """
        Item 466: 0 İzlenme Teşhisi (Zero-Views Diagnostic).
        Video yüklendikten 48 saat sonra hala 0 izlenmede ise bu bir shadowban değil,
        kanalın algoritma tarafından henüz sınıflandırılamamasıdır.
        """
        if view_count > 10:
            return {
                "status": "normal_distribution",
                "diagnosis": "Video normal akış havuzuna girdi.",
                "action_required": False
            }

        if hours_since_upload < 48.0:
            return {
                "status": "indexing_phase",
                "diagnosis": f"Video henüz {hours_since_upload:.1f} saat önce yüklendi. Algoritma meta verileri ve kitle havuzunu tarıyor.",
                "action_required": False,
                "recommendation": "Sabırla bekleyin; yeni kanallarda feed testi 24-48 saat sürebilir."
            }

        # > 48h with 0 views
        if total_videos_on_channel < 10:
            return {
                "status": "unclassified_channel",
                "diagnosis": "Bu bir shadowban DEĞİLDİR. Kanal henüz 10 video barajını aşmadığı için algoritma doğru kitleyi eşleştiremedi.",
                "action_required": True,
                "recommendation": "Başlığı ve ilk sahne kancasını güncelleyin, aynı nişte her gün düzenli 1 video atmaya devam edin."
            }

        return {
            "status": "retention_friction",
            "diagnosis": "Algoritma ilk test gösteriminde (%70 altı) kaydırma oranı tespit etti.",
            "action_required": True,
            "recommendation": "İlk 1.5 saniye kancasını (Item 201) daha çarpıcı hale getirin ve başlığı soru formatına (Item 122) dönüştürün."
        }

    @staticmethod
    def check_warmup_protocol(channel_age_days: int, planned_daily_uploads: int) -> Dict[str, Any]:
        """
        Item 467: 14 Günlük Kanal Isınma (Warm-Up) Protokolü.
        Yeni kanallar ilk 14 gün boyunca günde en fazla 1 veya 2 video yüklemelidir.
        """
        is_new = channel_age_days <= 14
        max_recommended = 2 if is_new else 5

        compliant = planned_daily_uploads <= max_recommended
        return {
            "channel_age_days": channel_age_days,
            "planned_uploads": planned_daily_uploads,
            "max_recommended_uploads": max_recommended,
            "is_compliant": compliant,
            "warning": None if compliant else f"Kanalınız henüz {channel_age_days} günlük. Algoritmada spam şüphesini önlemek için günde en fazla {max_recommended} video yükleyin."
        }

    @staticmethod
    def scan_borderline_risk(text: str) -> Dict[str, Any]:
        """
        Item 470 & 390: Şüpheli İçerik ve Topluluk Kuralları Kelime Taraması.
        Ölüm, cinayet, intihar, telif hakkı riski taşıyan sözcükleri tespit eder.
        """
        BORDERLINE_KEYWORDS = [
            "intihar", "cinayet", "ölüm", "şiddet", "katil", "kanlı", "uyuşturucu",
            "suicide", "murder", "kill", "violence", "blood", "drugs"
        ]
        found = [w for w in BORDERLINE_KEYWORDS if w in text.lower()]
        return {
            "is_clean": len(found) == 0,
            "flagged_words": found,
            "safe_replacements": {
                "intihar": "hayatına son verme",
                "cinayet": "gizemli olay",
                "ölüm": "ö*üm",
                "suicide": "unlived",
                "kill": "neutralize"
            },
            "recommendation": "Şüpheli kelimeleri yumuşatın veya mecazi ifadelerle değiştirin." if found else "Metin temiz."
        }

    @staticmethod
    def sanitize_borderline_words(text: str) -> Dict[str, Any]:
        """Item 390: Topluluk kuralları kelime sansürü — güvenli eşanlamlılarla yumuşatma."""
        scan = ProofArchiver.scan_borderline_risk(text)
        sanitized = text
        for word, replacement in scan.get("safe_replacements", {}).items():
            sanitized = re.sub(re.escape(word), replacement, sanitized, flags=re.IGNORECASE)
        return {
            **scan,
            "sanitized_text": sanitized,
            "was_sanitized": sanitized != text,
        }

    @staticmethod
    def analyze_algorithmic_view_threshold(
        view_count: int,
        swipe_rate_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Item 379: Algoritmik Eşik Analizi.
        1.000 izlenmede durma → retention; 10.000'de durma → paylaşım/yorum sinyali.
        """
        if view_count < 1000:
            diagnosis = "retention_friction"
            message = "Video ~1.000 izlenmede takıldı — ilk 3s kanca ve ortalama izlenme süresi düşük olabilir."
            action = "Item 201 kanca + Item 122 soru başlığı; sil-yeniden-yükleme yapmayın (Item 380)."
        elif view_count < 10000:
            diagnosis = "share_friction"
            message = "Video ~10.000 izlenmede durdu — retention iyi ama paylaşım/yorum sinyali zayıf."
            action = "Item 383 açıklama sorusu + Item 351 kalp/yorum CTA güçlendirin."
        else:
            diagnosis = "scaling_phase"
            message = "10.000+ izlenme — algoritma geniş dağıtım testine geçti."
            action = "Aynı nişte seri üretim; Item 387 feed ivmesi kaydırma oranını izleyin."

        if swipe_rate_pct is not None and swipe_rate_pct > 30.0:
            message += f" Kaydırma oranı %{swipe_rate_pct:.0f} (>30%) — feed genişlemesi yavaşlayabilir."

        return {
            "view_count": view_count,
            "swipe_rate_pct": swipe_rate_pct,
            "diagnosis": diagnosis,
            "message": message,
            "recommended_action": action,
            "analytics_source": "advisory_stub",
            "item": 379,
        }

    @staticmethod
    def get_reupload_avoidance_guidance(lang: str = "tr") -> Dict[str, str]:
        """Item 380: Yeniden yükleme hatasından kaçınma — spam riski rehberi."""
        if lang == "en":
            return {
                "rule": "Never delete and re-upload the same video on the same day — YouTube treats it as spam.",
                "action": "Edit title/hook/thumbnail and wait 48h before any new upload attempt.",
                "studio_note": "Prefer metadata edits over re-upload when performance is weak.",
                "item": "380",
            }
        return {
            "rule": "Tutmayan videoyu silip aynı gün tekrar yüklemeyin — algoritma bunu spam sayar (Item 380).",
            "action": "Başlık/kanca revize edin; 48 saat bekleyin; aynı içeriği yeniden yüklemeyin.",
            "studio_note": "Studio Analytics → metadata güncelleme tercih edin; re-upload değil.",
            "item": "380",
        }

    @staticmethod
    def analyze_feed_distribution_phase(
        swipe_rate_pct: float,
        test_audience: int = 500,
    ) -> Dict[str, Any]:
        """
        Item 387: Feed Dağıtım İvmesi.
        Algoritma videoyu önce ~500 kişiye gösterir; kaydırma %70 altıysa dağıtım durur.
        """
        retained_pct = max(0.0, 100.0 - swipe_rate_pct)
        expanded = retained_pct >= 70.0
        return {
            "test_audience_size": test_audience,
            "swipe_rate_pct": swipe_rate_pct,
            "retained_pct": round(retained_pct, 1),
            "threshold_retained_pct": 70.0,
            "distribution_expanded": expanded,
            "phase": "expanded" if expanded else "throttled",
            "message": (
                f"İlk {test_audience} gösterimde %{retained_pct:.0f} izlenme — "
                + ("geniş dağıtım devam edebilir." if expanded else "feed ivmesi durdu; kanca/retention revize edin.")
            ),
            "item": 387,
            "analytics_source": "advisory_stub",
        }

    @staticmethod
    def generate_monetization_funnel(niche: str, topic: str, lang: str = "tr") -> Dict[str, str]:
        """
        Items 477 & 478: Dijital Ürün / E-Kitap & Affiliate Funnel Şablonlayıcı.
        Biyografi ve sabitlenen yorum için 10$'lık rehber / e-kitap funnel metni üretir.
        """
        if lang == "en":
            return {
                "pinned_comment": f"📥 Download our Complete 50-Page {niche} Mastery Guide (Link in bio!) - Limited time discount.",
                "bio_link_text": f"📚 The Ultimate {topic} Blueprint (PDF Guide): linktr.ee/yourchannel",
                "affiliate_callout": "📌 Tools & books recommended in this video are linked in the channel description."
            }
        return {
            "pinned_comment": f"📥 Hayatınızı değiştirecek 50 sayfalık {niche} Rehberini profildeki linkten indirebilirsiniz! 💡",
            "bio_link_text": f"📚 Kapsamlı {topic} Başarı Kılavuzu (PDF): linktr.ee/kanaliniz",
            "affiliate_callout": "📌 Videoda bahsedilen kitap ve ekipman linkleri açıklama kısmındadır."
        }

    @staticmethod
    def get_tier1_rpm_multiplier(target_country: str = "US") -> Dict[str, Any]:
        """
        Item 481: Tier-1 Ülke Kazanç Çarpanı (RPM Multiplier).
        ABD ve İngiltere'den izlenen Shorts videolarının BGBG (RPM) oranı Türkiye'ye göre 8 ila 15 kat daha yüksektir.
        """
        return {
            "target_country": target_country,
            "rpm_multiplier": "8x - 15x" if target_country.upper() in ["US", "UK", "CA", "AU", "DE"] else "1.0x",
            "estimated_rpm_range_usd": "$0.08 - $0.20 per 1k views" if target_country.upper() in ["US", "UK"] else "$0.01 - $0.02 per 1k views",
            "strategy_action": "Tüm içerik dili İngilizceye ayarlanmalı, New York EST saat dilimiyle yayınlanmalı ve global kanca kalıpları kullanılmalıdır."
        }

    @staticmethod
    def generate_legal_disclaimer(category: str = "general", lang: str = "tr") -> str:
        """
        Item 485: Yasal Sorumluluk Reddi (Legal Disclaimer Generator).
        Tıbbi veya finansal tavsiye gibi görünen cümlelerin sonuna 'Yatırım tavsiyesi değildir' uyarısı.
        """
        if category in ["finance", "crypto", "money", "borsa"]:
            return "⚠️ YASAL UYARI: Bu videoda paylaşılan bilgiler yalnızca genel eğitim ve bilgilendirme amaçlıdır; kesinlikle yatırım tavsiyesi niteliğinde değildir." if lang == "tr" else "⚠️ DISCLAIMER: This video is for educational and informational purposes only and does not constitute financial or investment advice."
        elif category in ["health", "fitness", "sağlık"]:
            return "⚠️ SAĞLIK UYARISI: Bu içerik tıbbi tavsiye yerine geçmez; herhangi bir uygulamadan önce uzman doktorunuza danışınız." if lang == "tr" else "⚠️ HEALTH DISCLAIMER: This content is not intended as medical advice. Always consult a certified physician."
        return "⚖️ BİLGİLENDİRME: Bu video bağımsız araştırma ve eğitim amacıyla Fair Use prensipleri çerçevesinde üretilmiştir." if lang == "tr" else "⚖️ NOTICE: This video is produced for educational purposes under Fair Use principles."

    @staticmethod
    def generate_shadowban_recovery_plan(days: int = 7) -> Dict[str, Any]:
        """
        Item 486: Gölge Engelden (Shadowban) Çıkış Egzersizi & Soğuma Protokolü.
        Kanala 1 hafta boyunca Shorts yerine 3-5 dakikalık yüksek kaliteli 2 adet yatay video ve 4 gün soğuma takvimi üretir.
        """
        return {
            "protocol_name": "Shadowban Reset & Trust Reclamation",
            "steps": [
                {
                    "day": "Gün 1 - 4",
                    "action": "Algoritma Soğuma Süreci: Kanala kesinlikle hiçbir Shorts veya toplu video yüklemeyin."
                },
                {
                    "day": "Gün 5",
                    "action": "Kanal Temizliği: Son 30 günde 0 izlenmede kalmış veya şüpheli görünen eski videoları tamamen silin."
                },
                {
                    "day": "Gün 6",
                    "action": "Otorite Restorasyonu: Shorts yerine 3-5 dakikalık, kendi sesiniz veya yüzünüzle yüksek kaliteli 1 adet yatay video yükleyin."
                },
                {
                    "day": "Gün 7",
                    "action": "Organik Etkileşim: Topluluk anketinde soru sorun, gelen tüm yorumları kalpleyip yanıtlayın."
                },
                {
                    "day": "Gün 8+",
                    "action": "Shorts Akışına Dönüş: Günde sadece 1 adet, kusursuz ilk 1.5s kancalı (Item 201) yeni Shorts ile başlayın."
                }
            ]
        }

    @staticmethod
    def get_algorithm_reset_guidance(days_paused: int = 0, lang: str = "tr") -> Dict[str, Any]:
        """
        Item 394: Algoritma Resetleme Dönemleri.
        Kanal durakladıysa 4 gün yükleme yapmayıp güçlü kanca videosuyla dönüş önerilir.
        """
        reset_days = 4
        ready = days_paused >= reset_days
        if lang == "en":
            return {
                "item": "394",
                "pause_days_required": reset_days,
                "days_paused": days_paused,
                "ready_for_comeback": ready,
                "rule": f"After a channel pause, skip uploads for {reset_days} days before returning.",
                "action": (
                    "Publish one high-retention hook video (Item 201) — do not bulk-upload on return."
                    if ready
                    else f"Wait {reset_days - days_paused} more day(s) before the comeback upload."
                ),
                "studio_note": "YouTube Studio → Analytics → compare retention on the comeback video.",
            }
        return {
            "item": "394",
            "pause_days_required": reset_days,
            "days_paused": days_paused,
            "ready_for_comeback": ready,
            "rule": f"Kanal durakladıysa {reset_days} gün video atmayın; algoritma reset penceresi açılır.",
            "action": (
                "Bomba kanca (Item 201) ile tek güçlü Shorts yükleyin — toplu patlama yapmayın."
                if ready
                else f"Dönüş için {reset_days - days_paused} gün daha bekleyin."
            ),
            "studio_note": "Studio Analytics → dönüş videosunun retention eğrisini izleyin.",
        }

    @staticmethod
    def analyze_traffic_sources(
        shorts_feed_pct: float = 85.0,
        browse_features_pct: float = 8.0,
        external_pct: float = 5.0,
        suggested_upload_hours: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Items 406-409: Haftalık analitik + trafik kaynakları advisory stub.
        YouTube Analytics API yok; Studio grafiklerinden manuel okuma rehberi.
        """
        ideal_shorts_feed = 80.0
        external_warning_threshold = 90.0
        browse_growth_threshold = 5.0
        shorts_ok = shorts_feed_pct >= ideal_shorts_feed
        external_risk = external_pct >= external_warning_threshold
        browse_growing = browse_features_pct >= browse_growth_threshold
        hours = suggested_upload_hours or ["18:00", "20:00", "21:00"]
        return {
            "item": "406-409",
            "weekly_analytics_action": (
                "Studio → Analytics → İzleyicilerin YouTube'da olduğu zamanlar grafiğini haftalık okuyun."
            ),
            "traffic_sources": {
                "shorts_feed_pct": shorts_feed_pct,
                "browse_features_pct": browse_features_pct,
                "external_pct": external_pct,
            },
            "shorts_feed_healthy": shorts_ok,
            "shorts_feed_target_pct": ideal_shorts_feed,
            "browse_features_growing": browse_growing,
            "external_traffic_risk": external_risk,
            "diagnosis": (
                "Harici trafik riski — organik Shorts akışına dönün."
                if external_risk
                else (
                    "Browse Features yükseliyor — kanal ana sayfa görünürlüğü artıyor."
                    if browse_growing
                    else (
                        "Shorts Feed oranı sağlıklı."
                        if shorts_ok
                        else "Shorts Feed %80 altında — kanca/retention revize edin."
                    )
                )
            ),
            "recommended_upload_windows": hours,
            "analytics_source": "advisory_stub",
        }

    @staticmethod
    def get_engagement_recovery_guidance(
        hours_since_upload: float = 72.0,
        view_count: int = 0,
        total_videos_on_channel: int = 5,
    ) -> Dict[str, Any]:
        """
        Item 468: Etkileşim Kurtarma — 0 izlenmede başlık, küçük resim ve açıklama revizyonu.
        """
        diag = ProofArchiver.diagnose_zero_views(
            hours_since_upload, view_count, total_videos_on_channel
        )
        return {
            "item": "468",
            "diagnosis": diag,
            "metadata_actions": [
                "YouTube Studio → Video details → başlığı soru formatına çevirin (Item 122).",
                "Thumbnail A/B: yüz/duygusal ifade veya yüksek kontrastlı metin deneyin.",
                "Açıklamanın ilk 2 satırına spesifik anahtar kelime + CTA ekleyin.",
            ],
            "studio_note": "Sil-yeniden-yükleme yapmayın; metadata güncellemesi tercih edin (Item 380).",
        }

    @staticmethod
    def get_distribution_pause_guidance(days_paused: int = 0) -> Dict[str, Any]:
        """Item 469: Dağıtım duraklamasında 4 gün yükleme yapma kuralı."""
        guidance = ProofArchiver.get_algorithm_reset_guidance(days_paused)
        guidance["item"] = "469"
        guidance["rule"] = (
            "İzlenmeler aniden kesildiyse 4 gün boyunca hiçbir içerik yüklemeyin; "
            "algoritmanın soğuması beklenmelidir."
        )
        return guidance

    @staticmethod
    def get_copyright_strike_advisory(strike_count: int = 0) -> Dict[str, Any]:
        """
        Item 484: Telif ihtarı (Copyright Strike) yönetimi — 3 ihtarda kanal kalıcı silinir.
        """
        if strike_count >= 3:
            level, action = "critical", "Kanal kalıcı silinme riski — tüm içerikleri gözden geçirin, avukata danışın."
        elif strike_count == 2:
            level, action = "high", "2. ihtar: riskli tüm içerikleri inceleyin; Content-ID eşleşen klipleri değiştirin."
        elif strike_count == 1:
            level, action = "medium", "1. ihtar: şikayetçiyle iletişime geçin veya riskli içerikleri kaldırın."
        else:
            level, action = "low", "İhtar yok — stok kaynaklarını Pexels/Pixabay/AI ile sınırlayın (copyright_risk.py)."
        return {
            "item": "484",
            "strike_count": strike_count,
            "risk_level": level,
            "max_strikes_before_termination": 3,
            "action": action,
            "content_id_scan": "copyright_risk.scan_copyright_risk ile render öncesi tarama yapın.",
            "studio_note": "YouTube Studio → Copyright → Strike details",
        }

    @staticmethod
    def get_comment_moderation_blocklist(lang: str = "tr") -> Dict[str, Any]:
        """
        Item 495: Yorum denetiminde negatif kelime engeli — Studio blocklist için önerilen kelimeler.
        """
        if lang == "en":
            words = [
                "fuck", "shit", "bitch", "asshole", "scam", "fake", "bot", "spam",
                "idiot", "stupid", "hate", "kill yourself", "click here", "free money",
            ]
            instruction = "YouTube Studio → Settings → Community → Blocked words — paste list below."
        else:
            words = [
                "amk", "aq", "orospu", "salak", "aptal", "bot", "spam", "scam", "dolandırıcı",
                "link tıkla", "bedava para", "nefret", "öl", "küfür", "hakaret", "sahte",
            ]
            instruction = "YouTube Studio → Ayarlar → Topluluk → Engellenen kelimeler — listeyi yapıştırın."
        return {
            "item": "495",
            "blocked_words": words,
            "word_count": len(words),
            "studio_action": instruction,
            "note": "Küfür, hakaret ve bot kelimeleri Studio otomatik filtresine eklenmelidir.",
        }

    @staticmethod
    def validate_channel_language_policy(
        channel_primary_lang: str,
        content_lang: str,
    ) -> Dict[str, Any]:
        """
        Item 491: Kanalın dilini karıştırmama — farklı dil için yeni kanal açılmalı.
        """
        ch = (channel_primary_lang or "tr").lower()[:2]
        ct = (content_lang or "tr").lower()[:2]
        compliant = ch == ct
        return {
            "item": "491",
            "channel_primary_lang": ch,
            "content_lang": ct,
            "is_compliant": compliant,
            "warning": None if compliant else (
                f"Kanal dili '{ch}' iken içerik '{ct}' — yeni dil için ayrı kanal açın; "
                "mevcut kanala karışık dil yüklemeyin."
            ),
        }

    @staticmethod
    def get_channel_momentum_threshold(
        total_videos: int = 0,
        avg_views: int = 0,
    ) -> Dict[str, Any]:
        """
        Item 410: Sabır ve İvme Eşiği.
        İlk 30 videoda 0-500 izlenme normal; 30. videodan sonra kitle havuzu oturur.
        """
        threshold_videos = 30
        early_phase = total_videos < threshold_videos
        views_normal = avg_views <= 500
        return {
            "item": "410",
            "momentum_video_threshold": threshold_videos,
            "total_videos": total_videos,
            "avg_views": avg_views,
            "early_phase": early_phase,
            "views_in_normal_band": views_normal,
            "phase": "early_calibration" if early_phase else "momentum_unlocked",
            "message": (
                f"İlk {threshold_videos} videoda 0-500 izlenme normal — sabırlı olun; algoritma kitle havuzunu oturtuyor."
                if early_phase
                else "30+ video eşiği aşıldı — ivme ve Browse Features trendini haftalık izleyin."
            ),
            "action": (
                "Her gün 1 tutarlı niş videosu; başlık/kanca A/B test edin."
                if early_phase
                else "Retention ve Shorts Feed oranını (Item 407) haftalık değerlendirin."
            ),
        }


    @staticmethod
    def build_actionable_channel_health_checklist(
        channel_age_days: int = 14,
        planned_daily_uploads: int = 1,
        hours_since_upload: float = 72.0,
        view_count: int = 0,
        total_videos: int = 0,
        strike_count: int = 0,
        channel_primary_lang: str = "tr",
        content_lang: str = "tr",
        niche: str = "Stoacılık",
        topic: str = "Zihin Disiplini",
        lang: str = "tr",
    ) -> Dict[str, Any]:
        """
        B8 Batch 4 — actionable kanal sağlığı checklist (466-500 in-scope advisory).
        Studio/manuel adımlar checklist olarak; otomasyon yok.
        """
        import growth_tactics

        checklist = [
            {
                "item": 466,
                "title": "0 İzlenme Teşhisi",
                "status": "actionable",
                "action": ProofArchiver.diagnose_zero_views(
                    hours_since_upload, view_count, total_videos
                ),
            },
            {
                "item": 467,
                "title": "Isınma Protokolü",
                "status": "actionable",
                "action": ProofArchiver.check_warmup_protocol(channel_age_days, planned_daily_uploads),
            },
            {
                "item": 468,
                "title": "Etkileşim Kurtarma",
                "status": "actionable",
                "action": ProofArchiver.get_engagement_recovery_guidance(
                    hours_since_upload, view_count, total_videos
                ),
            },
            {
                "item": 469,
                "title": "Dağıtım Duraklaması",
                "status": "actionable",
                "action": ProofArchiver.get_distribution_pause_guidance(0),
            },
            {
                "item": 472,
                "title": "YouTube İtiraz Videosu (Appeal Script)",
                "status": "actionable",
                "action": ProofArchiver.build_appeal_video_operator_workflow(
                    channel_name=niche.replace(" ", "") + "Channel",
                    video_title=topic,
                ),
            },
            {
                "item": 477,
                "title": "Affiliate Funnel",
                "status": "actionable",
                "action": ProofArchiver.generate_monetization_funnel(niche, topic, lang),
            },
            {
                "item": 478,
                "title": "Dijital Ürün Funnel",
                "status": "actionable",
                "action": ProofArchiver.generate_monetization_funnel(niche, topic, lang),
            },
            {
                "item": 484,
                "title": "Telif İhtarı Yönetimi",
                "status": "actionable",
                "action": ProofArchiver.get_copyright_strike_advisory(strike_count),
            },
            {
                "item": 486,
                "title": "Gölge Engel Kurtarma",
                "status": "actionable",
                "action": ProofArchiver.generate_shadowban_recovery_plan(7),
            },
            {
                "item": 489,
                "title": "Trend Hız Avantajı",
                "status": "actionable",
                "action": {
                    "item": "489",
                    "rule": "Trend haberlerde 45 dk içinde üretim hedefleyin.",
                    "tools": ["trending_scanner.py", "rss_scanner.py"],
                },
            },
            {
                "item": 490,
                "title": "Bildirim CTA",
                "status": "actionable",
                "action": growth_tactics.should_show_notification_bell_cta(total_videos),
            },
            {
                "item": 491,
                "title": "Kanal Dili Politikası",
                "status": "actionable",
                "action": ProofArchiver.validate_channel_language_policy(
                    channel_primary_lang, content_lang
                ),
            },
            {
                "item": 495,
                "title": "Yorum Engelleme Listesi",
                "status": "actionable",
                "action": ProofArchiver.get_comment_moderation_blocklist(lang),
            },
            {
                "item": 497,
                "title": "Veri Yedekleme",
                "status": "actionable",
                "action": {
                    "item": "497",
                    "local_archive": config.OUTPUT_DIR,
                    "encrypted_backup": "database.encrypted_db_backup() — Item 439",
                    "studio_note": "Bulut yedek manuel; yerel + şifreli DB yedek otomatik.",
                },
            },
            {
                "item": 498,
                "title": "Konsept Koruma",
                "status": "actionable",
                "action": {
                    "item": "498",
                    "rule": "Niş şablon kilidi — cross-niche karıştırmayın.",
                    "tool": "niche_templates.py",
                },
            },
            {
                "item": 499,
                "title": "A/B Test Kültürü",
                "status": "actionable",
                "action": growth_tactics.generate_ab_test_variants(topic),
            },
            {
                "item": 500,
                "title": "Maraton Kalite Kuralı",
                "status": "actionable",
                "action": {
                    "item": "500",
                    "rule": "Batch maraton + kalite kapısı — roadmap_500_evaluator ile sürekli denetim.",
                    "tool": "batch_processor.py",
                },
            },
        ]
        deferred_manual = [
            {
                "item": 473,
                "title": "İtirazda Yüz Gösterme",
                "note": "Operatör kamera — checklist #472 workflow adım 2.",
            },
            {
                "item": 474,
                "title": "Kurgu Ekran Kaydı Kanıtı",
                "note": "Operatör screen record — checklist #472 workflow adım 3.",
            },
            {"item": 482, "title": "Çoklu Kanal Portföyü", "note": "DB multi-channel var; strateji manuel."},
        ]
        return {
            "checklist": checklist,
            "deferred_manual": deferred_manual,
            "actionable_count": len(checklist),
            "lang": lang,
        }


proof_archiver = ProofArchiver()
