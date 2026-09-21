"""
Audio Event Bus — intent-gated SFX (Items 154-159) without duplicate layers.
"""
from __future__ import annotations

from typing import List

from .schema import AudioEvent, DirectorPlan, ScenePlan


def _audio_rules(plan: DirectorPlan) -> dict:
    return (plan.niche_profile or {}).get("audio_rules") or {}


_CONTRAST_CUES = ("ama ", "fakat ", "tersine", "ancak ", "but ", "however", "yet ")


def collect_tape_stop_times(plan: DirectorPlan) -> List[float]:
    """
    Item 156 / P1-10: BGM 0.4s mute on shock/contrast beats.
    Stoic sparse profile: only explicit shock beat_type (no keyword contrast scan).
    """
    rules = _audio_rules(plan)
    sparse = bool(rules.get("sparse_transitions"))
    enable = rules.get("enable_tape_stop", not sparse)
    times: List[float] = []
    for scene in plan.scenes:
        if scene.beat_type == "shock":
            times.append(float(scene.t0))
            continue
        if enable and not sparse:
            narr = (scene.narration or "").lower()
            if any(cue in narr for cue in _CONTRAST_CUES):
                times.append(float(scene.t0))
    return sorted(set(times))


def build_audio_events(plan: DirectorPlan) -> List[AudioEvent]:
    """
    Single authoritative SFX timeline:
    - Item 155: one whoosh per cut (not duplicated elsewhere)
    - Item 154: sub_bass on shock/hook beats only
    - Item 157: heartbeat on tension niche + conflict/climax
    - Item 158: clock only on quiz beats
    - Item 159: typewriter on document beats
    """
    events: List[AudioEvent] = []
    scenes = plan.scenes
    niche = (plan.niche_id or "").lower()
    is_tension_niche = any(k in niche for k in ("mystery", "paranormal", "horror", "dark_psych", "7_dark"))
    rules = _audio_rules(plan)
    sparse = bool(rules.get("sparse_transitions"))
    max_transition_sfx = int(rules.get("max_transition_sfx", 999))
    whoosh_vol = float(rules.get("whoosh_volume", 0.18))
    enable_sub_impact = rules.get("enable_sub_impact", True)
    manifest = plan.effect_manifest or {}
    if manifest.get("item_154_sub_bass") is False:
        enable_sub_impact = False
    whoosh_count = 0

    for i, scene in enumerate(scenes):
        t0 = float(scene.t0)
        # Whoosh before cut (Item 155) — sparse mode: arc beat changes only
        if i > 0:
            add_whoosh = not sparse or scenes[i - 1].beat_type != scene.beat_type
            if add_whoosh and whoosh_count < max_transition_sfx:
                events.append(AudioEvent(
                    sound="whoosh",
                    at=max(0.0, t0 - 0.25),
                    beat_type=scene.beat_type,
                    volume=whoosh_vol,
                    duration=0.25,
                    item_id=155,
                ))
                whoosh_count += 1

        if enable_sub_impact and scene.beat_type in ("shock", "hook") and i == 0:
            events.append(AudioEvent(
                sound="sub_impact",
                at=min(2.5, t0 + scene.duration * 0.35),
                beat_type=scene.beat_type,
                volume=0.22,
                duration=0.4,
                item_id=154,
            ))
        elif enable_sub_impact and scene.beat_type == "shock":
            events.append(AudioEvent(
                sound="sub_impact",
                at=t0 + 0.15,
                beat_type="shock",
                volume=0.20,
                duration=0.4,
                item_id=154,
            ))

        if scene.beat_type == "quiz":
            events.append(AudioEvent(
                sound="clock_tick",
                at=t0,
                beat_type="quiz",
                volume=0.28,
                duration=3.0,
                item_id=158,
            ))

        if scene.beat_type == "document":
            events.append(AudioEvent(
                sound="typewriter",
                at=t0 + 0.2,
                beat_type="document",
                volume=0.25,
                duration=2.0,
                item_id=159,
            ))

        if is_tension_niche and scene.beat_type in ("conflict", "climax", "shock") and i == 1:
            events.append(AudioEvent(
                sound="heartbeat",
                at=t0,
                beat_type=scene.beat_type,
                volume=0.22,
                duration=4.0,
                item_id=157,
            ))

    # Deduplicate near-identical stamps
    events.sort(key=lambda e: (e.at, e.sound))
    deduped: List[AudioEvent] = []
    for ev in events:
        if deduped and deduped[-1].sound == ev.sound and abs(deduped[-1].at - ev.at) < 0.12:
            continue
        deduped.append(ev)

    plan.audio_events = deduped
    return deduped


def apply_audio_events_to_wav(
    narration_wav: str,
    events: List[AudioEvent],
    output_path: str,
    sfx_volume_scale: float = 1.0,
) -> str:
    """Mix intent-gated SFX onto narration via sfx_manager primitives."""
    if not events:
        return narration_wav
    try:
        from sfx_manager import ensure_sfx_files
        import os
        import subprocess
        import imageio_ffmpeg

        whoosh_path, _, _ = ensure_sfx_files()
        try:
            from sfx_manager import _panned_whoosh_path
            whoosh_path = _panned_whoosh_path(whoosh_path)
        except Exception:
            pass
        sfx_dir = os.path.dirname(whoosh_path)
        sound_paths = {
            "whoosh": whoosh_path,
            "sub_impact": os.path.join(sfx_dir, "sub_impact.wav"),
            "heartbeat": os.path.join(sfx_dir, "heartbeat.wav"),
            "clock_tick": os.path.join(sfx_dir, "clock_tick.wav"),
            "typewriter": os.path.join(sfx_dir, "typewriter.wav"),
        }
        # Ensure procedural files exist
        from sfx_manager import ensure_core_sfx_suite
        ensure_core_sfx_suite()

        inputs = ["-i", narration_wav]
        filter_parts = []
        valid = []
        for ev in events:
            sp = sound_paths.get(ev.sound)
            if not sp or not os.path.exists(sp):
                continue
            valid.append(ev)
            inputs.extend(["-i", sp])

        if not valid:
            return narration_wav

        for idx, ev in enumerate(valid):
            delay_ms = int(max(0.0, ev.at) * 1000)
            vol = max(0.05, min(0.6, ev.volume * sfx_volume_scale))
            filter_parts.append(
                f"[{idx+1}:a]adelay={delay_ms}|{delay_ms},volume={vol:.3f}[sfx{idx}]"
            )

        mix_inputs = "".join(f"[sfx{i}]" for i in range(len(valid)))
        fc = (
            f"{';'.join(filter_parts)};"
            f"[0:a]{mix_inputs}amix=inputs={len(valid)+1}:duration=first:dropout_transition=0:normalize=0[outa]"
        )
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y"] + inputs + [
            "-filter_complex", fc, "-map", "[outa]", "-c:a", "pcm_s16le", output_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_path):
            print(f"  [AudioBus] {len(valid)} intent-gated SFX events mixed (Items 154-159)")
            return output_path
    except Exception as e:
        print(f"  [AudioBus] Notice: {e}")
    return narration_wav


def master_audio_one_pass(
    narration_wav: str,
    plan: DirectorPlan,
    output_path: str,
    bgm_track: str = "",
    bgm_volume: float = 0.12,
) -> str:
    """
    Apply roadmap voice layers then intent SFX then BGM in a controlled chain.
    Does not disable items — orchestrates them once.
    """
    import os
    current = narration_wav
    base = output_path.rsplit(".", 1)[0]
    manifest = plan.effect_manifest or {}

    try:
        from voice_humanizer import (
            voice_humanizer,
            mix_pink_noise_into_narration,
            prepend_whoosh_ding_to_narration,
        )

        eq = base + "_eq.wav"
        current = voice_humanizer.apply_studio_eq_and_warmth(current, eq)

        if manifest.get("item_146_compand", True) or manifest.get("item_147_deesser", True):
            from voice.audio_dsp import apply_deesser_compand_master
            dsp146 = base + "_146147.wav"
            current = apply_deesser_compand_master(current, dsp146)

        if manifest.get("item_141_breaths", True):
            br = base + "_breaths.wav"
            current = voice_humanizer.inject_natural_breaths(current, br, interval_seconds=8.0)

        if manifest.get("item_112_whoosh_ding", True):
            intro = base + "_intro112.wav"
            current = prepend_whoosh_ding_to_narration(current, intro)

        if manifest.get("item_108_pink_noise", True) or manifest.get("item_145_room_ambience", True):
            room = base + "_room.wav"
            current = mix_pink_noise_into_narration(current, room, noise_db=-32.0, noise_type="room")

        norm = base + "_norm.wav"
        current = voice_humanizer.normalize_ebu_r128(current, norm)

        if manifest.get("item_87_sonic_watermark", True):
            sonic = base + "_sonic.wav"
            current = voice_humanizer.inject_sonic_brand_watermark(current, sonic)

        if manifest.get("item_101_jitter", True):
            try:
                jit = base + "_jitter.wav"
                current = voice_humanizer.apply_audio_jitter(current, jit, min_speed=0.985, max_speed=1.015)
            except Exception:
                pass

        niche_hint = f"{plan.niche_id or ''} {plan.title or ''}".lower()
        scene_blob = " ".join(
            str(s.narration or "") for s in (plan.scenes or [])[:6]
        ).lower()
        combined = f"{niche_hint} {scene_blob}"

        if manifest.get("item_182_piano", True) and any(
            k in combined for k in ("stoic", "felsefe", "philosophy", "duygusal", "poetry", "dini", "manevi", "tarih")
        ):
            from voice.acoustic_assets import inject_dramatic_piano_layer
            piano_out = base + "_piano182.wav"
            current = inject_dramatic_piano_layer(current, piano_out, timestamp_sec=1.2, volume=0.28)
            print("  [AudioMaster] [Item 182] Dramatik piyano katmanı mikslendi.")

        if manifest.get("item_183_synth_bass", True) and any(
            k in combined for k in ("yapay zeka", "ai", "cyber", "tech", "teknoloji", "gelecek", "robot")
        ):
            from voice.acoustic_assets import inject_cyberpunk_synth_bass
            synth_out = base + "_synth183.wav"
            current = inject_cyberpunk_synth_bass(current, synth_out, timestamp_sec=0.0, volume=0.22)
            print("  [AudioMaster] [Item 183] Cyberpunk synth bass mikslendi.")

        if manifest.get("item_188_crowd_ambience", True) and any(
            k in combined for k in ("haber", "news", "sokak", "street", "borsa", "finans", "kalabalık", "crowd")
        ):
            from voice.acoustic_assets import inject_room_ambience
            amb_out = base + "_crowd188.wav"
            current = inject_room_ambience(current, amb_out, volume=0.08)
            print("  [AudioMaster] [Item 188] Oda/kalabalık ambiyansı mikslendi.")

        if manifest.get("item_191_reverb_chamber", True) and any(
            k in combined for k in (
                "katedral", "cathedral", "manevi", "dini", "spiritual", "epic", "temple", "ibadet", "dua"
            )
        ):
            from voice.audio_dsp import apply_acoustic_reverb_chamber
            rev_out = base + "_reverb191.wav"
            current = apply_acoustic_reverb_chamber(current, rev_out, room_type="cathedral")
            print("  [AudioMaster] [Item 191] Akustik yankı odası uygulandı.")

        if manifest.get("item_195_epic_trailer_voice", True) and any(
            k in combined for k in (
                "epic", "trailer", "evren", "cosmos", "hans", "sinema", "film", "destansı", "cosmic"
            )
        ):
            from voice.audio_dsp import apply_epic_trailer_deep_voice
            epic_out = base + "_epic195.wav"
            current = apply_epic_trailer_deep_voice(current, epic_out, pitch_ratio=0.88)
            print("  [AudioMaster] [Item 195] Derin anlatıcı (trailer) sesi uygulandı.")
    except Exception as e:
        print(f"  [AudioMaster] Voice chain notice: {e}")

    # Intent SFX bus (replaces duplicate whoosh+composer layers)
    if plan.audio_events:
        sfx_out = base + "_sfxbus.wav"
        current = apply_audio_events_to_wav(current, plan.audio_events, sfx_out)

    # BGM
    if bgm_track or True:
        try:
            from bgm_manager import get_cached_bgm_path, get_bgm_path, mix_narration_and_bgm, match_bgm_track_to_niche
            chosen = bgm_track
            if not chosen:
                hint = (plan.niche_id or "") + " " + (plan.title or "")
                matched = match_bgm_track_to_niche(hint)
                chosen = os.path.basename(matched) if matched else ""
            bgm_p = get_cached_bgm_path(chosen) if chosen else get_cached_bgm_path("")
            if chosen and not bgm_p:
                bgm_p = get_bgm_path(chosen)
            if bgm_p:
                mixed = base + "_bgm.wav"
                tape_stops = collect_tape_stop_times(plan)
                current = mix_narration_and_bgm(
                    current,
                    bgm_p,
                    mixed,
                    volume=bgm_volume,
                    tape_stop_times=tape_stops,
                    allow_fade_out=False,
                )
                if tape_stops:
                    print(f"  [AudioMaster] Tape-stop @ {len(tape_stops)} beat(s) (Item 156)")
        except Exception as e:
            print(f"  [AudioMaster] BGM notice: {e}")

    # Two-pass loudnorm toward -14 LUFS (Item 162)
    try:
        from voice_humanizer import voice_humanizer
        target_lufs = float(_audio_rules(plan).get("target_lufs", -14.0))
        final_norm = output_path
        current = voice_humanizer.normalize_ebu_r128(current, final_norm, target_lufs=target_lufs)
    except Exception:
        if current != output_path:
            try:
                import shutil
                shutil.copy2(current, output_path)
                current = output_path
            except Exception:
                pass

    return current if os.path.exists(current) else narration_wav
