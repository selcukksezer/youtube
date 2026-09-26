"""
Audio Mood Director Service.
Adapted from gyoridavid/short-video-maker (music mood taxonomy & dynamic volume control).

Classifies video narrative sentiment into 12 structured mood categories and matches
the optimal copyright-safe background music track and ducking parameters.
"""
from __future__ import annotations

import os
import re
from enum import Enum
from typing import Any, Dict, List, Optional

import config
from bgm_manager import list_bgm_tracks_detailed, get_bgm_path, get_safe_default_bgm_path


class MusicMood(str, Enum):
    MELANCHOLIC = "melancholic"
    CHILL = "chill"
    UNEASY = "uneasy"
    EXCITED = "excited"
    EUPHORIC = "euphoric"
    DARK = "dark"
    SAD = "sad"
    HAPPY = "happy"
    ANGRY = "angry"
    HOPEFUL = "hopeful"
    CONTEMPLATIVE = "contemplative"
    FUNNY = "funny"


# Niche to default mood mapping
NICHE_MOOD_MAP: Dict[str, MusicMood] = {
    "stoic": MusicMood.CONTEMPLATIVE,
    "philosophy": MusicMood.CONTEMPLATIVE,
    "history": MusicMood.MELANCHOLIC,
    "crypto": MusicMood.EXCITED,
    "finans": MusicMood.CHILL,
    "mystery": MusicMood.UNEASY,
    "horror": MusicMood.DARK,
    "motivation": MusicMood.HOPEFUL,
    "fitness": MusicMood.EXCITED,
    "comedy": MusicMood.FUNNY,
    "kids": MusicMood.HAPPY,
    "gaming": MusicMood.EUPHORIC,
    "science": MusicMood.CONTEMPLATIVE,
}

# Keyword sentiment lexicon (Turkish & English)
MOOD_KEYWORDS: Dict[MusicMood, List[str]] = {
    MusicMood.DARK: ["karanlık", "korkunç", "dehşet", "ölüm", "katil", "lanet", "dark", "evil", "horror", "sinister"],
    MusicMood.UNEASY: ["gizem", "şüphe", "tehlike", "fısıltı", "kayboldu", "kaçtı", "mystery", "danger", "uneasy", "suspense"],
    MusicMood.EXCITED: ["patlama", "yükseliş", "rekor", "zafer", "milyon", "şampiyon", "pump", "record", "victory", "excited"],
    MusicMood.EUPHORIC: ["inanılmaz", "harika", "zirve", "uçuyor", "coşku", "euphoric", "triumph", "epic", "insane"],
    MusicMood.SAD: ["hüzün", "kayıp", "gözyaşı", "bitti", "ayrılık", "acı", "sad", "loss", "tears", "tragedy"],
    MusicMood.MELANCHOLIC: ["geçmiş", "eski", "unutulmuş", "hatıra", "özlem", "nostalgia", "melancholy", "forgotten", "ancient"],
    MusicMood.CONTEMPLATIVE: ["düşün", "gerçek", "zihin", "ruh", "anlam", "felsefe", "derin", "wisdom", "stoic", "truth", "soul"],
    MusicMood.HOPEFUL: ["umut", "gelecek", "başarı", "asla pes etme", "ışık", "doğuş", "hope", "future", "sunrise", "dream"],
    MusicMood.HAPPY: ["mutlu", "sevinç", "güzel", "bayram", "dostluk", "eğlence", "happy", "joy", "smile", "friend"],
    MusicMood.FUNNY: ["komik", "kahkaha", "şaka", "komedi", "absürt", "funny", "joke", "comedy", "hilarious"],
    MusicMood.ANGRY: ["öfke", "savaş", "ihanet", "kavga", "intikam", "yıkım", "rage", "battle", "betrayal", "vengeance"],
    MusicMood.CHILL: ["sakin", "huzur", "rahat", "gece", "kahve", "lofi", "chill", "calm", "relax", "peace"],
}


class AudioMoodDirector:
    """Detects narrative sentiment and selects matched BGM with precise ducking levels."""

    @classmethod
    def detect_mood(
        cls,
        text: str = "",
        niche_id: str = "general",
        explicit_mood: Optional[str] = None,
    ) -> MusicMood:
        """Determines best mood tag from explicit input, keyword scoring, or niche default."""
        if explicit_mood:
            try:
                return MusicMood(explicit_mood.lower())
            except ValueError:
                pass

        clean_text = text.lower()
        scored_moods: Dict[MusicMood, int] = {m: 0 for m in MusicMood}

        for mood, kws in MOOD_KEYWORDS.items():
            for kw in kws:
                if kw in clean_text:
                    scored_moods[mood] += 1

        best_mood, best_score = max(scored_moods.items(), key=lambda item: item[1])
        if best_score > 0:
            return best_mood

        # Fallback to niche default
        niche_key = (niche_id or "").lower()
        for nk, mood in NICHE_MOOD_MAP.items():
            if nk in niche_key:
                return mood

        return MusicMood.CHILL

    @classmethod
    def match_bgm_track(
        cls,
        mood: MusicMood,
        preferred_track: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Finds matching BGM track in local storage or catalog for the requested mood."""
        # Check if preferred track exists
        if preferred_track:
            full_path = get_bgm_path(preferred_track)
            if full_path and os.path.isfile(full_path):
                return {
                    "filename": preferred_track,
                    "path": full_path,
                    "mood": mood.value,
                    "source": "preferred",
                }

        # Search downloaded tracks detailed
        detailed = list_bgm_tracks_detailed(include_catalog=True)
        # 1. First priority: match exact mood in downloaded tracks
        for tr in detailed:
            tr_mood = str(tr.get("mood") or "").lower()
            if tr.get("downloaded") and (mood.value in tr_mood or tr_mood in mood.value):
                p = get_bgm_path(tr["filename"])
                if p and os.path.isfile(p):
                    return {
                        "filename": tr["filename"],
                        "path": p,
                        "mood": mood.value,
                        "title": tr.get("title", tr["filename"]),
                        "source": "matched_local",
                    }

        # 2. Fallback to default safe ambient
        safe_path = get_safe_default_bgm_path()
        return {
            "filename": os.path.basename(safe_path),
            "path": safe_path,
            "mood": mood.value,
            "title": "Royalty Free Ambient",
            "source": "safe_default",
        }

    @classmethod
    def get_audio_mix_params(
        cls,
        mood: MusicMood,
        narration_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates FFmpeg volume ducking parameters.
        Reduces BGM volume when narration is speaking to prevent muffled voices.
        """
        # Mood-adjusted base music volume
        if mood in (MusicMood.EXCITED, MusicMood.EUPHORIC, MusicMood.ANGRY):
            bgm_volume_db = -16.0 if narration_active else -9.0
        elif mood in (MusicMood.DARK, MusicMood.UNEASY, MusicMood.MELANCHOLIC):
            bgm_volume_db = -19.0 if narration_active else -11.0
        else:
            bgm_volume_db = -18.0 if narration_active else -10.0

        return {
            "mood": mood.value,
            "bgm_volume_db": bgm_volume_db,
            "bgm_volume_linear": round(10 ** (bgm_volume_db / 20.0), 3),
            "ducking_fade_sec": 0.6,
            "fade_in_sec": 0.8,
            "fade_out_sec": 1.2,
        }

    @classmethod
    def direct_audio_for_script(
        cls,
        script_text: str,
        niche_id: str = "general",
        preferred_track: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete audio mood direction pipeline for a video script."""
        mood = cls.detect_mood(script_text, niche_id=niche_id)
        track_info = cls.match_bgm_track(mood=mood, preferred_track=preferred_track)
        mix_params = cls.get_audio_mix_params(mood=mood, narration_active=True)

        return {
            "mood": mood.value,
            "track": track_info,
            "mix": mix_params,
        }


audio_mood_director = AudioMoodDirector()
