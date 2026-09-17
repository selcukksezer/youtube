"""
Voice Gender Selection Logic & Dynamic Voice Persona Rotation
Covers items: 161, 165
"""
from typing import Dict, Any, Optional

def select_voice_gender(niche_id: str, keyword: str) -> str:
    """Selects a varied narrator gender from topic intensity when auto mode is requested (Item 165)."""
    text = f"{niche_id or ''} {keyword or ''}".casefold()
    feminine_cues = ("uyku", "gece", "rahatla", "meditasyon", "masal", "dua", "şefkat", "asmr", "confession", "ilişki")
    masculine_cues = ("savas", "savaş", "korku", "gizem", "drama", "finans", "spor", "stoac", "askeri", "güç", "para")
    if any(cue in text for cue in feminine_cues):
        return "female"
    if any(cue in text for cue in masculine_cues):
        return "male"
    # Deterministic variation prevents every neutral topic on a channel using one voice.
    return "female" if sum(ord(char) for char in text) % 2 else "male"


def select_dynamic_voice_actor(target_lang: str = "tr", niche_id: str = "",
                               keyword: str = "", seed: Optional[str] = None) -> Dict[str, Any]:
    """
    Madde 165: Rastgele Ses Tonu Seçimi (Dynamic Voice Actor Selection).
    Aynı kanalda sürekli tek düze seslendirmen yerine, konunun dramatikliğine ve
    türüne göre optimize edilmiş erkek veya kadın seslendirmen profili seçer.
    """
    gender = select_voice_gender(niche_id, keyword)
    text = f"{niche_id or ''} {keyword or ''}".casefold()
    lang = (target_lang or "tr").lower()

    if lang == "en":
        if gender == "male":
            if any(k in text for k in ("stoic", "history", "war", "philosophy", "dark")):
                voice = "en-US-ChristopherNeural"
                mood = "deep_authoritative"
                rate = "+1%"
            else:
                voice = "en-US-GuyNeural"
                mood = "energetic_narrator"
                rate = "+4%"
        else:
            if any(k in text for k in ("asmr", "sleep", "calm", "meditation")):
                voice = "en-US-JennyNeural"
                mood = "intimate_soft"
                rate = "-8%"
            else:
                voice = "en-US-AriaNeural"
                mood = "clear_broadcast"
                rate = "+2%"
    else:
        # Türkçe
        if gender == "male":
            voice = "tr-TR-AhmetNeural"
            mood = "tok_ve_guclu"
            rate = "+2%"
        else:
            voice = "tr-TR-EmelNeural"
            mood = "akici_ve_anlatimci"
            rate = "+3%"

    return {
        "voice": voice,
        "gender": gender,
        "mood": mood,
        "recommended_rate": rate,
        "language": lang
    }

