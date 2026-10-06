"""
Tests for Chapter 8.4: Yayın Paketi (Publishing Package) JSON Standardı
Covers:
- build_publishing_package conforming to Section 8.4 canonical schema
- validate_publishing_package_schema validation logic
- build_seo_meta_package structure
- archive_publishing_bundle writing publishing_package.json, visual_credits.json, seo_meta.json
- Integration with export_output_package and write_delivery_package
"""
import json
import os
import tempfile
import pytest
from compliance.publishing_package import (
    build_publishing_package,
    build_seo_meta_package,
    validate_publishing_package_schema,
    archive_publishing_bundle,
    license_status_from_manifest,
)
from compliance import export_output_package
from production.package import write_delivery_package


def test_build_publishing_package_canonical_schema():
    manifest_items = [
        {"asset_id": "9029355", "provider": "pexels"},
        {"asset_id": "456123", "provider": "pixabay"},
    ]
    pkg = build_publishing_package(
        title="Hayatınızı Kolaylaştıracak 3 Ürün",
        niche_id="12_amazon_affiliate",
        viewer_score=98.0,
        manifest_items=manifest_items,
        research_gate_passed=True,
        license_status="COMMERCIAL_SAFE",
        originality_score=100.0,
        generated_at="2026-09-26T22:00:00Z",
    )

    # 1. Exact canonical keys match Section 8.4
    assert pkg["version"] == 1
    assert pkg["generated_at"] == "2026-09-26T22:00:00Z"
    assert pkg["title"] == "Hayatınızı Kolaylaştıracak 3 Ürün"
    assert pkg["niche_id"] == "12_amazon_affiliate"
    assert pkg["viewer_score"] == 98.0

    assert pkg["compliance"] == {
        "research_gate": "PASSED",
        "license_status": "COMMERCIAL_SAFE",
        "originality_score": 100.0,
    }

    assert pkg["credits"] == {
        "manifest_count": 2,
        "unique_uids": True,
    }

    valid, errors = validate_publishing_package_schema(pkg)
    assert valid is True
    assert errors == []


def test_validate_publishing_package_schema_catches_invalid_fields():
    # Bad version
    bad_pkg = {
        "version": 2,
        "generated_at": "2026-09-26T22:00:00Z",
        "title": "Test Video",
        "niche_id": "tech",
        "viewer_score": "not_a_number",
        "compliance": {"research_gate": "UNKNOWN", "license_status": ""},
        "credits": "invalid_credits",
    }
    valid, errors = validate_publishing_package_schema(bad_pkg)
    assert valid is False
    assert any("version" in e for e in errors)
    assert any("viewer_score" in e for e in errors)
    assert any("research_gate" in e for e in errors)
    assert any("credits" in e for e in errors)


def test_build_seo_meta_package():
    meta = build_seo_meta_package(
        title="Büyük Roma Yangını #tarih",
        description="Yangının bilinmeyen gerçekleri.",
        tags=["#tarih", "roma", "antik"],
        language="tr",
        privacy_status="unlisted",
        ai_disclosure_text="Bu video yapay zeka araçları ile üretilmiştir.",
    )
    assert meta["version"] == 1
    assert meta["title"] == "Büyük Roma Yangını #tarih"
    assert "yangın" in meta["description"].lower()
    assert meta["tags"] == ["tarih", "roma", "antik"]  # stripped #
    assert meta["language"] == "tr"
    assert meta["privacy_status"] == "unlisted"
    assert "yapay zeka" in meta["ai_disclosure_text"]


def test_archive_publishing_bundle():
    with tempfile.TemporaryDirectory() as tmpdir:
        pub_pkg = build_publishing_package(
            title="3 İlginç Bilgi",
            niche_id="3_did_you_know",
            viewer_score=92.5,
            manifest_items=[{"asset_id": "1"}],
        )
        seo_meta = build_seo_meta_package(
            title="3 İlginç Bilgi",
            description="Açıklama",
            tags=["bilgi"],
        )
        visual_credits = {"credits": [{"asset_id": "1", "provider": "pexels"}]}

        paths = archive_publishing_bundle(
            tmpdir,
            publishing_package=pub_pkg,
            seo_meta=seo_meta,
            visual_credits=visual_credits,
            visual_credits_text="Görsel Kaynaklar:\n- Pexels: ID #1",
        )

        assert os.path.isfile(paths["publishing_package"])
        assert os.path.isfile(paths["seo_meta"])
        assert os.path.isfile(paths["visual_credits"])
        assert os.path.isfile(paths["visual_credits_text"])

        with open(paths["publishing_package"], "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["version"] == 1
            assert data["niche_id"] == "3_did_you_know"


def test_integration_export_output_package_writes_publishing_and_seo():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock video file
        dummy_video = os.path.join(tmpdir, "render.mp4")
        with open(dummy_video, "wb") as f:
            f.write(b"mock video data")

        out_dir = os.path.join(tmpdir, "package_out")
        manifest = {
            "version": 1,
            "clips": [
                {"asset_id": "101", "source": "pexels", "title": "Ocean Waves"},
            ],
        }

        pkg = export_output_package(
            video_path=dummy_video,
            output_dir=out_dir,
            title="Ocean Wonders",
            description="Amazing ocean video #nature",
            tags=["ocean", "nature"],
            source_manifest=manifest,
            viewer_score={"score": 95.0},
            compliance={"niche_id": "10_nature", "originality_score": 98.0},
        )

        assert "publishing_package" in pkg["files"]
        assert "seo_meta" in pkg["files"]
        assert "visual_credits" in pkg["files"]

        pub_file = pkg["files"]["publishing_package"]
        assert os.path.isfile(pub_file)
        with open(pub_file, "r", encoding="utf-8") as f:
            pub_data = json.load(f)
            assert pub_data["version"] == 1
            assert pub_data["niche_id"] == "10_nature"
            assert pub_data["compliance"]["license_status"] == "COMMERCIAL_SAFE"
            assert pub_data["credits"]["manifest_count"] == 1


def test_integration_write_delivery_package_writes_publishing_and_seo():
    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_video = os.path.join(tmpdir, "final.mp4")
        with open(dummy_video, "wb") as f:
            f.write(b"final video bytes")

        plan = {
            "title": "Space Facts",
            "niche_id": "2_space",
            "description": "Space exploration",
            "tags": ["space", "nasa"],
            "meta": {
                "viewer_score": 88.5,
                "compliance": {
                    "originality_score": 95.0,
                },
            },
        }
        manifest = {
            "clips": [{"asset_id": "star_1", "provider": "pixabay"}],
        }

        paths = write_delivery_package(
            tmpdir,
            plan=plan,
            output_path=dummy_video,
            source_manifest=manifest,
        )

        assert "publishing_package" in paths
        assert "seo_meta" in paths
        assert "visual_credits" in paths

        with open(paths["publishing_package"], "r", encoding="utf-8") as f:
            pub_json = json.load(f)
            assert pub_json["version"] == 1
            assert pub_json["title"] == "Space Facts"
            assert pub_json["niche_id"] == "2_space"
            assert pub_json["credits"]["manifest_count"] == 1
            assert pub_json["compliance"]["research_gate"] == "FAILED"
            assert pub_json["compliance"]["license_status"] == "COMMERCIAL_SAFE"


def test_delivery_package_uses_real_seo_and_sits_beside_video():
    with tempfile.TemporaryDirectory() as tmpdir:
        project = os.path.join(tmpdir, "project")
        video_dir = os.path.join(tmpdir, "output")
        os.makedirs(project)
        os.makedirs(video_dir)
        video = os.path.join(video_dir, "final.mp4")
        with open(video, "wb") as handle:
            handle.write(b"video-bytes")
        with open(os.path.join(project, "visual_credits.json"), "w", encoding="utf-8") as handle:
            json.dump({"clips": [{"id": "77", "source": "pexels"}]}, handle)

        paths = write_delivery_package(
            project,
            plan={
                "title": "Plan başlığı",
                "niche_id": "7_space_cosmos",
                "meta": {
                    "viewer_score": {"score": 81.0},
                    "originality": {"originality_score": 64.0},
                    "compliance": {"research": {"action": "ALLOW"}},
                },
            },
            output_path=video,
            source_manifest={
                "clips": [{"id": "77", "source": "pexels", "license": {"license": "pexels", "safe": True}}],
            },
            seo={
                "seo_title": "SEO başlığı",
                "seo_description": "Açıklama gövdesi.\n\nID #77",
                "tags": ["uzay"],
                "ai_disclosure": {"description_paragraph": "Bu video, yapay zeka araçları ile üretildi."},
            },
        )

        with open(paths["publishing_package"], "r", encoding="utf-8") as handle:
            pub = json.load(handle)
        assert pub["title"] == "SEO başlığı"
        assert pub["viewer_score"] == 81.0
        assert pub["compliance"]["originality_score"] == 64.0
        assert pub["compliance"]["research_gate"] == "PASSED"
        assert pub["compliance"]["license_status"] == "COMMERCIAL_SAFE"
        with open(paths["seo_meta"], "r", encoding="utf-8") as handle:
            seo = json.load(handle)
        assert "ID #77" in seo["description"]
        assert os.path.isfile(os.path.join(video_dir, "publishing_package.json"))
        assert os.path.isfile(os.path.join(video_dir, "seo_meta.json"))
        assert os.path.isfile(os.path.join(video_dir, "visual_credits.json"))

        blocked = license_status_from_manifest([{"license": {"safe": False, "license": "cc_nc"}}])
        assert blocked == "NOT_COMMERCIAL_SAFE"
        assert license_status_from_manifest([]) == "UNVERIFIED"
