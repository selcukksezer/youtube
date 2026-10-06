"""
Tests for Chapter 9.2: PostBridge Çoklu Platform Webhook Dağıtıcısı
Covers:
- build_syndication_webhook_payload adhering to Chapter 9.2 canonical schema:
  video download url, title, tags, schedule parameters, platforms
- broadcast_to_webhook delivery, status codes, and dry_run simulation
- MultiPlatformSyndicator high-level coordination and SQLite share_decision persistence
- PostBridgeClient payload structure
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock

import database
from services.postbridge_syndicator import (
    build_syndication_webhook_payload,
    broadcast_to_webhook,
    MultiPlatformSyndicator,
    PostBridgeClient,
    SUPPORTED_PLATFORMS,
)


def test_build_syndication_webhook_payload_canonical_fields():
    payload = build_syndication_webhook_payload(
        title="Büyük Roma Yangını Sırları",
        video_url="https://storage.example.com/renders/rome_short.mp4",
        download_url="https://storage.example.com/downloads/rome_short.mp4",
        description="Yangının bilinmeyen detayları #tarih #roma",
        tags=["#tarih", "roma", "antik"],
        filename="rome_short.mp4",
        duration_seconds=58.2,
        niche_id="4_history",
        language="tr",
        publish_at="2026-09-27T18:00:00Z",
        target_platforms=["tiktok", "instagram_reels", "facebook_reels"],
    )

    # 1. Video parameters
    assert payload["version"] == 1
    assert payload["event"] == "video.ready_for_publish"
    assert payload["video"]["url"] == "https://storage.example.com/renders/rome_short.mp4"
    assert payload["video"]["download_url"] == "https://storage.example.com/downloads/rome_short.mp4"
    assert payload["video"]["filename"] == "rome_short.mp4"
    assert payload["video"]["duration_seconds"] == 58.2
    assert payload["video"]["aspect_ratio"] == "9:16"

    # 2. Metadata parameters
    assert payload["metadata"]["title"] == "Büyük Roma Yangını Sırları"
    assert payload["metadata"]["tags"] == ["tarih", "roma", "antik"]  # stripped #
    assert payload["metadata"]["niche_id"] == "4_history"
    assert payload["metadata"]["language"] == "tr"

    # 3. Schedule parameters
    assert payload["schedule"]["publish_at"] == "2026-09-27T18:00:00Z"
    assert payload["schedule"]["publish_now"] is False
    assert payload["schedule"]["timezone"] == "Europe/Istanbul"

    # 4. Target platforms
    assert payload["platforms"] == ["tiktok", "instagram_reels", "facebook_reels"]


def test_broadcast_to_webhook_dry_run_and_empty_url():
    payload = {"test": 123}

    # Empty URL error
    err_res = broadcast_to_webhook("", payload)
    assert err_res["success"] is False
    assert err_res["status_code"] == 400

    # Dry run simulation
    dry_res = broadcast_to_webhook("https://n8n.example.com/webhook/shorts", payload, dry_run=True)
    assert dry_res["success"] is True
    assert dry_res["status_code"] == 200
    assert dry_res["url"] == "https://n8n.example.com/webhook/shorts"


def test_broadcast_to_webhook_with_mocked_http():
    payload = {"title": "Test Webhook"}
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b'{"status": "received"}'
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = broadcast_to_webhook("https://hooks.zapier.com/hooks/catch/123", payload)
        assert res["success"] is True
        assert res["status_code"] == 200
        assert "received" in res["response"]


def test_multi_platform_syndicator_dry_run_updates_sqlite():
    # Insert a dummy video row in SQLite
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO videos (keyword, title, status) VALUES (?, ?, 'published')",
            ("gadget review", "3 Hayat Kurtaran Ürün"),
        )
        conn.commit()
        dummy_vid = cursor.lastrowid

    syndicator = MultiPlatformSyndicator(default_webhook_url="https://api.postbridge.com/dummy_hook")
    res = syndicator.syndicate(
        title="3 Hayat Kurtaran Ürün",
        video_path_or_url="https://storage.example.com/gadgets.mp4",
        description="Amazon linkleri profilde #shorts",
        tags=["gadget", "amazon"],
        video_id=dummy_vid,
        dry_run=True,
    )

    assert res["success"] is True
    assert "tiktok" in res["platforms"]
    assert "instagram_reels" in res["platforms"]
    assert res["webhook_result"]["success"] is True

    # Check that SQLite share_decision was updated
    row = database.get_video_by_id(dummy_vid)
    assert row["share_decision"] is not None
    dec = json.loads(row["share_decision"])
    assert "tiktok" in dec["platforms"]
    assert dec["webhook"] is True


def test_postbridge_client_publish_short_payload():
    client = PostBridgeClient(api_key="pb_test_key_123")
    with patch.object(client, "_request", return_value={"id": "post_789"}) as mock_req:
        res = client.publish_short(
            caption="Check out this short! #trending",
            social_account_ids=[101, 102],
            media_id="media_abc_456",
            scheduled_at="2026-09-28T12:00:00Z",
        )
        assert res == {"id": "post_789"}
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert args[0] == "POST"
        assert args[1].endswith("/posts")
        sent_data = json.loads(kwargs["data"].decode("utf-8"))
        assert sent_data["caption"] == "Check out this short! #trending"
        assert sent_data["social_accounts"] == [101, 102]
        assert sent_data["media"] == ["media_abc_456"]
        assert sent_data["scheduled_at"] == "2026-09-28T12:00:00Z"
