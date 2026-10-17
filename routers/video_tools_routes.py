"""
Creative video tools routes: title refinement, virality audit, YouTube clipper,
Helios prompt/shot grammar, punch-in zoom curve, visual grounding audit, and speaker layout.
Extracted from routers/video_router.py for modularity.
"""
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Video"])


@router.post("/api/video/title-ideas/refine")
def api_refine_video_title_idea(payload: Dict[str, Any]):
    """Refines a selected post-render title using concise creator feedback."""
    current_title = payload.get("current_title")
    feedback = payload.get("feedback")
    summary = payload.get("summary", "")
    language = payload.get("language", "tr")
    if not all(isinstance(value, str) for value in (current_title, feedback, summary, language)):
        raise HTTPException(
            status_code=422,
            detail="current_title, feedback, summary ve language metin olmalı.",
        )

    from services.video_title_ideas import (
        TitleIdeaRefinementError,
        TitleIdeaRefinementUnavailable,
        refine_video_title_idea,
    )

    try:
        refinement = refine_video_title_idea(
            current_title=current_title,
            feedback=feedback,
            summary=summary,
            language=language,
        )
    except TitleIdeaRefinementUnavailable as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except TitleIdeaRefinementError as err:
        raise HTTPException(status_code=502, detail=str(err)) from err
    return {"status": "ok", "refinement": refinement}


@router.post("/api/script/virality_audit")
def api_audit_script_virality(payload: Dict[str, Any]):
    """8-signal virality and slop audit adapted from Anil-matcha highlights engine."""
    from services.virality_evaluator import evaluate_script_virality

    narration = str(
        payload.get("narration")
        or payload.get("full_narration")
        or payload.get("script_text")
        or payload.get("text")
        or ""
    ).strip()
    topic = str(
        payload.get("topic")
        or payload.get("title")
        or payload.get("hook_text")
        or ""
    ).strip()
    result = evaluate_script_virality(narration, topic=topic)
    return {"status": "ok", "audit": result}


@router.post("/api/clipper/analyze")
def api_clipper_analyze(payload: Dict[str, Any]):
    """Analyzes a YouTube URL, fetches transcript, and detects viral 9:16 highlights."""
    url = str(payload.get("url") or "").strip()
    num_clips = int(payload.get("num_clips") or 3)
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL gerekli.")

    from services.multimodal_clipper import (
        MultimodalConfigurationError,
        analyze_video_highlights,
        multimodal_analysis_requested,
    )

    try:
        use_multimodal = multimodal_analysis_requested(payload)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    if use_multimodal and not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, detail="TwelveLabs analizi için HTTP(S) video URL gerekli."
        )

    try:
        from services.youtube_clipper import youtube_clipper

        info = youtube_clipper.extract_youtube_info(url)
        duration = float(info.get("duration") or 300)
        subs = None
        if use_multimodal:
            try:
                raw_highlights = analyze_video_highlights(
                    url,
                    video_duration=duration,
                    num_clips=num_clips,
                )
            except MultimodalConfigurationError as err:
                raise HTTPException(status_code=503, detail=str(err)) from err
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err)) from err
            except Exception as err:
                raise HTTPException(
                    status_code=502,
                    detail=f"TwelveLabs video analizi başarısız: {err}",
                ) from err
        else:
            from services.youtube_clipper import normalize_transcription_hotwords

            try:
                hotwords = normalize_transcription_hotwords(payload.get("hotwords", ""))
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err)) from err
            subs = youtube_clipper.fetch_subtitles_or_transcribe(
                url,
                "",
                hotwords=hotwords,
            )
            transcript_text = youtube_clipper.format_transcript_segments(subs)
            if not transcript_text:
                raise HTTPException(
                    status_code=422,
                    detail="Videoda klip zamanlarını belirlemek için kullanılabilir zaman damgalı altyazı bulunamadı.",
                )
            raw_highlights = youtube_clipper.detect_highlights_with_llm(
                transcript_text=transcript_text,
                num_clips=max(1, min(5, num_clips)),
                video_duration=duration,
            )
            raw_highlights = youtube_clipper.ground_highlights_in_transcript(
                raw_highlights,
                subs,
            )
        from services.highlight_clipper import select_highlights

        words = (
            [
                {"w": row.get("text") or "", "s": row.get("start"), "e": row.get("end")}
                for row in (subs or [])
            ]
            if not use_multimodal
            else []
        )
        highlights = select_highlights(
            raw_highlights,
            duration=duration,
            words=words,
            num_clips=num_clips,
        )
        return {
            "status": "ok",
            "video_info": info,
            "highlights_count": len(highlights),
            "highlights": highlights,
            "words": words,
        }
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Klip analizi başarısız: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clipper analizi başarısız: {e}")


@router.post("/api/clipper/render")
def api_clipper_render(payload: Dict[str, Any]):
    """Downloads YouTube video segment and applies OpenCV face-tracking 9:16 crop."""
    url = str(payload.get("url") or "").strip()
    highlight = payload.get("highlight") or {}
    clip_index = int(payload.get("clip_index") or 1)

    if not url or not highlight:
        raise HTTPException(status_code=400, detail="URL ve highlight objesi gerekli.")

    try:
        from services.youtube_clipper import youtube_clipper

        source_path = youtube_clipper.download_video(url)
        out_clip_path = youtube_clipper.render_highlight_clip(
            source_video_path=source_path,
            highlight=highlight,
            clip_index=clip_index,
        )
        return {
            "status": "ok",
            "message": "Viral Short başarıyla üretildi.",
            "output_path": out_clip_path,
            "filename": os.path.basename(out_clip_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clipper render başarısız: {e}")


@router.post("/api/helios/prompt")
def api_helios_prompt(payload: Dict[str, Any]):
    """Generates Helios 4-tier cinematographic prompt and inference configuration."""
    narration = str(payload.get("narration") or "").strip()
    scene_description = str(payload.get("scene_description") or "").strip()
    niche_id = str(payload.get("niche_id") or "general").strip()
    aspect = str(payload.get("aspect") or "9:16").strip()
    index = int(payload.get("index") or 0)
    duration = float(payload.get("duration") or 4.0)

    from visuals.ai_video.helios_prompt_builder import (
        HELIOS_NEGATIVE_PROMPT,
        HeliosPromptBuilder,
    )

    params = HeliosPromptBuilder.create_helios_params(
        narration=narration,
        scene_description=scene_description,
        niche_id=niche_id,
        duration=duration,
        aspect=aspect,
        index=index,
    )
    return {
        "status": "ok",
        "prompt": params.prompt,
        "negative_prompt": HELIOS_NEGATIVE_PROMPT,
        "inference_params": params.to_dict(),
    }


@router.post("/api/helios/enhance_scenes")
def api_helios_enhance_scenes(payload: Dict[str, Any]):
    """Applies Helios 4-tier shot grammar and sequence pacing across all script scenes."""
    scenes = payload.get("scenes") or []
    niche_id = str(payload.get("niche_id") or "general").strip()
    aspect = str(payload.get("aspect") or "9:16").strip()
    style_preset = str(payload.get("style_preset") or "").strip()
    character_anchor = str(payload.get("character_anchor") or "").strip()

    if not isinstance(scenes, list) or not scenes:
        raise HTTPException(status_code=400, detail="scenes listesi boş olamaz.")

    from services.helios_visual_enhancer import helios_visual_enhancer

    enhanced = helios_visual_enhancer.enhance_scenes_sequence(
        scenes=scenes,
        niche_id=niche_id,
        aspect=aspect,
    )
    if style_preset or character_anchor:
        for sc in enhanced:
            if isinstance(sc, dict):
                if style_preset:
                    sc["style_preset"] = style_preset
                if character_anchor:
                    sc["character_anchor"] = character_anchor
                    desc = str(sc.get("scene_description") or "").strip()
                    if desc and character_anchor.lower() not in desc.lower():
                        sc["scene_description"] = f"{character_anchor}, {desc}"
                    hp = str(sc.get("helios_prompt") or "").strip()
                    if hp and character_anchor.lower() not in hp.lower():
                        sc["helios_prompt"] = f"{character_anchor} — {hp}"
    return {
        "status": "ok",
        "count": len(enhanced),
        "scenes": enhanced,
    }


@router.post("/api/punch_in/curve")
def api_punch_in_curve(payload: Dict[str, Any]):
    """Calculates asymmetric smoothstep punch-in zoom curve and FFmpeg filter."""
    duration = float(payload.get("duration") or payload.get("duration_sec") or 5.0)
    fps = int(payload.get("fps") or 30)
    emphasis_times = payload.get("emphasis_times")
    intensity = payload.get("intensity")
    if payload.get("max_zoom") is not None:
        max_zoom = float(payload["max_zoom"])
    elif intensity is not None:
        max_zoom = 1.0 + max(0.01, min(0.5, float(intensity)))
    else:
        max_zoom = 1.12
    width = int(payload.get("width") or 1080)
    height = int(payload.get("height") or 1920)

    from effects.punch_in_director import punch_in_director

    zooms = punch_in_director.calculate_zoom_curve(
        total_duration_sec=duration,
        fps=fps,
        emphasis_times=emphasis_times,
        max_zoom=max_zoom,
    )
    ffmpeg_filter = punch_in_director.generate_ffmpeg_zoom_filter(
        width=width,
        height=height,
        total_duration_sec=duration,
        punch_time_sec=emphasis_times[0] if emphasis_times else 0.5,
        max_zoom=max_zoom,
        fps=fps,
    )
    rounded_curve = [round(z, 4) for z in zooms]
    return {
        "status": "ok",
        "frame_count": len(zooms),
        "peak_zoom": max(zooms) if zooms else 1.0,
        "curve": rounded_curve,
        "sample_zooms": [round(z, 3) for z in zooms[:15]],
        "ffmpeg_filter": ffmpeg_filter,
    }


@router.post("/api/grounding/audit")
def api_grounding_audit(payload: Dict[str, Any]):
    """Audits and regrounds narration vs visual scene descriptions to prevent absurd slop."""
    scenes = payload.get("scenes") or []
    niche_id = str(payload.get("niche_id") or "general").strip()

    if not isinstance(scenes, list) or not scenes:
        raise HTTPException(status_code=400, detail="scenes listesi boş olamaz.")

    from services.hook_visual_grounding import hook_visual_grounding

    regrounded = hook_visual_grounding.reground_plan_scenes(
        scenes=scenes,
        niche_id=niche_id,
    )
    flagged_scenes = [s for s in regrounded if not s.get("is_grounded")]
    mismatches = len(flagged_scenes)

    return {
        "status": "ok",
        "total_scenes": len(regrounded),
        "regrounded_count": mismatches,
        "flagged_count": mismatches,
        "flagged_scenes": flagged_scenes,
        "scenes": regrounded,
    }


@router.post("/api/speaker/layout")
def api_speaker_layout(payload: Dict[str, Any]):
    """Evaluates multi-speaker dialogue turns and selects optimal vertical layout."""
    turns = payload.get("turns") or []
    total_duration = float(payload.get("total_duration") or 30.0)

    from services.active_speaker_detector import active_speaker_detector

    res = active_speaker_detector.evaluate_turns(
        turns=turns,
        total_duration_sec=total_duration,
    )
    return {
        "status": "ok",
        "layout_decision": res.layout_decision.value,
        "is_multispeaker": res.is_multispeaker,
        "speaker_distribution": res.speaker_distribution,
        "explanation": res.explanation,
    }
