"""
Core scene generator with multi-provider AI fallback and post-processing filters.
"""

import json
import os
import re
from openai import OpenAI
import config
from api_models import validate_generated_plan_errors
from .prompts import get_rotated_system_prompt, advance_prompt_rotation, PROMPT_TR, PROMPT_EN
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


def _gemini_script_circuit_open() -> bool:
    try:
        from system_resilience import circuit_breaker
        return not circuit_breaker.can_execute("gemini_script")
    except Exception:
        return False


def _record_gemini_script_outcome(provider_name: str, model_name: str, err=None) -> None:
    is_gemini = "Gemini" in provider_name or "gemma" in (model_name or "").lower()
    if not is_gemini:
        return
    try:
        from system_resilience import circuit_breaker
        if err is None:
            circuit_breaker.record_success("gemini_script")
            return
        msg = str(err)
        if any(tok in msg for tok in ("429", "quota", "Quota", "rate limit", "RESOURCE_EXHAUSTED")):
            circuit_breaker.recovery_timeout = 1800.0
            s = circuit_breaker._get_service("gemini_script")
            s["failure_count"] = circuit_breaker.failure_threshold
            s["state"] = circuit_breaker.STATE_OPEN
            print("  [CircuitBreaker] gemini_script AÇILDI (429/kota) — sonraki sağlayıcıya geç")
        circuit_breaker.record_failure("gemini_script", msg)
    except Exception:
        pass


def _call(client, params, *, provider_name: str = "", model_name: str = ""):
    try:
        resp = client.chat.completions.create(**params)
        _record_gemini_script_outcome(provider_name, model_name)
        return resp
    except Exception as e:
        _record_gemini_script_outcome(provider_name, model_name, e)
        if "response_format" in params:
            del params["response_format"]
            return client.chat.completions.create(**params)
        raise e


_SCHEMA_RETRY_HINT = (
    "\n\nSCHEMA: Return a JSON object with a non-empty 'scenes' array. "
    "Each scene MUST include 'narration' (non-empty string) and either "
    "'search_queries' (string array) or 'scene_description'. "
    "Optional 'duration' must be a positive number."
)


def _schema_valid(data) -> bool:
    return not validate_generated_plan_errors(data)


def _parse_provider_json(raw: str):
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return _clean_json(raw)


def _clean_json(text):
    if not text:
        return None
    text = re.sub(r'//.*?\n', '\n', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


def _build_competitor_fingerprint_block(fp: dict, lang: str = "tr") -> str:
    """P2-04: inject trend/content-gap competitor format into system prompt."""
    if not fp:
        return ""
    scene_count = int(fp.get("scene_count") or 12)
    scene_count = max(MIN_SCENE_COUNT, min(16, scene_count))
    hook_style = fp.get("hook_style") or "Gizem / Merak Kancası"
    avg_dur = float(fp.get("avg_scene_duration") or 4.0)
    if lang == "en":
        return (
            f"\n\nCOMPETITOR FORMAT FINGERPRINT (mirror this viral structure — mandatory):\n"
            f"- Target scene count: {scene_count}\n"
            f"- Hook style: {hook_style}\n"
            f"- Average scene duration: {avg_dur}s\n"
            f"- Match competitor pacing and hook energy while keeping original narration."
        )
    return (
        f"\n\nRAKİP FORMAT FİNGERPRINT (viral yapıyı yansıt — zorunlu):\n"
        f"- Hedef sahne sayısı: {scene_count}\n"
        f"- Kanca stili: {hook_style}\n"
        f"- Ortalama sahne süresi: {avg_dur}s\n"
        f"- Rakip tempo ve kanca enerjisini koruyarak özgün anlatım yaz."
    )


def generate_scenes(
    title: str,
    niche_type: str = None,
    language: str = None,
    format_fingerprint: dict = None,
    variation_attempt: int = 0,
) -> dict:
    lang = language or getattr(config, "LANGUAGE", "tr")
    clean_title = sanitize_topic_title(title)
    try:
        from database import get_video_stats
        stats = get_video_stats()
        total_renders = int(stats.get("total_completed") or 0)
        if total_renders > 0 and total_renders % 20 == 0:
            advance_prompt_rotation(steps=1)
    except Exception:
        pass

    if variation_attempt > 0:
        advance_prompt_rotation(steps=variation_attempt)
    try:
        from director.visual_intent import resolve_niche_from_topic
        locked_niche = resolve_niche_from_topic(title, niche_type or "1_news_flash")
    except Exception:
        locked_niche = niche_type or "1_news_flash"
    force_fb = os.environ.get("SHORTS_FORCE_PROCEDURAL_FALLBACK", "").strip().lower() in {
        "1", "true", "yes", "on",
    }
    try:
        from niche_templates import get_niche_prompt
        prompt = get_niche_prompt(locked_niche, title, language=lang)
        if variation_attempt > 0:
            prompt = (
                prompt
                + f"\n\nVARYASYON #{variation_attempt + 1}: '{title}' konusuna özgü benzersiz "
                "anlatım yaz; önceki videolardaki kalıp cümleleri tekrarlama."
            )
    except Exception:
        prompt = get_rotated_system_prompt(
            base_lang=lang, force_variant=variation_attempt % 3
        )

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

    if lang == "en":
        user_msg = (
            f"Create a high-retention English YouTube Shorts video script for this topic: '{clean_title}'.\n"
            f"Original title context (hashtags stripped): '{title}'.\n"
            f"CRITICAL REQUIREMENT: The 'narration' field in EVERY scene MUST be written 100% in fluent, natural ENGLISH. "
            f"Each narration MUST be at least 12 complete words (1-2 full sentences) — never mood labels, dots, or emoji-only placeholders. "
            f"Each scene_description MUST be a concrete English visual sentence, never a placeholder. "
            f"Do NOT output Turkish narration. Translate and adapt the topic into an immersive English script."
        )
    else:
        user_msg = (
            f"Bu başlık için Türkçe YouTube Shorts senaryosu oluştur: '{clean_title}'.\n"
            f"Orijinal başlık (hashtag/emojisiz): '{title}'.\n"
            f"KRİTİK: Her sahnenin 'narration' alanı en az 12 kelimelik TAM Türkçe cümle(ler) olmalı; "
            f"sadece mood etiketi, nokta veya emoji placeholder YASAK. "
            f"scene_description gerçek İngilizce görsel cümle olmalı — placeholder YASAK. "
            f"8-16 sahne, toplam 38-60 saniye; konu ne kadar istiyorsa o kadar, 60'ı aşma."
        )

    # Build fallback provider chain
    providers = []
    # Primary configured provider first
    if getattr(config, "AI_PROVIDER", None) and getattr(config, "AI_API_KEY", None):
        providers.append((config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL))
        # If Gemini, add lite and flash variants as instant fallbacks
        if config.AI_PROVIDER == "Gemini":
            for alt_m in ["gemini-flash-lite-latest", "gemma-4-26b-a4b-it", "gemini-3.6-flash"]:
                if alt_m != config.AI_MODEL:
                    providers.append(("Gemini (" + alt_m + ")", config.AI_API_KEY, config.AI_BASE_URL, alt_m))

    # Other available providers in config._P
    if hasattr(config, "_P"):
        for n, k, u, m in config._P:
            if k and (n != getattr(config, "AI_PROVIDER", None)):
                providers.append((n, k, u, m))

    last_error = None
    data = None

    if force_fb:
        providers = []
        last_error = "SHORTS_FORCE_PROCEDURAL_FALLBACK"

    for provider_name, api_key, base_url, model_name in providers:
        if ("Gemini" in provider_name or "gemma" in (model_name or "").lower()) and _gemini_script_circuit_open():
            print(f"  [{provider_name}] gemini_script circuit OPEN — atlanıyor")
            continue
        print(f"  [{provider_name}] Senaryo üretiliyor: '{title}'")
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            params = dict(
                model=model_name,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                temperature=0.7, max_tokens=4000,
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
                print(f"  [{provider_name}] OK: Senaryo basariyla uretildi")
                break
        except Exception as e:
            print(f"  [UYARI] {provider_name} servisi hata verdi: {e}. Sıradaki AI modeline/sağlayıcısına geçiliyor...")
            last_error = e

    if data and data.get("scenes") and not plan_quality_usable(data.get("scenes", [])):
        print(
            "  [SceneGenerator] AI plan kalitesi düşük (kısa anlatım/placeholder görsel) — "
            "prosedürel fallback devreye alınıyor."
        )
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
            variation_seed=variation_attempt,
        )
        data["procedural_fallback"] = True

    halluc = verify_and_correct_hallucinations(data.get("scenes", []), topic=title)
    data["scenes"] = halluc.get("scenes", data.get("scenes", []))
    if not halluc.get("verified"):
        print(f"  [SceneGenerator] Halüsinasyon uyarısı: {halluc.get('hallucination_issues')}")

    data["scenes"], narr_issues = validate_and_fix_scenes(data.get("scenes", []))
    if narr_issues:
        print(f"  [SceneGenerator] Kopuk cümle düzeltmesi: {narr_issues}")
        # One strict retry when provider chain still has headroom
        retry_msg = (
            user_msg
            + "\n\nKRITIK: Her sahne narration alanı 1-2 TAM cümle olmalı (drama: 8-12 kelime, . ! ? ile bitmeli). "
            "Asla yarım fiil ile bitme (ilan., et., de., ki.) veya devam fiili ile başlama (Etti, Ediyor). "
            "Her sahne kendi başına anlamlı olmalı — fiil iki sahneye bölünmemeli."
        )
        for provider_name, api_key, base_url, model_name in providers:
            if data.get("scenes") and not any(
                scene_narration_issues((s.get("narration") or "")) for s in data["scenes"]
            ):
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
        if "search_query" in s and "search_queries" not in s:
            q = s.pop("search_query")
            w = q.split()
            s["search_queries"] = [q, " ".join(w[:2]) if len(w) > 2 else q, w[0] if w else "nature"]
        if not scene_description_usable(s.get("scene_description") or ""):
            s["scene_description"] = synthesize_scene_description(s)

        # Enrich search queries with cinematic adjectives (Item 89)
        if "search_queries" in s:
            s["search_queries"] = enrich_cinematic_search_queries(s["search_queries"], mood=s.get("mood", "epic"))

    # Preserve AI-assigned pacing; scale total to 38-60s Shorts band (Madde 494)
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
            data["scenes"] = enforce_fair_use_2_5s_rule(
                data.get("scenes", []), is_copyrighted_source=True
            )
            data["fair_use_2_5s_enforced"] = True
    except Exception:
        pass

    if variation_attempt >= 1:
        try:
            from .enrichment import apply_alternate_topic_angle
            data = apply_alternate_topic_angle(data, clean_title, lang=lang)
        except Exception:
            pass

    # Pad thin plans toward minimum cadence only when very short (Madde 88, flexible 8-16)
    if len(data["scenes"]) < MIN_SCENE_COUNT:
        data["scenes"] = enforce_visual_cadence_14(data["scenes"], min_cadence=MIN_SCENE_COUNT)

    # Item 226: Son sahne kapanış bakış stok ipuçları
    data["scenes"] = enrich_closing_gaze_queries(data["scenes"])

    # Item 247: Arka arkaya yüz/portre stok tekrarını kır
    data["scenes"] = avoid_consecutive_face_visuals(data["scenes"])

    # Item 271: Statik kare riski — uzun sahnelerde handheld motion ipuçları
    data["scenes"] = enrich_continuous_motion_hints(data["scenes"])

    # Item 273: Sakin ses + şok görsel (climax sahnesi) — skip if niche excludes those tokens
    data["scenes"] = enrich_audio_visual_contrast_scenes(data["scenes"], niche_id=locked_niche or niche_type or "")

    # Item 241: Numaralandırılmış kural hiyerarşisi
    data["scenes"] = enrich_numbered_rule_narration(data["scenes"], lang=lang)

    # Items 202-204, 209-210, 239, 244, 248, 257 (+ Item 240 trigger name)
    _hook_niche = locked_niche or niche_type
    data["niche_id"] = data.get("niche_id") or _hook_niche
    data = ensure_retention_hooks_on_plan(
        data, title, lang=lang, niche_type=_hook_niche, variation_attempt=variation_attempt
    )

    # Batch D — soft word budget before Director hard condense (~60s Shorts headroom)
    data = repair_post_hook_word_budget(data, max_words=172)

    # Batch E — mood/query diversity linter (regenerate weak AI plans)
    diversity = lint_plan_diversity(data)
    data["diversity_lint"] = diversity
    if diversity.get("weak") and not data.get("procedural_fallback"):
        print(
            f"  [SceneGenerator] Diversity zayıf ({diversity.get('warnings')}) — "
            "prosedürel fallback devreye alınıyor."
        )
        data = _generate_procedural_fallback_scenes(
            title,
            niche_type=locked_niche or niche_type,
            language=lang,
            variation_seed=variation_attempt,
        )
        data["procedural_fallback"] = True
        data = ensure_retention_hooks_on_plan(
            data, title, lang=lang, niche_type=_hook_niche, variation_attempt=variation_attempt
        )
        data = repair_post_hook_word_budget(data, max_words=172)

    # Final quality gate — regenerate if hooks/budget left stub narrations
    if not plan_quality_usable(data.get("scenes") or []) and not data.get("procedural_fallback"):
        print("  [SceneGenerator] Post-hook plan hâlâ zayıf — prosedürel fallback.")
        data = _generate_procedural_fallback_scenes(
            title,
            niche_type=locked_niche or niche_type,
            language=lang,
            variation_seed=variation_attempt,
        )
        data["procedural_fallback"] = True
        data = ensure_retention_hooks_on_plan(
            data, title, lang=lang, niche_type=_hook_niche, variation_attempt=variation_attempt
        )
        data = repair_post_hook_word_budget(data, max_words=172)

    # Final soft normalization — preserve relative pacing within 38-60s
    total = sum(float(s.get("duration") or 3.5) for s in data["scenes"])
    target_total = max(SHORTS_MIN_DURATION, min(SHORTS_MAX_DURATION, total))
    if total < SHORTS_MIN_DURATION or total > SHORTS_MAX_DURATION:
        scale = target_total / max(total, 1.0)
        for s in data["scenes"]:
            s["duration"] = round(max(2.0, min(7.5, float(s.get("duration") or 3.5) * scale)), 1)
        total = sum(s["duration"] for s in data["scenes"])

    total = sum(s["duration"] for s in data["scenes"])
    data["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in data["scenes"] if (s.get("narration") or "").strip()
    )
    remaining = [
        i for i, s in enumerate(data["scenes"])
        if scene_narration_issues(s.get("narration") or "")
    ]
    if remaining:
        print(f"  [SceneGenerator] UYARI: {len(remaining)} sahne hâlâ kopuk cümle içeriyor")
    if format_fingerprint:
        data["format_fingerprint"] = format_fingerprint

    try:
        from hybrid_niches import enrich_plan_with_hybrid
        data = enrich_plan_with_hybrid(data, title, niche_type or "")
    except Exception:
        pass

    print(f"  [SceneGenerator] Sahne Sayısı: {len(data['scenes'])}, Toplam Süre: {total}s | Tema: {data.get('visual_theme', '-')}")
    return sanitize_plan_scene_descriptions(data)
