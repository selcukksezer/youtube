"""
Tests for naqashafzal/ai-content-studio adaptations:
1. StyleProfileManager (multi-modal aesthetic matrix, script/visual prompt enrichment, TTS cues)
2. SmartApiRetry (quota & rate-limit auto-parser, ResourceExhausted handling, exponential backoff)
3. DynamicBRollDirector (retention cutaways, B-Roll cue clamping, FFmpeg overlay filter graph)
4. PodcastDebateEngine (multi-turn dual-host debate scripts, turn timestamps, speaker routing)
5. YouTubeClipperService (SEO metadata, B-Roll suggestions, audio ducking)
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from services.style_profile_manager import (
    ContentStyle,
    StyleProfileManager,
    style_profile_manager,
)
from services.smart_api_retry import (
    is_rate_limit_error,
    parse_retry_after,
    robust_api_call,
)
from services.dynamic_broll_director import (
    BRollCue,
    DynamicBRollDirector,
    dynamic_broll_director,
)
from services.podcast_debate_engine import (
    DebateScript,
    DialogueTurn,
    PodcastDebateEngine,
    podcast_debate_engine,
)
from services.youtube_clipper import youtube_clipper
from services.highlight_clipper import select_highlights


# --- 1. StyleProfileManager Tests ---
def test_style_profile_manager_resolution():
    """Verify keyword and multi-lingual resolution of content styles."""
    assert style_profile_manager.resolve_style("podcast") == ContentStyle.PODCAST
    assert style_profile_manager.resolve_style("korku") == ContentStyle.HORROR
    assert style_profile_manager.resolve_style("belgesel") == ContentStyle.DOCUMENTARY
    assert style_profile_manager.resolve_style("stoa felsefe") == ContentStyle.STOIC_FACTS
    assert style_profile_manager.resolve_style("asmr_video") == ContentStyle.ASMR
    # Unknown style falls back to default
    assert style_profile_manager.resolve_style("bilinmeyen_tur") == ContentStyle.VIRAL_VIDEO


def test_style_profile_manager_enrichment():
    """Verify prompt enrichment with script formula and visual aesthetics."""
    base_prompt = "Konu: Karadelikler"
    enriched_script = style_profile_manager.enrich_script_prompt(base_prompt, "documentary")
    assert "[STYLE PROFILE: Documentary]" in enriched_script
    assert "BBC/HBO" in enriched_script
    assert "~135 words/minute" in enriched_script

    visual_enriched = style_profile_manager.enrich_visual_prompt("Karadelik merkezinde ışık halkası", "asmr")
    assert "Hyper-macro 8K cinematography" in visual_enriched
    assert "tranquil earth tones" in visual_enriched

    tts_conf = style_profile_manager.get_tts_config("horror")
    assert "sinister undertone" in tts_conf["cadence_cue"]
    assert tts_conf["target_wpm"] == 120

    sub_theme = style_profile_manager.get_subtitle_theme("viral_video")
    assert sub_theme["font"] == "Impact"
    assert sub_theme["primary_color"] == (255, 255, 0)  # Viral yellow


# --- 2. SmartApiRetry Tests ---
def test_smart_api_retry_parsing():
    """Verify parsing of dynamic retry-after delays from exception messages."""
    err_gemini = "ResourceExhausted: 429 Resource has been exhausted. Please retry in 14.5s."
    delay = parse_retry_after(err_gemini)
    assert delay == 14.5

    err_header = "HTTP 429 Too Many Requests: Retry-After: 25"
    assert parse_retry_after(err_header) == 25.0

    err_generic = "rate limit exceeded, please wait 5 seconds before next request"
    assert parse_retry_after(err_generic) == 5.0

    assert is_rate_limit_error(Exception("429 Too Many Requests"))
    assert is_rate_limit_error(Exception("GoogleAPICallError: ResourceExhausted"))
    assert not is_rate_limit_error(ValueError("Invalid syntax"))


def test_smart_api_retry_execution():
    """Verify that robust_api_call retries and recovers after transient errors."""
    attempts = [0]

    @robust_api_call(max_retries=2, base_wait_sec=0.01)
    def flaky_service():
        attempts[0] += 1
        if attempts[0] < 2:
            raise Exception("ResourceExhausted: Please retry in 0.01s")
        return "success"

    result = flaky_service()
    assert result == "success"
    assert attempts[0] == 2


# --- 3. DynamicBRollDirector Tests ---
def test_dynamic_broll_director_sanitization():
    """Verify cue validation protecting the first 1.8s hook and minimum durations."""
    raw_cues = [
        {"start_offset": 0.5, "end_offset": 2.0, "subject": "intro"},  # Too early (in hook)
        {"start_offset": 3.0, "end_offset": 6.0, "subject": "hacker typing"},  # Valid
        {"start_offset": 7.0, "end_offset": 7.2, "subject": "too short"},  # Duration clamped to min
    ]
    cues = dynamic_broll_director.sanitize_cues(raw_cues, clip_duration=30.0)

    # First cue must be adjusted away from 0-1.8s hook
    assert len(cues) >= 2
    for cue in cues:
        assert cue.start_offset >= 1.8
        assert cue.duration >= 2.0
        assert cue.end_offset <= 29.0


def test_dynamic_broll_director_ffmpeg_filter():
    """Verify generation of multi-input FFmpeg overlay filter graph."""
    cues = [
        BRollCue(start_offset=2.5, end_offset=5.5, subject="money", visual_query="gold coins"),
        BRollCue(start_offset=12.0, end_offset=15.0, subject="chart", visual_query="stock market"),
    ]
    filter_graph, out_tag = dynamic_broll_director.generate_ffmpeg_overlay_graph(
        cues, width=1080, height=1920
    )
    assert "scale=1080:1920" in filter_graph
    assert "crop=1080:1920" in filter_graph
    assert "enable='between(t,2.5,5.5)'" in filter_graph
    assert "enable='between(t,12.0,15.0)'" in filter_graph
    assert out_tag == "v_overlay_1"


# --- 4. PodcastDebateEngine Tests ---
def test_podcast_debate_engine_generation():
    """Verify multi-round debate script generation and turn timestamps."""
    debate = podcast_debate_engine.generate_debate(
        topic="Yapay Zeka Sanatçıları Yok Edecek mi?",
        host_name="Ali",
        guest_name="Zeynep",
        rounds=3,
    )
    assert len(debate.turns) >= 5
    assert debate.topic == "Yapay Zeka Sanatçıları Yok Edecek mi?"
    assert debate.host_name == "Ali"
    assert debate.guest_name == "Zeynep"
    assert debate.estimated_total_duration_sec > 10.0

    turn_dicts = debate.to_turn_dicts()
    assert len(turn_dicts) == len(debate.turns)
    assert turn_dicts[0]["start"] == 0.0
    assert turn_dicts[0]["end"] > 0.0
    assert turn_dicts[1]["start"] >= turn_dicts[0]["end"]


# --- 5. YouTubeClipperService Enhancements Tests ---
def test_youtube_clipper_does_not_fabricate_fallback_highlights():
    """Missing AI configuration must not produce fabricated, successful-looking clips."""
    with patch("services.youtube_clipper.config.AI_API_KEY", ""):
        with pytest.raises(RuntimeError, match="AI API key"):
            youtube_clipper.detect_highlights_with_llm(
                transcript_text="Bu video çok önemli sırlar içeriyor...",
                num_clips=2,
                video_duration=120.0,
            )


def test_youtube_clipper_formats_timestamped_transcript_for_highlight_model():
    transcript = youtube_clipper.format_transcript_segments([
        {"start": 1.25, "end": 2.5, "text": "İlk cümle."},
        {"start": 4.0, "end": 6.75, "text": "İkinci cümle."},
    ])

    assert transcript == "[1.2s-2.5s] İlk cümle.\n[4.0s-6.8s] İkinci cümle."


def test_youtube_clipper_requires_source_transcript_inside_suggested_range():
    captions = [
        {"start": 10.0, "end": 13.0, "text": "One two three four five six seven eight."},
        {"start": 20.0, "end": 23.0, "text": "More actual speech appears in this source segment."},
    ]
    highlights = [
        {"title": "Grounded moment", "start_time": 8.0, "end_time": 18.0, "score": 90},
        {"title": "Invented moment", "start_time": 60.0, "end_time": 75.0, "score": 99},
    ]

    grounded = youtube_clipper.ground_highlights_in_transcript(highlights, captions)

    assert [item["title"] for item in grounded] == ["Grounded moment"]
    assert grounded[0]["transcript_excerpt"] == (
        "One two three four five six seven eight."
    )
    assert grounded[0]["transcript_word_count"] == 8


def test_youtube_clipper_drops_candidate_with_only_sparse_caption_evidence():
    highlights = [
        {"title": "Sparse moment", "start_time": 4.0, "end_time": 24.0, "score": 92}
    ]

    grounded = youtube_clipper.ground_highlights_in_transcript(
        highlights,
        [{"start": 8.0, "end": 9.0, "text": "Only three words."}],
    )

    assert grounded == []


def test_youtube_clipper_sanitizes_llm_broll_timeline():
    response = MagicMock()
    response.choices[0].message.content = json.dumps({
        "highlights": [{
            "title": "A hidden clue",
            "start_time": 20.0,
            "end_time": 60.0,
            "score": 90,
            "broll": [
                {"start_offset": 0.5, "end_offset": 4.5, "subject": "dramatic reveal"}
            ],
        }]
    })
    client = MagicMock()
    client.chat.completions.create.return_value = response

    with patch("services.youtube_clipper.config.AI_API_KEY", "test-key"), \
         patch("openai.OpenAI", return_value=client):
        highlights = youtube_clipper.detect_highlights_with_llm(
            transcript_text=youtube_clipper.format_transcript_segments([
                {"start": 12.0, "end": 16.5, "text": "A hidden clue changes everything."},
            ]),
            num_clips=1,
            video_duration=120.0,
        )

    prompt_text = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "[12.0s-16.5s]" in prompt_text
    selected = select_highlights(highlights, duration=120.0, num_clips=1)
    cue = selected[0]["broll"][0]
    assert cue["start_offset"] >= 1.8
    assert cue["end_offset"] <= 39.0
    assert cue["end_offset"] - cue["start_offset"] >= 2.0


def test_youtube_clipper_returns_separate_hook_and_retention_scores():
    response = MagicMock()
    response.choices[0].message.content = json.dumps({
        "highlights": [{
            "title": "A hidden clue",
            "start_time": 20.0,
            "end_time": 60.0,
            "score": 90,
            "hook_score": 115,
            "retention_score": "74.6",
        }]
    })
    client = MagicMock()
    client.chat.completions.create.return_value = response

    with patch("services.youtube_clipper.config.AI_API_KEY", "test-key"), \
         patch("openai.OpenAI", return_value=client):
        highlights = youtube_clipper.detect_highlights_with_llm(
            transcript_text="[20.0s-60.0s] A hidden clue changes everything.",
            num_clips=1,
            video_duration=120.0,
        )

    assert highlights[0]["score"] == 90
    assert highlights[0]["hook_score"] == 100
    assert highlights[0]["retention_score"] == 75
    selected = select_highlights(highlights, duration=120.0, num_clips=1)
    assert selected[0]["hook_score"] == 100
    assert selected[0]["retention_score"] == 75
    prompt_text = client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert '"hook_score":int' in prompt_text
    assert '"retention_score":int' in prompt_text


def test_youtube_clipper_drops_invalid_breakdown_scores_without_dropping_clip():
    response = MagicMock()
    response.choices[0].message.content = json.dumps({
        "highlights": [{
            "title": "A hidden clue",
            "start_time": 20.0,
            "end_time": 60.0,
            "score": 90,
            "hook_score": "unknown",
            "retention_score": True,
        }, {
            "title": "Another moment",
            "start_time": 70.0,
            "end_time": 110.0,
            "score": 86,
            "hook_score": 10 ** 1000,
            "retention_score": True,
        }]
    })
    client = MagicMock()
    client.chat.completions.create.return_value = response

    with patch("services.youtube_clipper.config.AI_API_KEY", "test-key"), \
         patch("openai.OpenAI", return_value=client):
        highlights = youtube_clipper.detect_highlights_with_llm(
            transcript_text="[20.0s-60.0s] A hidden clue changes everything.",
            num_clips=1,
            video_duration=120.0,
        )

    assert len(highlights) == 2
    assert "hook_score" not in highlights[0]
    assert "retention_score" not in highlights[0]
    assert "hook_score" not in highlights[1]
    assert "retention_score" not in highlights[1]


def test_youtube_clipper_analyzes_long_videos_in_overlapping_timestamp_chunks():
    def response_for(*highlight_rows):
        response = MagicMock()
        response.choices[0].message.content = json.dumps({
            "highlights": list(highlight_rows)
        })
        return response

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        response_for({
            "title": "Opening moment",
            "start_time": 100.0,
            "end_time": 140.0,
            "score": 90,
        }),
        response_for(
            {
                "title": "Boundary moment",
                "start_time": 1120.0,
                "end_time": 1205.0,
                "score": 92,
            },
            {
                "title": "Late moment",
                "start_time": 1800.0,
                "end_time": 1840.0,
                "score": 90,
            },
        ),
    ]
    transcript = youtube_clipper.format_transcript_segments([
        {"start": 0.0, "end": 5.0, "text": "Opening source segment."},
        {"start": 1120.0, "end": 1122.0, "text": "Boundary lead-in segment."},
        {"start": 1190.0, "end": 1192.0, "text": "Overlap boundary segment."},
        {"start": 1210.0, "end": 1212.0, "text": "Next source segment."},
        {"start": 1800.0, "end": 1802.0, "text": "Late source segment."},
        {"start": 1980.0, "end": 1982.0, "text": "Final source segment."},
    ])

    with patch("services.youtube_clipper.config.AI_API_KEY", "test-key"), \
         patch("openai.OpenAI", return_value=client):
        highlights = youtube_clipper.detect_highlights_with_llm(
            transcript_text=transcript,
            num_clips=1,
            video_duration=2000.0,
        )

    assert [highlight["title"] for highlight in highlights] == [
        "Opening moment",
        "Boundary moment",
        "Late moment",
    ]
    assert client.chat.completions.create.call_count == 2
    messages = [
        call.kwargs["messages"][1]["content"]
        for call in client.chat.completions.create.call_args_list
    ]
    assert "[1190.0s-1192.0s]" in messages[0]
    assert "[1190.0s-1192.0s]" in messages[1]
    assert "[1120.0s-1122.0s]" in messages[1]
    assert "[1800.0s-1802.0s]" in messages[1]


def test_youtube_clipper_chunks_oversized_timed_transcripts_without_truncation():
    segments = [
        {"start": 0.0, "end": 10.0, "text": "A" * 7000},
        {"start": 20.0, "end": 30.0, "text": "B" * 7000},
        {"start": 40.0, "end": 50.0, "text": "C" * 7000},
    ]
    transcript = youtube_clipper.format_transcript_segments(segments)

    chunks = youtube_clipper._chunk_transcript_text(transcript, video_duration=60.0)

    assert len(chunks) == 3
    assert all(len(chunk["text"]) <= 12000 for chunk in chunks)
    assert all(marker in chunk["text"] for marker, chunk in zip(("A" * 100, "B" * 100, "C" * 100), chunks))
