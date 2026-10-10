"""
DirectorPlan schema — single authoritative manifesto for the full production pipeline.
Maps roadmap items 88, 129, 201-225, 266, 274, 345, 494 into a typed plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


BEAT_TYPES = ("hook", "conflict", "climax", "resolution", "quiz", "document", "shock")


@dataclass
class VisualIntent:
    subject: str = ""
    action: str = "slow push in"
    setting: str = ""
    era: str = ""
    mood: str = "cinematic"
    lighting: str = "natural light"
    visual_priority: str = "subject"
    must_include: List[str] = field(default_factory=list)
    must_exclude: List[str] = field(default_factory=list)
    continuity_motif: str = "default"
    search_queries: List[str] = field(default_factory=list)
    shot_type: str = "establishing"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "VisualIntent":
        data = data or {}
        return cls(
            subject=str(data.get("subject", "")),
            action=str(data.get("action", "slow push in")),
            setting=str(data.get("setting", "")),
            era=str(data.get("era", "")),
            mood=str(data.get("mood", "cinematic")),
            lighting=str(data.get("lighting", "natural light")),
            visual_priority=str(data.get("visual_priority", "subject")),
            must_include=list(data.get("must_include") or []),
            must_exclude=list(data.get("must_exclude") or []),
            continuity_motif=str(data.get("continuity_motif", "default")),
            search_queries=list(data.get("search_queries") or []),
            shot_type=str(data.get("shot_type") or "establishing"),
        )


@dataclass
class AudioEvent:
    sound: str
    at: float
    beat_type: str = "conflict"
    volume: float = 0.20
    duration: float = 0.0
    item_id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioEvent":
        return cls(
            sound=str(data.get("sound", "whoosh")),
            at=float(data.get("at", 0.0)),
            beat_type=str(data.get("beat_type", "conflict")),
            volume=float(data.get("volume", 0.20)),
            duration=float(data.get("duration", 0.0)),
            item_id=int(data.get("item_id", 0)),
        )


SCENE_INTENTS = (
    "establishing", "closeup", "action", "transition",
    "question", "conclusion",
)
CAMERA_DIRECTIONS = (
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
    "tilt_up",
    "tilt_down",
    "static",
)


@dataclass
class ScenePlan:
    index: int
    narration: str
    duration: float
    t0: float = 0.0
    t1: float = 0.0
    beat_type: str = "conflict"
    scene_description: str = ""
    search_queries: List[str] = field(default_factory=list)
    visual_intent: VisualIntent = field(default_factory=VisualIntent)
    scene_intent: str = "action"
    camera_direction: str = "zoom_in"
    badge_label: Optional[str] = None
    enable_pip: bool = False
    pip_path: Optional[str] = None
    handheld_shake: bool = False
    wipe_transition: bool = False
    wipe_direction: str = "horizontal"
    path: Optional[str] = None
    mood: str = ""
    beat_hint_ms: Optional[float] = None
    claim_ids: List[str] = field(default_factory=list)
    evidence_required: bool = False
    caption_emphasis: List[str] = field(default_factory=list)
    transition_intent: str = "cut"
    arabic_text: Optional[str] = None
    source_citation: Optional[str] = None
    visual_mode: Optional[str] = None
    selected_video: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["visual_intent"] = self.visual_intent.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any], index: int = 0) -> "ScenePlan":
        vi = VisualIntent.from_dict(data.get("visual_intent"))
        return cls(
            index=int(data.get("index", index)),
            narration=str(data.get("narration", "")),
            duration=float(data.get("duration", 3.0)),
            t0=float(data.get("t0", 0.0)),
            t1=float(data.get("t1", 0.0)),
            beat_type=str(data.get("beat_type", "conflict")),
            scene_description=str(data.get("scene_description", "")),
            search_queries=list(
                data.get("search_queries")
                or ([data["search_query"]] if data.get("search_query") else [])
            ),
            visual_intent=vi,
            scene_intent=str(data.get("scene_intent", "action")),
            camera_direction=str(data.get("camera_direction", "zoom_in")),
            badge_label=data.get("badge_label"),
            enable_pip=bool(data.get("enable_pip", False)),
            pip_path=data.get("pip_path"),
            handheld_shake=bool(data.get("handheld_shake", False)),
            wipe_transition=bool(data.get("wipe_transition", False)),
            wipe_direction=str(data.get("wipe_direction", "horizontal")),
            path=data.get("path"),
            mood=str(data.get("mood", "")),
            beat_hint_ms=float(data["beat_hint_ms"]) if data.get("beat_hint_ms") is not None else None,
            claim_ids=list(data.get("claim_ids") or []),
            evidence_required=bool(data.get("evidence_required", False)),
            caption_emphasis=list(data.get("caption_emphasis") or []),
            transition_intent=str(data.get("transition_intent", "cut")),
            arabic_text=data.get("arabic_text"),
            source_citation=data.get("source_citation"),
            visual_mode=data.get("visual_mode"),
            selected_video=data.get("selected_video"),
        )


# Bölüm 7.6: DirectorScene, ScenePlan nesnesinin birinci sınıf tip takma adıdır (alias).
DirectorScene = ScenePlan


# tr-TR Edge TTS ≈ 2.3–2.6 words/s. ElevenLabs TR measured ~2.0 wps (slower).
TTS_WORDS_PER_SEC = 2.45
TTS_BUDGET_WPS = 2.5
# Historical emergency ceiling. Default fit path no longer speeds speech (Item 494).
TTS_EMERGENCY_MAX_SPEED = 1.35
# ElevenLabs TR ~2.0 wps. Natural 60s budget does not multiply by 1.35.
TTS_BUDGET_WPS_ELEVEN = 1.92
# Charon / Edge-TR measured ~1.9 wps (179 words → 94s). 60s natural ≈ 110 words.
NATURAL_TTS_WPS = 1.9
NATURAL_SHORTS_WORD_CAP = 110


def _effective_tts_budget_wps() -> float:
    """Conservative wps for word-cap math — slowest active TTS provider wins."""
    try:
        import config
        from tts_voices import is_elevenlabs_voice

        if is_elevenlabs_voice(getattr(config, "TTS_VOICE", "") or ""):
            return TTS_BUDGET_WPS_ELEVEN
    except Exception:
        pass
    return TTS_WORDS_PER_SEC


def natural_target_duration(
    word_count: int,
    min_d: float = 38.0,
    max_d: float = 60.0,
    wps: float = TTS_WORDS_PER_SEC,
) -> float:
    """Content-driven Shorts length. Floor 38, cap 60 — 48 is not a magnet."""
    natural = max(0, int(word_count or 0)) / max(float(wps) or TTS_WORDS_PER_SEC, 0.1)
    return round(min(float(max_d), max(float(min_d), natural)), 2)


def shorts_word_budget(max_duration: float = 60.0, max_audio_speed: float = 1.15) -> int:
    """
    Max narration words so raw TTS fits max_duration at natural pace (Item 494).
    Does not assume a 1.35× speed-up. Provider wps still applies, then the
    natural ceiling (110 words) wins when that pace would run past 60s.
    """
    _ = max_audio_speed
    wps = _effective_tts_budget_wps()
    cap = int(float(max_duration) * wps)
    # 1.35× used to lift Edge to ~198 words. That speech was rushed.
    # Natural 60s ceiling is 110 words at ~1.9 wps for every provider.
    cap = min(cap, NATURAL_SHORTS_WORD_CAP)
    return max(48, cap)


def natural_narration_word_cap(
    measured_words: int = 0,
    measured_seconds: float = 0.0,
    max_duration: float = 60.0,
) -> int:
    """
    Words that fit max_duration at the pace just measured.
    Ceiling is 110. A 1.35× speed-up is not part of the budget.
    179 words / 94s ≈ 1.9 wps → 60s ≈ 114, clamped to 110.
    """
    ceiling = NATURAL_SHORTS_WORD_CAP
    if measured_words > 0 and measured_seconds > 1.0:
        wps = float(measured_words) / float(measured_seconds)
        measured_cap = int(float(max_duration) * wps)
        ceiling = min(ceiling, measured_cap)
    else:
        ceiling = min(ceiling, shorts_word_budget(max_duration))
    return max(48, ceiling)


@dataclass
class QualityThresholds:
    min_duration: float = 38.0
    max_duration: float = 60.0
    target_duration: float = 0.0  # 0 = content-driven via natural_target_duration
    min_scenes: int = 8
    max_audio_speed: float = 1.15
    max_av_delta: float = 0.05
    min_alignment_score: float = 0.25
    max_sfx_density: float = 0.55

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DirectorPlan:
    title: str
    niche_id: str
    language: str = "tr"
    full_narration: str = ""
    scenes: List[ScenePlan] = field(default_factory=list)
    audio_events: List[AudioEvent] = field(default_factory=list)
    story_arc: Dict[str, Any] = field(default_factory=dict)
    cadence_durations: List[float] = field(default_factory=list)
    niche_profile: Dict[str, Any] = field(default_factory=dict)
    effect_manifest: Dict[str, bool] = field(default_factory=dict)
    quality_thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    time_map: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    visual_theme: str = ""
    hook_text: str = ""
    loop_text: str = ""
    reddit_post: Optional[Dict[str, Any]] = None
    visual_mode: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def total_duration(self) -> float:
        return round(sum(s.duration for s in self.scenes), 3)

    def rebuild_full_narration(self) -> str:
        self.full_narration = " ".join(
            s.narration.strip() for s in self.scenes if s.narration and s.narration.strip()
        )
        return self.full_narration

    def to_legacy_plan(self) -> Dict[str, Any]:
        """Backward-compatible plan.json shape for UI / plagiarism / DB."""
        meta = self.meta or {}
        return {
            "title": self.title,
            "full_narration": self.full_narration or self.rebuild_full_narration(),
            "niche_id": self.niche_id,
            "niche_profile": self.niche_profile,
            "visual_theme": self.visual_theme,
            "visual_mode": self.visual_mode or meta.get("visual_mode"),
            "hook_text": self.hook_text,
            "loop_text": self.loop_text,
            "reddit_post": self.reddit_post,
            "director_plan": True,
            "story_arc": self.story_arc,
            "hybrid_niche": meta.get("hybrid_niche"),
            "hybrid_split_screen": meta.get("hybrid_split_screen"),
            "hybrid_render_overlay": meta.get("hybrid_render_overlay"),
            "retention_metadata": meta.get("retention_metadata"),
            "scenes": [
                {
                    "index": s.index,
                    "narration": s.narration,
                    "duration": s.duration,
                    "t0": s.t0,
                    "t1": s.t1,
                    "beat_type": s.beat_type,
                    "scene_description": s.scene_description,
                    "search_queries": s.search_queries or s.visual_intent.search_queries,
                    "visual_intent": s.visual_intent.to_dict(),
                    "scene_intent": s.scene_intent,
                    "camera_direction": s.camera_direction,
                    "badge_label": s.badge_label,
                    "enable_pip": s.enable_pip,
                    "pip_path": s.pip_path,
                    "handheld_shake": s.handheld_shake,
                    "wipe_transition": s.wipe_transition,
                    "wipe_direction": s.wipe_direction,
                    "mood": s.mood or s.visual_intent.mood,
                    "path": s.path,
                    "claim_ids": s.claim_ids,
                    "evidence_required": s.evidence_required,
                    "caption_emphasis": s.caption_emphasis,
                    "transition_intent": s.transition_intent,
                    "arabic_text": s.arabic_text,
                    "source_citation": s.source_citation,
                    "visual_mode": s.visual_mode,
                    "selected_video": s.selected_video,
                }
                for s in self.scenes
            ],
            "audio_events": [e.to_dict() for e in self.audio_events],
            "effect_manifest": self.effect_manifest,
            "quality_thresholds": self.quality_thresholds.to_dict(),
            "time_map": self.time_map,
            "validation": self.validation,
            "meta": self.meta,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_legacy_plan()

    def to_clips(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": s.path,
                "duration": s.duration,
                "narration": s.narration,
                "scene_description": s.scene_description,
                "badge_label": s.badge_label,
                "enable_pip": s.enable_pip,
                "pip_path": s.pip_path,
                "handheld_shake": s.handheld_shake,
                "wipe_transition": s.wipe_transition,
                "wipe_direction": s.wipe_direction,
                "beat_type": s.beat_type,
                "visual_intent": s.visual_intent.to_dict(),
                "scene_intent": s.scene_intent,
                "camera_direction": s.camera_direction,
                "t0": s.t0,
                "t1": s.t1,
                "search_queries": s.search_queries,
            }
            for s in self.scenes
        ]


DEFAULT_EFFECT_MANIFEST = {
    "item_101_jitter": False,
    "item_87_sonic_watermark": False,
    "item_103_out_of_focus": True,
    "item_108_pink_noise": False,
    "item_112_whoosh_ding": False,
    "item_138_progress_bar": True,
    "item_141_breaths": False,
    "item_145_room_ambience": False,
    "item_154_sub_bass": True,
    "item_155_riser_whoosh": True,
    "item_157_heartbeat": False,
    "item_158_clock_tick": True,
    "item_159_typewriter": True,
    "item_166_loop_no_fade": True,
    "item_205_max_3_4_words": True,
    "item_266_cadence_accel": True,
    "item_274_story_arc": True,
    "item_182_piano": True,
    "item_183_synth_bass": True,
    "item_187_stereo_pan": True,
    "item_188_crowd_ambience": False,
    "item_191_reverb_chamber": False,
    "item_195_epic_trailer_voice": False,
    "item_418_ffmpeg_graph": True,
    # Visual bait — opt-in per niche family (default off)
    "item_211_blur_bait": False,
    "item_212_countdown": False,
    "item_246_curiosity": False,
    "item_232_sticky_banner": False,
    "item_238_sticker": False,
    "item_260_white_flash": False,
    "item_201_pattern_interrupt": False,
}

# P0-07: calm/stoic publish mix — narration-forward, minimal SFX bed
STOIC_EFFECT_MANIFEST_OVERRIDES = {
    "item_108_pink_noise": False,
    "item_141_breaths": False,
    "item_87_sonic_watermark": False,
    "item_112_whoosh_ding": False,
    "item_101_jitter": False,
    "item_145_room_ambience": False,
    "item_154_sub_bass": False,
}

STOIC_AUDIO_RULES = {
    "sparse_transitions": True,
    "max_transition_sfx": 5,
    "whoosh_volume": 0.108,  # ~40% below default 0.18
    "enable_sub_impact": False,
    "enable_tape_stop": False,  # P1-10: only explicit shock beats, not contrast keyword scan
    "target_lufs": -14.0,
}


def merge_effect_manifest(niche_profile: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
    """Apply per-niche effect_manifest overrides on top of defaults."""
    manifest = dict(DEFAULT_EFFECT_MANIFEST)
    overrides = (niche_profile or {}).get("effect_manifest_overrides") or {}
    manifest.update(overrides)
    return manifest
