"""
Human-craft director — make Shorts feel editor-made, not AI-slop.

Research basis (2025–2026):
- YouTube inauthentic content (mass template spam ≠ monetizable)
- Shorts discovery: swipe-away, % viewed, loop/share — not "has a face"
- Creator craft: mute-readable 1–3s hook, 2–4s visual cuts, loop payoff

This module is a FINAL pass on a plan: unique POV, mute hook, loop closure,
anti-generic filler, discovery score, and edit directives for the composer.
"""
from __future__ import annotations

import hashlib
import random
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ── POV libraries (Turkish). One angle per video — not interchangeable templates.
_POV_BANK: Dict[str, Tuple[str, ...]] = {
    "religious": (
        "itiraf",  # "Kimse söylemez ama…"
        "uyarı",  # "Sakın şunu yapma…"
        "sayı",  # "3 kelimeyle…"
        "gizli",  # "En çok tekrar ettiği…"
    ),
    "crypto": (
        "paradoks",
        "sayı",
        "uyarı",
        "kanıt",
    ),
    "stoic": (
        "paradoks",
        "itiraf",
        "yasak",
        "sayı",
    ),
    "mystery": (
        "gizli",
        "soru",
        "kanıt",
        "uyarı",
    ),
    "kids": (
        "oyun",
        "sayı",
        "merak",
        "kahraman",
    ),
    "default": (
        "soru",
        "paradoks",
        "sayı",
        "itiraf",
        "uyarı",
        "kanıt",
    ),
}

_HOOK_OPENERS: Dict[str, Tuple[str, ...]] = {
    "itiraf": ("Kimse bunu söylemez:", "Dürüst olayım:", "İtiraf ediyorum:"),
    "uyarı": ("Sakın atlama:", "Bunu duyunca dur:", "Uyarı:"),
    "sayı": ("Bir sayı yeter:", "Sadece üç şey:", "Tek rakam:"),
    "paradoks": ("Mantığa aykırı ama:", "Tersine düşün:", "Herkes yanılıyor:"),
    "gizli": ("Gizli kalan taraf:", "Kimsenin bakmadığı yer:", "Asıl detay:"),
    "soru": ("Hiç sordun mu:", "Peki ya:", "Neden kimse demez:"),
    "kanıt": ("Kanıt burada:", "İz bırakmadılar ama:", "Veri net:"),
    "yasak": ("Yasak gibi durur ama:", "Kimse öğretmez:", "Kuralı kır:"),
    "oyun": ("Hadi bir oyun:", "Tahmin et:", "Bak ne olacak:"),
    "merak": ("Merak etme zamanı:", "Şuna bak:", "İçeride ne var:"),
    "kahraman": ("Küçük kahraman:", "Bugünün yıldızı:", "Cesur bir adım:"),
}

_GENERIC_FILLER = re.compile(
    r"^(bunu aklında tut\.?|devamını izle\.?|takip et\.?|like and subscribe\.?|"
    r"çok önemli\.?|inanılmaz\.?|şok olacaksın\.?)$",
    re.I,
)

_SHARE_BAIT = re.compile(
    r"[?？]|!\s*$|\b(sakın|asla|kimse|neden|kaç|kaçın|yasak|gizli|sayı|kanıt)\b",
    re.I,
)


def _family(niche_id: str) -> str:
    n = (niche_id or "").lower()
    if "relig" in n or "10_" in n and "relig" in n:
        return "religious"
    if "crypto" in n or n.startswith("8_"):
        return "crypto"
    if "stoic" in n or "6_stoic" in n:
        return "stoic"
    if "mystery" in n or "paranormal" in n or "13_" in n:
        return "mystery"
    if "kids" in n or "36_" in n or "çocuk" in n:
        return "kids"
    return "default"


def _seed_rng(title: str, niche_id: str, variation: int = 0) -> random.Random:
    h = hashlib.sha256(f"{title}|{niche_id}|{variation}".encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def pick_pov_angle(title: str, niche_id: str, variation: int = 0) -> str:
    fam = _family(niche_id)
    bank = _POV_BANK.get(fam) or _POV_BANK["default"]
    rng = _seed_rng(title, niche_id, variation)
    return rng.choice(bank)


def mute_hook_line(title: str, angle: str, lang: str = "tr") -> str:
    """
    First-frame caption for muted autoplay — ≤10 words, claim-first.
    """
    openers = _HOOK_OPENERS.get(angle) or _HOOK_OPENERS["soru"]
    opener = openers[hash(title + angle) % len(openers)]
    # Strip fluff from title for the claim
    claim = re.sub(r"[\"“”]", "", (title or "").strip())
    claim = re.sub(r"\s+", " ", claim)
    # Keep first ~6 words of topic as the payload
    words = claim.split()
    payload = " ".join(words[:8]) if words else "bu detay"
    if lang != "tr":
        return f"{opener} {payload}"[:90]
    line = f"{opener} {payload}"
    # Hard cap ~10 words for mute readability
    parts = line.split()
    if len(parts) > 10:
        line = " ".join(parts[:10])
    return line.strip()


def _strip_generic(narr: str) -> str:
    t = (narr or "").strip()
    if _GENERIC_FILLER.match(t):
        return ""
    # Drop trailing filler clauses
    t = re.sub(
        r"\s*(Bunu aklında tut\.?|Devamını izle\.?|Takip et ve bildirimleri aç\.?)\s*$",
        "",
        t,
        flags=re.I,
    )
    return t.strip()


def _inject_specificity(narr: str, angle: str, title: str, lang: str) -> str:
    t = _strip_generic(narr)
    if not t:
        t = mute_hook_line(title, angle, lang=lang)
    # Already specific enough?
    has_digit = bool(re.search(r"\d", t))
    has_contrast = bool(re.search(r"\b(ama|ancak|oysa|aslında|çünkü|ama)\b", t, re.I))
    has_you = bool(re.search(r"\b(sen|siz|senin|sizin|dün|bugün)\b", t, re.I))
    if has_digit or (has_contrast and has_you) or len(t.split()) >= 14:
        return t
    # Angle-specific spice (Turkish)
    spice = {
        "itiraf": " — ve çoğu kişi bunu atlıyor.",
        "uyarı": " Sakın bu videonun sonunu görmeden kaydırma.",
        "sayı": " Tek bir ayrıntı yeter.",
        "paradoks": " Mantığın tersine işliyor.",
        "gizli": " Asıl nokta görünmüyor.",
        "soru": " Cevabı beklediğin yerde değil.",
        "kanıt": " İz var, tesadüf yok.",
        "yasak": " Kimse açıkça söylemez.",
        "oyun": " Bir turda öğrenirsin.",
        "merak": " İçerisi dışarıdan farklı.",
        "kahraman": " Küçük bir cesaret yeter.",
    }.get(angle, " Bundan sonra bakışın değişir.")
    if lang != "tr":
        spice = " — and most people miss this."
    if not t.endswith((".", "!", "?", "…")):
        t = t + "."
    return (t + spice).strip()


def _rewrite_opening_scene(scene: Dict[str, Any], hook: str, angle: str, title: str, lang: str) -> None:
    narr = _inject_specificity(scene.get("narration") or "", angle, title, lang)
    # Ensure hook claim leads the narration
    if hook and not narr.lower().startswith(hook.split(":")[0].lower()[:8]):
        # Prepend hook as first sentence if missing
        rest = narr
        if rest.lower().startswith(hook.lower()[:12]):
            scene["narration"] = rest
        else:
            scene["narration"] = f"{hook} {rest}".strip()
    else:
        scene["narration"] = narr
    scene["mute_hook_line"] = hook
    scene["mood"] = scene.get("mood") or "urgent"
    # Shot description for editors / AI video
    if not scene_description_ok(scene.get("scene_description") or ""):
        scene["scene_description"] = (
            f"Close vertical 9:16 cold open, high contrast, text-ready negative space top third, "
            f"subject matching: {(title or 'topic')[:60]}, cinematic practical light"
        )


def scene_description_ok(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 12:
        return False
    if re.search(r"^\(?\s*scene_description\s*\)?$", t, re.I):
        return False
    return True


def _rewrite_closing_loop(scenes: List[Dict[str, Any]], hook: str, lang: str) -> None:
    if len(scenes) < 2:
        return
    first_tokens = set(re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{4,}", (scenes[0].get("narration") or "").lower()))
    last = scenes[-1]
    narr = _strip_generic(last.get("narration") or "")
    # Loop line ties back to hook promise
    if lang == "tr":
        loop = "Başa dön: vaat buydu — şimdi sen karar ver."
        if hook:
            short_hook = " ".join(hook.split()[:6])
            loop = f"Başa dön — {short_hook} Cevabı gördün; kaydırma, bir kez daha bak."
    else:
        loop = "Loop it: that was the promise — you decide."
    # Keep some of original if substantive
    if len(narr.split()) >= 8 and first_tokens & set(re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{4,}", narr.lower())):
        last["narration"] = f"{narr} {loop}".strip()
    else:
        last["narration"] = loop
    last["loop_closure"] = True


def _diversify_middles(scenes: List[Dict[str, Any]], angle: str, title: str, lang: str) -> None:
    for i, s in enumerate(scenes[1:-1] if len(scenes) > 2 else scenes[1:], start=1):
        s["narration"] = _inject_specificity(s.get("narration") or "", angle, title, lang)
        # Mild mood rotation so 13× same mood dies
        moods = ("tense", "urgent", "dramatic", "calm", "energetic", "curious")
        if (s.get("mood") or "").lower() in ("", "stoic calm contemplative", "stoic"):
            s["mood"] = moods[i % len(moods)]


def edit_directives(scenes: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Composer / UI hints that mimic CapCut/Submagic craft."""
    n = max(1, len(scenes))
    total = sum(float(s.get("duration") or 3.5) for s in scenes) or 45.0
    avg = total / n
    return {
        "max_shot_hold_sec": 3.5,
        "target_cut_sec": 2.8 if avg > 3.2 else max(2.0, avg * 0.85),
        "caption_style": "karaoke_mid_frame",
        "caption_words_per_chunk": 3,
        "caption_y_position": 0.52,  # mid-frame — Shorts UI covers bottom
        "mute_hook_overlay_sec": 1.6,
        "pattern_interrupt_first_sec": 1.2,
        "loop_last_frame_match_first": True,
        "sfx_on_punch_words": True,
        "avoid_static_hold_over_sec": 4.0,
        "visual_change_every_sec": 3.0,
        "rationale": "Submagic/CapCut-like density: cut 2–4s, mid karaoke captions, cold-open hook",
    }


def enforce_shot_holds(
    scenes: List[Dict[str, Any]],
    *,
    max_hold: float = 3.5,
    min_hold: float = 2.0,
    band_min: float = 38.0,
    band_max: float = 60.0,
) -> List[Dict[str, Any]]:
    """
    Cap per-scene hold (anti-static) then rescale total into Shorts band.
    Mutates scenes in place; returns same list.
    """
    if not scenes:
        return scenes
    for s in scenes:
        d = float(s.get("duration") or 3.0)
        s["duration"] = round(max(min_hold, min(max_hold, d)), 2)
    total = sum(float(s.get("duration") or min_hold) for s in scenes)
    if total < band_min or total > band_max:
        target = max(band_min, min(band_max, total))
        scale = target / max(total, 0.01)
        for s in scenes:
            nd = float(s.get("duration") or min_hold) * scale
            s["duration"] = round(max(min_hold, min(max_hold, nd)), 2)
        # If still short (many scenes * max_hold still < band_min), allow mild stretch
        total2 = sum(float(s.get("duration") or min_hold) for s in scenes)
        if total2 < band_min and scenes:
            deficit = band_min - total2
            bump = deficit / len(scenes)
            for s in scenes:
                s["duration"] = round(min(max_hold + 0.4, float(s["duration"]) + bump), 2)
    return scenes


def subtitle_opts_from_craft(human_craft: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge karaoke mid-frame prefs into subtitle_opts for compose_video."""
    if not human_craft:
        return {}
    d = human_craft.get("edit_directives") or {}
    opts: Dict[str, Any] = {
        "color": "#FFFFFF",
        "highlight_color": "#FFD700",
        "stroke_color": "#000000",
        "stroke_width": 5,
        "font_size": 54,
        "font_name": "Anton",
        "uppercase": True,
        "glow": True,
        "y_position": float(d.get("caption_y_position") or 0.52),
        "max_words_per_line": int(d.get("caption_words_per_chunk") or 3),
        "max_words_per_frame": int(d.get("caption_words_per_chunk") or 3),
        "human_craft": True,
        "allow_mid_frame": True,
    }
    return opts


def clamp_interrupt_duration(human_craft: Optional[Dict[str, Any]], default: float = 1.5) -> float:
    d = (human_craft or {}).get("edit_directives") or {}
    try:
        return max(0.8, min(2.0, float(d.get("pattern_interrupt_first_sec") or default)))
    except (TypeError, ValueError):
        return default


def discovery_beast_score(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict seed-test survival (0–100).
    Components map to creator reports: hook, density, loop, share bait, uniqueness.
    """
    scenes = plan.get("scenes") or []
    if not scenes:
        return {"score": 0.0, "pass": False, "components": {}, "fail_reasons": ["no_scenes"]}

    hook = (scenes[0].get("mute_hook_line") or scenes[0].get("narration") or "").strip()
    hook_words = len(hook.split())
    hook_s = 1.0 if 4 <= hook_words <= 12 and _SHARE_BAIT.search(hook) else (
        0.7 if 4 <= hook_words <= 14 else 0.3
    )

    # Visual / duration density
    holds = [float(s.get("duration") or 3.5) for s in scenes]
    over = sum(1 for h in holds if h > 4.0)
    density_s = 1.0 if over == 0 else (0.6 if over <= 2 else 0.25)

    loop_flag = bool(scenes[-1].get("loop_closure")) or bool(
        set(re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{4,}", (scenes[0].get("narration") or "").lower()))
        & set(re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{4,}", (scenes[-1].get("narration") or "").lower()))
    )
    loop_s = 1.0 if loop_flag else 0.35

    full = " ".join((s.get("narration") or "") for s in scenes)
    share_s = 1.0 if _SHARE_BAIT.search(full) else 0.4

    # Uniqueness vs self-similarity
    from compliance import scene_template_similarity, commentary_angle_score

    sim = scene_template_similarity(scenes)
    uniq_s = 1.0 if sim < 0.45 else (0.55 if sim < 0.6 else 0.2)
    angle_s = commentary_angle_score(full, keyword=str(plan.get("keyword") or plan.get("title") or ""))

    score = (
        30 * hook_s
        + 20 * density_s
        + 20 * loop_s
        + 15 * share_s
        + 10 * uniq_s
        + 5 * angle_s
    )
    fails = []
    if hook_s < 0.5:
        fails.append("weak_mute_hook")
    if density_s < 0.5:
        fails.append("shots_too_long_static")
    if loop_s < 0.5:
        fails.append("no_loop_closure")
    if uniq_s < 0.5:
        fails.append("scenes_interchangeable")
    if angle_s < 0.35:
        fails.append("generic_commentary")

    return {
        "score": round(score, 1),
        "pass": score >= 58 and not any(
            f in fails for f in ("weak_mute_hook", "scenes_interchangeable", "generic_commentary")
        ),
        "components": {
            "mute_hook": round(hook_s * 100, 1),
            "cut_density": round(density_s * 100, 1),
            "loop": round(loop_s * 100, 1),
            "share_bait": round(share_s * 100, 1),
            "uniqueness": round(uniq_s * 100, 1),
            "commentary_angle": round(angle_s * 100, 1),
        },
        "fail_reasons": fails,
        "policy_note": "High score ≠ guaranteed Discover; low score ≈ swipe-away death in seed test",
    }


def apply_human_craft(
    plan: Dict[str, Any],
    *,
    title: str = "",
    niche_id: str = "",
    language: str = "tr",
    variation: int = 0,
) -> Dict[str, Any]:
    """
    Mutates and returns plan with human-craft metadata + rewritten narrations.
    """
    if not isinstance(plan, dict):
        return plan
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return plan

    title = title or plan.get("keyword") or plan.get("title") or ""
    niche_id = niche_id or plan.get("niche_id") or ""
    lang = language or plan.get("language") or "tr"
    angle = pick_pov_angle(title, niche_id, variation=variation)
    hook = mute_hook_line(title, angle, lang=lang)

    _rewrite_opening_scene(scenes[0], hook, angle, title, lang)
    if len(scenes) > 1:
        _diversify_middles(scenes, angle, title, lang)
        _rewrite_closing_loop(scenes, hook, lang)

    # Cap static holds BEFORE scoring density (otherwise discovery always fails long shots)
    enforce_shot_holds(scenes, max_hold=3.5, min_hold=2.0)

    # Rebuild full narration
    plan["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in scenes if (s.get("narration") or "").strip()
    )
    plan["keyword"] = plan.get("keyword") or title
    plan["title"] = plan.get("title") or title
    plan["niche_id"] = niche_id or plan.get("niche_id")
    plan["total_duration"] = round(sum(float(s.get("duration") or 0) for s in scenes), 2)

    directives = edit_directives(scenes)
    discovery = discovery_beast_score(plan)

    # Channel voice fingerprint — same niche still differs by title seed
    voice_id = hashlib.sha1(f"{niche_id}|{angle}|{title[:40]}".encode()).hexdigest()[:10]

    plan["human_craft"] = {
        "pov_angle": angle,
        "mute_hook_line": hook,
        "channel_voice_id": voice_id,
        "edit_directives": directives,
        "discovery_beast": discovery,
        "anti_slop": {
            "no_generic_filler": True,
            "unique_pov_per_video": True,
            "loop_required": True,
            "interchangeable_scenes_blocked": discovery["score"] >= 40,
        },
        "manifesto": "HUMAN_CRAFTED_SHORTS.md",
    }
    # Flatten for UI convenience
    plan.setdefault("meta", {})
    plan["meta"]["human_craft"] = plan["human_craft"]
    plan["meta"]["discovery_beast"] = discovery
    return plan


def human_craft_hard_reject(plan: Dict[str, Any]) -> Tuple[bool, str]:
    """True, reason if plan should not ship as 'quality'."""
    hc = plan.get("human_craft") or (plan.get("meta") or {}).get("human_craft") or {}
    disc = hc.get("discovery_beast") or {}
    if not disc:
        return True, "missing_human_craft_pass"
    if not disc.get("pass"):
        return True, ",".join(disc.get("fail_reasons") or ["discovery_beast_fail"])
    return False, ""
