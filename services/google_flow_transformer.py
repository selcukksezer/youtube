"""
Google Flow & Viral Video Transformer Service.
Enables transforming viral YouTube videos into new, copyright-clean viral Shorts using:
1. YouTube viral DNA & transcript extraction (yt_dlp).
2. Google Flow / Veo cinematic storyboard generation (camera angles, volumetric lighting, motion vectors).
3. 1-Click conversion into our bot's 0 TL automated render pipeline (Pollinations Flux + Ken Burns)
   OR Google Flow Studio export (ready-to-paste prompts for free Google Labs/Veo accounts).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional
import yt_dlp
import config
from scenes.generator import generate_scenes


def sanitize_flow_prompt(text: str) -> str:
    """Sanitize prompt text for Google Flow / Veo camera directives."""
    clean = re.sub(r"[^\w\s,.-]", " ", text or "")
    return re.sub(r"\s+", " ", clean).strip()


FLOW_CINEMATIC_STYLES = [
    "cinematic 35mm lens, photorealistic 8k, volumetric rim lighting, shallow depth of field, 9:16 portrait",
    "hyper-detailed macro cinematography, dramatic side shadows, anamorphic lens flare, 9:16 vertical",
    "fast-paced dynamic tracking shot, cinematic motion blur, natural daylight, professional color grade, 9:16",
    "moody atmospheric film still, soft diffused studio light, high-end commercial aesthetic, 9:16 portrait",
]

FLOW_CAMERA_MOTIONS = [
    "cinematic slow push-in (zoom in)",
    "dolly tracking shot with slight orbit",
    "low-angle heroic tilt up",
    "macro extreme close-up with rack focus",
    "smooth horizontal pan with parallax depth",
    "high-angle top-down product inspection",
]


class GoogleFlowTransformer:
    """Transforms viral YouTube videos into Google Flow storyboards and Shorts plans."""

    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or os.path.join(config.BASE_DIR, "data", "flow_temp")
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_viral_dna(self, youtube_url: str) -> Dict[str, Any]:
        """Extract title, duration, view count, tags, and transcript from a viral YouTube video."""
        url = youtube_url.strip()
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["tr", "en"],
            "subtitlesformat": "json3",
            "outtmpl": os.path.join(self.temp_dir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            vid_id = info.get("id", "")
            title = info.get("title", "")
            duration = info.get("duration", 0)
            view_count = info.get("view_count", 0)
            description = (info.get("description") or "")[:1000]
            thumbnail = info.get("thumbnail", "")

        # Extract transcript if subtitles exist
        transcript_text = ""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                sub_tr = os.path.join(self.temp_dir, f"{vid_id}.tr.json3")
                sub_en = os.path.join(self.temp_dir, f"{vid_id}.en.json3")
                target = sub_tr if os.path.exists(sub_tr) else (sub_en if os.path.exists(sub_en) else None)
                if target and os.path.exists(target):
                    with open(target, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    lines = []
                    for ev in data.get("events", []):
                        segs = ev.get("segs", [])
                        text = "".join(s.get("utf8", "") for s in segs).strip()
                        if text:
                            lines.append(text)
                    transcript_text = " ".join(lines)
        except Exception as e:
            print(f"  [FlowTransformer] Subtitle note: {e}")

        # Fallback to description/title if auto-captions unavailable
        if not transcript_text:
            transcript_text = f"Başlık: {title}\nAçıklama: {description}"

        return {
            "video_id": vid_id,
            "url": url,
            "title": title,
            "duration": duration,
            "view_count": view_count,
            "thumbnail": thumbnail,
            "transcript": transcript_text[:4000],
            "is_short": duration <= 90,
        }

    def generate_flow_storyboard(
        self,
        viral_dna: Dict[str, Any],
        target_niche: str = "12_amazon_affiliate",
        language: str = "tr",
    ) -> Dict[str, Any]:
        """
        Transform the viral concept into an original Google Flow / Veo storyboard
        with camera directives, scene prompts, and retention pacing.
        """
        source_title = viral_dna.get("title", "")
        source_transcript = viral_dna.get("transcript", "")

        # Generate fresh, plagiarism-free script plan using our scene generator
        seed_topic = f"{source_title} - Yenilikçi Viral Kurgu"
        plan = generate_scenes(
            title=source_title,
            niche_type=target_niche,
            language=language,
        )

        scenes = plan.get("scenes", [])
        flow_scenes: List[Dict[str, Any]] = []

        for idx, scene in enumerate(scenes):
            narr = scene.get("narration", "")
            base_desc = scene.get("scene_description", "")
            dur = float(scene.get("duration", 4.5))

            style = FLOW_CINEMATIC_STYLES[idx % len(FLOW_CINEMATIC_STYLES)]
            motion = FLOW_CAMERA_MOTIONS[idx % len(FLOW_CAMERA_MOTIONS)]

            # Construct Google Flow / Veo prompt
            clean_subject = sanitize_flow_prompt(base_desc or narr)
            flow_prompt = (
                f"{clean_subject}, camera motion: {motion}, {style}, "
                f"cinematic color grading, highly realistic, masterpiece, vertical 9:16 aspect ratio"
            )

            flow_scenes.append({
                "scene_index": idx,
                "duration": dur,
                "narration": narr,
                "camera_motion": motion,
                "flow_prompt": flow_prompt,
                "negative_prompt": "blurry, low resolution, watermark, text overlay, distorted, cartoon, oversaturated",
                "search_queries": scene.get("search_queries", [clean_subject]),
                "scene_description": base_desc,
            })

        flow_project = {
            "source_viral_video": {
                "title": source_title,
                "url": viral_dna.get("url", ""),
                "view_count": viral_dna.get("view_count", 0),
            },
            "flow_project_title": plan.get("title", source_title),
            "target_niche": target_niche,
            "language": language,
            "total_duration": sum(s["duration"] for s in flow_scenes),
            "scenes": flow_scenes,
            "google_flow_instructions": (
                "Google Flow / Google Labs (Veo 2/3) Kullanımı:\n"
                "1. labs.google veya Google Flow Studio paneline giriş yapın.\n"
                "2. Aşağıdaki 'flow_prompt' metinlerini sahne sahne Flow/Veo prompt kutusuna yapıştırın.\n"
                "3. Aspect Ratio: 9:16 Dikey, Model: Veo seçip videonuzu ücretsiz Google hesabınızla üretin.\n"
                "4. VEYA doğrudan botumuzun 'Bu Senaryo İle Render Al' butonuyla 0 TL lokal render motorunu kullanın."
            ),
        }

        return flow_project

    def export_flow_clipboard_text(self, flow_storyboard: Dict[str, Any]) -> str:
        """Format the storyboard into a clean text block ready to paste into Google Flow."""
        lines = [
            f"=== GOOGLE FLOW / VEO STORYBOARD: {flow_storyboard.get('flow_project_title', '')} ===",
            f"Niş: {flow_storyboard.get('target_niche')} | Süre: {flow_storyboard.get('total_duration', 0):.1f}s | Sahne Sayısı: {len(flow_storyboard.get('scenes', []))}",
            "",
        ]

        for s in flow_storyboard.get("scenes", []):
            lines.append(f"--- SAHNE {s['scene_index'] + 1} ({s['duration']:.1f}s) ---")
            lines.append(f"Seslendirme: \"{s['narration']}\"")
            lines.append(f"Kamera Hareketi: {s['camera_motion']}")
            lines.append(f"Google Flow Prompt:\n{s['flow_prompt']}")
            lines.append("")

        return "\n".join(lines)


def transform_youtube_url_to_flow(
    youtube_url: str,
    target_niche: str = "12_amazon_affiliate",
    language: str = "tr",
) -> Dict[str, Any]:
    """1-shot helper to ingest a viral YouTube URL and generate a full Flow Storyboard."""
    transformer = GoogleFlowTransformer()
    dna = transformer.extract_viral_dna(youtube_url)
    storyboard = transformer.generate_flow_storyboard(dna, target_niche=target_niche, language=language)
    storyboard["clipboard_text"] = transformer.export_flow_clipboard_text(storyboard)
    return storyboard
