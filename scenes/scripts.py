"""
Specialized script generators: Counter-Argument Dialectics and Reddit Story Rewriting.
"""

import math
import re
from typing import Union, Dict, Any
import config
from .prompts import (
    COUNTER_ARGUMENT_PROMPT_TR,
    COUNTER_ARGUMENT_PROMPT_EN,
    REDDIT_REWRITE_PROMPT_TR,
    REDDIT_REWRITE_PROMPT_EN
)
from .fallback import _generate_procedural_fallback_scenes


_REDDIT_FRAGMENT_ENDING_RE = re.compile(
    r"(?:\b(?:etmek|olmak|bulmak|yapmak|görmek|öğrenmek|anlamak)\s*[.!?]?|"
    r"\bgözler(?:i)?\s+önüne\s*[.!?]?)$",
    re.IGNORECASE,
)
_REDDIT_UNFINISHED_POSSESSIVE_RE = re.compile(
    r"\b(?:sakladığı|gizlediği|bulduğu|okuduğu|gördüğü|incelediği)\s+"
    r"\w+(?:\s+\w+)?(?:ların|lerin)\s*[.!?]?$",
    re.IGNORECASE,
)
_REDDIT_NUMBERED_FILLER_RE = re.compile(
    r"\b(?:ilk|ikinci|üçüncü|dördüncü)\b.{0,28}\b(?:detay|nokta|bulgu|işaret)\b",
    re.IGNORECASE,
)
_REDDIT_TITLE_STOPWORDS = {
    "ama", "artık", "bunu", "bir", "bu", "da", "de", "etmek", "için", "ile",
    "ve", "var", "ben", "the", "and", "for", "with", "was", "were", "my",
}


def _reddit_script_issues(plan: Dict[str, Any]) -> list[str]:
    """Reject Reddit scripts with obvious title echoes, fragments, or template repetition."""
    from .narration_validate import normalize_narration_for_validation, scene_narration_issues

    scenes = plan.get("scenes") or []
    if len(scenes) < 8:
        return ["too_few_scenes"]

    issues = []
    for index, scene in enumerate(scenes):
        narration = normalize_narration_for_validation(str(scene.get("narration") or ""))
        scene_issues = scene_narration_issues(narration, normalized=True)
        if scene_issues:
            issues.append(f"scene_{index + 1}:{'|'.join(scene_issues)}")
        if _REDDIT_FRAGMENT_ENDING_RE.search(narration):
            issues.append(f"scene_{index + 1}:incomplete_clause")
        if _REDDIT_UNFINISHED_POSSESSIVE_RE.search(narration):
            issues.append(f"scene_{index + 1}:unfinished_possessive")

    narration = " ".join(
        normalize_narration_for_validation(str(scene.get("narration") or ""))
        for scene in scenes
    )
    if len(_REDDIT_NUMBERED_FILLER_RE.findall(narration)) > 1:
        issues.append("repetitive_numbered_filler")

    title = str(plan.get("title") or "")
    title_words = {
        word.casefold()
        for word in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿĞğİıŞşÜüÇç]+", title)
        if len(word) > 2 and word.casefold() not in _REDDIT_TITLE_STOPWORDS
    }
    if title_words and scenes:
        hook_words = {
            word.casefold()
            for word in re.findall(
                r"[A-Za-zÀ-ÖØ-öø-ÿĞğİıŞşÜüÇç]+",
                str(scenes[0].get("narration") or ""),
            )
        }
        overlap = len(title_words & hook_words)
        if len(title_words) >= 5 and overlap / len(title_words) >= 0.6:
            issues.append("hook_repeats_title")
    return issues


def generate_counter_argument_script(topic: str, lang: str = "tr") -> Dict[str, Any]:
    """
    Generates a thesis-antithesis counter argument video script.
    """
    is_tr = (lang == "tr" or config.LANGUAGE == "tr")
    prompt = COUNTER_ARGUMENT_PROMPT_TR if is_tr else COUNTER_ARGUMENT_PROMPT_EN
    
    # Try procedural generation by default or AI
    clean_topic = topic.strip()
    if is_tr:
        narrations = [
            f"Herkes {clean_topic} konusunda tamamen yanılıyor.",
            "Toplumun bize dayattığı en büyük yanılgı, bu durumun her zaman olumlu sonuç verdiği inancıdır.",
            "Oysa bilimsel araştırmalar ve tarihsel gerçekler tam tersini gösteriyor.",
            "Derine indiğinizde, bu yaklaşımın insan psikolojisi üzerinde nasıl bir tahribat yarattığını görüyorsunuz.",
            "Asıl kazananlar, herkesin koştuğu bu yöne değil, tam zıddına odaklananlardır.",
            "Unutmayın, kalabalıkları takip etmek sizi sadece ortalama yapar.",
            "Peki bu iddianın hangi kısmı sana hâlâ mantıklı geliyor? Cevabı başa döndüğünde daha net göreceksin."
        ]
    else:
        narrations = [
            f"Almost everything you have been told about {clean_topic} is a lie.",
            "Society convinces us that this is the only path to genuine success.",
            "However, groundbreaking data and historical facts prove the exact opposite.",
            "Looking closer reveals the subtle psychological trap hidden underneath.",
            "The top performers never follow this mainstream advice; they inverse it completely.",
            "Remember: following the herd guarantees nothing more than average results.",
            "Which part of this claim still feels convincing? Rewatch the opening and compare it with the evidence."
        ]

    scenes = []
    for i, txt in enumerate(narrations):
        scenes.append({
            "scene_number": i + 1,
            "narration": txt,
            "scene_description": f"Dramatic contrasting cinematic footage illustrating {clean_topic} argument {i+1}",
            "search_queries": [f"{clean_topic} cinematic", "dramatic lighting shadow", "person thinking deep"],
            "duration": round(60.0 / len(narrations), 1),
            "mood": "dramatic"
        })

    return {
        "title": clean_topic,
        "visual_theme": "dark contrast dramatic argument",
        "full_narration": " ".join(narrations),
        "scenes": scenes
    }


def generate_reddit_rewrite_script(source: Union[str, Dict[str, Any]], lang: str = "tr") -> Dict[str, Any]:
    """
    Transforms Reddit post / confession into an engaging, fair-use compliant Shorts plan.
    Attempts AI generation first, falling back to rich procedural story reconstruction.
    """
    if isinstance(source, dict):
        title = source.get("title", "")
        body = source.get("body", source.get("selftext", ""))
    else:
        text = str(source).strip()
        lines = text.split("\n", 1)
        title = lines[0][:80] if lines else "Reddit Hikayesi"
        body = lines[1] if len(lines) > 1 else ""

    is_tr = (lang == "tr" or config.LANGUAGE == "tr")
    prompt = REDDIT_REWRITE_PROMPT_TR if is_tr else REDDIT_REWRITE_PROMPT_EN
    user_msg = (
        f"Aşağıdaki Reddit gönderisini viral, merak uyandırıcı, 1. tekil şahıs ağzından 14 sahneli bir YouTube Shorts senaryosuna dönüştür:\n\nBAŞLIK: {title}\nİÇERİK: {body}"
        if is_tr
        else f"Transform this Reddit post into an engaging, 1st-person 14-scene YouTube Shorts script:\n\nTITLE: {title}\nBODY: {body}"
    )

    # Try AI providers if available
    try:
        from .generator import _call, _clean_json
        from openai import OpenAI
        providers = []
        if getattr(config, "AI_PROVIDER", None) and getattr(config, "AI_API_KEY", None):
            providers.append((config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL))
        if hasattr(config, "_P"):
            for n, k, u, m in config._P:
                if k and (n != getattr(config, "AI_PROVIDER", None)):
                    providers.append((n, k, u, m))

        for provider_name, api_key, base_url, model_name in providers:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                retry_message = user_msg
                for attempt in range(2):
                    params = dict(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": retry_message},
                        ],
                        temperature=0.7 if attempt == 0 else 0.4,
                        max_tokens=4000,
                    )
                    if "Gemini" in provider_name or "OpenAI" in provider_name:
                        params["response_format"] = {"type": "json_object"}
                    resp = _call(client, params)
                    raw = resp.choices[0].message.content.strip()
                    data = _clean_json(raw)
                    if not data or "scenes" not in data or len(data["scenes"]) < 8:
                        break

                    data["title"] = title or data.get("title", "Reddit Hikayesi")
                    issues = _reddit_script_issues(data)
                    if not issues:
                        return data
                    print(
                        f"  [Reddit Script] AI taslağı reddedildi ({', '.join(issues)}); "
                        f"düzeltme denemesi {attempt + 1}/2"
                    )
                    if attempt == 0:
                        retry_message = (
                            f"{user_msg}\n\nÖnceki taslak şu kalite sorunları nedeniyle reddedildi: "
                            f"{', '.join(issues)}. Kaynağı yeniden incele, cümleleri tamamla ve yalnızca "
                            "düzeltilmiş JSON senaryoyu döndür."
                        )
            except Exception:
                continue
    except Exception:
        pass

    # Intelligent procedural fallback
    plan = _generate_procedural_fallback_scenes(
        title or "Bilinmeyen İtiraf",
        niche_type="2_reddit_confessions",
        raw_body=body,
        language=lang,
    )
    return plan
