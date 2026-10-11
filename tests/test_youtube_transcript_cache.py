import json
import os
import tempfile
from unittest.mock import patch

from services.transcript_cache import LocalTranscriptCache
from services.youtube_clipper import YouTubeClipperService


_TRANSCRIPT = [{"start": 0.0, "end": 0.8, "text": "Cached transcript."}]
_WHISPER_WORDS = [
    {"text": "Cached", "offset": 0.0, "duration": 0.3},
    {"text": "transcript.", "offset": 0.35, "duration": 0.45},
]


def test_local_whisper_fallback_reuses_cache_and_invalidates_context():
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = os.path.join(temp_dir, "source.mp4")
        with open(source_path, "wb") as handle:
            handle.write(b"source")
        cache_dir = os.path.join(temp_dir, "transcript_cache")

        with patch("services.transcript_cache.DEFAULT_CACHE_DIR", cache_dir):
            service = YouTubeClipperService(download_dir=temp_dir, output_dir=temp_dir)
            with patch(
                "services.youtube_clipper.importlib.util.find_spec",
                return_value=object(),
            ), patch(
                "subtitle_generator._transcribe_whisper_words",
                return_value=_WHISPER_WORDS,
            ) as transcribe:
                first = service.fetch_subtitles_or_transcribe("", source_path, "OpenAI GPT-5")
                cached = service.fetch_subtitles_or_transcribe("", source_path, "OpenAI GPT-5")
                changed_hotwords = service.fetch_subtitles_or_transcribe(
                    "", source_path, "Claude"
                )

                with open(source_path, "ab") as handle:
                    handle.write(b" updated")
                changed_source = service.fetch_subtitles_or_transcribe(
                    "", source_path, "Claude"
                )

        assert first == _TRANSCRIPT
        assert cached == _TRANSCRIPT
        assert changed_hotwords == _TRANSCRIPT
        assert changed_source == _TRANSCRIPT
        assert transcribe.call_count == 3


def test_transcript_cache_invalidates_model_and_language():
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = os.path.join(temp_dir, "source.mp4")
        with open(source_path, "wb") as handle:
            handle.write(b"source")
        cache = LocalTranscriptCache(cache_dir=os.path.join(temp_dir, "cache"))
        producer_calls = 0

        def producer():
            nonlocal producer_calls
            producer_calls += 1
            return list(_TRANSCRIPT)

        def fail_on_cache_miss():
            raise AssertionError("matching transcript should be cached")

        baseline = cache.get_or_create(
            source_path,
            language="tr",
            hotwords="",
            model={"name": "small", "device": "cpu", "compute": "int8"},
            producer=producer,
        )
        same_context = cache.get_or_create(
            source_path,
            language="tr",
            hotwords="",
            model={"name": "small", "device": "cpu", "compute": "int8"},
            producer=fail_on_cache_miss,
        )
        changed_language = cache.get_or_create(
            source_path,
            language="en",
            hotwords="",
            model={"name": "small", "device": "cpu", "compute": "int8"},
            producer=producer,
        )
        changed_model = cache.get_or_create(
            source_path,
            language="en",
            hotwords="",
            model={"name": "medium", "device": "cpu", "compute": "int8"},
            producer=producer,
        )

        assert baseline == same_context == changed_language == changed_model == _TRANSCRIPT
        assert producer_calls == 3


def test_empty_or_corrupt_transcripts_are_not_reused():
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = os.path.join(temp_dir, "source.mp4")
        with open(source_path, "wb") as handle:
            handle.write(b"source")
        cache_dir = os.path.join(temp_dir, "cache")
        cache = LocalTranscriptCache(cache_dir=cache_dir)
        empty_calls = 0

        def empty_producer():
            nonlocal empty_calls
            empty_calls += 1
            return []

        for _ in range(2):
            assert cache.get_or_create(
                source_path,
                language="tr",
                hotwords="",
                model={"name": "small"},
                producer=empty_producer,
            ) == []
        assert empty_calls == 2

        cache.get_or_create(
            source_path,
            language="tr",
            hotwords="",
            model={"name": "small"},
            producer=lambda: list(_TRANSCRIPT),
        )
        cache_path = next(
            os.path.join(cache_dir, name)
            for name in os.listdir(cache_dir)
            if name.endswith(".json")
        )
        with open(cache_path, "w", encoding="utf-8") as handle:
            json.dump({"version": 1, "segments": []}, handle)

        recomputed = cache.get_or_create(
            source_path,
            language="tr",
            hotwords="",
            model={"name": "small"},
            producer=lambda: list(_TRANSCRIPT),
        )
        assert recomputed == _TRANSCRIPT
