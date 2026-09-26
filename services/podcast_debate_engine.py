"""
Podcast Debate & Multi-Speaker Script Engine.
Adapted and enhanced from naqashafzal/AI-Content-Studio (agents.py WriterAgent).
Orchestrates high-tension, multi-speaker conversational debates (Host vs Guest)
optimized for YouTube Shorts retention and podcast clips.
"""
from dataclasses import dataclass, field
import json
import logging
import re
from typing import Any, Dict, List, Optional
import config

logger = logging.getLogger(__name__)


@dataclass
class DialogueTurn:
    speaker: str
    role: str  # "host" or "guest"
    text: str
    round_num: int
    estimated_duration_sec: float = 0.0


@dataclass
class DebateScript:
    topic: str
    host_name: str
    guest_name: str
    turns: List[DialogueTurn] = field(default_factory=list)
    full_text: str = ""
    estimated_total_duration_sec: float = 0.0

    def to_turn_dicts(self) -> List[Dict[str, Any]]:
        """Exports turns with timestamps for ActiveSpeakerDetector / layout routing."""
        turn_list = []
        cur_t = 0.0
        for turn in self.turns:
            end_t = cur_t + turn.estimated_duration_sec
            turn_list.append({
                "speaker": turn.speaker,
                "role": turn.role,
                "text": turn.text,
                "start": round(cur_t, 2),
                "end": round(end_t, 2),
            })
            cur_t = end_t + 0.2  # natural micro-pause between speakers
        return turn_list


class PodcastDebateEngine:
    """Generates dynamic dual-host conversational debate scripts."""

    def __init__(self):
        pass

    def _estimate_turn_duration(self, text: str, words_per_min: int = 150) -> float:
        words = len(text.strip().split())
        return max(1.5, round((words / words_per_min) * 60.0, 1))

    def generate_debate(
        self,
        topic: str,
        host_name: str = "Barış",
        guest_name: str = "Deniz",
        host_persona: str = "Meraklı, provokatif sorular soran bir podcast sunucusu",
        guest_persona: str = "Şüpheci, somut kanıt ve gerçekçi veriler arayan uzman konuk",
        rounds: int = 3,
        language: str = "tr",
    ) -> DebateScript:
        """
        Creates a multi-turn debate script. Attempts LLM generation first,
        falling back to deterministic debate blueprint if offline.
        """
        try:
            from openai import OpenAI
            api_key = config.AI_API_KEY
            base_url = config.AI_BASE_URL
            model = config.AI_MODEL

            if api_key:
                client = OpenAI(api_key=api_key, base_url=base_url)
                sys_prompt = (
                    f"Sen iki kişilik viral bir podcast tartışma yazarı ve yapay zeka yönetmenisin.\n"
                    f"Format: {host_name} (Sunucu, {host_persona}) ve {guest_name} (Konuk, {guest_persona}).\n"
                    f"Konu: {topic}\n"
                    f"Kurallar:\n"
                    f"- Toplam {rounds} tur olsun (her turda bir Host, bir Guest konuşması).\n"
                    f"- Sunucu sarsıcı ve merak uyandıran bir soruyla/iddia ile açar.\n"
                    f"- Konuk beklenmedik bir karşı tez ve çarpıcı bir veri ile meydan okur.\n"
                    f"- Cümleler konuşma dilinde, akıcı, keskin ve kısa olsun (her replik 1-3 cümle).\n"
                    f"Cevabı YALNIZCA geçerli JSON olarak ver:\n"
                    f'{{"turns": [{{"speaker": "{host_name}", "role": "host", "round": 1, "text": "..."}}, '
                    f'{{"speaker": "{guest_name}", "role": "guest", "round": 1, "text": "..."}}]}}'
                )
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": f"Podcast tartışması yaz: {topic}"},
                    ],
                    temperature=0.7,
                )
                raw = resp.choices[0].message.content.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()

                data = json.loads(raw)
                turns_raw = data.get("turns", [])
                if turns_raw:
                    dialogue_turns: List[DialogueTurn] = []
                    total_dur = 0.0
                    text_parts = []
                    for t in turns_raw:
                        spk = str(t.get("speaker", host_name))
                        role = "host" if spk == host_name else "guest"
                        text = str(t.get("text", "")).strip()
                        r_num = int(t.get("round", 1))
                        dur = self._estimate_turn_duration(text)
                        total_dur += dur
                        dialogue_turns.append(
                            DialogueTurn(speaker=spk, role=role, text=text, round_num=r_num, estimated_duration_sec=dur)
                        )
                        text_parts.append(f"[{spk}] {text}")

                    return DebateScript(
                        topic=topic,
                        host_name=host_name,
                        guest_name=guest_name,
                        turns=dialogue_turns,
                        full_text="\n\n".join(text_parts),
                        estimated_total_duration_sec=round(total_dur, 1),
                    )
        except Exception as e:
            logger.warning(f"LLM debate script generation error, using fallback: {e}")

        # Deterministic High-Retention Fallback Script
        fallback_turns = [
            DialogueTurn(
                speaker=host_name,
                role="host",
                text=f"{topic} hakkında herkesin doğru bildiği o büyük yanılgıyı bugün yıkıyoruz.",
                round_num=1,
                estimated_duration_sec=4.0,
            ),
            DialogueTurn(
                speaker=guest_name,
                role="guest",
                text="Aslında durum insanların sandığından çok daha karmaşık ve tehlikeli.",
                round_num=1,
                estimated_duration_sec=4.5,
            ),
            DialogueTurn(
                speaker=host_name,
                role="host",
                text="Peki en kritik kanıt ne? Neden kimse bu gerçeği açıkça konuşmuyor?",
                round_num=2,
                estimated_duration_sec=4.0,
            ),
            DialogueTurn(
                speaker=guest_name,
                role="guest",
                text="Çünkü veriler gösteriyor ki, sonuçları kabul etmek tüm sistemi sorgulamak anlamına geliyor.",
                round_num=2,
                estimated_duration_sec=5.0,
            ),
            DialogueTurn(
                speaker=host_name,
                role="host",
                text="Ve asıl soru şu: Bu döngüyü kırmaya gerçekten hazır mıyız?",
                round_num=3,
                estimated_duration_sec=3.5,
            ),
        ]

        full_txt = "\n\n".join([f"[{t.speaker}] {t.text}" for t in fallback_turns])
        total_d = sum(t.estimated_duration_sec for t in fallback_turns)

        return DebateScript(
            topic=topic,
            host_name=host_name,
            guest_name=guest_name,
            turns=fallback_turns,
            full_text=full_txt,
            estimated_total_duration_sec=round(total_d, 1),
        )


podcast_debate_engine = PodcastDebateEngine()
