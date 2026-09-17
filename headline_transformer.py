"""Original question-style transformations for news headlines."""
import random

from openai import OpenAI

import config
from scene_generator import _call, _clean_json


_QUESTION_TEMPLATES_TR = [
    lambda title: f"Neden kimse {title.rstrip('.')} hakkında konuşmuyor? #shorts",
    lambda title: f"{title.rstrip('.')} gerçekten doğru mu? #shorts",
    lambda title: f"Bu haberi duydunuz mu? {title.rstrip('.')} #shorts",
    lambda title: f"{title.rstrip('.')} — ve kimse fark etmedi #shorts",
    lambda title: f"Peki bunun ardında ne var? {title.rstrip('.')} #shorts",
    lambda title: f"{title.rstrip('.')} — siz ne düşünüyorsunuz? #shorts",
]
_QUESTION_TEMPLATES_EN = [
    lambda title: f"Why is nobody talking about {title.rstrip('.')}? #shorts",
    lambda title: f"Is {title.rstrip('.')} actually true? #shorts",
    lambda title: f"Did you hear about this? {title.rstrip('.')} #shorts",
    lambda title: f"{title.rstrip('.')} — and nobody noticed #shorts",
    lambda title: f"What's really behind {title.rstrip('.')}? #shorts",
    lambda title: f"{title.rstrip('.')} — what do you think? #shorts",
]
_NEWS_TO_QUESTION_PROMPT = """Sen bir YouTube Shorts başlık uzmanısın.
Verilen haber ajansı başlığını, izleyicide merak, şok veya soru uyandıran viral bir Shorts başlığına dönüştür.

Kurallar:
1. Haber ajansı başlığını birebir kullanma.
2. Merak/şok/soru/gizem stratejilerinden birini seç.
3. #Shorts etiketi ekle.
4. Maksimum 70 karakter.
5. Emoji KULLANMA.

SADECE JSON:
{"question_title": "...", "strategy": "curiosity|shock|question|mystery"}"""


def convert_headline_to_question(news_headline: str, lang: str = "tr", use_ai: bool = True) -> dict:
    """Converts a news headline into an original, question-led Shorts title."""
    templates = _QUESTION_TEMPLATES_TR if lang == "tr" else _QUESTION_TEMPLATES_EN
    raw_transformed = random.choice(templates)(news_headline)
    if len(raw_transformed) > 70:
        base_part = raw_transformed.replace("#shorts", "").strip()[:61].rstrip()
        rule_based = f"{base_part} #shorts"
    else:
        rule_based = raw_transformed
    result = {"question_title": rule_based, "strategy": "rule_based", "original": news_headline}
    if not use_ai or not config.AI_PROVIDER or not config.AI_API_KEY:
        print(f"  [Item 122] Kural tabanlı dönüşüm: '{rule_based}'")
        return result
    print("  [Item 122] Haber başlığı AI ile soru formatına çevriliyor...")
    try:
        client = OpenAI(api_key=config.AI_API_KEY, base_url=config.AI_BASE_URL)
        params = {"model": config.AI_MODEL, "messages": [{"role": "system", "content": _NEWS_TO_QUESTION_PROMPT}, {"role": "user", "content": f"Haber başlığı: {news_headline}\nDil: {'Türkçe' if lang == 'tr' else 'English'}"}], "temperature": 0.75, "max_tokens": 200}
        if "Gemini" in config.AI_PROVIDER or "OpenAI" in config.AI_PROVIDER:
            params["response_format"] = {"type": "json_object"}
        data = _clean_json(_call(client, params).choices[0].message.content.strip())
        if data and "question_title" in data:
            return {"question_title": data["question_title"][:70], "strategy": data.get("strategy", "ai_generated"), "original": news_headline}
    except Exception as error:
        print(f"    [Item 122] AI hatası: {error}. Kural tabanlı fallback.")
    return result


def batch_convert_headlines(headlines: list, lang: str = "tr") -> list:
    """Converts headlines with rotating rule-based strategies."""
    templates = _QUESTION_TEMPLATES_TR if lang == "tr" else _QUESTION_TEMPLATES_EN
    used_strategies, results = [], []
    for headline in headlines:
        available = [index for index in range(len(templates)) if index not in used_strategies]
        if not available:
            used_strategies.clear()
            available = list(range(len(templates)))
        index = random.choice(available)
        used_strategies.append(index)
        results.append({"question_title": templates[index](headline)[:70], "strategy": f"template_{index}", "original": headline})
    print(f"  [Item 122] {len(results)} haber başlığı soru formatına dönüştürüldü.")
    return results