"""
YouTube to Shorts Viral Clipper Engine.
Adapted and integrated from Anil-matcha/AI-Youtube-Shorts-Generator.
Downloads long YouTube videos, extracts transcript, detects viral highlights using LLM + 8-signal scoring,
and clips to 9:16 with one FFmpeg cover crop. Face x comes from five samples.
"""
import importlib.util
import json
import math
import os
import re
import subprocess
import types
from typing import Any, Dict, List, Optional
try:
    import yt_dlp
except ImportError:
    yt_dlp = types.SimpleNamespace(YoutubeDL=None)  # type: ignore[assignment]
import config
from .transcript_cache import LocalTranscriptCache
from .youtube_clipper_helpers import (
    HIGHLIGHT_SYSTEM_PROMPT,
    MAX_TRANSCRIPTION_HOTWORDS_LENGTH,
    VIRALITY_CRITERIA_PROMPT,
    _HIGHLIGHT_CHUNK_OVERLAP_SECONDS,
    _HIGHLIGHT_CHUNK_SECONDS,
    _LONG_VIDEO_CHUNK_THRESHOLD_SECONDS,
    _MAX_HIGHLIGHT_TRANSCRIPT_CHARS,
    _TIMESTAMPED_TRANSCRIPT_LINE,
    _normalize_breakdown_scores,
    chunk_transcript_text,
    format_transcript_segments,
    ground_highlights_in_transcript,
    group_whisper_words,
    normalize_transcription_hotwords,
)


def _require_yt_dlp():
    if yt_dlp is None or getattr(yt_dlp, "YoutubeDL", None) is None:
        raise RuntimeError("yt-dlp paketi kurulu değil (`pip install yt-dlp`).")
    return yt_dlp


class YouTubeClipperService:
    def __init__(self, download_dir: Optional[str] = None, output_dir: Optional[str] = None):
        self.download_dir = download_dir or os.path.join(config.BASE_DIR, "output", "clipper_downloads")
        self.output_dir = output_dir or os.path.join(config.BASE_DIR, "output", "shorts_clipped")
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self.transcript_cache = LocalTranscriptCache()

    def extract_youtube_info(self, url: str) -> Dict[str, Any]:
        """Fetch title, duration, and thumbnail without downloading."""
        ydl_opts = {"quiet": True, "no_warnings": True}
        with _require_yt_dlp().YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            max_height = 0
            formats = info.get("formats")
            if isinstance(formats, list):
                for video_format in formats:
                    if not isinstance(video_format, dict):
                        continue
                    if (
                        str(video_format.get("vcodec") or "none").lower() == "none"
                        or str(video_format.get("protocol") or "").lower() == "mhtml"
                        or str(video_format.get("ext") or "").lower() == "mhtml"
                    ):
                        continue
                    try:
                        height = int(video_format.get("height") or 0)
                    except (TypeError, ValueError):
                        continue
                    max_height = max(max_height, height)
            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail"),
                "description": info.get("description", "")[:500],
                "max_height": max_height,
            }

    def download_video(self, url: str, max_height: int = 720) -> str:
        """Download YouTube video to local mp4 file."""
        out_tmpl = os.path.join(self.download_dir, "%(id)s.%(ext)s")
        ydl_opts = {
            "format": f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={max_height}][ext=mp4]/best",
            "outtmpl": out_tmpl,
            "quiet": False,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }
        with _require_yt_dlp().YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get("id")
            for ext in (".mp4", ".mkv", ".webm"):
                cand = os.path.join(self.download_dir, f"{video_id}{ext}")
                if os.path.exists(cand):
                    return cand
            raise FileNotFoundError(f"Downloaded video not found for {url}")

    def fetch_subtitles_or_transcribe(
        self,
        url: str,
        local_video_path: str,
        hotwords: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Attempts to extract YouTube auto-subtitles first for speed;
        falls back to local Whisper when the optional model dependency is installed.
        """
        hotwords = normalize_transcription_hotwords(hotwords)
        transcript_language = "tr"
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["tr", "en"],
            "subtitlesformat": "json3",
            "outtmpl": os.path.join(self.download_dir, "%(id)s.%(ext)s"),
            "quiet": True,
        }
        if url:
            try:
                with _require_yt_dlp().YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    vid_id = info.get("id")
                    transcript_language = str(info.get("language") or transcript_language)
                    sub_file_tr = os.path.join(self.download_dir, f"{vid_id}.tr.json3")
                    sub_file_en = os.path.join(self.download_dir, f"{vid_id}.en.json3")
                    target_sub = sub_file_tr if os.path.exists(sub_file_tr) else (sub_file_en if os.path.exists(sub_file_en) else None)

                    if target_sub and os.path.exists(target_sub):
                        with open(target_sub, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        events = data.get("events", [])
                        segments = []
                        for ev in events:
                            segs = ev.get("segs", [])
                            text = "".join(s.get("utf8", "") for s in segs).strip()
                            t_start = float(ev.get("tStartMs", 0)) / 1000.0
                            d_dur = float(ev.get("dDurationMs", 0)) / 1000.0
                            if text and d_dur > 0:
                                segments.append({
                                    "start": t_start,
                                    "end": t_start + d_dur,
                                    "text": text,
                                })
                        if segments:
                            return segments
            except Exception as exc:
                print(f"[YouTubeClipper] Subtitle extraction failed: {exc}")

        if not local_video_path or not os.path.isfile(local_video_path):
            if importlib.util.find_spec("faster_whisper") is None:
                if not url:
                    raise RuntimeError(
                        "Yerel videoyu transkribe etmek için faster-whisper kurulmalı."
                    )
                print("[YouTubeClipper] No captions found; local faster-whisper is not installed.")
                return []
            if not url:
                raise RuntimeError("Yerel transkripsiyon için video dosyası bulunamadı.")
            try:
                local_video_path = self.download_video(url)
            except Exception as exc:
                raise RuntimeError(f"Video download for local transcription failed: {exc}") from exc

        model = {
            "name": os.getenv("WHISPER_MODEL", "small"),
            "device": os.getenv("WHISPER_DEVICE", "cpu"),
            "compute": os.getenv("WHISPER_COMPUTE", "int8"),
        }

        def transcribe() -> List[Dict[str, Any]]:
            if importlib.util.find_spec("faster_whisper") is None:
                if not url:
                    raise RuntimeError(
                        "Yerel videoyu transkribe etmek için faster-whisper kurulmalı."
                    )
                print("[YouTubeClipper] No captions found; local faster-whisper is not installed.")
                return []
            try:
                from subtitle_generator import _transcribe_whisper_words

                if hotwords:
                    words = _transcribe_whisper_words(
                        local_video_path,
                        language=transcript_language,
                        initial_prompt=hotwords,
                    )
                else:
                    words = _transcribe_whisper_words(
                        local_video_path, language=transcript_language
                    )
            except Exception as exc:
                raise RuntimeError(f"Local Whisper transcription failed: {exc}") from exc
            return self._group_whisper_words(words)

        return self.transcript_cache.get_or_create(
            local_video_path,
            language=transcript_language,
            hotwords=hotwords,
            model=model,
            producer=transcribe,
        )

    @staticmethod
    def _group_whisper_words(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Whisper word timestamps into short caption-like transcript segments."""
        return group_whisper_words(words)

    @staticmethod
    def format_transcript_segments(segments: List[Dict[str, Any]]) -> str:
        """Keep source timing attached so highlight timestamps can be grounded."""
        return format_transcript_segments(segments)

    @staticmethod
    def _chunk_transcript_text(
        transcript_text: str,
        video_duration: float,
    ) -> List[Dict[str, Any]]:
        """Bound prompt size while retaining absolute times and boundary overlap."""
        return chunk_transcript_text(transcript_text, video_duration)

    @staticmethod
    def ground_highlights_in_transcript(
        highlights: List[Dict[str, Any]],
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Keep only suggested ranges supported by enough timed source speech."""
        return ground_highlights_in_transcript(highlights, segments)

    def detect_highlights_with_llm(
        self,
        transcript_text: str,
        num_clips: int = 3,
        video_duration: float = 600.0,
    ) -> List[Dict[str, Any]]:
        """Call configured LLM (Gemini or OpenAI) to select best viral moments."""
        if not isinstance(transcript_text, str) or not transcript_text.strip():
            raise ValueError("Zaman damgalı konuşma dökümü olmadan klip zamanı belirlenemez.")

        chunks = self._chunk_transcript_text(transcript_text, video_duration)
        if not chunks:
            raise ValueError("No transcript content is available to analyze.")

        prompt = HIGHLIGHT_SYSTEM_PROMPT.format(
            virality_criteria=VIRALITY_CRITERIA_PROMPT,
            num_clips=num_clips,
        )

        try:
            from openai import OpenAI
            api_key = config.AI_API_KEY
            base_url = config.AI_BASE_URL
            model = config.AI_MODEL

            if not api_key:
                raise ValueError("No AI API key configured")

            client = OpenAI(api_key=api_key, base_url=base_url)
            valid = []
            for chunk_index, chunk in enumerate(chunks, start=1):
                user_msg = (
                    f"Video total duration: {video_duration}s.\n"
                    f"Transcript part {chunk_index}/{len(chunks)} covers absolute source timestamps "
                    f"{chunk['start_time']:.1f}s-{chunk['end_time']:.1f}s. "
                    "Suggest clips only within this range and preserve absolute video timestamps.\n"
                    f"Transcript:\n{chunk['text']}\n\n"
                    f"Find the top {num_clips} viral moments (each 35-75 seconds)."
                )
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"} if "gemini" in model.lower() or "gpt" in model.lower() else None,
                )
                raw = resp.choices[0].message.content.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw)
                highlights = parsed.get("highlights", [])
                if not isinstance(highlights, list):
                    raise ValueError("AI highlight response must include a highlights list.")

                for highlight in highlights:
                    if not isinstance(highlight, dict):
                        continue
                    try:
                        start = float(highlight.get("start_time", 0))
                        end = float(highlight.get("end_time", 0))
                    except (TypeError, ValueError):
                        continue
                    if (
                        not math.isfinite(start)
                        or not math.isfinite(end)
                        or end <= start
                        or end - start < 15
                        or start < max(0.0, chunk["start_time"] - 1.0)
                        or end > min(video_duration, chunk["end_time"] + 1.0)
                    ):
                        continue
                    valid.append(_normalize_breakdown_scores(dict(highlight)))
            return valid
        except Exception as e:
            print(f"[YouTubeClipper] LLM highlight detection error: {e}")
            raise RuntimeError(f"AI highlight detection failed: {e}") from e

    def render_highlight_clip(
        self,
        source_video_path: str,
        highlight: Dict[str, Any],
        clip_index: int = 1,
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.08,
    ) -> str:
        """
        Cuts highlight, reframes to 9:16 vertical using OpenCV face tracking,
        and optionally mixes background music with ducking.
        """
        base_name = os.path.splitext(os.path.basename(source_video_path))[0]
        out_filename = f"{base_name}_short_{clip_index:02d}.mp4"
        out_path = os.path.join(self.output_dir, out_filename)

        start = float(highlight.get("start_time", 0))
        end = float(highlight.get("end_time", 45))
        from services.highlight_clipper import cut_ranges_vertical
        cropped_clip = cut_ranges_vertical(
            source_video_path,
            [(start, end)],
            out_path,
        )

        # Optional audio ducking with BGM if provided
        if bgm_path and os.path.exists(bgm_path):
            bgm_out = os.path.join(self.output_dir, f"bgm_{out_filename}")
            try:
                cmd = [
                    "ffmpeg", "-y", "-i", cropped_clip, "-i", bgm_path,
                    "-filter_complex",
                    f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2",
                    "-c:v", "copy",
                    bgm_out,
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode == 0:
                    return bgm_out
            except Exception as e:
                print(f"[YouTubeClipper] Audio ducking error: {e}")

        return cropped_clip


youtube_clipper = YouTubeClipperService()
