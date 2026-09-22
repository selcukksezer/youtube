"""
Tests for RSS viral news engine, YouTube publishing hub, and multi-region trend scanner.
"""
import pytest
from fastapi.testclient import TestClient
from server import app
from rss_scanner import clean_html, get_breaking_news_topics, transform_rss_item_to_shorts_idea, DEFAULT_RSS_FEEDS
from trending_scanner import scan_youtube_shorts_trends, CATEGORIES, REGION_HEADERS

client = TestClient(app)


def test_rss_clean_html():
    raw = "<p>Son <b>Dakika</b> haberi: &quot;Bilim insanları&quot; &amp; uzay!&#39; </p>"
    cleaned = clean_html(raw)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert '"Bilim insanları"' in cleaned
    assert "&" in cleaned
    assert "'" in cleaned


def test_rss_default_feeds_structure():
    assert "aa_guncel" in DEFAULT_RSS_FEEDS
    assert "trt_haber" in DEFAULT_RSS_FEEDS
    assert "evrim_agaci" in DEFAULT_RSS_FEEDS
    assert "arkeofili" in DEFAULT_RSS_FEEDS
    assert "donanimhaber" in DEFAULT_RSS_FEEDS
    for key, val in DEFAULT_RSS_FEEDS.items():
        assert "name" in val
        assert "url" in val
        assert "niche" in val


def test_rss_transform_to_shorts_idea():
    item = {
        "title": "NASA James Webb Teleskobu ile Yeni Bir Gezegen Keşfetti",
        "description": "Astronomlar yaşam belirtisi olabilecek atmosfer verileri saptadı.",
        "source_name": "TRT Haber",
        "suggested_niche": "1_news_flash"
    }
    idea = transform_rss_item_to_shorts_idea(item, lang="tr")
    assert "question_title" in idea
    assert len(idea["question_title"]) > 5
    # Since it mentions NASA and gezegen, it should route to space_cosmos
    assert idea["suggested_niche"] == "17_space_cosmos"
    assert idea["source"] == "TRT Haber"


def test_trending_scanner_multi_region_and_categories():
    assert "kids" in CATEGORIES
    assert "science" in CATEGORIES
    assert "crypto" in CATEGORIES
    assert "TR" in REGION_HEADERS
    assert "US" in REGION_HEADERS

    results_tr = scan_youtube_shorts_trends("Bebek Şarkısı", time_filter="week", category="kids", region="TR")
    assert isinstance(results_tr, list)
    assert len(results_tr) > 0
    first = results_tr[0]
    assert "title" in first
    assert "viral_score" in first
    assert "hook_analysis" in first

    results_us = scan_youtube_shorts_trends("Space Mysteries", time_filter="month", category="science", region="US")
    assert isinstance(results_us, list)
    assert len(results_us) > 0


def test_api_rss_sources_endpoint():
    res = client.get("/api/rss/sources")
    assert res.status_code == 200
    data = res.json()
    assert "sources" in data
    assert "trt_haber" in data["sources"]


def test_api_rss_fetch_endpoint():
    res = client.get("/api/rss/fetch?source=aa_guncel&limit=3")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert isinstance(data.get("items"), list)
    assert len(data["items"]) > 0


def test_api_rss_convert_to_shorts_endpoint():
    payload = {
        "title": "Antik Mısır Piramitlerinde Gizli Bir Geçit Bulundu",
        "description": "Arkeologlar radar taraması ile yeni bir oda tespit etti.",
        "source": "Arkeofili",
        "suggested_niche": "12_historical_mysteries",
        "language": "tr"
    }
    res = client.post("/api/rss/convert-to-shorts", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "idea" in data
    assert "question_title" in data["idea"]
    assert data["idea"]["suggested_niche"] == "12_historical_mysteries"


def test_api_trending_scan_with_region():
    res = client.get("/api/trending/scan?topic=Uzay&region=TR&category=science")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["region"] == "TR"
    assert isinstance(data.get("trends"), list)
    assert len(data["trends"]) > 0
