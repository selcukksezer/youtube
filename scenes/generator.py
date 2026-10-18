"""
Core scene generator with multi-provider AI fallback and post-processing filters.
"""

import json
import logging
import os
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple
from openai import OpenAI
import config
from api_models import validate_generated_plan_errors
from .prompts import get_rotated_system_prompt, advance_prompt_rotation
from .fallback import _generate_procedural_fallback_scenes, sanitize_topic_title
from .enrichment import (
    enrich_cinematic_search_queries,
    enrich_closing_gaze_queries,
    enrich_numbered_rule_narration,
    enrich_continuous_motion_hints,
    enrich_audio_visual_contrast_scenes,
    avoid_consecutive_face_visuals,
    enforce_visual_cadence_14,
    verify_and_correct_hallucinations,
)
from .retention_hooks import ensure_retention_hooks_on_plan
from .narration_validate import (
    scene_narration_issues,
    validate_and_fix_scenes,
    plan_quality_usable,
    scene_description_usable,
    synthesize_scene_description,
    sanitize_plan_scene_descriptions,
    SHORTS_MIN_DURATION,
    SHORTS_MAX_DURATION,
    MIN_SCENE_COUNT,
    repair_post_hook_word_budget,
)
from .plan_linter import lint_plan_diversity
from director.schema import shorts_word_budget
from director.visual_intent import resolve_niche_from_topic
from .llm_scene_client import (
    _SCHEMA_RETRY_HINT,
    _build_competitor_fingerprint_block,
    _build_series_continuity_prompt,
    _call,
    _clean_json,
    _configured_script_providers,
    _gemini_script_circuit_open,
    _normalize_series_outline,
    _parse_provider_json,
    _record_gemini_script_outcome,
    _schema_valid,
    _tts_word_cap,
    _usable_repair_description,
    _usable_repair_queries,
    generate_series_outline,
    repair_script_quality,
)

logger = logging.getLogger(__name__)
_LAST_ROTATED_COMPLETED_COUNT: Optional[int] = None


def generate_scenes(
    title: str,
    niche_type: str = None,
    language: str = None,
    format_fingerprint: dict = None,
    variation_attempt: int = 0,
    previous_narration: Optional[str] = None,
    force_regenerate: bool = False,
    enable_outro: bool = True,
    continuity_context: Optional[str] = None,
    reddit_post: Optional[dict] = None,
) -> dict:
    global _LAST_ROTATED_COMPLETED_COUNT
    lang = language or getattr(config, "LANGUAGE", "tr")
    clean_title = sanitize_topic_title(title)
    clean_continuity_context = (continuity_context or "").strip()[:4000]
    try:
        from database import get_video_stats
        stats = get_video_stats()
        total_renders = int(stats.get("total_completed") or 0)
        if total_renders > 0 and total_renders % 20 == 0 and total_renders != _LAST_ROTATED_COMPLETED_COUNT:
            advance_prompt_rotation(steps=1)
            _LAST_ROTATED_COMPLETED_COUNT = total_renders
    except Exception:
        pass

    effective_var = max(1, variation_attempt) if (force_regenerate or variation_attempt > 0) else 0
    if effective_var > 0:
        advance_prompt_rotation(steps=effective_var)
    locked_niche = resolve_niche_from_topic(title, niche_type or "1_news_flash")
    word_cap = _tts_word_cap()
    force_fb = os.environ.get("SHORTS_FORCE_PROCEDURAL_FALLBACK", "").strip().lower() in {
        "1", "true", "yes", "on",
    }
    try:
        from niche_templates import get_niche_prompt
        prompt = get_niche_prompt(locked_niche, title, language=lang, enable_outro=enable_outro)
        if variation_attempt > 0:
            if lang == "en":
                prompt = (
                    prompt
                    + f"\n\nVARIATION #{variation_attempt + 1}: Write a completely fresh, unique narrative for '{title}'. "
                    "Do not repeat opening lines or formulaic phrasing from previous scripts."
                )
            else:
                prompt = (
                    prompt
                    + f"\n\nVARYASYON #{variation_attempt + 1}: '{title}' konusuna özgü benzersiz "
                    "anlatım yaz; önceki videolardaki kalıp cümleleri tekrarlama."
                )
    except Exception:
        prompt = get_rotated_system_prompt(base_lang=lang, force_variant=variation_attempt % 3)

    fp_block = _build_competitor_fingerprint_block(format_fingerprint, lang=lang)
    if fp_block:
        prompt = prompt + fp_block

    try:
        from director.visual_intent import resolve_topic_intelligence
        from hybrid_niches import build_hybrid_prompt_block
        intel = resolve_topic_intelligence(title, locked_niche)
        if intel.get("hybrid_niche"):
            prompt = prompt + build_hybrid_prompt_block(intel["hybrid_niche"], lang=lang)
    except Exception:
        pass

    fact_snippets: list = []
    try:
        from services.web_fact_researcher import format_snippet_block, research_topic_facts
        fact_snippets = research_topic_facts(title, max_snippets=4)
        fact_context = format_snippet_block(fact_snippets)
        if fact_context:
            prompt = prompt + "\n\n" + fact_context
            print(f"  [FactResearcher] Anti-hallucination web araştırması prompta eklendi ({title[:40]})")
    except Exception as fact_err:
        fact_snippets = []
        logger.warning("Scene generation fact research failed: %s", fact_err)

    try:
        from services.niche_guardrails import format_niche_prompt_guardrails
        guardrail_prompt = format_niche_prompt_guardrails(locked_niche, lang=lang)
        if guardrail_prompt:
            prompt = prompt + guardrail_prompt
    except Exception:
        pass

    if not enable_outro:
        if lang == "tr":
            prompt += (
                "\n\nOUTRO KAPALI: Son sahneye CTA, yorum sorusu veya döngü kapanışı ekleme. "
                "Son cümle konunun son olgusu olsun.\n"
            )
        else:
            prompt += (
                "\n\nOUTRO OFF: Do not add a CTA, comment question, or loop close. "
                "End on the last fact.\n"
            )

    if lang == "en":
        user_msg = (
            f"Create a high-retention English YouTube Shorts video script for this topic: '{clean_title}'.\n"
            f"Original title context (hashtags stripped): '{title}'.\n"
            f"CRITICAL REQUIREMENT: The 'narration' field in EVERY scene MUST be written 100% in fluent, natural ENGLISH. "
            f"Each narration MUST be 1-2 complete, concise sentences (12-18 words per scene) — never mood labels, dots, or emoji-only placeholders. "
            f"Each scene_description MUST be a concrete English visual sentence, never a placeholder. "
            f"Do NOT output Turkish narration. Translate and adapt the topic into an immersive English script.\n"
            f"CRITICAL LENGTH RULE: Write exactly 6 spoken scenes. Total narration MUST be 85-{word_cap} words and NEVER exceed {word_cap} words. "
            f"Use the available budget for topic-specific details without filler; never exceed 60 seconds."
        )
    else:
        user_msg = (
            f"Bu başlık için Türkçe YouTube Shorts senaryosu oluştur: '{clean_title}'.\n"
            f"Orijinal başlık (hashtag/emojisiz): '{title}'.\n"
            f"KRİTİK: Her sahnenin 'narration' alanı kısa, doğal ve TAM Türkçe cümle(ler) olmalı; "
            f"her sahne 12-18 kelimelik zengin içerik taşımalı, sadece mood etiketi, nokta veya emoji placeholder YASAK. "
            f"scene_description gerçek İngilizce görsel cümle olmalı — placeholder YASAK. "
            f"UZUNLUK KURALI: Tam 6 konuşma sahnesi yaz. "
            f"Seslendirme toplamı 85-{word_cap} kelime aralığında olsun ve {word_cap} kelimeyi ASLA aşmasın. "
            f"Bütçeyi konuya özgü somut bilgilerle kullan, dolgu ekleme."
        )
        try:
            from scenes.hadith_overlay import is_sacred_niche
            if is_sacred_niche(str(locked_niche or niche_type or ""), clean_title):
                user_msg += (
                    "\nHadis/ayet sahnesi: her sahneye 'arabic_text' (harekeli Arapça) ve "
                    "'source_citation' (Buhari, Müslim veya sure) yaz. "
                    "narration yalnız Türkçe meal olsun. Arapça seslendirmeye girmez, ekranda üstte durur."
                )
        except Exception:
            pass

    if lang == "en":
        user_msg += (
            "\n\nNARRATIVE FLOW: Treat all scene narrations as one continuous spoken script, not separate summaries. "
            "Each scene must add a distinct new beat and connect naturally to what came before. "
            "Do not reintroduce the topic or restate a previous fact in every scene. "
            "Vary sentence openings and rhythm; avoid repeated transitions, rhetorical templates, and filler. "
            "Use numbered phrasing only when the topic genuinely calls for a list."
        )
    else:
        user_msg += (
            "\n\nANLATIM AKIŞI: Tüm sahne anlatımlarını ayrı özetler gibi değil, tek ve doğal bir konuşma metninin "
            "ardışık parçaları olarak yaz. Her sahne yeni bir fikir veya gelişme eklesin ve önceki sahneye "
            "doğal biçimde bağlansın. Her sahnede konuyu yeniden tanıtma veya önceki bilgiyi tekrarlama. "
            "Cümle başlangıçlarını ve ritmi çeşitlendir; aynı geçişleri, soru kalıplarını ve dolgu ifadelerini "
            "tekrarlama. Numaralı anlatımı yalnızca konu gerçekten liste gerektiriyorsa kullan."
        )

    user_msg += _build_series_continuity_prompt(clean_continuity_context, lang)

    if reddit_post and locked_niche == "2_reddit_confessions":
        r_dict = reddit_post if isinstance(reddit_post, dict) else (reddit_post.model_dump() if hasattr(reddit_post, "model_dump") else {})
        r_title = str(r_dict.get("title") or getattr(reddit_post, "title", "") or "").strip()[:300]
        r_body = str(r_dict.get("body") or r_dict.get("selftext") or getattr(reddit_post, "body", "") or "").strip()[:3000]
        if r_title or r_body:
            if lang == "en":
                user_msg += f"\n\nREDDIT CONFESSION CONTEXT:\nTitle: {r_title}\nBody: {r_body}\nAdapt this confession into an original 6-scene spoken script."
            else:
                user_msg += f"\n\nREDDIT İTİRAF BAĞLAMI:\nBaşlık: {r_title}\nGönderi: {r_body}\nBu itirafı özgün bir 6 sahnelik Türkçe anlatıma uyarla."

    if previous_narration and len(previous_narration.strip()) > 20:
        prev_snip = previous_narration.strip()[:400].replace('\n', ' ')
        if lang == "en":
            user_msg += (
                f"\n\n[CRITICAL VARIATION INSTRUCTION]: The user requested a brand-new script for this topic. "
                f"The previous script text was: '{prev_snip}'. "
                f"DO NOT repeat these sentences, the same opening hook, or the same narrative order! "
                f"Rewrite completely from a new angle, with different facts/examples and a fresh narrative structure."
            )
        else:
            user_msg += (
                f"\n\n[KRİTİK VARYASYON TALİMATI]: Kullanıcı bu konu için yeni bir senaryo istedi. "
                f"Önceki senaryoda yazılan metin şuydu: '{prev_snip}'. "
                f"KESİNLİKLE bu cümleleri, aynı açılış kancasını veya aynı anlatı sıralamasını TEKRARLAMA! "
                f"Tamamen farklı bir bakış açısı, farklı bir olay/örnek/çarpıcı bilgi ve taze bir kurgu ile baştan yaz."
            )
    elif effective_var > 0:
        if lang == "en":
            user_msg += (
                f"\n\n[CRITICAL VARIATION #{effective_var + 1}]: A script was previously written for this topic. "
                f"Break away from conventional tropes, write an alternative opening hook, and craft a brand-new variation with fresh facts."
            )
        else:
            user_msg += (
                f"\n\n[KRİTİK VARYASYON #{effective_var + 1}]: Bu konu için daha önce senaryo yazıldı. "
                f"Klasik kalıpların dışına çık, alternatif bir açılış kancası ve farklı bilgiler içeren yepyeni bir varyasyon yaz."
            )

    providers = _configured_script_providers()
    last_error = None
    data = None
    successful_provider_tuple = None

    if force_fb:
        providers = []
        last_error = "SHORTS_FORCE_PROCEDURAL_FALLBACK"

    for provider_name, api_key, base_url, model_name in providers:
        if provider_name == "Gemini" and _gemini_script_circuit_open():
            print(f"  [{provider_name}] gemini_script circuit OPEN — fallback modele geçiliyor")
            continue
        print(f"  [{provider_name}] Senaryo üretiliyor: '{title}'")
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            call_temp = 0.88 if (effective_var > 0 or force_regenerate) else 0.7
            params = dict(
                model=model_name,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                temperature=call_temp, max_tokens=4000,
            )
            if "Gemini" in provider_name or "OpenAI" in provider_name:
                params["response_format"] = {"type": "json_object"}

            resp = _call(client, params, provider_name=provider_name, model_name=model_name)
            raw = resp.choices[0].message.content.strip()
            data = _parse_provider_json(raw)
            if not data:
                print(f"  [{provider_name}] JSON ayrıştırma başarısız, retrying...")
                params["temperature"] = 0.3
                resp2 = _call(client, params, provider_name=provider_name, model_name=model_name)
                data = _parse_provider_json(resp2.choices[0].message.content.strip())

            if data and not _schema_valid(data):
                schema_errs = validate_generated_plan_errors(data)
                print(f"  [{provider_name}] Schema invalid ({schema_errs[0]}), strict retry...")
                schema_params = dict(
                    params,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_msg + _SCHEMA_RETRY_HINT},
                    ],
                )
                resp3 = _call(client, schema_params, provider_name=provider_name, model_name=model_name)
                retry_data = _parse_provider_json(resp3.choices[0].message.content.strip())
                if retry_data and _schema_valid(retry_data):
                    data = retry_data
                else:
                    print(f"  [{provider_name}] Schema retry failed — next provider")
                    data = None

            if data and _schema_valid(data):
                successful_provider_tuple = (provider_name, api_key, base_url, model_name)
                print(f"  [{provider_name}] OK: Senaryo basariyla uretildi")
                break
        except Exception as e:
            print(f"  [UYARI] {provider_name} servisi hata verdi: {e}. Sıradaki AI modeline/sağlayıcısına geçiliyor...")
            last_error = e

    if data and data.get("scenes") and not plan_quality_usable(data.get("scenes", [])):
        data["scenes"], _ = validate_and_fix_scenes(data.get("scenes", []))
        sanitize_plan_scene_descriptions(data)
        if not plan_quality_usable(data.get("scenes", [])):
            print("  [SceneGenerator] AI plan kalitesi düşük (kısa anlatım/placeholder görsel) — prosedürel fallback devreye alınıyor.")
            data = None

    if not data or not data.get("scenes"):
        print(
            f"  [BİLGİ] AI servisleri yanıt vermedi ({last_error}). "
            f"Akıllı Prosedürel Senaryo Motoru devreye alındı (varyasyon={variation_attempt})."
        )
        data = _generate_procedural_fallback_scenes(
            title,
            niche_type=locked_niche or niche_type,
            language=lang,
            variation_seed=effective_var,
        )
        data["procedural_fallback"] = True

    halluc = verify_and_correct_hallucinations(data.get("scenes", []), topic=title)
    data["scenes"] = halluc.get("scenes", data.get("scenes", []))
    if not halluc.get("verified"):
        print(f"  [SceneGenerator] Halüsinasyon uyarısı: {halluc.get('hallucination_issues')}")

    data["scenes"], narr_issues = validate_and_fix_scenes(data.get("scenes", []))
    if narr_issues:
        print(f"  [SceneGenerator] Kopuk cümle düzeltmesi: {narr_issues}")
        if lang == "en":
            retry_msg = (
                user_msg
                + "\n\nCRITICAL: Every scene narration field MUST be 1-2 COMPLETE English sentences (drama: 8-15 words, ending in . ! ?). "
                "Never leave trailing fragments or comma splices. Narration must be 100% natural, fluent English."
            )
        else:
            retry_msg = (
                user_msg
                + "\n\nKRITIK: Her sahne narration alanı 1-2 TAM cümle olmalı (drama: 8-12 kelime, . ! ? ile bitmeli). "
                "Asla yarım fiil ile bitme (ilan., et., de., ki.) veya devam fiili ile başlama (Etti, Ediyor). "
                "Her sahne kendi başına anlamlı olmalı — fiil iki sahneye bölünmemeli."
            )
        retry_providers = [successful_provider_tuple] if successful_provider_tuple else providers[:1]
        for provider_name, api_key, base_url, model_name in retry_providers:
            if data.get("scenes") and not any(scene_narration_issues((s.get("narration") or "")) for s in data["scenes"]):
                break
            print(f"  [{provider_name}] Kopuk cümle — sıkı retry")
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                params = dict(
                    model=model_name,
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": retry_msg}],
                    temperature=0.4, max_tokens=4000,
                )
                if "Gemini" in provider_name or "OpenAI" in provider_name:
                    params["response_format"] = {"type": "json_object"}
                resp = _call(client, params, provider_name=provider_name, model_name=model_name)
                raw = resp.choices[0].message.content.strip()
                if "```" in raw:
                    raw = raw.split("```json")[-1].split("```")[0].strip() if "```json" in raw else raw.split("```")[1].split("```")[0].strip()
                retry_data = _clean_json(raw)
                if retry_data and retry_data.get("scenes"):
                    data = retry_data
                    data["scenes"], narr_issues = validate_and_fix_scenes(data["scenes"])
                    break
            except Exception as e:
                print(f"  [SceneGenerator] Retry failed ({provider_name}): {e}")

    for s in data.get("scenes", []):
        if "narration" in s and s["narration"]:
            try:
                from services.niche_guardrails import clean_forbidden_phrases
                cleaned_narr = clean_forbidden_phrases(s["narration"], lang=lang)
                if cleaned_narr:
                    s["narration"] = cleaned_narr
            except Exception:
                pass
        if "search_query" in s and "search_queries" not in s:
            q = str(s.pop("search_query") or "").strip()
            s["search_queries"] = [q] if q else []
        if not scene_description_usable(s.get("scene_description") or ""):
            s["scene_description"] = synthesize_scene_description(s)

        from visuals.subject_lock import lock_scene_queries
        lock_scene_queries(s)
        if s.get("search_queries"):
            cleaned = enrich_cinematic_search_queries(s["search_queries"], mood=s.get("mood", "epic"))
            if cleaned:
                s["search_queries"] = cleaned

    scenes_list = data["scenes"]
    current_total = sum(float(s.get("duration") or 3.5) for s in scenes_list)
    if current_total <= 0:
        current_total = len(scenes_list) * 3.5
    target_total = max(SHORTS_MIN_DURATION, min(SHORTS_MAX_DURATION, current_total))
    if current_total < SHORTS_MIN_DURATION or current_total > SHORTS_MAX_DURATION:
        scale = target_total / current_total
        for s in scenes_list:
            s["duration"] = round(max(2.0, min(7.5, float(s.get("duration") or 3.5) * scale)), 1)

    try:
        from copyright_risk import scenes_need_fair_use_enforcement
        from .enrichment import enforce_fair_use_2_5s_rule
        if scenes_need_fair_use_enforcement(data.get("scenes", [])):
            data["scenes"] = enforce_fair_use_2_5s_rule(data.get("scenes", []), is_copyrighted_source=True)
            data["fair_use_2_5s_enforced"] = True
    except Exception:
        pass

    if len(data["scenes"]) < MIN_SCENE_COUNT:
        data["scenes"] = enforce_visual_cadence_14(data["scenes"], min_cadence=MIN_SCENE_COUNT)

    data["scenes"] = enrich_closing_gaze_queries(data["scenes"])
    data["scenes"] = avoid_consecutive_face_visuals(data["scenes"])
    data["scenes"] = enrich_continuous_motion_hints(data["scenes"])
    data["scenes"] = enrich_audio_visual_contrast_scenes(data["scenes"], niche_id=locked_niche or niche_type or "")
    data["scenes"] = enrich_numbered_rule_narration(data["scenes"], lang=lang)

    _hook_niche = locked_niche or niche_type
    data["niche_id"] = data.get("niche_id") or _hook_niche
    data = ensure_retention_hooks_on_plan(
        data, title, lang=lang, niche_type=_hook_niche, variation_attempt=variation_attempt, enable_outro=enable_outro
    )
    data = repair_post_hook_word_budget(data, max_words=_tts_word_cap())

    diversity = lint_plan_diversity(data)
    data["diversity_lint"] = diversity
    if diversity.get("warnings"):
        print(f"  [SceneGenerator] Diversity bildirimi: {diversity.get('warnings')}")

    if not plan_quality_usable(data.get("scenes") or []) and not data.get("procedural_fallback"):
        print("  [SceneGenerator] Post-hook plan kalitesi yetersiz — prosedürel fallback.")
        data = _generate_procedural_fallback_scenes(
            title, niche_type=locked_niche or niche_type, language=lang, variation_seed=variation_attempt
        )
        data["procedural_fallback"] = True
        data = ensure_retention_hooks_on_plan(
            data, title, lang=lang, niche_type=_hook_niche, variation_attempt=variation_attempt, enable_outro=enable_outro
        )
        data = repair_post_hook_word_budget(data, max_words=_tts_word_cap())

    total = sum(float(s.get("duration") or 3.5) for s in data["scenes"])
    target_total = max(SHORTS_MIN_DURATION, min(SHORTS_MAX_DURATION, total))
    if total < SHORTS_MIN_DURATION or total > SHORTS_MAX_DURATION:
        scale = target_total / max(total, 1.0)
        for s in data["scenes"]:
            s["duration"] = round(max(2.0, min(7.5, float(s.get("duration") or 3.5) * scale)), 1)

    data["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in data["scenes"] if (s.get("narration") or "").strip()
    )
    remaining = [i for i, s in enumerate(data["scenes"]) if scene_narration_issues(s.get("narration") or "")]
    if remaining:
        print(f"  [SceneGenerator] UYARI: {len(remaining)} sahne hâlâ kopuk cümle içeriyor")
    if format_fingerprint:
        data["format_fingerprint"] = format_fingerprint

    try:
        from hybrid_niches import enrich_plan_with_hybrid
        data = enrich_plan_with_hybrid(data, title, locked_niche or niche_type or "")
    except Exception:
        pass

    try:
        from craft import apply_human_craft
        data = apply_human_craft(
            data,
            title=title,
            niche_id=str(data.get("niche_id") or locked_niche or niche_type or ""),
            language=lang,
            variation=int(variation_attempt or 0),
        )
    except Exception as craft_exc:
        print(f"  [SceneGenerator] human_craft skip: {craft_exc}")

    data["language"] = lang
    try:
        from .narration_sense import repair_nonsensical_narration
        data = repair_nonsensical_narration(data, topic=clean_title or title, language=lang)
    except Exception as sense_exc:
        print(f"  [SceneGenerator] narration sense skip: {sense_exc}")

    try:
        from services.web_fact_researcher import scrub_unverified_claims
        data = scrub_unverified_claims(data, fact_snippets, lang=lang)
    except Exception as fact_scrub_exc:
        print(f"  [FactResearcher] claim scrub skip: {fact_scrub_exc}")

    try:
        from services.virality_evaluator import evaluate_script_virality
        audit = evaluate_script_virality(data.get("full_narration", ""), topic=title)
        data["virality_audit"] = audit
        print(
            f"  [ViralityAudit] Skor: {audit.get('score')}/100, "
            f"Tutarlı: {audit.get('is_coherent')}, Sinyaller: {audit.get('signals_detected')}"
        )
        if audit.get("issues"):
            print(f"  [ViralityAudit] Uyarılar: {audit.get('issues')}")
    except Exception as va_exc:
        print(f"  [ViralityAudit] skip: {va_exc}")

    data = repair_post_hook_word_budget(data, max_words=min(145, _tts_word_cap()))
    scenes_list = data.get("scenes") or []
    if scenes_list:
        total = sum(float(s.get("duration") or 4.0) for s in scenes_list)
        target_total = max(SHORTS_MIN_DURATION, min(SHORTS_MAX_DURATION, total))
        if total < SHORTS_MIN_DURATION or total > SHORTS_MAX_DURATION:
            scale = target_total / max(total, 1.0)
            for s in scenes_list:
                s["duration"] = round(max(2.0, min(7.5, float(s.get("duration") or 4.0) * scale)), 1)
        data["total_duration"] = round(sum(float(s.get("duration") or 0) for s in scenes_list), 2)

    if clean_continuity_context:
        data["series_continuity"] = {
            "context": clean_continuity_context,
            "applied": not bool(data.get("procedural_fallback")),
        }
    if reddit_post and locked_niche == "2_reddit_confessions":
        data["reddit_post"] = reddit_post

    return sanitize_plan_scene_descriptions(data)
