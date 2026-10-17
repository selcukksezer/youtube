"""Channel health diagnostics, monetization funnels, recovery plans, and checklist builders."""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

import config


def _pa_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("proof_archiver")
    return getattr(mod, name, default) if mod is not None else default


class ProofReportBuilderMixin:
    """Advisory, recovery, monetization, and channel health report methods for ProofArchiver."""

    @staticmethod
    def analyze_algorithmic_view_threshold(
        view_count: int, swipe_rate_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """Item 379: Algoritmik Eşik Analizi."""
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
        swipe_rate_pct: float, test_audience: int = 500
    ) -> Dict[str, Any]:
        """Item 387: Feed Dağıtım İvmesi."""
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
        """Items 477 & 478: Dijital Ürün / E-Kitap & Affiliate Funnel Şablonlayıcı."""
        if lang == "en":
            return {
                "pinned_comment": f"📥 Download our Complete 50-Page {niche} Mastery Guide (Link in bio!) - Limited time discount.",
                "bio_link_text": f"📚 The Ultimate {topic} Blueprint (PDF Guide): linktr.ee/yourchannel",
                "affiliate_callout": "📌 Tools & books recommended in this video are linked in the channel description.",
            }
        return {
            "pinned_comment": f"📥 Hayatınızı değiştirecek 50 sayfalık {niche} Rehberini profildeki linkten indirebilirsiniz! 💡",
            "bio_link_text": f"📚 Kapsamlı {topic} Başarı Kılavuzu (PDF): linktr.ee/kanaliniz",
            "affiliate_callout": "📌 Videoda bahsedilen kitap ve ekipman linkleri açıklama kısmındadır.",
        }

    @staticmethod
    def get_repeated_content_rejection_recovery_plan(
        channel_name: str = "YourChannel", days: int = 30, lang: str = "tr"
    ) -> Dict[str, Any]:
        """Item 476: Tekrarlanan İçerik (Reused Content) ret kararı sonrası 30 günlük operatör planı."""
        if lang == "en":
            return {
                "item": 476,
                "protocol": "30-Day Original Content Recovery",
                "channel_name": channel_name,
                "duration_days": days,
                "rules": [
                    "Pause bulk uploads for 4 days; review last 10 videos for repetitive patterns.",
                    "Produce 100% transformative narration — no stock-only compilations.",
                    "Add visible human editorial layer: unique hooks, alternate angles, custom B-roll mix.",
                    "Archive proof dossier per video (timeline screenshot + script diff).",
                    "Re-apply for monetization only after 30 consecutive original uploads.",
                ],
                "weekly_targets": {
                    "week_1": "Audit + 2 fully original Shorts (new niche angle each).",
                    "week_2": "3 Shorts with dual stock providers + custom voice humanization.",
                    "week_3": "3 Shorts with hybrid overlay + appeal-ready proof archive.",
                    "week_4": "2 Shorts + file YPP re-review request with proof links.",
                },
                "tools": ["proof_archiver.py", "plagiarism_checker.py", "director/validate.py"],
                "manual_only": True,
            }
        return {
            "item": 476,
            "protocol": "30 Günlük Özgün İçerik Kurtarma",
            "channel_name": channel_name,
            "duration_days": days,
            "rules": [
                "4 gün toplu yükleme yapmayın; son 10 videoyu tekrar eden kalıplar için inceleyin.",
                "100% dönüştürücü anlatım — sadece stok derlemesi yok.",
                "Görünür editoryal katman: özgün kanca, alternatif açı, karışık B-roll.",
                "Her video için proof arşivi (timeline ekran görüntüsü + senaryo diff).",
                "30 ardışık özgün yüklemeden sonra monetizasyon için yeniden başvurun.",
            ],
            "weekly_targets": {
                "hafta_1": "Denetim + 2 tam özgün Shorts (her biri farklı niş açısı).",
                "hafta_2": "3 Shorts — çift stok sağlayıcı + voice humanization.",
                "hafta_3": "3 Shorts — hybrid overlay + itiraz dossier hazır.",
                "hafta_4": "2 Shorts + YPP yeniden inceleme talebi (proof linkleri ile).",
            },
            "tools": ["proof_archiver.py", "plagiarism_checker.py", "director/validate.py"],
            "manual_only": True,
        }

    @staticmethod
    def get_tier1_rpm_multiplier(target_country: str = "US") -> Dict[str, Any]:
        """Item 481: Tier-1 Ülke Kazanç Çarpanı (RPM Multiplier)."""
        return {
            "target_country": target_country,
            "rpm_multiplier": "8x - 15x" if target_country.upper() in ["US", "UK", "CA", "AU", "DE"] else "1.0x",
            "estimated_rpm_range_usd": "$0.08 - $0.20 per 1k views"
            if target_country.upper() in ["US", "UK"]
            else "$0.01 - $0.02 per 1k views",
            "strategy_action": "Tüm içerik dili İngilizceye ayarlanmalı, New York EST saat dilimiyle yayınlanmalı ve global kanca kalıpları kullanılmalıdır.",
        }

    @staticmethod
    def generate_legal_disclaimer(category: str = "general", lang: str = "tr") -> str:
        """Item 485: Yasal Sorumluluk Reddi (Legal Disclaimer Generator)."""
        if category in ["finance", "crypto", "money", "borsa"]:
            return (
                "⚠️ YASAL UYARI: Bu videoda paylaşılan bilgiler yalnızca genel eğitim ve bilgilendirme amaçlıdır; kesinlikle yatırım tavsiyesi niteliğinde değildir."
                if lang == "tr"
                else "⚠️ DISCLAIMER: This video is for educational and informational purposes only and does not constitute financial or investment advice."
            )
        if category in ["health", "fitness", "sağlık"]:
            return (
                "⚠️ SAĞLIK UYARISI: Bu içerik tıbbi tavsiye yerine geçmez; herhangi bir uygulamadan önce uzman doktorunuza danışınız."
                if lang == "tr"
                else "⚠️ HEALTH DISCLAIMER: This content is not intended as medical advice. Always consult a certified physician."
            )
        return (
            "⚖️ BİLGİLENDİRME: Bu video bağımsız araştırma ve eğitim amacıyla Fair Use prensipleri çerçevesinde üretilmiştir."
            if lang == "tr"
            else "⚖️ NOTICE: This video is produced for educational purposes under Fair Use principles."
        )

    @staticmethod
    def generate_shadowban_recovery_plan(days: int = 7) -> Dict[str, Any]:
        """Item 486: Gölge Engelden (Shadowban) Çıkış Egzersizi & Soğuma Protokolü."""
        return {
            "protocol_name": "Shadowban Reset & Trust Reclamation",
            "steps": [
                {"day": "Gün 1 - 4", "action": "Algoritma Soğuma Süreci: Kanala kesinlikle hiçbir Shorts veya toplu video yüklemeyin."},
                {"day": "Gün 5", "action": "Kanal Temizliği: Son 30 günde 0 izlenmede kalmış veya şüpheli görünen eski videoları tamamen silin."},
                {"day": "Gün 6", "action": "Otorite Restorasyonu: Shorts yerine 3-5 dakikalık, kendi sesiniz veya yüzünüzle yüksek kaliteli 1 adet yatay video yükleyin."},
                {"day": "Gün 7", "action": "Organik Etkileşim: Topluluk anketinde soru sorun, gelen tüm yorumları kalpleyip yanıtlayın."},
                {"day": "Gün 8+", "action": "Shorts Akışına Dönüş: Günde sadece 1 adet, kusursuz ilk 1.5s kancalı (Item 201) yeni Shorts ile başlayın."},
            ],
        }

    @staticmethod
    def get_algorithm_reset_guidance(days_paused: int = 0, lang: str = "tr") -> Dict[str, Any]:
        """Item 394: Algoritma Resetleme Dönemleri."""
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
        """Items 406-409: Haftalık analitik + trafik kaynakları advisory stub."""
        ideal_shorts_feed = 80.0
        shorts_ok = shorts_feed_pct >= ideal_shorts_feed
        external_risk = external_pct >= 90.0
        browse_growing = browse_features_pct >= 5.0
        hours = suggested_upload_hours or ["18:00", "20:00", "21:00"]
        diagnosis = (
            "Harici trafik riski — organik Shorts akışına dönün."
            if external_risk
            else (
                "Browse Features yükseliyor — kanal ana sayfa görünürlüğü artıyor."
                if browse_growing
                else ("Shorts Feed oranı sağlıklı." if shorts_ok else "Shorts Feed %80 altında — kanca/retention revize edin.")
            )
        )
        return {
            "item": "406-409",
            "weekly_analytics_action": "Studio → Analytics → İzleyicilerin YouTube'da olduğu zamanlar grafiğini haftalık okuyun.",
            "traffic_sources": {
                "shorts_feed_pct": shorts_feed_pct,
                "browse_features_pct": browse_features_pct,
                "external_pct": external_pct,
            },
            "shorts_feed_healthy": shorts_ok,
            "shorts_feed_target_pct": ideal_shorts_feed,
            "browse_features_growing": browse_growing,
            "external_traffic_risk": external_risk,
            "diagnosis": diagnosis,
            "recommended_upload_windows": hours,
            "analytics_source": "advisory_stub",
        }

    @staticmethod
    def get_engagement_recovery_guidance(
        hours_since_upload: float = 72.0, view_count: int = 0, total_videos_on_channel: int = 5
    ) -> Dict[str, Any]:
        """Item 468: Etkileşim Kurtarma — 0 izlenmede başlık, küçük resim ve açıklama revizyonu."""
        pa_cls = _pa_attr("ProofArchiver", ProofReportBuilderMixin)
        diag = pa_cls.diagnose_zero_views(hours_since_upload, view_count, total_videos_on_channel)
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
        pa_cls = _pa_attr("ProofArchiver", ProofReportBuilderMixin)
        guidance = pa_cls.get_algorithm_reset_guidance(days_paused)
        guidance["item"] = "469"
        guidance["rule"] = (
            "İzlenmeler aniden kesildiyse 4 gün boyunca hiçbir içerik yüklemeyin; "
            "algoritmanın soğuması beklenmelidir."
        )
        return guidance

    @staticmethod
    def get_copyright_strike_advisory(strike_count: int = 0) -> Dict[str, Any]:
        """Item 484: Telif ihtarı (Copyright Strike) yönetimi — 3 ihtarda kanal kalıcı silinir."""
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
        """Item 495: Yorum denetiminde negatif kelime engeli — Studio blocklist için önerilen kelimeler."""
        if lang == "en":
            words = ["fuck", "shit", "bitch", "asshole", "scam", "fake", "bot", "spam", "idiot", "stupid", "hate", "kill yourself", "click here", "free money"]
            instruction = "YouTube Studio → Settings → Community → Blocked words — paste list below."
        else:
            words = ["amk", "aq", "orospu", "salak", "aptal", "bot", "spam", "scam", "dolandırıcı", "link tıkla", "bedava para", "nefret", "öl", "küfür", "hakaret", "sahte"]
            instruction = "YouTube Studio → Ayarlar → Topluluk → Engellenen kelimeler — listeyi yapıştırın."
        return {
            "item": "495",
            "blocked_words": words,
            "word_count": len(words),
            "studio_action": instruction,
            "note": "Küfür, hakaret ve bot kelimeleri Studio otomatik filtresine eklenmelidir.",
        }

    @staticmethod
    def validate_channel_language_policy(channel_primary_lang: str, content_lang: str) -> Dict[str, Any]:
        """Item 491: Kanalın dilini karıştırmama — farklı dil için yeni kanal açılmalı."""
        ch = (channel_primary_lang or "tr").lower()[:2]
        ct = (content_lang or "tr").lower()[:2]
        compliant = ch == ct
        return {
            "item": "491",
            "channel_primary_lang": ch,
            "content_lang": ct,
            "is_compliant": compliant,
            "warning": None if compliant else f"Kanal dili '{ch}' iken içerik '{ct}' — yeni dil için ayrı kanal açın; mevcut kanala karışık dil yüklemeyin.",
        }

    @staticmethod
    def get_channel_momentum_threshold(total_videos: int = 0, avg_views: int = 0) -> Dict[str, Any]:
        """Item 410: Sabır ve İvme Eşiği."""
        threshold_videos = 30
        early_phase = total_videos < threshold_videos
        return {
            "item": "410",
            "momentum_video_threshold": threshold_videos,
            "total_videos": total_videos,
            "avg_views": avg_views,
            "early_phase": early_phase,
            "views_in_normal_band": avg_views <= 500,
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
        """B8 Batch 4 — actionable kanal sağlığı checklist (466-500 in-scope advisory)."""
        import growth_tactics

        pa_cls = _pa_attr("ProofArchiver", ProofReportBuilderMixin)
        cfg = _pa_attr("config", config)
        funnel = pa_cls.generate_monetization_funnel(niche, topic, lang)
        checklist = [
            {"item": 466, "title": "0 İzlenme Teşhisi", "status": "actionable", "action": pa_cls.diagnose_zero_views(hours_since_upload, view_count, total_videos)},
            {"item": 467, "title": "Isınma Protokolü", "status": "actionable", "action": pa_cls.check_warmup_protocol(channel_age_days, planned_daily_uploads)},
            {"item": 468, "title": "Etkileşim Kurtarma", "status": "actionable", "action": pa_cls.get_engagement_recovery_guidance(hours_since_upload, view_count, total_videos)},
            {"item": 469, "title": "Dağıtım Duraklaması", "status": "actionable", "action": pa_cls.get_distribution_pause_guidance(0)},
            {"item": 472, "title": "YouTube İtiraz Videosu (Appeal Script)", "status": "actionable", "action": pa_cls.build_appeal_video_operator_workflow(channel_name=niche.replace(" ", "") + "Channel", video_title=topic)},
            {"item": 477, "title": "Affiliate Funnel", "status": "actionable", "action": funnel},
            {"item": 478, "title": "Dijital Ürün Funnel", "status": "actionable", "action": funnel},
            {"item": 484, "title": "Telif İhtarı Yönetimi", "status": "actionable", "action": pa_cls.get_copyright_strike_advisory(strike_count)},
            {"item": 486, "title": "Gölge Engel Kurtarma", "status": "actionable", "action": pa_cls.generate_shadowban_recovery_plan(7)},
            {"item": 489, "title": "Trend Hız Avantajı", "status": "actionable", "action": {"item": "489", "rule": "Trend haberlerde 45 dk içinde üretim hedefleyin.", "tools": ["trending_scanner.py", "rss_scanner.py"]}},
            {"item": 490, "title": "Bildirim CTA", "status": "actionable", "action": growth_tactics.should_show_notification_bell_cta(total_videos)},
            {"item": 491, "title": "Kanal Dili Politikası", "status": "actionable", "action": pa_cls.validate_channel_language_policy(channel_primary_lang, content_lang)},
            {"item": 495, "title": "Yorum Engelleme Listesi", "status": "actionable", "action": pa_cls.get_comment_moderation_blocklist(lang)},
            {"item": 497, "title": "Veri Yedekleme", "status": "actionable", "action": {"item": "497", "local_archive": cfg.OUTPUT_DIR, "encrypted_backup": "database.encrypted_db_backup() — Item 439", "studio_note": "Bulut yedek manuel; yerel + şifreli DB yedek otomatik."}},
            {"item": 498, "title": "Konsept Koruma", "status": "actionable", "action": {"item": "498", "rule": "Niş şablon kilidi — cross-niche karıştırmayın.", "tool": "niche_templates.py"}},
            {"item": 499, "title": "A/B Test Kültürü", "status": "actionable", "action": growth_tactics.generate_ab_test_variants(topic)},
            {"item": 500, "title": "Maraton Kalite Kuralı", "status": "actionable", "action": {"item": "500", "rule": "Batch maraton + kalite kapısı — roadmap_500_evaluator ile sürekli denetim.", "tool": "batch_processor.py"}},
        ]
        deferred_manual = [
            {"item": 473, "title": "İtirazda Yüz Gösterme", "note": "Operatör kamera — checklist #472 workflow adım 2."},
            {"item": 474, "title": "Kurgu Ekran Kaydı Kanıtı", "note": "Operatör screen record — checklist #472 workflow adım 3."},
            {"item": 482, "title": "Çoklu Kanal Portföyü", "note": "DB multi-channel var; strateji manuel."},
        ]
        return {
            "checklist": checklist,
            "deferred_manual": deferred_manual,
            "actionable_count": len(checklist),
            "lang": lang,
        }
