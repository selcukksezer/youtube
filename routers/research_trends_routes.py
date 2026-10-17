"""Trending scan, content gaps, Reddit/RSS feeds, facts/podcast/flow generators, dubbing, and style profile routes."""
from __future__ import annotations

import logging
import re
import sys
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

import config
from api_models import ContentGapResearchRequest
from niche_templates import get_niche_production_profile
from reddit_client import fetch_public_posts
from research_service import (
    aggregate_format_fingerprint,
    build_content_gap_fingerprint,
    build_content_gap_suggestions,
)
from rss_scanner import (
    DEFAULT_RSS_FEEDS,
    get_breaking_news_topics,
    transform_rss_item_to_shorts_idea,
)
from trending_scanner import scan_youtube_shorts_trends

router = APIRouter(tags=["Research"])
logger = logging.getLogger(__name__)


def _rr_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("routers.research_router")
    return getattr(mod, name, default) if mod is not None else default


class TopicTranslateRequest(BaseModel):
    topic: str
    target_lang: str = "en"


class SubtitleTranslateRequest(BaseModel):
    srt_text: str
    target_language: str = Field(min_length=1, max_length=64)
    source_language: str = Field(default="", max_length=64)

    @model_validator(mode="before")
    @classmethod
    def map_ui_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if not data.get("srt_text") and data.get("srt_content") is not None:
                data["srt_text"] = data["srt_content"]
            if not data.get("target_language") and data.get("target_lang") is not None:
                data["target_language"] = data["target_lang"]
        return data


class RssConvertRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    source: Optional[str] = "RSS"
    suggested_niche: Optional[str] = "1_news_flash"
    language: Optional[str] = None


class FactsGenerateRequest(BaseModel):
    topic: str
    niche: Optional[str] = "8_ancient_history"
    language: Optional[str] = "tr"
    fetch_videos: Optional[bool] = False


class ViralFlowTransformRequest(BaseModel):
    youtube_url: Optional[str] = None
    raw_idea: Optional[str] = None
    url: Optional[str] = None
    topic: Optional[str] = None
    video_url: Optional[str] = None
    target_niche: Optional[str] = "12_amazon_affiliate"
    niche: Optional[str] = None
    language: Optional[str] = "tr"
    target_duration_sec: Optional[int] = 45


class PodcastGenerateRequest(BaseModel):
    topic: str
    host_name: Optional[str] = "Barış"
    guest_name: Optional[str] = "Deniz"
    rounds: Optional[int] = None
    turns: Optional[int] = None
    niche: Optional[str] = "6_stoic_philosophy"
    language: Optional[str] = "tr"
    fetch_videos: Optional[bool] = False


class DubbingApplyRequest(BaseModel):
    plan: Optional[Dict[str, Any]] = None
    scenes: Optional[List[Dict[str, Any]]] = None
    target_lang: Optional[str] = None
    target_language: Optional[str] = None
    target_languages: Optional[List[str]] = None
    strict: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def normalize_dubbing_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if not isinstance(data.get("plan"), dict) and isinstance(data.get("scenes"), list):
                data["plan"] = {"title": str(data.get("title") or ""), "scenes": data["scenes"], "language": data.get("source_language") or "tr"}
            if not data.get("target_lang") and data.get("target_language"):
                data["target_lang"] = data["target_language"]
        return data


class StyleProfileApplyRequest(BaseModel):
    plan: Optional[Dict[str, Any]] = None
    scenes: Optional[List[Dict[str, Any]]] = None
    style: Optional[str] = None
    profile_id: Optional[str] = None
    lock_character: Optional[bool] = True
    character_name: Optional[str] = None
    character_description: Optional[str] = None


@router.get("/api/trending/scan")
def api_scan_trending(
    topic: str = "Uzay",
    time_filter: str = "week",
    sort_by: str = "views",
    category: str = "all",
    region: str = "TR",
    geo: Optional[str] = None,
    limit: Optional[int] = None,
):
    scan_fn = _rr_attr("scan_youtube_shorts_trends", scan_youtube_shorts_trends)
    agg_fn = _rr_attr("aggregate_format_fingerprint", aggregate_format_fingerprint)
    effective_region = (geo or region or "TR").strip().upper()
    try:
        trends = scan_fn(topic, time_filter=time_filter, sort_by=sort_by, category=category, region=effective_region)
        if limit and int(limit) > 0:
            trends = list(trends)[: int(limit)]
        fps = [t.get("format_fingerprint") for t in trends if t.get("format_fingerprint")]
        return {
            "status": "ok",
            "topic": topic,
            "region": effective_region,
            "trends": trends,
            "items": trends,
            "format_fingerprint": agg_fn(fps),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/research/content-gaps")
def analyze_content_gaps(req: ContentGapResearchRequest):
    if len(req.raw_topics) > 12_000:
        raise HTTPException(status_code=400, detail="En fazla 12.000 karakterlik araştırma metni girin.")
    prof_fn = _rr_attr("get_niche_production_profile", get_niche_production_profile)
    sugg_fn = _rr_attr("build_content_gap_suggestions", build_content_gap_suggestions)
    fp_fn = _rr_attr("build_content_gap_fingerprint", build_content_gap_fingerprint)
    niche = req.niche or "1_news_flash"
    profile = prof_fn(niche)
    suggestions = sugg_fn(req.raw_topics, niche)
    return {
        "status": "ok",
        "source": "YouTube Studio Research / Content gaps (manuel içe aktarma)",
        "profile": profile,
        "suggestions": suggestions,
        "format_fingerprint": fp_fn(suggestions, niche),
    }


@router.post("/api/subtitles/translate")
def api_translate_subtitles(req: SubtitleTranslateRequest):
    """Translate SRT cue text without changing cue indices or timestamps."""
    from services.subtitle_translation import SubtitleTranslationError, translate_srt

    cfg = _rr_attr("config", config)
    try:
        translated = translate_srt(
            req.srt_text,
            target_language=req.target_language,
            source_language=req.source_language,
            api_key=cfg.AI_API_KEY,
            base_url=cfg.AI_BASE_URL,
            model=cfg.AI_MODEL,
        )
    except SubtitleTranslationError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except Exception as err:
        logger.exception("Subtitle translation failed")
        raise HTTPException(status_code=502, detail="Altyazı çevirisi AI sağlayıcısında başarısız oldu.") from err
    return {
        "status": "ok",
        "target_language": req.target_language.strip(),
        "srt_text": translated,
        "translated_srt": translated,
        "srt": translated,
    }


@router.post("/api/topics/translate")
def api_translate_topic(req: TopicTranslateRequest):
    """Translates video topic/title between Turkish and English using fast LLM."""
    text = (req.topic or "").strip()
    if not text:
        return {"status": "ok", "translated": ""}
    target_lang = "English" if (req.target_lang or "en").lower().startswith("en") else "Turkish"
    cfg = _rr_attr("config", config)
    try:
        from openai import OpenAI

        client = OpenAI(api_key=cfg.AI_API_KEY, base_url=cfg.AI_BASE_URL)
        prompt = (
            f"Translate this YouTube Shorts video title into natural, captivating, high-CTR {target_lang}. "
            f"Return ONLY the translated title as plain text, no markdown, no quotes:\n{text}"
        )
        resp = client.chat.completions.create(
            model=cfg.AI_MODEL or "gemini-flash-lite-latest",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.3,
        )
        translated = resp.choices[0].message.content.strip().strip("\"'")
        return {"status": "ok", "original": text, "translated": translated, "target_lang": req.target_lang}
    except Exception as e:
        return {"status": "error", "message": str(e), "translated": text}


@router.get("/api/research/reddit")
def get_reddit_posts(subreddit: str = "AITA", limit: int = 10, lang: str = None):
    """Fetches Reddit research posts with automatic discovery fallback (zero API key requirement)."""
    safe_subreddit = re.sub(r"[^A-Za-z0-9_]", "", subreddit) or "AITA"
    cfg = _rr_attr("config", config)
    fetch_fn = _rr_attr("fetch_public_posts", fetch_public_posts)
    try:
        target_lang = lang or getattr(cfg, "LANGUAGE", "tr")
        posts = fetch_fn(safe_subreddit, limit, lang=target_lang)
        has_keys = bool(getattr(cfg, "REDDIT_CLIENT_ID", "") and getattr(cfg, "REDDIT_CLIENT_SECRET", ""))
        is_ai = bool(posts and posts[0].get("source") == "ai_discovery")
        mode = "oauth" if has_keys else ("ai_discovery" if is_ai else "viral_archive")
        msg = (
            "Resmi OAuth üzerinden çekildi."
            if mode == "oauth"
            else ("Yapay zeka ile anlık taze viral hikayeler keşfedildi." if mode == "ai_discovery" else "Genişletilmiş viral arşiv rotasyonundan çekildi.")
        )
        return {"status": "ok", "posts": posts, "mode": mode, "message": msg}
    except Exception as exc:
        return {"status": "error", "detail": f"Reddit araştırması alınamadı: {exc}", "posts": []}


@router.get("/api/rss/sources")
def get_rss_sources():
    """Returns default RSS sources (Items 1, 57)."""
    return {"sources": _rr_attr("DEFAULT_RSS_FEEDS", DEFAULT_RSS_FEEDS)}


@router.get("/api/rss/fetch")
def fetch_rss_news(source: str = "aa_guncel", limit: int = 5):
    """Fetches breaking news from RSS feed (Item 57)."""
    items = _rr_attr("get_breaking_news_topics", get_breaking_news_topics)(source, max_items=limit)
    return {"status": "ok", "source": source, "items": items}


@router.post("/api/rss/convert-to-shorts")
def convert_rss_to_shorts_endpoint(req: RssConvertRequest):
    """Transforms RSS headline into an original high-retention curiosity/shock question (Item 122)."""
    cfg = _rr_attr("config", config)
    transform_fn = _rr_attr("transform_rss_item_to_shorts_idea", transform_rss_item_to_shorts_idea)
    try:
        target_lang = req.language or getattr(cfg, "LANGUAGE", "tr")
        idea = transform_fn(
            {
                "title": req.title,
                "description": req.description or "",
                "source_name": req.source or "RSS",
                "suggested_niche": req.suggested_niche or "1_news_flash",
            },
            lang=target_lang,
        )
        return {"status": "ok", "idea": idea}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/facts/generate")
def api_generate_facts_script(req: FactsGenerateRequest):
    """Generates slop-free educational/facts Shorts script adapted from ShortGPT and builds a scene plan."""
    from services.facts_story_engine import FactsStoryEngine
    from services.manuscript_script import build_manuscript_plan

    cfg = _rr_attr("config", config)
    try:
        lang = req.language or getattr(cfg, "LANGUAGE", "tr")
        niche_id = req.niche or "8_ancient_history"
        script_data = FactsStoryEngine.generate_facts_script(topic=req.topic, language=lang)
        if isinstance(script_data, dict) and script_data.get("scenes"):
            plan = dict(script_data)
            plan.setdefault("title", req.topic)
            plan.setdefault("topic", req.topic)
            plan.setdefault("niche_id", niche_id)
            plan.setdefault("language", lang)
        else:
            raw_text = script_data.get("full_narration") if isinstance(script_data, dict) else str(script_data)
            plan = build_manuscript_plan(raw_text or req.topic, title=req.topic, niche_id=niche_id, language=lang)
        if req.fetch_videos and plan.get("scenes"):
            try:
                from routers.media_router import auto_fetch_videos_for_scenes

                plan["scenes"] = auto_fetch_videos_for_scenes(plan["scenes"], niche_id=niche_id)
            except Exception:
                pass
        act_labels = ["Hook (Kanca)", "Bağlam & Mekanizma", "Kırılma (Twist)", "Final & Soru"]
        acts = [
            {
                "act": act_labels[idx] if idx < len(act_labels) else f"Sahne {idx + 1}",
                "narration": sc.get("narration", ""),
                "duration": sc.get("duration", 4.5),
            }
            for idx, sc in enumerate(plan.get("scenes") or [])
        ]
        return {"status": "ok", "script": script_data, "plan": plan, "acts": acts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Facts senaryosu üretilemedi: {e}")


@router.post("/api/flow/transform_viral")
def api_transform_viral_to_flow(req: ViralFlowTransformRequest):
    """Transforms any viral YouTube video or raw idea into an original Google Flow / Veo storyboard."""
    from services.google_flow_transformer import transform_youtube_url_to_flow

    source_input = (
        req.youtube_url or req.raw_idea or req.url or req.topic or req.video_url or ""
    ).strip()
    if not source_input:
        raise HTTPException(status_code=400, detail="youtube_url veya raw_idea gereklidir.")
    effective_niche = (req.niche or req.target_niche or "12_amazon_affiliate").strip()
    try:
        storyboard = transform_youtube_url_to_flow(
            youtube_url=source_input,
            target_niche=effective_niche,
            language=req.language or "tr",
        )
        narration = ""
        if isinstance(storyboard, dict):
            scenes = storyboard.get("scenes") or storyboard.get("shots") or []
            narration = storyboard.get("full_narration") or " ".join(
                str(s.get("narration") or s.get("voiceover") or s.get("prompt") or "")
                for s in scenes if isinstance(s, dict)
            ).strip()
        return {
            "status": "ok",
            "data": storyboard,
            "result": {"transformed_script": narration or str(storyboard), "storyboard": storyboard},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Viral video dönüştürülemedi: {e}")


@router.post("/api/podcast/generate")
def api_generate_podcast_debate(req: PodcastGenerateRequest):
    """Generates a two-host conversational debate script and converts it into a ready-to-render Shorts plan."""
    from services.active_speaker_detector import ActiveSpeakerDetector
    from services.podcast_debate_engine import podcast_debate_engine

    if not (req.topic or "").strip():
        raise HTTPException(status_code=400, detail="Podcast konusu boş olamaz.")
    try:
        effective_rounds = req.rounds if req.rounds is not None else (max(2, int(req.turns) // 2) if req.turns else 3)
        debate = podcast_debate_engine.generate_debate(
            topic=req.topic.strip(),
            host_name=(req.host_name or "Barış").strip(),
            guest_name=(req.guest_name or "Deniz").strip(),
            rounds=max(2, min(int(effective_rounds), 5)),
            language=req.language or "tr",
        )
        turn_dicts = debate.to_turn_dicts()
        audit_res = ActiveSpeakerDetector.evaluate_turns(turn_dicts, debate.estimated_total_duration_sec)
        scenes = [
            {
                "scene_number": idx + 1,
                "narration": t.text,
                "duration": max(3.5, float(t.estimated_duration_sec or 4.0)),
                "speaker": t.speaker,
                "speaker_role": t.role,
                "scene_description": (
                    f"Cinematic 4K podcast studio close-up of {t.speaker} ({t.role}) speaking passionately about {req.topic}, "
                    f"condenser microphone, warm amber & teal bokeh lighting"
                ),
                "search_queries": ["podcast studio microphone talking", "two people conversation interview studio", f"{req.topic} cinematic b-roll"],
                "mood": "dramatic" if t.role == "guest" else "intriguing",
            }
            for idx, t in enumerate(debate.turns)
        ]
        if req.turns and len(scenes) > int(req.turns):
            scenes = scenes[: int(req.turns)]
        niche_id = (req.niche or "6_stoic_philosophy").strip()
        if req.fetch_videos and scenes:
            try:
                from routers.media_router import auto_fetch_videos_for_scenes

                scenes = auto_fetch_videos_for_scenes(scenes, niche_id=niche_id)
            except Exception:
                pass
        plan = {
            "title": req.topic.strip(),
            "niche_id": niche_id,
            "language": req.language or "tr",
            "scenes": scenes,
            "full_narration": " ".join(s["narration"] for s in scenes),
            "hybrid_split_screen": True,
            "podcast_debate": {
                "host_name": debate.host_name,
                "guest_name": debate.guest_name,
                "turns": turn_dicts,
                "layout_decision": audit_res.layout_decision.value,
                "speaker_distribution": audit_res.speaker_distribution,
                "layout_segments": [
                    {
                        "start_sec": seg.start_sec,
                        "end_sec": seg.end_sec,
                        "layout_mode": audit_res.layout_decision.value,
                        "active_speaker": seg.speaker_id,
                    }
                    for seg in audit_res.speaker_turns
                ],
            },
        }
        return {"status": "ok", "plan": plan, "debate": plan["podcast_debate"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Podcast senaryosu üretilemedi: {e}")


@router.post("/api/dubbing/apply")
def api_apply_dubbing(req: DubbingApplyRequest):
    """Translates and dubs a scene plan into target_lang(s) while preserving visual timing and assets."""
    from services.dubbing import apply_dubbing_to_plan, build_dubbing_pack

    if not isinstance(req.plan, dict) or not req.plan.get("scenes"):
        raise HTTPException(status_code=400, detail="Dublaj için geçerli bir sahne planı gereklidir.")
    try:
        src_lang = str(req.plan.get("language") or "tr")
        langs = [l.strip() for l in (req.target_languages or []) if l and str(l).strip()] or [str(req.target_lang or "en").strip()]
        dubbed_tracks: Dict[str, Any] = {}
        primary_plan = primary_pack = None
        for lang in langs:
            d_plan = apply_dubbing_to_plan(req.plan, target_lang=lang, strict=bool(req.strict))
            d_pack = build_dubbing_pack(
                req.plan.get("scenes") or [], source_lang=src_lang, target_lang=lang,
                title=str(req.plan.get("title") or ""), strict=bool(req.strict),
            )
            dubbed_tracks[lang] = {
                "title": d_plan.get("title"),
                "language": lang,
                "voice": d_pack.get("recommended_voice") or d_plan.get("tts_voice") or "auto",
                "scenes": d_plan.get("scenes") or [],
                "pack": d_pack,
            }
            if primary_plan is None:
                primary_plan, primary_pack = d_plan, d_pack
        return {"status": "ok", "plan": primary_plan, "pack": primary_pack, "dubbed_tracks": dubbed_tracks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dublaj paketi oluşturulamadı: {e}")


@router.get("/api/style-profiles")
def api_list_style_profiles():
    """Returns all available ContentStyle presets from StyleProfileManager."""
    from services.style_profile_manager import STYLE_PROFILES

    profiles = [
        {
            "id": key.value, "name": prof.name, "target_wpm": prof.target_wpm,
            "subtitle_font": prof.subtitle_font, "video_aesthetic": prof.video_aesthetic,
            "tts_cadence_cue": prof.tts_cadence_cue,
        }
        for key, prof in STYLE_PROFILES.items()
    ]
    return {"status": "ok", "profiles": profiles}


@router.post("/api/style-profiles/apply")
def api_apply_style_profile(req: StyleProfileApplyRequest):
    """Applies a StyleProfile and optional CharacterIdentityAnchor across all scenes in a plan."""
    from services.character_identity_anchor import character_identity_anchor
    from services.style_profile_manager import style_profile_manager

    plan = dict(req.plan) if isinstance(req.plan, dict) else {"title": "Viral Video", "scenes": list(req.scenes or [])}
    if not plan.get("scenes") and req.scenes:
        plan["scenes"] = list(req.scenes)
    if not plan.get("scenes"):
        raise HTTPException(status_code=400, detail="Stil profili için geçerli bir sahne planı gereklidir.")

    style_key = (req.style or req.profile_id or "viral_video").strip()
    profile = style_profile_manager.get_profile(style_key)
    topic = str(plan.get("title") or "Viral Video")
    char_hint = (req.character_name or req.character_description or "").strip() or None
    anchor = (
        character_identity_anchor.extract_or_create_anchor(
            topic=f"{topic} {char_hint}" if char_hint else topic,
            character_name=char_hint,
            art_style=profile.video_aesthetic,
        )
        if (req.lock_character or char_hint)
        else None
    )

    updated_scenes = []
    for sc in plan.get("scenes") or []:
        s_copy = dict(sc)
        base_desc = str(s_copy.get("scene_description") or s_copy.get("narration") or topic).strip()
        enriched = style_profile_manager.enrich_visual_prompt(base_desc, style_key)
        if anchor is not None:
            enriched = character_identity_anchor.inject_anchor_into_scene_prompt(enriched, anchor)
        s_copy["scene_description"] = enriched
        s_copy["style_profile"] = profile.name
        updated_scenes.append(s_copy)

    plan["scenes"] = updated_scenes
    plan["style_profile"] = {
        "style_id": style_key,
        "name": profile.name,
        "tts": style_profile_manager.get_tts_config(style_key),
        "subtitle_theme": style_profile_manager.get_subtitle_theme(style_key),
        "character_anchor": anchor.to_police_sketch() if anchor else None,
        "character_reference_prompt": character_identity_anchor.build_reference_image_prompt(anchor) if anchor else None,
    }
    return {"status": "ok", "plan": plan, "scenes": updated_scenes, "style_profile": plan["style_profile"]}
