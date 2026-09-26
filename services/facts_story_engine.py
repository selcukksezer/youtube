"""
Facts & Educational Story Engine.
Adapted from ShortGPT (facts_short_engine.py + facts_generator.yaml).
Generates engaging, coherent, slop-free factual shorts (3 facts / weird history / science)
under 50 seconds verbal without artificial template distortion.
"""
import json
import re
from typing import Any, Dict, List, Optional
import config
from services.timed_visual_matcher import clean_query

FACTS_SYSTEM_PROMPT = """You are an expert scriptwriter for an edutainment YouTube Shorts channel.
You specialize in captivating, mind-blowing facts and historical/scientific secrets.
Your scripts are strictly less than 50 seconds verbally (around 120-140 words total).
They are 100% coherent, original, and free of AI clichés.

CRITICAL RULES:
1. NO filler phrases like "In this video...", "Let's explore...", "Keep this in mind", "Tek bir ayrıntı yeter".
2. NO fake quotes from historical figures not directly related to the topic.
3. Every sentence must be a complete, grammatically sound sentence that naturally flows into the next.
4. Structure:
   - Cold Hook (1-2 sentences): A shocking statement or question that stops the scroll immediately.
   - Fact 1 & 2 (Context & Mechanism): Intriguing, concrete facts with numbers or specific details.
   - Fact 3 (The Twist / Climax): The most unexpected or counter-intuitive revelation.
   - Final Thought: A memorable conclusion or open question for comments.
"""

FACTS_USER_TEMPLATE_TR = """Bu konu hakkında yüksek etkileşimli, 50 saniyelik bir Türkçe Shorts senaryosu yaz:
Konu: "{topic}"

Çıktı formatı SADECE geçerli JSON olmalıdır:
{{
  "title": "{topic}",
  "hook": "İlk 3 saniye kancası",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Kanca cümlesi. Dikkat çeken ilk iddia.",
      "scene_description": "Concrete English visual description",
      "search_queries": ["query one", "query two", "query three"],
      "duration": 5.0
    }}
  ]
}}
"""

FACTS_USER_TEMPLATE_EN = """Write a high-retention 50-second English YouTube Shorts script on this topic:
Topic: "{topic}"

Output format MUST be valid JSON only:
{{
  "title": "{topic}",
  "hook": "Opening hook line",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "Opening hook sentence. Gripping first claim.",
      "scene_description": "Concrete English visual description",
      "search_queries": ["query one", "query two", "query three"],
      "duration": 5.0
    }}
  ]
}}
"""


class FactsStoryEngine:
    """Generates captivating, slop-free educational and facts shorts scripts."""

    @staticmethod
    def generate_facts_script(topic: str, language: str = "tr") -> Dict[str, Any]:
        is_tr = language.lower().startswith("tr")
        user_prompt = FACTS_USER_TEMPLATE_TR.format(topic=topic) if is_tr else FACTS_USER_TEMPLATE_EN.format(topic=topic)

        try:
            from openai import OpenAI
            api_key = config.AI_API_KEY
            base_url = config.AI_BASE_URL
            model = config.AI_MODEL

            if not api_key:
                raise ValueError("No AI API key configured")

            client = OpenAI(api_key=api_key, base_url=base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": FACTS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                response_format={"type": "json_object"} if "gemini" in model.lower() or "gpt" in model.lower() else None,
            )

            raw = resp.choices[0].message.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = json.loads(raw)
            scenes = data.get("scenes", [])
            for sc in scenes:
                raw_qs = sc.get("search_queries", [])
                sc["search_queries"] = [clean_query(q) for q in raw_qs if clean_query(q)][:3]

            data["full_narration"] = " ".join(
                str(s.get("narration") or "").strip() for s in scenes
            )
            return data

        except Exception as exc:
            print(f"[FactsStoryEngine] LLM generation note: {exc}, using procedural factual fallback")
            return FactsStoryEngine._procedural_fallback(topic, is_tr)

    @staticmethod
    def _procedural_fallback(topic: str, is_tr: bool) -> Dict[str, Any]:
        """Clean fallback without slop or fake quotes."""
        if is_tr:
            scenes = [
                {
                    "scene_number": 1,
                    "narration": f"Çoğu insanın {topic} hakkında bildiği şeylerin neredeyse tamamı eksik ya da yanlış.",
                    "scene_description": f"Antique books and documents on a desk with warm light",
                    "search_queries": [clean_query(topic), "ancient manuscript archive", "library books dark"],
                    "duration": 5.0,
                },
                {
                    "scene_number": 2,
                    "narration": f"Tarihsel ve bilimsel kayıtlar incelendiğinde, bu konunun arkasındaki ilk büyük sır ortaya çıkıyor.",
                    "scene_description": "Person examining documents with magnifying glass in archive",
                    "search_queries": ["magnifying glass paper", "detective investigation desk", "vintage map table"],
                    "duration": 5.5,
                },
                {
                    "scene_number": 3,
                    "narration": f"Uzmanların asıl şaşırdığı nokta ise, bu gerçeğin yüzyıllar boyunca göz önünde saklanmış olmasıydı.",
                    "scene_description": "Close up eyes looking shocked in dramatic lighting",
                    "search_queries": ["shocked eyes closeup", "whispering shadow darkness", "vault door opening"],
                    "duration": 5.5,
                },
                {
                    "scene_number": 4,
                    "narration": f"Peki sizce {topic} konusunda toplumun göremediği en büyük ayrıntı ne olabilir?",
                    "scene_description": "Cinematic sunset over ancient stone temple",
                    "search_queries": ["sunset horizon sea", "ancient stone temple", "thinking person silhouette"],
                    "duration": 5.0,
                },
            ]
        else:
            scenes = [
                {
                    "scene_number": 1,
                    "narration": f"Almost everything you've ever been told about {topic} is either incomplete or completely backward.",
                    "scene_description": "Antique books and documents on a desk with warm light",
                    "search_queries": [clean_query(topic), "ancient books", "dark library desk"],
                    "duration": 5.0,
                },
                {
                    "scene_number": 2,
                    "narration": f"When you look at the primary historical records, a very different picture immediately begins to emerge.",
                    "scene_description": "Person examining documents with magnifying glass",
                    "search_queries": ["magnifying glass", "old archive desk", "vintage map"],
                    "duration": 5.5,
                },
                {
                    "scene_number": 3,
                    "narration": f"The most startling part is how this crucial detail was hidden in plain sight for generations.",
                    "scene_description": "Dramatic vault door unlocking in dark lighting",
                    "search_queries": ["vault door", "dramatic lighting", "shadow mystery"],
                    "duration": 5.5,
                },
                {
                    "scene_number": 4,
                    "narration": f"Now the real question is: why was this side of {topic} kept out of public discussion?",
                    "scene_description": "Sunset horizon with thinking silhouette",
                    "search_queries": ["sunset horizon", "silhouette thinking", "ancient ruins"],
                    "duration": 5.0,
                },
            ]

        full_narr = " ".join(s["narration"] for s in scenes)
        return {
            "title": topic,
            "scenes": scenes,
            "full_narration": full_narr,
            "procedural_fallback": True,
        }
