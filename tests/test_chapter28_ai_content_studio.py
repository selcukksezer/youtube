"""
Unit and Integration tests for Chapter 28.2 (ai-content-studio adaptations):
- services.secret_vault (SecretVault, LicenseManager)
- director.prompt_chains (RoleBasedPromptChain, detect_punch_in_cues, build_punch_in_filter)
- services.evidence_overlay (EvidenceBadgeGenerator)
"""

import os
import tempfile
import pytest
from PIL import Image

from services.secret_vault import SecretVault, LicenseManager
from services.evidence_overlay import EvidenceBadgeGenerator
from director.prompt_chains import (
    RoleBasedPromptChain,
    detect_punch_in_cues,
    build_punch_in_filter,
)


def test_secret_vault_aes256_encryption_and_decryption():
    """Verify AES-256-GCM encryption, decryption, and disk persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault.enc")
        vault = SecretVault(vault_path=vault_path)

        # Initially empty
        assert vault.get_secret("NON_EXISTENT") is None

        # Store secrets
        vault.set_secret("OPENAI_API_KEY", "sk-proj-super-secret-123456")
        vault.set_secret("WAVESPEED_API_KEY", "ws-prod-99887766")

        # Read back in same instance
        assert vault.get_secret("OPENAI_API_KEY") == "sk-proj-super-secret-123456"
        assert vault.get_secret("WAVESPEED_API_KEY") == "ws-prod-99887766"

        # Verify disk file is encrypted (contains version prefix and ciphertext, not plain text)
        with open(vault_path, "r", encoding="utf-8") as f:
            raw_disk = f.read()
        assert raw_disk.startswith("v1:")
        assert "sk-proj-super-secret-123456" not in raw_disk

        # Open fresh vault instance pointing to same file and verify decryption
        vault_loaded = SecretVault(vault_path=vault_path)
        assert vault_loaded.get_secret("OPENAI_API_KEY") == "sk-proj-super-secret-123456"

        # Delete secret
        assert vault_loaded.delete_secret("OPENAI_API_KEY") is True
        assert vault_loaded.get_secret("OPENAI_API_KEY") is None


def test_license_manager_tiers_and_validation():
    """Verify license manager key validations, activations, and tier access."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault.enc")
        vault = SecretVault(vault_path=vault_path)
        lm = LicenseManager(vault=vault)

        # Unlicensed state
        assert lm.is_activated("core") is False
        assert lm.get_license()["status"] == "unlicensed"

        # Validate beta test key
        val_beta = lm.validate_key("BETA-TEST-KEY")
        assert val_beta["valid"] is True
        assert val_beta["tier"] == "pro"

        # Save and verify activation
        save_res = lm.save_license("BETA-TEST-KEY", customer="BetaTester")
        assert save_res["status"] == "activated"
        assert lm.is_activated("watermark_removal") is True
        assert lm.is_activated("4k_rendering") is True
        assert lm.is_activated("cloud_farm") is False  # Pro does not get cloud farm

        # Activate Enterprise key
        lm.save_license("ENT-XYZ-999-KEY", customer="EnterpriseCorp")
        assert lm.is_activated("cloud_farm") is True
        assert lm.is_activated("priority_gpu") is True

        # Invalid key
        assert lm.validate_key("INVALID-GARBAGE")["valid"] is False


def test_role_based_prompt_chain():
    """Verify role-based prompt generation for investigator, screenwriter, and director."""
    chain = RoleBasedPromptChain()
    roles = chain.generate_chain(
        topic="Karadeliklerin Olay Ufku",
        niche="science",
        target_duration=45.0,
        language="tr",
    )

    assert "investigator" in roles
    assert "screenwriter" in roles
    assert "visual_director" in roles

    # Content checks
    assert "Karadeliklerin Olay Ufku" in roles["investigator"]["prompt"]
    assert "science" in roles["investigator"]["prompt"]
    assert roles["screenwriter"]["word_target"] == 112  # 45s * 2.5 wps
    assert "Safe-Zone" in roles["visual_director"]["prompt"]


def test_punch_in_detection_and_ffmpeg_filter():
    """Verify dynamic punch-in zoom detection and single-pass FFmpeg filter string generation."""
    cues = [
        {"word": "NORMAL", "start": 0.0, "end": 0.5},
        {"word": "ŞOK", "start": 1.2, "end": 1.7},  # Power word -> punch-in
        {"word": "ve", "start": 1.8, "end": 2.0},
        {"word": "DİKKAT", "start": 3.0, "end": 3.4},  # Power word -> punch-in
    ]

    detected = detect_punch_in_cues(cues, min_gap_seconds=1.0)
    assert len(detected) == 2
    assert detected[0]["word"] == "ŞOK"
    assert detected[1]["word"] == "DİKKAT"

    # Generate single-pass FFmpeg filter
    filter_str = build_punch_in_filter(detected, input_label="0:v", output_label="v_zoomed")
    assert "[0:v]split=2[base_v][punch_v]" in filter_str
    assert "crop=iw*0.87:ih*0.87" in filter_str
    assert "between(t," in filter_str
    assert "[v_zoomed]" in filter_str


def test_evidence_badge_png_generation_and_overlay_filter():
    """Verify clean evidence badge PNG generation and safe-zone FFmpeg overlay filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        badge_png = os.path.join(tmpdir, "badge.png")
        EvidenceBadgeGenerator.generate_badge_png(
            source_domain="https://www.nature.com/articles/s41586-024-001",
            output_png_path=badge_png,
            label="KAYNAK",
        )

        assert os.path.exists(badge_png)
        with Image.open(badge_png) as img:
            assert img.size == (EvidenceBadgeGenerator.DEFAULT_WIDTH, EvidenceBadgeGenerator.DEFAULT_HEIGHT)
            assert img.mode == "RGBA"

        # Test overlay filter string
        filt = EvidenceBadgeGenerator.build_ffmpeg_overlay_filter(
            input_label="bg_v",
            badge_input_label="1:v",
            output_label="out_v",
            start_time=1.0,
            end_time=5.0,
            position="top_left",
        )
        assert "[bg_v][1:v]overlay=x=40:y=140:enable='between(t,1.00,5.00)'[out_v]" == filt
