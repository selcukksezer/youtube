"""
Tests for Chapter 9.3: E-Ticaret ve Amazon Satış Ortağı Kısa Video Motoru (AFM)
Covers:
- URL parsing for Amazon, Trendyol, Hepsiburada
- 3-scene canonical viral AFM script structure:
  1. Scene 1: Hook ("Bunu neden daha önce almadım diyeceksiniz...")
  2. Scene 2: Problem-Solution & practical usage
  3. Scene 3: Call-To-Action ("Link profilde / açıklamada")
- Detailed 7-scene mode support
- Multilingual script generation (TR & EN)
- Mandatory affiliate disclosure (#işbirliği #reklam / #ad #affiliate)
"""
import pytest
from services.affiliate_product_engine import (
    parse_ecommerce_url,
    extract_product_from_url,
    generate_affiliate_short_plan,
)


def test_parse_ecommerce_url_amazon_asin():
    url = "https://www.amazon.com.tr/dp/B08N5WRWNW?ref_=cm_sw_r_cp_ud_dp"
    info = parse_ecommerce_url(url)
    assert info["platform"] == "amazon"
    assert info["product_id"] == "B08N5WRWNW"


def test_parse_ecommerce_url_trendyol():
    url = "https://www.trendyol.com/xiaomi/akilli-robot-supurge-p-87654321?boutiqueId=61"
    info = parse_ecommerce_url(url)
    assert info["platform"] == "trendyol"
    assert info["product_id"] == "87654321"


def test_parse_ecommerce_url_hepsiburada():
    url = "https://www.hepsiburada.com/anker-kablosuz-kulaklik-p-HBV00000XYZ"
    info = parse_ecommerce_url(url)
    assert info["platform"] == "hepsiburada"
    assert info["product_id"] == "HBV00000XYZ"


def test_canonical_3_scene_afm_structure_tr():
    plan = generate_affiliate_short_plan(
        product_input="Kablosuz Masa Süpürgesi",
        affiliate_url="https://amzn.to/example123",
        language="tr",
        mode="viral_3_scene",
    )

    assert plan["ok"] is True
    assert plan["niche_id"] == "12_amazon_affiliate"
    scenes = plan["scenes"]
    assert len(scenes) == 3, f"Expected exactly 3 scenes, got {len(scenes)}"

    # 1. Sahne 1: Kanca
    s1 = scenes[0]
    assert s1["scene_index"] == 1
    assert s1["beat_type"] == "hook"
    assert "Bunu neden daha önce almadım diyeceksiniz" in s1["narration"]

    # 2. Sahne 2: Problem ve Çözüm
    s2 = scenes[1]
    assert s2["scene_index"] == 2
    assert s2["beat_type"] == "problem_solution"
    assert "can sıkıcı" in s2["narration"] or "kolaylaştırıyor" in s2["narration"]

    # 3. Sahne 3: Kapanış & CTA
    s3 = scenes[2]
    assert s3["scene_index"] == 3
    assert s3["beat_type"] == "cta"
    assert "Link profilde ve açıklamada" in s3["narration"] or "bağlantı" in s3["narration"]

    # Disclosure
    assert "#işbirliği" in plan["seo_metadata"]["affiliate_disclosure"]
    assert "#reklam" in plan["seo_metadata"]["affiliate_disclosure"]


def test_canonical_3_scene_afm_structure_en():
    plan = generate_affiliate_short_plan(
        product_input="Wireless Mini Desk Vacuum",
        affiliate_url="https://amzn.to/us123",
        language="en",
        mode="viral_3_scene",
    )

    assert plan["ok"] is True
    assert plan["language"] == "en"
    scenes = plan["scenes"]
    assert len(scenes) == 3

    assert "Why didn't I buy this sooner" in scenes[0]["narration"]
    assert scenes[1]["beat_type"] == "problem_solution"
    assert scenes[2]["beat_type"] == "cta"

    assert "#ad" in plan["seo_metadata"]["affiliate_disclosure"]
    assert "#affiliate" in plan["seo_metadata"]["affiliate_disclosure"]


def test_detailed_7_scene_mode():
    plan = generate_affiliate_short_plan(
        product_input="Smart Air Purifier",
        language="tr",
        mode="detailed_7_scene",
    )
    assert len(plan["scenes"]) == 7
    assert plan["mode"] == "detailed_7_scene"
    assert plan["scenes"][0]["beat_type"] == "hook"
    assert plan["scenes"][-1]["beat_type"] == "cta"
