"""
Specialized script generators: Counter-Argument Dialectics and Reddit Story Rewriting.
"""

from typing import Union, Dict, Any
import config
from .prompts import (
    COUNTER_ARGUMENT_PROMPT_TR,
    COUNTER_ARGUMENT_PROMPT_EN,
    REDDIT_REWRITE_PROMPT_TR,
    REDDIT_REWRITE_PROMPT_EN
)
from .fallback import _generate_procedural_fallback_scenes


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
                params = dict(
                    model=model_name,
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                    temperature=0.7, max_tokens=4000
                )
                if "Gemini" in provider_name or "OpenAI" in provider_name:
                    params["response_format"] = {"type": "json_object"}
                resp = _call(client, params)
                raw = resp.choices[0].message.content.strip()
                data = _clean_json(raw)
                if data and "scenes" in data and len(data["scenes"]) >= 8:
                    data["title"] = title or data.get("title", "Reddit Hikayesi")
                    return data
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
