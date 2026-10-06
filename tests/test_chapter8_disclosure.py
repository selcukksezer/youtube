"""
Tests for Chapter 8.3: Şeffaf AI Açıklama ve Kaynakça Bloğu Üretimi
Covers:
- format_visual_source_item for Pexels, Pixabay, Flux, Pollinations, Wikimedia, Procedural
- extract_unique_providers with deduplication and canonical fallback
- generate_visual_sources_block (TR and EN formats)
- build_transparent_ai_disclosure_block matching Section 8.3 canonical layout
- append_ai_disclosure_to_description (idempotency and length capping)
- Backward-compatible ai_disclosure_block integration
"""
import pytest
from compliance.transparent_disclosure import (
    format_visual_source_item,
    extract_unique_providers,
    generate_visual_sources_block,
    build_transparent_ai_disclosure_block,
    append_ai_disclosure_to_description,
)
from compliance import ai_disclosure_block


def test_format_visual_source_item_pexels():
    item = {
        "provider": "pexels",
        "asset_id": "9029355",
        "source_url": "https://www.pexels.com/video/9029355/",
        "license": {"name": "Pexels License"},
    }
    res = format_visual_source_item(item)
    assert res == "- Pexels: ID #9029355 (Pexels License)"


def test_format_visual_source_item_pixabay():
    item = {
        "provider": "pixabay",
        "asset_id": "456123",
        "source_url": "https://pixabay.com/videos/nature-456123/",
    }
    res = format_visual_source_item(item)
    assert res == "- Pixabay: ID #456123 (Pixabay License)"


def test_format_visual_source_item_pollinations_flux():
    item = {
        "provider": "pollinations",
        "model": "Flux SDXL",
        "source_url": "https://pollinations.ai/p/futuristic_city",
    }
    res = format_visual_source_item(item)
    assert res == "- Pollinations AI: Flux SDXL (Generated Asset)"


def test_format_visual_source_item_wikimedia():
    item = {
        "provider": "wikimedia",
        "title": "Roman Forum Sunset",
        "license": {"name": "CC-BY-SA 4.0"},
    }
    res = format_visual_source_item(item)
    assert res == "- Wikimedia Commons: Roman Forum Sunset (CC-BY-SA 4.0)"


def test_format_visual_source_item_procedural():
    item = {
        "provider": "procedural",
        "title": "Whiteboard Drawing",
    }
    res = format_visual_source_item(item)
    assert res == "- Procedural Graphics Engine: Animated Canvas"


def test_extract_unique_providers():
    clips = [
        {"provider": "pexels", "asset_id": "1"},
        {"provider": "pexels", "asset_id": "2"},
        {"provider": "pixabay", "asset_id": "3"},
        {"provider": "pollinations", "model": "Flux"},
    ]
    providers = extract_unique_providers(clips)
    assert "Pexels" in providers
    assert "Pixabay" in providers
    assert "Flux" in providers
    assert len(providers) == 3

    assert extract_unique_providers([]) == []
    empty_sources = generate_visual_sources_block([], lang="tr")
    assert "9029355" not in empty_sources


def test_generate_visual_sources_block_deduplication():
    # Duplicate items should only appear once in visual credits
    clips = [
        {"provider": "pexels", "asset_id": "9029355", "source_url": "https://pexels.com/video/9029355/"},
        {"provider": "pexels", "asset_id": "9029355", "source_url": "https://pexels.com/video/9029355/"},
        {"provider": "pollinations", "model": "Flux SDXL"},
    ]
    block_tr = generate_visual_sources_block(clips, lang="tr")
    lines = block_tr.strip().splitlines()
    assert lines[0] == "Görsel Kaynaklar:"
    assert lines.count("- Pexels: ID #9029355 (Pexels License)") == 1
    assert lines.count("- Pollinations AI: Flux SDXL (Generated Asset)") == 1
    assert len(lines) == 3


def test_build_transparent_ai_disclosure_block_canonical_text():
    clips = [
        {"provider": "pexels", "asset_id": "9029355"},
        {"provider": "pixabay", "asset_id": "12345"},
        {"provider": "pollinations", "model": "Flux SDXL"},
    ]
    block = build_transparent_ai_disclosure_block(
        clips_or_manifest=clips,
        uses_tts=True,
        uses_ai_script=True,
        uses_photoreal_ai=False,
        lang="tr",
    )

    header = block["header_text"]
    assert "Bu video, yapay zeka araçları ve telifsiz stok kütüphaneleri (Pexels, Pixabay, Flux) kullanılarak üretilmiştir." in header
    assert "Tüm görsel materyaller ticari kullanıma uygun lisanslanmıştır." in header

    sources = block["sources_text"]
    assert "Görsel Kaynaklar:" in sources
    assert "- Pexels: ID #9029355 (Pexels License)" in sources
    assert "- Pollinations AI: Flux SDXL (Generated Asset)" in sources

    full = block["full_disclosure_text"]
    assert header in full
    assert sources in full

    assert block["studio_ai_survey"] == "no"
    assert block["disclosure_required"] is False


def test_build_transparent_ai_disclosure_block_photoreal_requires_survey():
    block = build_transparent_ai_disclosure_block(
        uses_photoreal_ai=True,
        lang="tr",
    )
    assert block["studio_ai_survey"] == "yes"
    assert block["disclosure_required"] is True
    assert "photorealistic_ai_visual" in block["reasons"]


def test_append_ai_disclosure_to_description():
    desc = "Roma İmparatorluğu'nun en gizemli 3 sırrı! #tarih #roma"
    disc_block = {
        "full_disclosure_text": (
            "Bu video, yapay zeka araçları ve telifsiz stok kütüphaneleri (Pexels, Pixabay, Flux) kullanılarak üretilmiştir.\n"
            "Tüm görsel materyaller ticari kullanıma uygun lisanslanmıştır.\n"
            "Görsel Kaynaklar:\n"
            "- Pexels: ID #9029355 (Pexels License)"
        )
    }

    # First append
    appended = append_ai_disclosure_to_description(desc, disc_block)
    assert desc in appended
    assert "Bu video, yapay zeka araçları" in appended
    assert "Görsel Kaynaklar:" in appended

    # Second append should be idempotent (no duplicate blocks)
    re_appended = append_ai_disclosure_to_description(appended, disc_block)
    assert re_appended == appended
    assert re_appended.count("Bu video, yapay zeka araçları") == 1


def test_ai_disclosure_block_with_manifest_integration():
    clips = [
        {"provider": "pexels", "asset_id": "9029355"},
        {"provider": "pollinations", "model": "Flux SDXL"},
    ]
    res = ai_disclosure_block(clips_or_manifest=clips, lang="tr")
    assert "header_text" in res
    assert "sources_text" in res
    assert "full_disclosure_text" in res
    assert "Pexels" in res["providers"]
    assert "Flux" in res["providers"]
    assert "- Pexels: ID #9029355 (Pexels License)" in res["description_paragraph"]


def test_seo_description_carries_real_manifest_ids():
    from viral_seo_agent import finalize_seo_compliance

    clips = [{"source": "pexels", "id": "441122", "source_url": "https://www.pexels.com/video/441122/"}]
    seo = finalize_seo_compliance(
        {"seo_description": "Roma hakkında kısa bir not. #tarih #roma #shorts #ekstra"},
        visual_manifest=clips,
    )
    assert "ID #441122" in seo["seo_description"]
    assert seo["description"] == seo["seo_description"]
    assert "9029355" not in seo["seo_description"]

    bare = finalize_seo_compliance({"seo_description": "Sadece metin."}, visual_manifest=[])
    assert "9029355" not in bare["seo_description"]
    assert "Görsel Kaynaklar:" not in bare["seo_description"]
