"""
Tests for naqashafzal/ai-content-studio adaptations:
1. StyleProfileManager (multi-modal aesthetic matrix, script/visual prompt enrichment, TTS cues)
2. SmartApiRetry (quota & rate-limit auto-parser, ResourceExhausted handling, exponential backoff)
3. DynamicBRollDirector (retention cutaways, B-Roll cue clamping, FFmpeg overlay filter graph)
4. PodcastDebateEngine (multi-turn dual-host debate scripts, turn timestamps, speaker routing)
5. YouTubeClipperService (SEO metadata, B-Roll suggestions, audio ducking)
"""
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
def test_youtube_clipper_metadata_enrichment():
    """Verify fallback highlight moments now carry SEO and B-Roll timeline metadata."""
    highlights = youtube_clipper.detect_highlights_with_llm(
        transcript_text="Bu video çok önemli sırlar içeriyor...",
        num_clips=2,
        video_duration=120.0,
    )
    assert len(highlights) == 2
    first = highlights[0]
    assert "seo_title" in first and "#shorts" in first["seo_title"]
    assert "seo_tags" in first and len(first["seo_tags"]) > 0
    assert "broll" in first and isinstance(first["broll"], list)
    assert first["broll"][0]["start_offset"] >= 1.5
