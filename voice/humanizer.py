"""
VoiceHumanizer Coordinator Class & Singleton
"""
from typing import Dict, List, Any, Optional

from .gender import select_voice_gender, select_dynamic_voice_actor
from .script_humanizer import (
    SPEECH_RHYTHM,
    apply_pronunciation_library,
    build_speech_rhythm_segments,
    extract_reaction_cues,
    humanize_script_ssml,
    sanitize_ai_cliches,
    clean_narration_for_speech,
    synthesize_natural_pauses,
    get_asmr_voice_settings,
    apply_micro_pauses,
    apply_emphasis_pitch_jumps,
    apply_climax_tempo_curve,
    inject_monologue_text_pauses,
    apply_question_pitch_inflection,
    inject_shock_silence_ssml,
)
from .audio_dsp import (
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
    lock_bass_frequencies_to_mono,
    apply_phase_aligned_mix,
    apply_audio_pitch_jump,
    apply_noise_gate,
    export_master_and_stream_audio,
    run_mobile_device_audio_check,
    accelerate_audio_tempo,
    apply_reverse_reverb_whisper,
    apply_audio_question_inflection,
    apply_shock_silence_cut,
    mix_intro_punch_bgm,
    align_visual_cue_to_audio,
    audit_av_sync_precision,
    apply_outro_music_swell,
)
from .acoustic_assets import (
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
    ensure_quiz_ding_sfx,
    inject_quiz_ding,
    ensure_quiz_buzzer_sfx,
    inject_quiz_buzzer,
    ensure_swallow_sound,
    inject_monologue_pause_and_swallow,
    ensure_vinyl_crackle_sfx,
    inject_vinyl_crackle_layer,
    ensure_dramatic_piano_note_sfx,
    inject_dramatic_piano_layer,
    ensure_cyberpunk_synth_bass_sfx,
    inject_cyberpunk_synth_bass,
)

class VoiceHumanizer:
    """Processes Edge-TTS output and scripts to achieve broadcast-level humanization."""

    SPEECH_RHYTHM = SPEECH_RHYTHM

    @staticmethod
    def apply_pronunciation_library(text: str, engine_type: str = "plain") -> str:
        return apply_pronunciation_library(text, engine_type)

    @staticmethod
    def build_speech_rhythm_segments(text: str) -> List[Dict[str, Any]]:
        return build_speech_rhythm_segments(text)

    @staticmethod
    def extract_reaction_cues(text: str) -> List[str]:
        return extract_reaction_cues(text)

    @staticmethod
    def humanize_script_ssml(text: str, is_hook: bool = False, lang: str = "tr") -> str:
        return humanize_script_ssml(text, is_hook, lang)

    @staticmethod
    def sanitize_ai_cliches(text: str) -> str:
        return sanitize_ai_cliches(text)

    @staticmethod
    def clean_narration_for_speech(text: str) -> str:
        return clean_narration_for_speech(text)

    @staticmethod
    def synthesize_natural_pauses(text: str, engine_type: str = "ssml", break_ms: int = 150) -> str:
        return synthesize_natural_pauses(text, engine_type, break_ms)

    @staticmethod
    def apply_studio_eq_and_warmth(input_wav: str, output_wav: str) -> str:
        return apply_studio_eq_and_warmth(input_wav, output_wav)

    @staticmethod
    def apply_high_pass_filter(input_wav: str, output_wav: str, cutoff_hz: float = 80.0) -> str:
        return apply_high_pass_filter(input_wav, output_wav, cutoff_hz)

    @staticmethod
    def apply_voice_warmth_eq(input_wav: str, output_wav: str, center_freq: float = 220.0, gain_db: float = 2.0) -> str:
        return apply_voice_warmth_eq(input_wav, output_wav, center_freq, gain_db)

    @staticmethod
    def apply_presence_air_eq(input_wav: str, output_wav: str, center_freq: float = 11000.0, gain_db: float = 1.5) -> str:
        return apply_presence_air_eq(input_wav, output_wav, center_freq, gain_db)

    @staticmethod
    def apply_stereo_widener(input_music_wav: str, output_music_wav: str, width: float = 1.4) -> str:
        return apply_stereo_widener(input_music_wav, output_music_wav, width)

    @staticmethod
    def mix_wide_stereo_with_center_vocal(bg_music_wav: str, vocal_wav: str, output_wav: str,
                                          music_vol: float = 0.18, vocal_vol: float = 1.0,
                                          stereo_width: float = 1.4) -> str:
        return mix_wide_stereo_with_center_vocal(bg_music_wav, vocal_wav, output_wav, music_vol, vocal_vol, stereo_width)

    @staticmethod
    def ensure_sub_bass_impact_sfx(output_path: str = None, duration: float = 0.8, base_freq: float = 45.0) -> str:
        return ensure_sub_bass_impact_sfx(output_path, duration, base_freq)

    @staticmethod
    def inject_sub_bass_impact(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0, volume: float = 0.85) -> str:
        return inject_sub_bass_impact(audio_wav, output_wav, timestamp_sec, volume)

    @staticmethod
    def ensure_riser_whoosh_sfx(output_path: str = None, duration: float = 0.25) -> str:
        return ensure_riser_whoosh_sfx(output_path, duration)

    @staticmethod
    def sync_riser_whoosh_transitions(audio_wav: str, scene_cut_times: list, output_wav: str, volume: float = 0.65) -> str:
        return sync_riser_whoosh_transitions(audio_wav, scene_cut_times, output_wav, volume)

    @staticmethod
    def ensure_tape_stop_sfx(output_path: str = None, duration: float = 0.40) -> str:
        return ensure_tape_stop_sfx(output_path, duration)

    @staticmethod
    def apply_tape_stop_to_audio(audio_wav: str, output_wav: str, stop_timestamps: list, volume: float = 0.85) -> str:
        return apply_tape_stop_to_audio(audio_wav, output_wav, stop_timestamps, volume)

    @staticmethod
    def ensure_heartbeat_sfx(output_path: str = None, duration: float = 4.0, bpm: float = 65.0) -> str:
        return ensure_heartbeat_sfx(output_path, duration, bpm)

    @staticmethod
    def inject_heartbeat_layer(audio_wav: str, output_wav: str, start_sec: float = 0.0,
                               duration_sec: float = 4.0, volume: float = 0.35, bpm: float = 65.0) -> str:
        return inject_heartbeat_layer(audio_wav, output_wav, start_sec, duration_sec, volume, bpm)

    @staticmethod
    def ensure_ticking_clock_sfx(output_path: str = None, duration: float = 3.0) -> str:
        return ensure_ticking_clock_sfx(output_path, duration)

    @staticmethod
    def inject_ticking_clock(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0,
                             duration: float = 3.0, volume: float = 0.40) -> str:
        return inject_ticking_clock(audio_wav, output_wav, timestamp_sec, duration, volume)

    @staticmethod
    def ensure_typewriter_sfx(output_path: str = None, duration: float = 2.0, speed_cps: float = 11.0) -> str:
        return ensure_typewriter_sfx(output_path, duration, speed_cps)

    @staticmethod
    def inject_typewriter_sfx(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0,
                              duration: float = 2.0, volume: float = 0.35) -> str:
        return inject_typewriter_sfx(audio_wav, output_wav, timestamp_sec, duration, volume)

    @staticmethod
    def apply_micro_pauses(text: str, comma_ms: int = 120, dot_ms: int = 280,
                           question_ms: int = 350, paragraph_ms: int = 450, engine_type: str = "ssml") -> str:
        return apply_micro_pauses(text, comma_ms, dot_ms, question_ms, paragraph_ms, engine_type)

    @staticmethod
    def apply_spectral_notch_filter(input_wav: str, output_wav: str, f1: float = 120.0, f2: float = 4000.0) -> str:
        return apply_spectral_notch_filter(input_wav, output_wav, f1, f2)

    @staticmethod
    def apply_audio_jitter(input_wav: str, output_wav: str, min_speed: float = 0.98, max_speed: float = 1.02) -> str:
        return apply_audio_jitter(input_wav, output_wav, min_speed, max_speed)

    @staticmethod
    def normalize_ebu_r128(input_audio: str, output_audio: str, target_lufs: float = -14.0, true_peak: float = -1.5, lra: float = 11.0) -> str:
        return normalize_ebu_r128(input_audio, output_audio, target_lufs, true_peak, lra)

    @staticmethod
    def measure_audio_loudness(audio_path: str) -> dict:
        return measure_audio_loudness(audio_path)

    @staticmethod
    def apply_telephone_filter(input_audio: str, output_audio: str) -> str:
        return apply_telephone_filter(input_audio, output_audio)

    @staticmethod
    def apply_asmr_whisper_dsp(input_wav: str, output_wav: str) -> str:
        return apply_asmr_whisper_dsp(input_wav, output_wav)

    @staticmethod
    def select_dynamic_voice_actor(target_lang: str = "tr", niche_id: str = "",
                                   keyword: str = "", seed: Optional[str] = None) -> dict:
        return select_dynamic_voice_actor(target_lang, niche_id, keyword, seed)

    @staticmethod
    def get_asmr_voice_settings(niche_id: str, keyword: str) -> dict:
        return get_asmr_voice_settings(niche_id, keyword)

    @staticmethod
    def inject_natural_breaths(narration_wav: str, output_wav: str, interval_seconds: float = 8.0) -> str:
        return inject_natural_breaths(narration_wav, output_wav, interval_seconds)

    @staticmethod
    def inject_sonic_brand_watermark(narration_wav: str, output_wav: str) -> str:
        return inject_sonic_brand_watermark(narration_wav, output_wav)

    @staticmethod
    def ensure_quiz_ding_sfx(output_path: str = None, freq_hz: float = 1800.0, duration: float = 0.45) -> str:
        return ensure_quiz_ding_sfx(output_path, freq_hz, duration)

    @staticmethod
    def inject_quiz_ding(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0, volume: float = 0.55) -> str:
        return inject_quiz_ding(audio_wav, output_wav, timestamp_sec, volume)

    @staticmethod
    def ensure_quiz_buzzer_sfx(output_path: str = None, freq_hz: float = 120.0, duration: float = 0.55) -> str:
        return ensure_quiz_buzzer_sfx(output_path, freq_hz, duration)

    @staticmethod
    def inject_quiz_buzzer(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0, volume: float = 0.5) -> str:
        return inject_quiz_buzzer(audio_wav, output_wav, timestamp_sec, volume)

    @staticmethod
    def lock_bass_frequencies_to_mono(input_audio: str, output_audio: str, cutoff_hz: float = 120.0) -> str:
        return lock_bass_frequencies_to_mono(input_audio, output_audio, cutoff_hz)

    @staticmethod
    def apply_phase_aligned_mix(narration_wav: str, music_wav: str, output_wav: str,
                                music_volume: float = 0.12, cutoff_hz: float = 120.0) -> str:
        return apply_phase_aligned_mix(narration_wav, music_wav, output_wav, music_volume, cutoff_hz)

    # ─── ITEMS 171 - 175 ───

    @staticmethod
    def apply_emphasis_pitch_jumps(text: str, engine_type: str = "ssml",
                                   custom_keywords: Optional[List[str]] = None,
                                   pitch_boost: str = "+12%") -> str:
        """Madde 171: Vurgulu kelimelerde perde (pitch) sıçraması."""
        return apply_emphasis_pitch_jumps(text, engine_type, custom_keywords, pitch_boost)

    @staticmethod
    def apply_audio_pitch_jump(input_wav: str, output_wav: str,
                               timestamp_sec: float = 0.0,
                               duration_sec: float = 0.35,
                               pitch_semitones: float = 2.0) -> str:
        """Madde 171: Seste zaman damgalı pitch sıçraması."""
        return apply_audio_pitch_jump(input_wav, output_wav, timestamp_sec, duration_sec, pitch_semitones)

    @staticmethod
    def apply_noise_gate(input_audio: str, output_audio: str,
                         threshold_db: float = -42.0,
                         attack_ms: float = 10.0,
                         release_ms: float = 120.0,
                         range_db: float = -60.0) -> str:
        """Madde 172: Arka plan uğultusunu ve nefes artıklarını sessizliğe çeken noise gate."""
        return apply_noise_gate(input_audio, output_audio, threshold_db, attack_ms, release_ms, range_db)

    @staticmethod
    def export_master_and_stream_audio(input_audio: str,
                                       output_dir: Optional[str] = None,
                                       base_name: str = "audio_export") -> dict:
        """Madde 173: Çoklu ses formatı ihracı (48kHz 24-bit PCM WAV + AAC-LC 320kbps)."""
        return export_master_and_stream_audio(input_audio, output_dir, base_name)

    @staticmethod
    def run_mobile_device_audio_check(voice_or_mix_wav: str,
                                      bgm_wav: Optional[str] = None) -> dict:
        """Madde 174: Mobil tek hoparlör uyumluluk ve mono netlik denetimi."""
        return run_mobile_device_audio_check(voice_or_mix_wav, bgm_wav)

    @staticmethod
    def apply_climax_tempo_curve(sentences_or_scenes: List[Any],
                                 climax_index: Optional[int] = None,
                                 peak_rate: str = "+15%",
                                 buildup_rate: str = "+8%",
                                 engine_type: str = "ssml") -> List[Dict[str, Any]]:
        """Madde 175: Hikaye doruk noktasında kademeli ses hızlanması (%115 tempo)."""
        return apply_climax_tempo_curve(sentences_or_scenes, climax_index, peak_rate, buildup_rate, engine_type)

    @staticmethod
    def accelerate_audio_tempo(input_audio: str, output_audio: str,
                               speed_factor: float = 1.15) -> str:
        """Madde 175: Ses hızını perdesini değiştirmeden %115'e hızlandırma."""
        return accelerate_audio_tempo(input_audio, output_audio, speed_factor)

    # ─── ITEMS 176 - 180 ───

    @staticmethod
    def apply_reverse_reverb_whisper(input_wav: str, output_wav: str,
                                     tail_sec: float = 0.30,
                                     wet_mix: float = 0.40) -> str:
        """Madde 176: Gizem nişinde cümle sonuna 0.3s ters çevrilmiş yankı (reverse reverb)."""
        return apply_reverse_reverb_whisper(input_wav, output_wav, tail_sec, wet_mix)

    @staticmethod
    def ensure_swallow_sound(output_path: str = None) -> str:
        """Madde 177: Doğal boğaz rahatlatma / yutkunma sesi (220ms)."""
        return ensure_swallow_sound(output_path)

    @staticmethod
    def inject_monologue_pause_and_swallow(audio_wav: str, output_wav: str,
                                           interval_seconds: float = 40.0,
                                           volume: float = 0.25) -> str:
        """Madde 177: Uzun monologlarda her 40 saniyede bir doğal duraksama ve yutkunma ekleme."""
        return inject_monologue_pause_and_swallow(audio_wav, output_wav, interval_seconds, volume)

    @staticmethod
    def inject_monologue_text_pauses(text: str, interval_words: int = 65, pause_ms: int = 450, engine_type: str = "ssml") -> str:
        """Madde 177: Metin içi monolog duraksamaları ekleme."""
        return inject_monologue_text_pauses(text, interval_words, pause_ms, engine_type)

    @staticmethod
    def apply_question_pitch_inflection(text: str, pitch_boost: str = "+5%", engine_type: str = "ssml") -> str:
        """Madde 178: Soru cümlelerinin sonunda ses perdesi yukarı bükülmesi (+5%)."""
        return apply_question_pitch_inflection(text, pitch_boost, engine_type)

    @staticmethod
    def apply_audio_question_inflection(input_wav: str, output_wav: str, end_sec: float = 0.40, pitch_semitones: float = 0.85) -> str:
        """Madde 178: Ses seviyesinde soru perdesi yükselme entonasyonu."""
        return apply_audio_question_inflection(input_wav, output_wav, end_sec, pitch_semitones)

    @staticmethod
    def inject_shock_silence_ssml(text: str, trigger_phrases: Optional[List[str]] = None, silence_ms: int = 200) -> str:
        """Madde 179: Şok anında SSML 0.2s mutlak sessizlik."""
        return inject_shock_silence_ssml(text, trigger_phrases, silence_ms)

    @staticmethod
    def apply_shock_silence_cut(audio_wav: str, output_wav: str, shock_timestamps: list, silence_sec: float = 0.20) -> str:
        """Madde 179: Şok anında seste 0.2s mutlak sessizlik oluşturma."""
        return apply_shock_silence_cut(audio_wav, output_wav, shock_timestamps, silence_sec)

    @staticmethod
    def mix_intro_punch_bgm(narration_wav: str, music_wav: str, output_wav: str,
                            intro_blast_sec: float = 1.0, blast_volume: float = 0.85, ducked_volume: float = 0.14) -> str:
        """Madde 180: Videonun ilk 1 saniyesinde müzik %100 hacim, ardından anında ducking."""
        return mix_intro_punch_bgm(narration_wav, music_wav, output_wav, intro_blast_sec, blast_volume, ducked_volume)

    # ─── ITEMS 181 - 185 ───

    @staticmethod
    def ensure_vinyl_crackle_sfx(output_path: str = None, duration: float = 15.0, volume_db: float = -28.0) -> str:
        """Madde 181: Tarihi ve nostaljik nişler için -28dB vinil plak cızırtısı."""
        return ensure_vinyl_crackle_sfx(output_path, duration, volume_db)

    @staticmethod
    def inject_vinyl_crackle_layer(audio_wav: str, output_wav: str, volume_db: float = -28.0) -> str:
        """Madde 181: Sese vinil plak cızırtısı katmanı miksleme."""
        return inject_vinyl_crackle_layer(audio_wav, output_wav, volume_db)

    @staticmethod
    def ensure_dramatic_piano_note_sfx(output_path: str = None, note_freq: float = 220.0, duration: float = 3.5) -> str:
        """Madde 182: Duygusal anlar için yankılı tek nota kuyruklu piyano tınısı."""
        return ensure_dramatic_piano_note_sfx(output_path, note_freq, duration)

    @staticmethod
    def inject_dramatic_piano_layer(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0, volume: float = 0.35) -> str:
        """Madde 182: Sese dramatik piyano katmanı enjeksiyonu."""
        return inject_dramatic_piano_layer(audio_wav, output_wav, timestamp_sec, volume)

    @staticmethod
    def ensure_cyberpunk_synth_bass_sfx(output_path: str = None, duration: float = 4.0, freq_hz: float = 55.0) -> str:
        """Madde 183: Teknoloji/AI haberleri için 55Hz analog cyberpunk synthwave bas darbesi."""
        return ensure_cyberpunk_synth_bass_sfx(output_path, duration, freq_hz)

    @staticmethod
    def inject_cyberpunk_synth_bass(audio_wav: str, output_wav: str, timestamp_sec: float = 0.0, volume: float = 0.35) -> str:
        """Madde 183: Sese cyberpunk analog synth bası enjeksiyonu."""
        return inject_cyberpunk_synth_bass(audio_wav, output_wav, timestamp_sec, volume)

    @staticmethod
    def align_visual_cue_to_audio(visual_cue_time: float, audio_word_timestamps: List[Dict[str, Any]],
                                  target_phrase: str, tolerance_sec: float = 0.05) -> dict:
        """Madde 184: Görsel grafik / yazı kartı başlangıcını konuşma sesine milisaniye hassasiyetinde eşleme."""
        return align_visual_cue_to_audio(visual_cue_time, audio_word_timestamps, target_phrase, tolerance_sec)

    @staticmethod
    def audit_av_sync_precision(video_duration: float, audio_duration: float, tolerance_ms: float = 25.0) -> dict:
        """Madde 184: Video-ses süre uyumu milisaniye denetimi."""
        return audit_av_sync_precision(video_duration, audio_duration, tolerance_ms)

    @staticmethod
    def apply_outro_music_swell(music_audio: str, output_audio: str, total_duration: float,
                                swell_seconds: float = 5.0, boost_db: float = 3.5) -> str:
        """Madde 185: Son 5 saniyede CTA verilirken fon müziğinin kademeli yükselmesi (+3.5dB)."""
        return apply_outro_music_swell(music_audio, output_audio, total_duration, swell_seconds, boost_db)


voice_humanizer = VoiceHumanizer()



