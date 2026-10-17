"""Compatibility hook for render paths.

Post-render anti-detect manipulation is disabled.  Keeping this function as a
no-op avoids breaking older callers while preserving the encoded file and its
timestamps exactly as produced by the renderer.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional


def apply_post_render_humanization(video_path: str, title: str = "") -> Dict[str, Any]:
    """Return an audit record without modifying the file."""
    result: Dict[str, Any] = {
        "path": video_path,
        "size_delta_kb": 0,
        "aged_minutes": 0,
        "metadata_applied": False,
        "hash_scrambled": False,
    }
    if not video_path or not os.path.exists(video_path):
        return result

    return result


def scrub_channel_image_exif(
    image_path: str,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Item 33: Strip EXIF, GPS, XMP, and software fingerprint metadata from channel
    banner and profile avatar images by reconstructing a clean pixel buffer.
    """
    target = output_path or image_path
    report: Dict[str, Any] = {
        "ok": False,
        "rule": "item_33_channel_image_exif_scrub",
        "source_path": image_path,
        "output_path": target,
        "exif_removed": False,
        "had_exif": False,
    }
    if not image_path or not os.path.isfile(image_path):
        report["error"] = "file_not_found"
        return report

    try:
        from PIL import Image

        with Image.open(image_path) as src:
            raw_exif = src.info.get("exif") or (src.getexif() if hasattr(src, "getexif") else None)
            report["had_exif"] = bool(raw_exif) or bool(src.info)
            mode = src.mode if src.mode in ("RGB", "RGBA") else "RGBA"
            converted = src.convert(mode)
            clean_img = Image.new(mode, converted.size)
            clean_img.putdata(list(converted.getdata()))
            fmt = "PNG" if target.lower().endswith(".png") else "JPEG"
            save_kwargs: Dict[str, Any] = {"optimize": True}
            if fmt == "JPEG":
                if clean_img.mode == "RGBA":
                    clean_img = clean_img.convert("RGB")
                save_kwargs["quality"] = 95
            clean_img.save(target, format=fmt, **save_kwargs)
            report["ok"] = True
            report["exif_removed"] = True
            report["width"], report["height"] = clean_img.size
    except Exception as exc:
        report["error"] = str(exc)
    return report

