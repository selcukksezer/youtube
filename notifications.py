"""
Notifications Manager — Telegram & Discord Webhook Alerts (Item 77)
Sends status updates when video rendering completes, uploads succeed, or errors occur.
"""
import os, json, urllib.request
import config

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

def send_telegram_message(message: str) -> bool:
    """Sends a text message to Telegram channel/user via Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"  [Notification] Telegram send failed: {e}")
        return False

def send_discord_notification(title: str, description: str, color: int = 0x00FF88) -> bool:
    """Sends an embed notification to Discord Webhook."""
    if not DISCORD_WEBHOOK_URL:
        return False
    try:
        payload = json.dumps({
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": "YouTube Shorts Ultimate Studio"}
            }]
        }).encode("utf-8")
        req = urllib.request.Request(DISCORD_WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"  [Notification] Discord send failed: {e}")
        return False

def notify_video_ready(title: str, video_url: str, duration_sec: float = 0.0):
    """Broadcasts a success notification across configured channels."""
    msg = (
        f"🎬 <b>Yeni Shorts Videosu Hazır!</b>\n"
        f"📌 <b>Başlık:</b> {title}\n"
        f"⏱ <b>Süre:</b> {duration_sec:.1f} saniye\n"
        f"🔗 <b>İzleme Linki:</b> {video_url}"
    )
    send_telegram_message(msg)
    send_discord_notification("🎬 Yeni Video Hazırlandı", f"**{title}**\nSüre: {duration_sec:.1f}s\nLink: {video_url}", 0x00D4FF)

def notify_upload_success(title: str, youtube_video_id: str):
    """Broadcasts a YouTube upload notification."""
    yt_url = f"https://youtube.com/shorts/{youtube_video_id}"
    msg = (
        f"🚀 <b>YouTube'a Yüklendi!</b>\n"
        f"📌 <b>Başlık:</b> {title}\n"
        f"🔗 <b>YouTube:</b> {yt_url}"
    )
    send_telegram_message(msg)
    send_discord_notification("🚀 YouTube Yüklemesi Başarılı", f"**{title}**\nİzleyin: {yt_url}", 0xFF0033)
