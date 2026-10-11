"""
YouTube to Shorts Viral Clipper Engine.
Adapted and integrated from Anil-matcha/AI-Youtube-Shorts-Generator.
Downloads long YouTube videos, extracts transcript, detects viral highlights using LLM + 8-signal scoring,
and clips to 9:16 with one FFmpeg cover crop. Face x comes from five samples.
"""
import os
import re
import json
import importlib.util
import math
import subprocess
from typing import Any, Dict, List, Optional
import yt_dlp
import config
from .transcript_cache import LocalTranscriptCache

VIRALITY_CRITERIA_PROMPT = """
Virality signals to prioritize (ranked by impact):
1. HOOK MOMENTS — statements that create immediate curiosity ("The secret is...", "Nobody talks about...", "I was completely wrong about...")
2. EMOTIONAL PEAKS — genuine surprise, laughter, anger, vulnerability, excitement; raw reactions
3. OPINION BOMBS — strong, polarizing or counter-intuitive statements that trigger debate
4. REVELATION MOMENTS — surprising facts, stats, or confessions that reframe how the viewer thinks
5. CONFLICT/TENSION — disagreement, pushback, or a problem being confronted head-on
6. QUOTABLE ONE-LINERS — a sentence that works as a standalone quote
7. STORY PEAKS — the climax or twist of an anecdote; the payoff moment
8. PRACTICAL VALUE — a concrete tip, hack, or insight the viewer can immediately apply
"""

HIGHLIGHT_SYSTEM_PROMPT = """You are an elite short-form video editor who has studied thousands of viral clips on TikTok, Instagram Reels, and YouTube Shorts. You know exactly what makes viewers stop scrolling, watch to the end, and share.

{virality_criteria}

Your task: identify the most viral-worthy highlights from the transcript.

Rules:
- Every highlight must open with a strong HOOK — a line that grabs attention within the first 3 seconds
- Duration sweet spot: 35-75 seconds.
- Use the supplied transcript timestamps for every start_time and end_time; never guess timing from the description.
- Never cut mid-sentence or mid-thought — each clip must feel complete and self-contained
- Clips must not overlap significantly with each other
- Score 0-100 on viral potential
- Add "hook_score" (1-100) for the opening hook's strength in the first 3 seconds
- Add "retention_score" (1-100) for pacing, sustained curiosity, and payoff across the clip
- Score hook and retention independently; do not copy the overall score into both fields
- Pick the top {num_clips} highlights
- Identify "hook_sentence" (the opening line) and "virality_reason" (why it works)
- Generate "seo_title" (clickbaity YouTube Shorts title with tags like #shorts), "seo_description", and "seo_tags"
- Suggest 1-3 "broll" overlay moments where visual cutaway increases retention: [{{"start_offset": float (seconds from clip start), "end_offset": float, "subject": "visual search term"}}]

Respond ONLY with valid JSON:
{{"highlights":[{{"title":"string","start_time":float,"end_time":float,"score":int,"hook_score":int,"retention_score":int,"hook_sentence":"string","virality_reason":"string","seo_title":"string","seo_description":"string","seo_tags":"string","broll":[{{"start_offset":float,"end_offset":float,"subject":"string"}}]}}]}}
"""

_MAX_HIGHLIGHT_TRANSCRIPT_CHARS = 12000
_LONG_VIDEO_CHUNK_THRESHOLD_SECONDS = 1800.0
_HIGHLIGHT_CHUNK_SECONDS = 1200.0
_HIGHLIGHT_CHUNK_OVERLAP_SECONDS = 90.0
_TIMESTAMPED_TRANSCRIPT_LINE = re.compile(
    r"^\[(?P<start>\d+(?:\.\d+)?)s-(?P<end>\d+(?:\.\d+)?)s\]"
)
MAX_TRANSCRIPTION_HOTWORDS_LENGTH = 500


def normalize_transcription_hotwords(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("ASR terimleri metin olmalı.")
    normalized = " ".join(value.split())
    if len(normalized) > MAX_TRANSCRIPTION_HOTWORDS_LENGTH:
        raise ValueError(
            f"ASR terimleri en fazla {MAX_TRANSCRIPTION_HOTWORDS_LENGTH} karakter olabilir."
        )
    return normalized


def _normalize_breakdown_scores(highlight: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("hook_score", "retention_score"):
        value = highlight.get(field)
        if value is None:
            continue
        if isinstance(value, bool):
            highlight.pop(field, None)
            continue
        try:
            score = float(value)
        except (OverflowError, TypeError, ValueError):
            highlight.pop(field, None)
            continue
        if not math.isfinite(score):
            highlight.pop(field, None)
            continue
        highlight[field] = int(round(max(1.0, min(100.0, score))))
    return highlight



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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
        grouped: List[Dict[str, Any]] = []
        current: List[Dict[str, Any]] = []

        def flush() -> None:
            if not current:
                return
            grouped.append({
                "start": current[0]["start"],
                "end": current[-1]["end"],
                "text": " ".join(item["text"] for item in current),
            })
            current.clear()

        for word in words or []:
            if not isinstance(word, dict):
                continue
            text = str(word.get("text") or "").strip()
            try:
                start = float(word.get("offset"))
                duration = float(word.get("duration"))
            except (TypeError, ValueError):
                continue
            end = start + duration
            if (
                not text
                or not math.isfinite(start)
                or not math.isfinite(end)
                or start < 0
                or duration <= 0
            ):
                continue
            if current and (
                start - current[-1]["end"] >= 0.65
                or len(current) >= 12
                or current[-1]["text"].endswith((".", "!", "?"))
            ):
                flush()
            current.append({"start": start, "end": end, "text": text})
        flush()
        return grouped

    @staticmethod
    def format_transcript_segments(segments: List[Dict[str, Any]]) -> str:
        """Keep source timing attached so highlight timestamps can be grounded."""
        lines = []
        for segment in segments or []:
            if not isinstance(segment, dict):
                continue
            text = str(segment.get("text") or "").strip()
            try:
                start = float(segment.get("start"))
                end = float(segment.get("end"))
            except (TypeError, ValueError):
                continue
            if not text or not math.isfinite(start) or not math.isfinite(end) or end <= start:
                continue
            lines.append(f"[{start:.1f}s-{end:.1f}s] {text}")
        return "\n".join(lines)

    @staticmethod
    def _chunk_transcript_text(
        transcript_text: str,
        video_duration: float,
    ) -> List[Dict[str, Any]]:
        """Bound prompt size while retaining absolute times and boundary overlap."""
        text = transcript_text.strip()
        if not text:
            return []
        if (
            len(text) <= _MAX_HIGHLIGHT_TRANSCRIPT_CHARS
            and video_duration < _LONG_VIDEO_CHUNK_THRESHOLD_SECONDS
        ):
            return [{
                "start_time": 0.0,
                "end_time": max(0.0, video_duration),
                "text": text,
            }]

        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            match = _TIMESTAMPED_TRANSCRIPT_LINE.match(line)
            if not match:
                raise ValueError(
                    "Long-video highlight analysis requires timestamped transcript lines."
                )
            start_time = float(match.group("start"))
            end_time = float(match.group("end"))
            if (
                not math.isfinite(start_time)
                or not math.isfinite(end_time)
                or start_time < 0
                or end_time <= start_time
            ):
                raise ValueError("Transcript contains an invalid timestamp range.")
            if len(line) > _MAX_HIGHLIGHT_TRANSCRIPT_CHARS:
                raise ValueError(
                    "A single timestamped transcript line exceeds the AI prompt limit."
                )
            rows.append({
                "start_time": start_time,
                "end_time": end_time,
                "text": line,
            })

        if not rows:
            raise ValueError("No timestamped transcript lines are available to analyze.")
        rows.sort(key=lambda row: row["start_time"])

        chunks = []
        first_index = 0
        while first_index < len(rows):
            chunk_start = rows[first_index]["start_time"]
            time_limit = chunk_start + _HIGHLIGHT_CHUNK_SECONDS
            chunk_rows = []
            chunk_chars = 0
            index = first_index

            while index < len(rows):
                row = rows[index]
                next_chars = chunk_chars + len(row["text"]) + (1 if chunk_rows else 0)
                if chunk_rows and (
                    row["end_time"] > time_limit
                    or next_chars > _MAX_HIGHLIGHT_TRANSCRIPT_CHARS
                ):
                    break
                chunk_rows.append(row)
                chunk_chars = next_chars
                index += 1

            chunks.append({
                "start_time": chunk_rows[0]["start_time"],
                "end_time": max(row["end_time"] for row in chunk_rows),
                "text": "\n".join(row["text"] for row in chunk_rows),
            })
            if index >= len(rows):
                break

            overlap_start = chunk_rows[-1]["end_time"] - _HIGHLIGHT_CHUNK_OVERLAP_SECONDS
            next_index = index
            while (
                next_index > first_index
                and rows[next_index - 1]["end_time"] > overlap_start
            ):
                next_index -= 1

            while next_index < index:
                overlap_chars = sum(
                    len(row["text"]) for row in rows[next_index:index]
                ) + (index - next_index - 1)
                if overlap_chars + len(rows[index]["text"]) + 1 <= _MAX_HIGHLIGHT_TRANSCRIPT_CHARS:
                    break
                next_index += 1

            first_index = next_index if next_index > first_index else index

        return chunks

    @staticmethod
    def ground_highlights_in_transcript(
        highlights: List[Dict[str, Any]],
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Keep only suggested ranges supported by enough timed source speech."""
        grounded = []
        for highlight in highlights or []:
            if not isinstance(highlight, dict):
                continue
            try:
                start = float(highlight.get("start_time"))
                end = float(highlight.get("end_time"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(start) or not math.isfinite(end) or end <= start:
                continue

            excerpt_parts = []
            for segment in segments or []:
                if not isinstance(segment, dict):
                    continue
                try:
                    segment_start = float(segment.get("start"))
                    segment_end = float(segment.get("end"))
                except (TypeError, ValueError):
                    continue
                if (
                    not math.isfinite(segment_start)
                    or not math.isfinite(segment_end)
                    or segment_end <= segment_start
                    or min(end, segment_end) <= max(start, segment_start)
                ):
                    continue
                text = str(segment.get("text") or "").strip()
                if text:
                    excerpt_parts.append(text)

            excerpt = " ".join(excerpt_parts)
            word_count = len(re.findall(r"\b[\w'-]+\b", excerpt, flags=re.UNICODE))
            if word_count < 8:
                continue
            grounded.append({
                **highlight,
                "transcript_excerpt": excerpt,
                "transcript_word_count": word_count,
            })
        return grounded

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
