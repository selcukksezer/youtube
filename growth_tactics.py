"""
Growth Tactics & Algorithm Optimizers (Items 65, 76, 83, 85, 89, 91, 97, 98, 99)
Implements:
- A/B Testing hook and title generators (Item 98)
- Community Post & Poll generator (Item 89)
- Comment-to-Video conversion hook (Item 83)
- Cross-platform metadata for TikTok and Reels (Item 99)
- Channel warm-up limit tracker (Item 85)
- 24/7 Live stream command generator (Items 76, 97)
- Copyright risk checker (Item 65)
"""
import os, time
from typing import Dict, Any, List

def should_show_notification_bell_cta(video_index: int = 0) -> Dict[str, Any]:
    """
    Item 490: Her 5 videodan birinde bildirim açma mikro görseli/CTA önerilir.
    """
    idx = max(0, int(video_index))
    show = idx > 0 and idx % 5 == 0
    return {
        "item": "490",
        "video_index": idx,
        "show_notification_cta": show,
        "overlay_text": (
            "Yeni sırları kaçırmamak için bildirimleri açmayı unutma! 🔔"
            if show
            else ""
        ),
        "ui_type": "ios_notification" if show else None,
        "rule": "Her 5. videoda bildirim zili CTA overlay veya end-card metni kullanın.",
    }


def generate_ab_test_variants(topic: str) -> List[Dict[str, str]]:
    """
    Item 310: 3 hook/title A/B varyantı + 2 altyazı stili (karaoke neon vs minimal gölge).
    Item 98 ile uyumlu; CTR/retention test paketi üretir.
    """
    subtitle_styles = ["karaoke_bold_neon", "minimal_white_shadow"]
    return [
        {
            "variant": "A_Curiosity",
            "title": f"Bunu Biliyor Muydunuz? {topic} Hakkında Gizli Gerçek #Shorts",
            "hook": f"{topic} hakkında bildiğiniz her şey yanlış olabilir! İşte kimsenin anlatmadığı o detay...",
            "subtitle_style_a": subtitle_styles[0],
            "subtitle_style_b": subtitle_styles[1],
        },
        {
            "variant": "B_Shock",
            "title": f"İNANILMAZ! {topic} Olayı Herkesi Şok Etti #Shorts",
            "hook": f"Bu bilgiyi duyduğunuzda tüyleriniz ürperecek: {topic} aslında göründüğü gibi değil!",
            "subtitle_style_a": subtitle_styles[0],
            "subtitle_style_b": subtitle_styles[1],
        },
        {
            "variant": "C_Debate",
            "title": f"Siz Olsaydınız Ne Yapardınız? {topic} #Shorts",
            "hook": f"Tarihin en büyük ikilemi: {topic} konusunda siz hangi taraftasınız?",
            "subtitle_style_a": subtitle_styles[0],
            "subtitle_style_b": subtitle_styles[1],
        }
    ]

def generate_community_poll(topic: str) -> Dict[str, Any]:
    """
    Item 89 / 312: Community poll + kazanan seçeneği Shorts üretim brifine dönüştürme.
    """
    return {
        "question": f"Bugünkü Shorts konumuz '{topic}'. Sizce bu konuda en çok merak edilen şey nedir?",
        "options": [
            f"{topic} hakkında hiç bilinmeyen sırlar",
            "Tarihteki en büyük hatalar",
            "Gelecekte bizi bekleyenler",
            "Sonucu görmek istiyorum"
        ],
        "scheduled_delay_minutes": 60,
        "shorts_production_delay_hours": 2,
        "workflow_note": "Item 312: Anket sonucu kazanan seçenek 2 saat içinde Shorts konusu olarak üretilmeli (manuel Studio upload).",
    }


def plan_shorts_from_poll_winner(poll_topic: str, winning_option: str) -> Dict[str, Any]:
    """
    Item 312: Topluluk anketinde en çok oy alan konuyu Shorts brifine çevirir.
    """
    return {
        "source": "community_poll_winner",
        "poll_topic": poll_topic,
        "winning_option": winning_option,
        "shorts_title": f"{winning_option} — {poll_topic} #Shorts",
        "hook": f"Siz oyladınız, biz dinledik: '{winning_option}' konusunu derinlemesine inceliyoruz.",
        "production_delay_hours": 2,
        "upload_note": "Manuel Studio upload — otomatik yayın yok.",
    }

def create_comment_to_video_hook(user_comment: str, username: str = "Takipçi") -> Dict[str, str]:
    """
    Item 311 / 83: Transforms a top viewer comment into an engaging video opening hook.
    """
    clean_comment = user_comment.strip().strip('"').strip("'")
    return {
        "visual_overlay_text": f"@{username}: '{clean_comment[:60]}...'",
        "spoken_hook": f"Bir takipçimiz demiş ki: '{clean_comment}'. İşte bu sorunun cevabı ve kimsenin bilmediği gerçekler...",
        "suggested_title": f"Takipçi Yorumu: {clean_comment[:40]} #Shorts"
    }

def format_cross_platform_metadata(title: str, description: str, tags: List[str]) -> Dict[str, Any]:
    """
    Item 322 / 99: Adapts YouTube Shorts metadata for seamless cross-posting to TikTok and Instagram Reels.
    Filigransız TikTok ve Reels caption paketi (auto-upload out of scope).
    """
    clean_title = title.replace("#Shorts", "").replace("#shorts", "").strip()
    hashtags = " ".join([f"#{t.lstrip('#')}" for t in tags[:8]])
    
    return {
        "tiktok": {
            "caption": f"{clean_title}\n.\n{hashtags} #fyp #viral #kesfet",
            "max_chars": 2200
        },
        "instagram_reels": {
            "caption": f"{clean_title}\n\n{description[:300]}...\n\n{hashtags} #reels #trend",
            "share_to_feed": True
        }
    }


# Backward-compatible alias (audit + smoke tests reference this name)
generate_cross_platform_metadata = format_cross_platform_metadata


def generate_viewer_choice_cta(option_a: str, option_b: str, lang: str = "tr") -> Dict[str, str]:
    """
    Item 335: İzleyiciye Seçim Yaptırma — Kapı 1 / Kapı 2 yorum CTA.
    """
    if lang == "en":
        return {
            "spoken_hook": f"Door 1: {option_a}. Door 2: {option_b}. Which one would you choose?",
            "visual_overlay": f"DOOR 1 vs DOOR 2 — Comment your pick!",
            "pinned_comment_bait": f"🚪 Door 1 ({option_a}) or Door 2 ({option_b})? Drop your choice below — most creative answer gets pinned!",
        }
    return {
        "spoken_hook": f"Kapı 1: {option_a}. Kapı 2: {option_b}. Sen hangisini seçerdin?",
        "visual_overlay": "KAPI 1 mi KAPI 2 mi? — Seçimini yoruma yaz!",
        "pinned_comment_bait": f"🚪 Kapı 1 ({option_a}) mi Kapı 2 ({option_b}) mi? Seçimini yoruma yaz — en yaratıcı cevap sabitlenecek!",
    }


def check_channel_warmup_limit(channel_id: str, daily_uploads_count: int, channel_age_days: int = 5) -> Dict[str, Any]:
    """
    Item 85: 2-Week Warm-Up Safety Rule.
    Prevents new channels (<14 days old) from uploading >3-5 videos/day to avoid spam flags.
    """
    max_allowed = 3 if channel_age_days <= 14 else 15
    is_safe = daily_uploads_count < max_allowed
    return {
        "is_safe": is_safe,
        "daily_uploads_count": daily_uploads_count,
        "max_allowed_for_age": max_allowed,
        "channel_age_days": channel_age_days,
        "warning": None if is_safe else f"UYARI: Kanalınız henüz {channel_age_days} günlük. Algoritmada spam şüphesini önlemek için günde en fazla {max_allowed} video yüklemeniz önerilir."
    }

def generate_micro_interview_dialogue(question: str, lang: str = "tr") -> Dict[str, Any]:
    """
    Item 316: Sokak röportajı kurgusu — tek derin soru + 3 farklı cevap diyalogu.
    """
    if lang == "en":
        return {
            "question": question,
            "interviewer_hook": f"We asked strangers one question: '{question}'",
            "responses": [
                {"speaker": "Person A", "line": "Honestly? I never thought about it until now."},
                {"speaker": "Person B", "line": "That's the hardest question I've been asked all year."},
                {"speaker": "Person C", "line": "Give me five seconds... okay, here's my truth."},
            ],
            "visual_style": "handheld_street_interview",
        }
    return {
        "question": question,
        "interviewer_hook": f"Sokakta tek bir soru sorduk: '{question}'",
        "responses": [
            {"speaker": "Kişi A", "line": "Dürüst olmak gerekirse, daha önce hiç düşünmemiştim."},
            {"speaker": "Kişi B", "line": "Bu yıl bana sorulan en zor soru bu."},
            {"speaker": "Kişi C", "line": "5 saniye ver... tamam, işte gerçeğim."},
        ],
        "visual_style": "handheld_street_interview",
    }


def generate_seasonal_trend_hook(film_or_trend: str, angle: str = "philosophy", lang: str = "tr") -> Dict[str, str]:
    """
    Item 317: Vizyondaki film/trend üzerinden felsefe veya tarih açılı kancası.
    """
    if lang == "en":
        return {
            "title": f"What {film_or_trend} Really Teaches Us About {angle.title()} #Shorts",
            "hook": f"Everyone is talking about {film_or_trend} — but the real {angle} lesson is hidden here.",
            "angle": angle,
            "trend_source": film_or_trend,
        }
    return {
        "title": f"{film_or_trend} Aslında Bize Ne Anlatıyor? ({angle.title()}) #Shorts",
        "hook": f"Herkes {film_or_trend} konuşuyor — ama asıl {angle} dersi burada gizli.",
        "angle": angle,
        "trend_source": film_or_trend,
    }


def generate_studio_engagement_checklist(lang: str = "tr") -> Dict[str, str]:
    """
    Items 350-351, 374-375: Manuel Studio yükleme sonrası etkileşim kontrol listesi.
    Otomatik pin/kalp/yorum filtresi kapsam dışı — operatör Studio'da uygular.
    """
    if lang == "en":
        return {
            "pinned_comment_action": "Post the suggested comment immediately after upload and pin it to the top.",
            "heart_action": "Heart the first 5-10 viewer comments within 2 hours (channel-owner red heart).",
            "reply_action": "Reply to every viewer comment within the first 120 minutes after upload (Item 374).",
            "spam_filter_action": (
                "YouTube Studio → Settings → Community → Automated filters: block links and common spam phrases (Item 375)."
            ),
            "studio_note": "Auto pin/heart/spam filter out of scope — manual Studio only.",
        }
    return {
        "pinned_comment_action": "Yükleme sonrası önerilen yorumu hemen atın ve en üste sabitleyin (Item 350).",
        "heart_action": "İlk 2 saatte gelen ilk 5-10 yoruma kanal sahibi olarak kırmızı kalp bırakın (Item 351).",
        "reply_action": "Yükleme sonrası ilk 120 dakikada gelen her yoruma hızlıca yanıt verin (Item 374).",
        "spam_filter_action": (
            "YouTube Studio → Ayarlar → Topluluk → Otomatik filtreler: linkli ve bot yorumları engelleyin (Item 375)."
        ),
        "studio_note": "Otomatik pin/kalp/spam filtresi kapsam dışı — Studio manuel.",
    }


def generate_weekly_live_stream_plan(lang: str = "tr") -> Dict[str, str]:
    """
    Item 384: Canlı Sohbet / Canlı Yayın Geçişi.
    Haftalık canlı yayın ile organik kullanıcı sinyali planı (manuel Studio).
    """
    if lang == "en":
        return {
            "schedule": "Once per week — 30-45 min live Q&A on your best-performing Shorts niche topic (Item 384).",
            "ffmpeg_loop_note": "For 24/7 Shorts loop streaming use generate_live_stream_loop_command() (Items 76/97/315).",
            "studio_action": "YouTube Studio → Go Live → schedule a recurring weekly slot.",
            "item": "384",
        }
    return {
        "schedule": "Haftada 1 kez 30-45 dk canlı yayın — en iyi performans gösteren Shorts konusunu açın (Item 384).",
        "ffmpeg_loop_note": "24/7 Shorts döngüsü için generate_live_stream_loop_command() FFmpeg komutu (Items 76/97/315).",
        "studio_action": "YouTube Studio → Canlı Yayın → haftalık tekrarlayan slot planlayın.",
        "item": "384",
    }


def generate_affiliate_pinned_cta(product_name: str, affiliate_url: str = "", lang: str = "tr") -> Dict[str, str]:
    """
    Item 319: Videoda adı geçen ürün/kitap için şeffaf sabitlenmiş yorum affiliate CTA.
    """
    url_hint = affiliate_url.strip() or "(link açıklamada veya kanal profilinde)"
    if lang == "en":
        return {
            "pinned_comment": (
                f"📌 Transparent affiliate: The {product_name} mentioned in this video → {url_hint}. "
                f"Purchases through this link support the channel at no extra cost."
            ),
            "affiliate_disclosure": f"#ad Affiliate link for {product_name}",
        }
    return {
        "pinned_comment": (
            f"📌 Şeffaf affiliate: Videoda bahsettiğim {product_name} → {url_hint}. "
            f"Bu linkten alışveriş kanalı destekler; size ekstra maliyet yok."
        ),
        "affiliate_disclosure": f"#reklam {product_name} affiliate bağlantısı",
    }


def generate_live_stream_loop_command(video_path: str, stream_key: str, rtmp_url: str = "rtmp://a.rtmp.youtube.com/live2") -> str:
    """
    Items 315 / 76 / 97: FFmpeg komutu — Shorts'ları 24/7 kesintisiz canlı yayın döngüsüne verir.
    """
    return (
        f'ffmpeg -re -stream_loop -1 -i "{video_path}" -c:v libx264 -preset veryfast '
        f'-maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -c:a aac -b:a 160k -ar 44100 '
        f'-f flv "{rtmp_url}/{stream_key}"'
    )

def build_tier1_adaptation_brief(topic: str, target_country: str = "US", lang: str = "en") -> Dict[str, Any]:
    """
    Item 321: Tier-1 ülke adaptasyonu — EN metadata + EST yayın penceresi operatör brifi.
    """
    from proof_archiver import ProofArchiver

    rpm = ProofArchiver.get_tier1_rpm_multiplier(target_country)
    if lang == "en":
        return {
            "item": "321",
            "topic": topic,
            "target_country": target_country,
            "language": "en",
            "title_template": f"Why {topic} Changes Everything (Most People Miss This) #Shorts",
            "hook_template": f"Nobody talks about this side of {topic} — and it might explain everything.",
            "upload_window": "19:00-21:00 America/New_York (EST/EDT)",
            "rpm_advisory": rpm,
            "studio_actions": [
                "Set channel default language to English.",
                "Use EN titles, descriptions, and pinned comments.",
                "Schedule publish in US peak window via Studio → Visibility → Schedule.",
            ],
        }
    return {
        "item": "321",
        "topic": topic,
        "target_country": target_country,
        "language": "en",
        "title_template": f"Why {topic} Changes Everything #Shorts",
        "hook_template": f"{topic} hakkında kimse konuşmuyor — işte gerçek sebep.",
        "upload_window": "19:00-21:00 America/New_York (EST/EDT)",
        "rpm_advisory": rpm,
        "studio_actions": [
            "Kanal varsayılan dilini İngilizce yapın.",
            "Başlık, açıklama ve sabit yorum EN üretin; operatör Studio'da yapıştırır.",
            "Studio → Görünürlük → Zamanla ile ABD pik saatinde yayınlayın.",
        ],
    }


def export_growth_operator_pack(
    topic: str,
    *,
    user_comment: str = "",
    username: str = "Takipçi",
    related_video_url: str = "",
    long_form_title: str = "",
    series_title: str = "",
    episode_num: int = 1,
    product_name: str = "",
    affiliate_url: str = "",
    niche_a_id: str = "stoic_cyberpunk",
    niche_b_id: str = "mythology_ai_epic",
    loop_video_path: str = "output/latest_short.mp4",
    stream_key: str = "(Studio stream key)",
    title: str = "",
    description: str = "",
    tags: List[str] = None,
    target_country: str = "US",
    lang: str = "tr",
) -> Dict[str, Any]:
    """
    Items 311-322, 384 — growth taktikleri operatör paketi.
    Otomatik Studio upload kapsam dışı; JSON checklist ile manuel uygulama.
    """
    from hybrid_niches import collide_two_niches, generate_episodic_series_hook
    from viral_seo_agent import generate_related_video_bridge

    clean_title = title or topic
    tag_list = tags or [topic.replace(" ", ""), "Shorts", "Viral"]
    cross_platform = format_cross_platform_metadata(clean_title, description or clean_title, tag_list)

    pack: Dict[str, Any] = {
        "pack_type": "growth_operator_pack",
        "items_covered": "311-322,384",
        "topic": topic,
        "manual_studio_only": True,
        "comment_to_video": create_comment_to_video_hook(user_comment or f"{topic} hakkında ne düşünüyorsunuz?", username),
        "community_poll": generate_community_poll(topic),
        "poll_winner_brief": plan_shorts_from_poll_winner(topic, generate_community_poll(topic)["options"][0]),
        "related_video_bridge": generate_related_video_bridge(
            clean_title,
            related_video_url or "https://youtube.com/watch?v=PLACEHOLDER",
            long_form_title or f"Full {topic} Documentary",
        ),
        "series_format": generate_episodic_series_hook(
            series_title or f"{topic} Serisi",
            episode_num=episode_num,
            lang=lang,
        ),
        "live_stream_loop_ffmpeg": generate_live_stream_loop_command(loop_video_path, stream_key),
        "weekly_live_plan": generate_weekly_live_stream_plan(lang=lang),
        "affiliate_pinned_cta": generate_affiliate_pinned_cta(product_name or topic, affiliate_url, lang=lang),
        "niche_collision": collide_two_niches(niche_a_id, niche_b_id),
        "tier1_adaptation": build_tier1_adaptation_brief(topic, target_country=target_country, lang=lang),
        "cross_platform": cross_platform,
        "ab_test_variants": generate_ab_test_variants(topic),
        "studio_checklist": [
            "311: Top yorumu hook olarak kullanın; render sonrası manuel Studio upload.",
            "312: Community poll atın; kazanan seçeneği 2 saat içinde Shorts brifine çevirin.",
            "313: Açıklamaya related video link ekleyin (Shorts end screen yok).",
            "314: Başlıkta Bölüm N / Part N formatını koruyun.",
            "315: 24/7 stream için FFmpeg komutunu OBS veya sunucuda çalıştırın.",
            "319: Affiliate pinned comment — şeffaf #ad disclosure ile.",
            "320: İki niş çarpışması prompt'unu Director planına enjekte edin.",
            "321: Tier-1 EN metadata + EST upload penceresi.",
            "322: TikTok/Reels caption paketini cross-post için kopyalayın.",
            "384: Haftalık canlı yayın slotunu Studio'da planlayın.",
        ],
    }
    return pack


def check_copyright_risk(script_text: str, search_queries: List[str]) -> Dict[str, Any]:
    """
    Item 65: Copyright and Policy Pre-check.
    Checks for high-risk trademarked terms, explicit words, or restricted content.
    """
    risk_words = ["disney", "marvel", "netflix", "nfl", "fifa", "premier league", "telif", "şiddet"]
    found_risks = []
    lower_text = script_text.lower()
    
    for rw in risk_words:
        if rw in lower_text:
            found_risks.append(rw)
            
    risk_score = min(100, len(found_risks) * 25)
    return {
        "risk_score": risk_score,
        "flagged_keywords": found_risks,
        "is_safe_to_publish": risk_score < 50,
        "recommendation": "Görüntüde ayna (mirror) ve ses tonu kaydırma kullanın" if risk_score > 0 else "İçerik güvenli."
    }
