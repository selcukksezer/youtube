"""
Acoustic Voice Humanizer & Studio Audio Engineering Engine (Facade)
Maintained for 100% backwards-compatibility across all tests and pipeline callers.
All core logic is modularly organized in the `voice/` package:
- voice/gender.py           : Voice gender selection from topic/niche cues
- voice/acoustic_assets.py  : Breath sound synthesis, sonic branding chime, whoosh intro, pink noise, ID3 tags
- voice/script_humanizer.py : Pronunciation dictionary, SSML prosody, AI cliché cleansing, text cleaning, natural pauses
- voice/audio_dsp.py        : Studio EQ warmth, notch filters, audio jitter, EBU R128 normalization, telephone band
- voice/humanizer.py        : VoiceHumanizer coordinator class and singleton instance
"""

from voice import (
    select_voice_gender,
    select_dynamic_voice_actor,
    ensure_breath_sound,
    ensure_sonic_branding_chime,
    ensure_whoosh_ding_intro,
    prepend_whoosh_ding_to_narration,
    generate_pink_noise_wav,
    mix_pink_noise_into_narration,
    inject_id3_tags,
    ensure_sub_bass_impact_sfx,
    inject_sub_bass_impact,
    ensure_riser_whoosh_sfx,
    sync_riser_whoosh_transitions,
    ensure_tape_stop_sfx,
    apply_tape_stop_to_audio,
    ensure_heartbeat_sfx,
    inject_heartbeat_layer,
    ensure_ticking_clock_sfx,
    inject_ticking_clock,
    ensure_typewriter_sfx,
    inject_typewriter_sfx,
    PRONUNCIATION_LIBRARY,
    SPEECH_RHYTHM,
    VoiceHumanizer,
    voice_humanizer,
    apply_pronunciation_library,
    build_speech_rhythm_segments,
    extract_reaction_cues,
    humanize_script_ssml,
    sanitize_ai_cliches,
    clean_narration_for_speech,
    synthesize_natural_pauses,
    get_asmr_voice_settings,
    apply_micro_pauses,
    apply_studio_eq_and_warmth,
    apply_high_pass_filter,
    apply_voice_warmth_eq,
    apply_presence_air_eq,
    apply_stereo_widener,
    mix_wide_stereo_with_center_vocal,
    apply_spectral_notch_filter,
    apply_audio_jitter,
    normalize_ebu_r128,
    measure_audio_loudness,
    apply_telephone_filter,
    apply_asmr_whisper_dsp,
    inject_natural_breaths,
    inject_sonic_brand_watermark,
    ensure_quiz_ding_sfx,
    inject_quiz_ding,
    ensure_quiz_buzzer_sfx,
    inject_quiz_buzzer,
    lock_bass_frequencies_to_mono,
    apply_phase_aligned_mix,
    __all__,
)
