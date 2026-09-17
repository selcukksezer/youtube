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
            "Peki sizce bu iddia doğru mu? Fikrinizi yorumlarda paylaşın ve takipte kalın!"
        ]
    else:
        narrations = [
            f"Almost everything you have been told about {clean_topic} is a lie.",
            "Society convinces us that this is the only path to genuine success.",
            "However, groundbreaking data and historical facts prove the exact opposite.",
            "Looking closer reveals the subtle psychological trap hidden underneath.",
            "The top performers never follow this mainstream advice; they inverse it completely.",
            "Remember: following the herd guarantees nothing more than average results.",
            "Do you agree or disagree? Drop your thoughts in the comments and subscribe!"
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
    """
    if isinstance(source, dict):
        title = source.get("title", "")
        body = source.get("body", source.get("selftext", ""))
        text = f"{title}\n{body}".strip()
    else:
        text = str(source).strip()
        title = text.split("\n")[0][:60] if text else "Reddit Hikayesi"

    plan = _generate_procedural_fallback_scenes(title or "Bilinmeyen İtiraf", niche_type="2_reddit_confessions")
    return plan
