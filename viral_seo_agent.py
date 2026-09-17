import json
from openai import OpenAI
import config
from scene_generator import _call, _clean_json

SEO_PROMPT = """Sen profesyonel bir YouTube SEO Uzmanı ve Viral İçerik Stratejistisin.
Verilen YouTube Shorts anahtar kelimesi/başlığı için şu bilgileri üret:

1. "hook_text": İzleyiciyi ilk 3 saniyede yakalayacak çok güçlü, merak uyandıran, duygusal veya şok edici bir kanca cümlesi (en fazla 15 kelime).
2. "seo_title": Tıklama oranını (CTR) maksimize edecek, arama motorlarına uyumlu, ilgi çekici bir video başlığı (en fazla 70 karakter).
3. "seo_description": Videonun bulunabilirliğini artıracak, anahtar kelime zengini, 3 paragraf açıklama metni. İçinde "Abone olmayı unutmayın" gibi eylem çağrıları da barındırsın.
4. "tags": Virgülle ayrılmış, en çok aranan 15 yüksek hacimli hashtag/etiket.

SADECE JSON FORMATINDA YANIT VER:
{"hook_text": "...", "seo_title": "...", "seo_description": "...", "tags": ["a", "b", "c"]}
"""

def generate_viral_seo_metadata(keyword: str) -> dict:
    fallback = {
        "hook_text": f"{keyword} hakkında kimsenin bilmediği gerçekler!",
        "seo_title": f"{keyword} | İnanılmaz Bilgiler #shorts",
        "seo_description": f"{keyword} hakkında şok edici detaylar ve gizli kalmış sırlar bu videoda. İzlediğiniz için teşekkürler, abone olmayı unutmayın! #shorts #{keyword.replace(' ', '')}",
        "tags": ["shorts", "bilgi", keyword.replace(" ", ""), "ilginc", "viral"]
    }

    if not config.AI_PROVIDER or not config.AI_API_KEY:
        return fallback

    print(f"\n  [Viral SEO Agent] '{keyword}' için SEO ve Kanca verileri üretiliyor...")

    try:
        client = OpenAI(api_key=config.AI_API_KEY, base_url=config.AI_BASE_URL)
        params = dict(
            model=config.AI_MODEL,
            messages=[
                {"role": "system", "content": SEO_PROMPT},
                {"role": "user", "content": f"Anahtar kelime: {keyword}"}
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        if "Gemini" in config.AI_PROVIDER or "OpenAI" in config.AI_PROVIDER:
            params["response_format"] = {"type": "json_object"}

        resp = _call(client, params)
        raw = resp.choices[0].message.content.strip()
        data = _clean_json(raw)

        if data and "seo_title" in data:
            print(f"    [OK] Viral SEO verileri başarıyla üretildi.")
            return data
    except Exception as e:
        print(f"    [UYARI] Viral SEO Agent hatası: {e}. Fallback kullanılıyor.")

    return fallback
