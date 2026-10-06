"""
Bölüm 9.2: PostBridge Çoklu Platform Webhook Dağıtıcısı
(PostBridge & Webhook Multi-Platform Video Syndicator)

Tamamlanan videolar tek tıkla PostBridge veya özel Webhook adreslerine iletilerek
TikTok, Instagram Reels ve Facebook sayfalarına otomatik servis edilir:
- Kanonik JSON gövdesinde video indirme linki, başlık, etiketler ve zamanlama parametreleri yer alır.
- PostBridge REST API (v1) üzerinden sosyal hesaplara medya yükleme ve zamanlı paylaşım.
- Özel Webhook (n8n, Make, Zapier) üzerinden tam otomatik kurumsal dağıtım.
"""
from __future__ import annotations

import json
import logging
import mimetypes
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import database

logger = logging.getLogger("PostBridgeSyndicator")

POSTBRIDGE_API_BASE = "https://api.post-bridge.com/v1"
SUPPORTED_PLATFORMS = ("tiktok", "instagram_reels", "facebook_reels", "youtube_shorts", "linkedin")


def build_syndication_webhook_payload(
    *,
    title: str,
    video_url: str,
    description: str = "",
    tags: Optional[Sequence[str]] = None,
    download_url: Optional[str] = None,
    filename: str = "",
    duration_seconds: float = 0.0,
    niche_id: str = "general",
    language: str = "tr",
    publish_at: Optional[str] = None,
    publish_now: bool = True,
    timezone_str: str = "Europe/Istanbul",
    target_platforms: Optional[Sequence[str]] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Bölüm 9.2 kanonik Webhook dağıtım JSON gövdesini derler:
    video indirme linki, başlık, etiketler, zamanlama ve platform parametreleri.
    """
    clean_tags = [str(t).lstrip("#").strip() for t in (tags or []) if str(t).strip()][:30]
    platforms = list(target_platforms) if target_platforms else ["tiktok", "instagram_reels", "facebook_reels"]

    payload: Dict[str, Any] = {
        "version": 1,
        "event": "video.ready_for_publish",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "video": {
            "url": str(video_url or "").strip(),
            "download_url": str(download_url or video_url or "").strip(),
            "filename": str(filename or "short_video.mp4").strip(),
            "duration_seconds": round(float(duration_seconds), 2),
            "aspect_ratio": "9:16",
        },
        "metadata": {
            "title": str(title or "").strip()[:100],
            "description": str(description or "").strip(),
            "tags": clean_tags,
            "niche_id": str(niche_id or "general").strip(),
            "language": str(language or "tr").lower(),
        },
        "schedule": {
            "publish_at": publish_at,
            "publish_now": publish_now if not publish_at else False,
            "timezone": timezone_str,
        },
        "platforms": platforms,
    }

    if extra_payload and isinstance(extra_payload, dict):
        payload["extra"] = extra_payload

    return payload


def broadcast_to_webhook(
    webhook_url: str,
    payload: Dict[str, Any],
    timeout: float = 15.0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Bölüm 9.2: Dağıtım paketini özel Webhook adresine (n8n, Make, Zapier vb.) iletir.
    Returns:
        {"success": bool, "status_code": int, "error": Optional[str], "url": str}
    """
    if not webhook_url:
        return {"success": False, "status_code": 400, "error": "Boş Webhook URL'si", "url": ""}

    if dry_run:
        return {
            "success": True,
            "status_code": 200,
            "error": None,
            "url": webhook_url,
            "message": "Webhook iletimi simüle edildi (dry_run=True)",
            "payload": payload,
        }

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "ShortsVideoCreators/1.0 (Multi-Platform Syndicator)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            success = res.status in (200, 201, 202, 204)
            resp_body = res.read().decode("utf-8", errors="ignore")
            return {
                "success": success,
                "status_code": res.status,
                "response": resp_body[:500],
                "error": None if success else f"Unexpected HTTP status {res.status}",
                "url": webhook_url,
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"Webhook HTTP {e.code}: {err_body}")
        return {
            "success": False,
            "status_code": e.code,
            "error": f"HTTP {e.code}: {err_body[:200]}",
            "url": webhook_url,
        }
    except Exception as e:
        logger.error(f"Webhook connection error: {e}")
        return {
            "success": False,
            "status_code": 0,
            "error": str(e),
            "url": webhook_url,
        }


class PostBridgeClient:
    """Thin client for Post Bridge API (v1)."""

    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key.strip()
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ShortsVideoCreators/1.0",
        }

    def _request(
        self,
        method: str,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        req_headers = headers if headers is not None else self.headers
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                content = res.read().decode("utf-8")
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.error(f"PostBridge HTTP {e.code}: {err_body}")
            return {"error": f"HTTP {e.code}", "detail": err_body}
        except Exception as e:
            logger.error(f"PostBridge error: {e}")
            return {"error": str(e)}

    def list_accounts(self, platforms: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
        """Fetch connected social accounts."""
        url = f"{POSTBRIDGE_API_BASE}/social-accounts"
        if platforms:
            url += "?platform=" + ",".join(platforms)
        res = self._request("GET", url)
        return res.get("data", []) if isinstance(res, dict) else []

    def upload_media(self, file_path: str) -> Optional[str]:
        """Upload video file to PostBridge storage and return media_id."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Media file not found: {file_path}")

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        mime_type = mimetypes.guess_type(file_path)[0] or "video/mp4"

        # 1. Create upload url
        create_payload = json.dumps({
            "name": file_name,
            "mime_type": mime_type,
            "size_bytes": file_size,
        }).encode("utf-8")

        res = self._request("POST", f"{POSTBRIDGE_API_BASE}/media/create-upload-url", data=create_payload)
        media_id = res.get("media_id")
        upload_url = res.get("upload_url")

        if not media_id or not upload_url:
            logger.error(f"PostBridge create-upload-url failed: {res}")
            return None

        # 2. Upload raw bytes via PUT
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        put_headers = {"Content-Type": mime_type}
        req = urllib.request.Request(upload_url, data=file_bytes, headers=put_headers, method="PUT")
        with urllib.request.urlopen(req, timeout=300) as upload_res:
            if upload_res.status not in (200, 201):
                logger.error(f"Media upload failed with status {upload_res.status}")
                return None

        return media_id

    def publish_short(
        self,
        caption: str,
        social_account_ids: Sequence[int],
        media_id: str,
        scheduled_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish video to multiple connected social channels."""
        payload: Dict[str, Any] = {
            "caption": caption,
            "social_accounts": list(social_account_ids),
            "media": [media_id],
            "processing_enabled": True,
        }
        if scheduled_at:
            payload["scheduled_at"] = scheduled_at

        return self._request(
            "POST",
            f"{POSTBRIDGE_API_BASE}/posts",
            data=json.dumps(payload).encode("utf-8"),
        )


class MultiPlatformSyndicator:
    """
    Bölüm 9.2: Yüksek seviyeli Çoklu Platform Dağıtım Yöneticisi.
    PostBridge API ve Özel Webhook kanallarını birleşik arayüzden yönetir.
    """

    def __init__(
        self,
        postbridge_api_key: Optional[str] = None,
        default_webhook_url: Optional[str] = None,
    ):
        self.api_key = (postbridge_api_key or os.getenv("POSTBRIDGE_API_KEY", "")).strip()
        self.default_webhook = (default_webhook_url or os.getenv("DISTRIBUTION_WEBHOOK_URL", "")).strip()
        self.postbridge_client = PostBridgeClient(self.api_key) if self.api_key else None

    def syndicate(
        self,
        *,
        title: str,
        video_path_or_url: str,
        description: str = "",
        tags: Optional[Sequence[str]] = None,
        webhook_url: Optional[str] = None,
        target_platforms: Optional[Sequence[str]] = None,
        publish_at: Optional[str] = None,
        video_id: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Videoyu tek tıkla yapılandırılmış Webhook ve/veya PostBridge kanallarına dağıtır.
        Sonucu SQLite'a kalıcı olarak kaydeder.
        """
        platforms = list(target_platforms) if target_platforms else ["tiktok", "instagram_reels", "facebook_reels"]
        active_webhook = webhook_url or self.default_webhook

        payload = build_syndication_webhook_payload(
            title=title,
            video_url=video_path_or_url,
            description=description,
            tags=tags,
            publish_at=publish_at,
            target_platforms=platforms,
        )

        results: Dict[str, Any] = {
            "success": False,
            "platforms": platforms,
            "webhook_result": None,
            "postbridge_result": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Webhook İletimi
        if active_webhook:
            wh_res = broadcast_to_webhook(active_webhook, payload, dry_run=dry_run)
            results["webhook_result"] = wh_res
            if wh_res.get("success"):
                results["success"] = True

        # 2. PostBridge İletimi (Eğer API key varsa ve dosya yerelde mevcutsa)
        if self.postbridge_client and os.path.isfile(video_path_or_url) and not dry_run:
            try:
                media_id = self.postbridge_client.upload_media(video_path_or_url)
                if media_id:
                    # Fetch connected accounts
                    accs = self.postbridge_client.list_accounts()
                    acc_ids = [a["id"] for a in accs if a.get("id")]
                    if acc_ids:
                        caption = f"{title}\n\n{description}"[:2000]
                        pb_res = self.postbridge_client.publish_short(
                            caption=caption,
                            social_account_ids=acc_ids,
                            media_id=media_id,
                            scheduled_at=publish_at,
                        )
                        results["postbridge_result"] = pb_res
                        if not pb_res.get("error"):
                            results["success"] = True
            except Exception as pb_err:
                logger.error(f"PostBridge syndication failed: {pb_err}")
                results["postbridge_result"] = {"error": str(pb_err)}

        elif dry_run:
            results["postbridge_result"] = {"simulated": True, "media_id": "sim_pb_media_123"}
            results["success"] = True

        # 3. SQLite Dağıtım Kararı Kalıcılığı
        if video_id and results["success"]:
            try:
                decision_record = json.dumps({
                    "syndicated_at": datetime.now(timezone.utc).isoformat(),
                    "platforms": platforms,
                    "webhook": bool(active_webhook),
                }, ensure_ascii=False)
                with database.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE videos SET share_decision = ? WHERE id = ?",
                        (decision_record, int(video_id)),
                    )
                    conn.commit()
            except Exception as db_err:
                logger.warning(f"Could not persist share_decision to SQLite: {db_err}")

        return results
