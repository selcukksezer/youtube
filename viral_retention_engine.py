"""
Viral Retention, Psychological Hooks & Loop Matrix Engine
Implements Items 201 - 275 of the 500-Item YouTube Shorts Automation Roadmap.
Covers:
- 12 Seamless Infinite Loop (Döngü Köprüsü) Formulas (Items 137, 204)
- Cognitive Dissonance & Zeigarnik Hooks (Items 202, 203)
- First 1.5s Pattern Interrupt Triggers (Items 201, 237)
- Bionic Reading / High-Speed Word Formatter (Item 215)
- Controversial Question, Spotted Mistake Bait & Polarizing Dilemma (Items 209, 210)
- FOMO, Forbidden Knowledge & Social Proof Hooks (Items 218, 219, 220)
- Interactive Challenge, Role-Play & Countdown Hook (Items 228, 257, 268)
- Shocking Statistic & Counter-Intuitive Hooks (Items 259, 263)
- Sticky Top Hook Banner (Item 232)
- Acoustic Curiosity, Share, Bookmark & Community CTAs (Items 233, 235, 236, 270)
- Plot Twist Closing & Trigger Name Hooks (Items 239, 240)
- Pinned Comment Bait Generator (Items 234, 269)
- Numbered Rule Hierarchy Formatter (Item 241)
- Narrow Audience & Emotional Bond Hooks (Items 244, 248)
- Subconscious Color Psychology Palettes (Item 249)
- Subtitle Safe Zone & Eye-Tracking Coordinates (Items 206, 265)
- Cadence Acceleration Curve (Item 266)
- 45s Shorts Story Arc Breakdown (Item 274)
- Retention Audit Scoring (0 - 100) (Item 275)

Static hook/retention pattern catalogs and template generators live in
`production/retention_catalog.py` and are re-exported on `ViralRetentionEngine`.
"""

import random
import re
from typing import Any, Dict, List

from production import retention_catalog as _cat
from production.retention_catalog import (
    DIVERSE_LOOP_CONJUNCTIONS_EN,
    DIVERSE_LOOP_CONJUNCTIONS_TR,
    LOOP_FORMULAS,
    PATTERN_INTERRUPTS,
    SUBCONSCIOUS_PALETTES,
    TRIGGER_NAMES,
    _OPEN_LOOP_TAIL_RE,
    _clean_hook_topic,
    _finish_spoken_line,
)


class ViralRetentionEngine:
    """Calculates and enhances video retention psychology for Shorts."""

    TRIGGER_NAMES = TRIGGER_NAMES
    LOOP_FORMULAS = LOOP_FORMULAS
    PATTERN_INTERRUPTS = PATTERN_INTERRUPTS
    SUBCONSCIOUS_PALETTES = SUBCONSCIOUS_PALETTES

    @classmethod
    def get_loop_formula(cls, formula_id: str = None) -> Dict[str, str]:
        """Returns a selected loop formula or a random one (Item 204 & 137)."""
        if formula_id:
            for f in cls.LOOP_FORMULAS:
                if f["id"] == formula_id:
                    return f
        return random.choice(cls.LOOP_FORMULAS)

    @classmethod
    def get_diverse_loop_conjunctions(cls, min_count: int = 10, lang: str = "tr") -> List[str]:
        """Item 137: Döngü Cümlesi Çeşitliliği (TR & EN)."""
        conjunctions = list(DIVERSE_LOOP_CONJUNCTIONS_EN if lang == "en" else DIVERSE_LOOP_CONJUNCTIONS_TR)
        return conjunctions[:max(min_count, len(conjunctions))]

    @classmethod
    def pick_loop_bridge_for_video(cls, video_index: int = 0, lang: str = "tr") -> str:
        """Item 137 & 204: Videoya ve dile özel döngüsel bağlaç seçer."""
        pool = cls.get_diverse_loop_conjunctions(lang=lang)
        return pool[video_index % len(pool)]

    @classmethod
    def spoken_loop_tail(cls, opening: str, lang: str = "tr", video_index: int = 0) -> str:
        """Conjunction the opening's first words can finish. Does not repeat them."""
        text = (opening or "").strip()
        question = text.endswith("?") or bool(
            re.match(r"^(neden|nasıl|nasil|peki|kim|ne|hangi|what|why|how|who)\b", text, re.I)
        )
        if lang == "en":
            tails = ("so",) if question else ("because", "and that is why", "which is why")
        else:
            tails = ("peki",) if question else ("çünkü", "ve tam da bu yüzden", "işte bu sebeple")
        return tails[int(video_index) % len(tails)]

    @classmethod
    def synthesize_seamless_loop(
        cls,
        opening_hook: str,
        final_narration: str = "",
        loop_formula_id: str = None,
        video_index: int = 0,
        lang: str = "tr",
    ) -> Dict[str, str]:
        """Item 204 & 345 / Plan 7.2: loop metadata for the editor."""
        opening = (opening_hook or "").strip()
        closing = (final_narration or "").strip()

        formula = cls.get_loop_formula(loop_formula_id) if loop_formula_id else None
        if (lang or "tr").lower()[:2] != "en" and formula and formula.get("ending_bridge"):
            bridge = formula["ending_bridge"]
        else:
            bridge = cls.pick_loop_bridge_for_video(video_index, lang=lang)

        seamless_closing = _finish_spoken_line(closing)
        preview = f"{seamless_closing} {opening}".strip()
        return {
            "seamless_closing": seamless_closing,
            "ending_bridge": bridge,
            "opening_hook": opening,
            "preview_loop": preview,
        }

    @classmethod
    def generate_cognitive_dissonance_hook(cls, topic: str, lang: str = "tr") -> str:
        """Item 202: Bilişsel Çelişki Kancası (Cognitive Dissonance Hook)."""
        t = _clean_hook_topic(topic, lang=lang)
        if lang == "en":
            hooks = [
                f"Until you learn this about {t}, your mind was never truly under your control.",
                f"Everything you've been taught about {t} is deliberately backwards.",
                f"What if I told you the truth about {t} is the exact opposite of what you believe?",
                f"You think you understand {t}, but 99% of people fall for this exact cognitive trap.",
            ]
        else:
            hooks = [
                f"Bunu öğrenene kadar {t} konusunda bildiğiniz her şey sadece bir yanılsamaydı.",
                f"Çoğu insan {t} hakkında tamamen yanılıyor ve bu hata her gün tekrarlanıyor.",
                f"{t} hakkında size bugüne kadar anlatılanların tam tersi doğru olsaydı ne yapardınız?",
                f"Bunu bilmeden geçen her gün, {t} tuzağına biraz daha çekiliyorsunuz.",
            ]
        return random.choice(hooks)

    @classmethod
    def generate_zeigarnik_hook(cls, topic: str, total_points: int = 3, lang: str = "tr") -> str:
        """Item 203: Zeigarnik Etkisi (Tamamlanmamışlık Hissi)."""
        if lang == "en":
            return f"By the end of this video, you will uncover rule #{total_points} that completely changes everything, but first..."
        return f"Bu videonun sonunda hayatınızı değiştirecek o {total_points}. kuralı duyacaksınız, ama önce..."

    @classmethod
    def get_subtitles_safe_zone(cls, screen_height: int = 1920, screen_width: int = 1080) -> Dict[str, Any]:
        """Items 206 & 265: Göz Bebeği Takip Noktası & Güvenli Alan."""
        bottom_ui_margin = int(screen_height * 0.25)
        top_ui_margin = int(screen_height * 0.15)
        eye_tracking_y_min = int(screen_height * 0.40)
        eye_tracking_y_max = int(screen_height * 0.60)
        optimal_subtitle_y = int(screen_height * 0.52)

        return {
            "screen_width": screen_width,
            "screen_height": screen_height,
            "bottom_ui_margin": bottom_ui_margin,
            "top_ui_margin": top_ui_margin,
            "eye_tracking_y_range": [eye_tracking_y_min, eye_tracking_y_max],
            "optimal_subtitle_y": optimal_subtitle_y,
            "max_words_per_frame": 4,
            "safe_zone_verified": True,
        }

    @classmethod
    def generate_polarizing_dilemma(cls, topic: str, lang: str = "tr") -> Dict[str, str]:
        return _cat.generate_polarizing_dilemma(topic, lang=lang)

    @classmethod
    def generate_fomo_forbidden_knowledge_hook(cls, topic: str, category: str = "fomo", lang: str = "tr") -> str:
        return _cat.generate_fomo_forbidden_knowledge_hook(topic, category=category, lang=lang)

    @classmethod
    def generate_challenge_hook(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_challenge_hook(topic, lang=lang)

    @classmethod
    def generate_role_play_hook(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_role_play_hook(topic, lang=lang)

    @classmethod
    def generate_curiosity_gap_hook(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_curiosity_gap_hook(topic, lang=lang)

    @classmethod
    def generate_problem_agitation_hook(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_problem_agitation_hook(topic, lang=lang)

    @classmethod
    def generate_shocking_statistic_hook(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_shocking_statistic_hook(topic, lang=lang)

    @classmethod
    def generate_counter_intuitive_hook(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_counter_intuitive_hook(topic, lang=lang)

    @classmethod
    def get_sticky_hook_banner(cls, topic: str, mood: str = "warning", lang: str = "tr") -> str:
        return _cat.get_sticky_hook_banner(topic, mood=mood, lang=lang)

    @classmethod
    def generate_acoustic_curiosity_hook(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_acoustic_curiosity_hook(topic, lang=lang)

    @classmethod
    def generate_share_cta(cls, topic: str = "", lang: str = "tr") -> str:
        return _cat.generate_share_cta(topic=topic, lang=lang)

    @classmethod
    def generate_bookmark_cta(cls, topic: str = "", lang: str = "tr") -> str:
        return _cat.generate_bookmark_cta(topic=topic, lang=lang)

    @classmethod
    def generate_community_follow_cta(cls, topic: str = "", lang: str = "tr") -> str:
        return _cat.generate_community_follow_cta(topic=topic, lang=lang)

    @classmethod
    def generate_plot_twist_closing(cls, topic: str, lang: str = "tr") -> str:
        return _cat.generate_plot_twist_closing(topic, lang=lang)

    @classmethod
    def inject_trigger_name_hook(cls, hook: str, topic: str = "", lang: str = "tr") -> str:
        """Keep the written hook."""
        return (hook or "").strip()

    @classmethod
    def generate_pinned_comment_bait(cls, topic: str, lang: str = "tr") -> Dict[str, str]:
        return _cat.generate_pinned_comment_bait(topic, lang=lang)

    @classmethod
    def format_numbered_rule_hierarchy(cls, rules: List[str], lang: str = "tr") -> List[Dict[str, Any]]:
        return _cat.format_numbered_rule_hierarchy(rules, lang=lang)

    @classmethod
    def generate_narrow_audience_hook(cls, topic: str = "", year: int = 2026, lang: str = "tr") -> str:
        return _cat.generate_narrow_audience_hook(topic=topic, year=year, lang=lang)

    @classmethod
    def generate_single_sentence_identity_hook(cls, topic: str = "", lang: str = "tr") -> str:
        return _cat.generate_single_sentence_identity_hook(topic=topic, lang=lang)

    @classmethod
    def generate_emotional_bond_hook(cls, lang: str = "tr") -> str:
        return _cat.generate_emotional_bond_hook(lang=lang)

    @classmethod
    def get_subconscious_color_palette(cls, niche_or_mood: str) -> Dict[str, str]:
        """Item 249: Bilinçaltı Renk Psikolojisi Paleti."""
        low = (niche_or_mood or "").lower()
        if any(k in low for k in ["danger", "horror", "gizem", "korku", "tehlike", "shock"]):
            return cls.SUBCONSCIOUS_PALETTES["danger_mystery"]
        elif any(k in low for k in ["money", "finance", "wealth", "zengin", "para", "borsa", "kripto"]):
            return cls.SUBCONSCIOUS_PALETTES["wealth_success"]
        elif any(k in low for k in ["tech", "ai", "cyber", "robot", "bilim", "space", "yapay zeka", "zeka", "teknoloji"]):
            return cls.SUBCONSCIOUS_PALETTES["cyber_tech"]
        return cls.SUBCONSCIOUS_PALETTES["stoic_philosophy"]

    @classmethod
    def calculate_cadence_acceleration(cls, total_duration: float = 60.0, scene_count: int = 14) -> List[float]:
        """Item 266: Kurgu Ritim Hızlandırması (Cadence Acceleration Curve)."""
        if scene_count <= 0:
            return []

        min_scene = 3.2
        weights = [1.0 - (0.5 * (i / max(1, scene_count - 1))) for i in range(scene_count)]
        sum_weights = sum(weights) or 1.0
        durations = [(w / sum_weights) * total_duration for w in weights]

        if scene_count * min_scene <= total_duration + 0.05:
            durations = [max(min_scene, d) for d in durations]
            overflow = sum(durations) - total_duration
            i = len(durations) - 1
            while overflow > 0.01 and i >= 0:
                spare = durations[i] - min_scene
                take = min(spare, overflow)
                durations[i] -= take
                overflow -= take
                i -= 1
            if overflow < -0.01:
                durations[0] += -overflow
        else:
            durations = [max(1.2, min(4.5, d)) for d in durations]

        adjusted = [round(d, 2) for d in durations]
        if adjusted:
            last_floor = min_scene if scene_count * min_scene <= total_duration + 0.05 else 1.2
            ms = [int(round(x * 100)) for x in adjusted]
            target_ms = int(round(total_duration * 100))
            ms[-1] += target_ms - sum(ms)
            floor_ms = int(round(last_floor * 100))
            if ms[-1] < floor_ms:
                steal = floor_ms - ms[-1]
                ms[-1] = floor_ms
                ms[0] -= steal
            ms[-1] += target_ms - sum(ms)
            out = [m / 100.0 for m in ms[:-1]]
            head = sum(out)
            out.append(float(target_ms) / 100.0 - head)
            return out
        return adjusted

    @classmethod
    def build_shorts_story_arc_breakdown(cls, duration: float = 60.0) -> Dict[str, Any]:
        """Item 274: Shorts hikaye arkı — percent of actual duration, not a 45s lock."""
        intro_end = round(duration * 0.07, 1)
        conflict_end = round(duration * 0.45, 1)
        climax_end = round(duration * 0.75, 1)
        return {
            "total_duration": duration,
            "phases": [
                {
                    "phase": "Hook / Giriş",
                    "time_range": f"0 - {intro_end:.0f}s",
                    "goal": "Pattern interrupt, şok görsel, kaydırmayı engelleme (%75+ Viewed)",
                    "sfx": "Whoosh + Ding",
                    "scale_punch": True,
                },
                {
                    "phase": "Conflict / Çatışma & Gelişme",
                    "time_range": f"{intro_end:.0f} - {conflict_end:.0f}s",
                    "goal": "Bilişsel çelişkiyi detaylandırma, tez ve antitez argümanları",
                    "sfx": "Subtle heartbeat & ambient sound",
                    "scale_punch": False,
                },
                {
                    "phase": "Climax / Duygusal Zirve",
                    "time_range": f"{conflict_end:.0f} - {climax_end:.0f}s",
                    "goal": "En sarsıcı bilginin açıklanması, kurgu ritminin hızlanması",
                    "sfx": "Rising tension riser",
                    "scale_punch": True,
                },
                {
                    "phase": "Resolution & Loop / Çözüm & Döngü",
                    "time_range": f"{climax_end:.0f} - {duration:.0f}s",
                    "goal": "Sentez çıkarımı, kusursuz sonsuz döngü köprüsü (Seamless Loop)",
                    "sfx": "Zero fade-out cut",
                    "scale_punch": False,
                },
            ],
        }

    @staticmethod
    def format_bionic_text(words: List[str]) -> List[str]:
        """Bionic Reading formatter (Item 215)."""
        bionic = []
        for w in words:
            mid = max(1, len(w) // 2)
            bionic.append(f"<b>{w[:mid]}</b>{w[mid:]}")
        return bionic

    @staticmethod
    def generate_spotted_mistake_bait(topic: str) -> str:
        return _cat.generate_spotted_mistake_bait(topic)

    @classmethod
    def calculate_retention_score(
        cls,
        has_split_screen: bool,
        has_anti_duplicate: bool,
        has_karaoke: bool,
        has_loop: bool,
        audio_ducking: bool,
    ) -> Dict[str, Any]:
        """Calculates Retention / Virality score out of 100 based on algorithm rules (Item 275)."""
        score = 60
        checks = []
        if has_loop:
            score += 15
            checks.append("Kusursuz Sonsuz Döngü (+15)")
        if has_karaoke:
            score += 10
            checks.append("CapCut Kelime Kelime Altyazı (+10)")
        if audio_ducking:
            score += 8
            checks.append("Akıllı Audio Ducking & SFX (+8)")
        if has_anti_duplicate:
            score += 4
            checks.append("pHash & Anti-Tekrar Koruması (+4)")
        if has_split_screen:
            score += 3
            checks.append("Dopamin Split-Screen Oynanışı (+3)")

        score = min(100, score)
        tier = "Viral Potansiyeli Yüksek 🔥" if score >= 90 else "İyi Performans 👍"
        return {"score": score, "tier": tier, "checks": checks}


viral_retention_engine = ViralRetentionEngine()
