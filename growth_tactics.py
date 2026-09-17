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

def generate_ab_test_variants(topic: str) -> List[Dict[str, str]]:
    """
    Item 98: Generates 3 distinct A/B test variations (Curiosity, Shock, Story)
    to test which hook and title get the highest CTR and retention.
    """
    return [
        {
            "variant": "A_Curiosity",
            "title": f"Bunu Biliyor Muydunuz? {topic} Hakkında Gizli Gerçek #Shorts",
            "hook": f"{topic} hakkında bildiğiniz her şey yanlış olabilir! İşte kimsenin anlatmadığı o detay..."
        },
        {
            "variant": "B_Shock",
            "title": f"İNANILMAZ! {topic} Olayı Herkesi Şok Etti #Shorts",
            "hook": f"Bu bilgiyi duyduğunuzda tüyleriniz ürperecek: {topic} aslında göründüğü gibi değil!"
        },
        {
            "variant": "C_Debate",
            "title": f"Siz Olsaydınız Ne Yapardınız? {topic} #Shorts",
            "hook": f"Tarihin en büyük ikilemi: {topic} konusunda siz hangi taraftasınız?"
        }
    ]

def generate_community_poll(topic: str) -> Dict[str, Any]:
    """
    Item 89: Generates a YouTube Community post / poll to warm up audience 1h before video upload.
    """
    return {
        "question": f"Bugünkü Shorts konumuz '{topic}'. Sizce bu konuda en çok merak edilen şey nedir?",
        "options": [
            f"{topic} hakkında hiç bilinmeyen sırlar",
            "Tarihteki en büyük hatalar",
            "Gelecekte bizi bekleyenler",
            "Sonucu görmek istiyorum"
        ],
        "scheduled_delay_minutes": 60
    }

def create_comment_to_video_hook(user_comment: str, username: str = "Takipçi") -> Dict[str, str]:
    """
    Item 83: Transforms a top viewer comment into an engaging video opening hook.
    """
    clean_comment = user_comment.strip().strip('"').strip("'")
    return {
        "visual_overlay_text": f"@{username}: '{clean_comment[:60]}...'",
        "spoken_hook": f"Bir takipçimiz demiş ki: '{clean_comment}'. İşte bu sorunun cevabı ve kimsenin bilmediği gerçekler...",
        "suggested_title": f"Takipçi Yorumu: {clean_comment[:40]} #Shorts"
    }

def format_cross_platform_metadata(title: str, description: str, tags: List[str]) -> Dict[str, Any]:
    """
    Item 99: Adapts YouTube Shorts metadata for seamless cross-posting to TikTok and Instagram Reels.
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

def generate_live_stream_loop_command(video_path: str, stream_key: str, rtmp_url: str = "rtmp://a.rtmp.youtube.com/live2") -> str:
    """
    Items 76, 97: Builds FFmpeg command to broadcast Shorts in an infinite 24/7 loop on YouTube Live.
    """
    return (
        f'ffmpeg -re -stream_loop -1 -i "{video_path}" -c:v libx264 -preset veryfast '
        f'-maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -c:a aac -b:a 160k -ar 44100 '
        f'-f flv "{rtmp_url}/{stream_key}"'
    )

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
