"""
Tests for Chapter 9.1: Kotasız YouTube Studio Headless Browser Uploader
Covers:
- Profile detection for Chrome and Firefox (detect_default_browser_profiles)
- Zero-quota browser upload flow (upload_video_via_browser)
- SQLite database persistence of captured YouTube URL (database.update_video_published_url)
- HeadlessStudioUploader OOP class interface
- Error handling for missing video files
"""
import os
import tempfile
import pytest

import database
from services.headless_uploader import (
    detect_default_browser_profiles,
    upload_video_via_browser,
    HeadlessStudioUploader,
)


def test_detect_default_browser_profiles_structure():
    profiles = detect_default_browser_profiles()
    assert "chrome" in profiles
    assert "firefox" in profiles
    assert "base_dir" in profiles["chrome"]
    assert isinstance(profiles["chrome"]["profiles"], list)
    assert isinstance(profiles["firefox"], list)


def test_upload_missing_video_fails_gracefully():
    res = upload_video_via_browser(
        video_path="non_existent_file_xyz_123.mp4",
        title="Test Title",
        description="Test Desc",
        dry_run=False,
    )
    assert res["success"] is False
    assert "bulunamadı" in res["error"] or "not found" in res["error"].lower()


def test_upload_dry_run_persists_to_sqlite_new_record():
    with tempfile.TemporaryDirectory() as td:
        dummy_video = os.path.join(td, "sample_short.mp4")
        with open(dummy_video, "wb") as f:
            f.write(b"video content")

        title = "Roma'nın Gizli Tarihi #Shorts"
        desc = "Tarihin bilinmeyen yüzü."
        res = upload_video_via_browser(
            video_path=dummy_video,
            title=title,
            description=desc,
            channel_slug="history_hub",
            dry_run=True,
        )

        assert res["success"] is True
        assert res["quota_consumed"] == 0
        assert res["url"].startswith("https://youtu.be/")
        assert res["video_id"] is not None

        # Verify in SQLite database
        row = database.get_video_by_id(res["video_id"])
        assert row is not None
        assert row["title"] == title
        assert row["status"] == "published"
        assert row["youtube_url"] == res["url"]
        assert row["channel_slug"] == "history_hub"


def test_upload_dry_run_updates_existing_sqlite_record():
    # Insert a pending video record first
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO videos (keyword, title, status, channel_slug) VALUES (?, ?, 'pending', ?)",
            ("ancient rome", "Pending Rome Video", "test_channel"),
        )
        conn.commit()
        existing_vid = cursor.lastrowid

    res = upload_video_via_browser(
        video_path="dummy_path.mp4",
        title="Pending Rome Video",
        description="Updated description",
        video_id=existing_vid,
        channel_slug="test_channel",
        dry_run=True,
    )

    assert res["success"] is True
    assert res["video_id"] == existing_vid

    # Verify updated in SQLite
    row = database.get_video_by_id(existing_vid)
    assert row["status"] == "published"
    assert row["youtube_url"] == res["url"]


def test_headless_studio_uploader_class_interface():
    uploader = HeadlessStudioUploader(browser_type="chrome")
    profiles = uploader.get_detected_profiles()
    assert "chrome" in profiles

    res = uploader.upload(
        video_path="dummy_video.mp4",
        title="OOP Class Test",
        description="Test desc",
        dry_run=True,
    )
    assert res["success"] is True
    assert res["quota_consumed"] == 0
    assert "sim_" in res["url"]
