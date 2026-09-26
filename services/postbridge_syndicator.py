"""
PostBridge & Webhook Multi-Platform Video Syndicator.
Adapted and extended from MoneyPrinterV2's PostBridge integration.

Allows 1-click cross-posting of rendered 9:16 Shorts to:
- YouTube Shorts
- TikTok
- Instagram Reels
- Facebook Reels
- LinkedIn
Also supports generic webhooks (n8n, Make, Zapier) for fully custom distribution.
"""

from __future__ import annotations
import os
import time
import mimetypes
import logging
import urllib.request
import urllib.error
import json
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger("PostBridgeSyndicator")

POSTBRIDGE_API_BASE = "https://api.post-bridge.com/v1"


class PostBridgeClient:
    """Thin client for Post Bridge API (v1)."""

    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key.strip()
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ShortsVideoCreators/1.0"
        }

    def _request(self, method: str, url: str, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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
            "size_bytes": file_size
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
        scheduled_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish video to multiple connected social channels."""
        payload: Dict[str, Any] = {
            "caption": caption,
            "social_accounts": list(social_account_ids),
            "media": [media_id],
            "processing_enabled": True
        }
        if scheduled_at:
            payload["scheduled_at"] = scheduled_at

        return self._request(
            "POST",
            f"{POSTBRIDGE_API_BASE}/posts",
            data=json.dumps(payload).encode("utf-8")
        )


def broadcast_to_webhook(webhook_url: str, payload: Dict[str, Any], timeout: float = 10.0) -> bool:
    """Send video release package to n8n / Make / Zapier webhook."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "ShortsVideoCreators"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status in (200, 201, 204)
    except Exception as e:
        logger.error(f"Webhook broadcast failed: {e}")
        return False
