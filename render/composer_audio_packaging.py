"""
FFmpeg Process Supervision, Progress Logging, A/V Duration Sync,
and Manual Upload / Proof Packaging for `video_composer.py`.

Audio mastering and SFX/BGM mixing live in `render/composer_mastering.py` and are
re-exported here for backward compatibility.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import wave
from typing import Any, Callable, Dict, List, Optional, Tuple

import imageio_ffmpeg
from proglog import ProgressBarLogger

import config
from bgm_manager import (
    align_scenes_to_bgm_beats,
    get_bgm_path,
    mix_narration_and_bgm,
)
from render.composer_mastering import (
    _COMPOSER_AUDIO_TEMP_SUFFIXES,
    _cleanup_composer_audio_files,
    _select_auto_bgm,
    build_composer_audio_master,
)
from sfx_manager import add_sfx_to_narration


class MoviePyProgressLogger(ProgressBarLogger):
    def __init__(self, callback=None, cancel_check=None, *args, **kwargs):
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ("ignore_new_bars",)}
        try:
            super().__init__(*args, **filtered_kwargs)
        except TypeError:
            try:
                super().__init__(
                    bars=None,
                    ignored_bars=None,
                    logged_bars="all",
                    min_time_interval=0,
                    ignore_bars_under=0,
                )
            except Exception:
                try:
                    super().__init__()
                except Exception:
                    pass
        self.ui_callback = callback
        self.cancel_check = cancel_check
        self.last_log_time = 0.0
        self.last_frame_pct = -1
        self.print_messages = False

    def callback(self, **changes):
        pass

    def log_message(self, message):
        pass

    def bars_callback(self, bar, attr, value, old_value=None):
        if self.cancel_check and self.cancel_check():
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
        if bar == "t" and attr == "index":
            total = self.bars["t"].get("total", 0)
            if total > 0:
                now = time.time()
                frame_pct = int((value / total) * 100)
                if (
                    (now - self.last_log_time >= 0.8)
                    or (frame_pct >= self.last_frame_pct + 2)
                    or value >= total
                ):
                    self.last_log_time = now
                    self.last_frame_pct = frame_pct
                    overall_pct = int(75 + (value / total) * 23)
                    msg = f"[FFmpeg Export] %{frame_pct} ({int(value)}/{int(total)} kare kodlandı)"
                    print(f"  [Composer] {msg}", flush=True)
                    if self.ui_callback:
                        try:
                            self.ui_callback(overall_pct, msg)
                        except Exception:
                            pass


def write_composer_manual_upload_and_proof_pack(
    *,
    output_path: str,
    title: str,
    scene_clips: list,
    retention_metadata: Optional[dict],
    thumb_path: str,
    anti_duplicate: bool,
    split_screen: bool,
    enable_ken_burns: bool,
    export_seo_operator_pack_fn: Callable,
) -> None:
    """Writes manual upload info JSON/TXT, canonical output package, and ProofArchiver dossier."""
    try:
        from proof_archiver import proof_archiver
        from database import get_video_stats

        clean_title = title or os.path.splitext(os.path.basename(output_path))[0]
        render_stats = get_video_stats()
        total_renders = int(render_stats.get("total_completed") or 0)
        script_text = " ".join(
            str(sc.get("narration", "")) for sc in scene_clips if sc.get("narration")
        )
        borderline_scan = proof_archiver.sanitize_borderline_words(script_text) if script_text else {}
        operator = export_seo_operator_pack_fn(
            keyword=clean_title,
            title=clean_title,
            source_name=getattr(config, "NICHE", "") or "general",
            retention_metadata=retention_metadata,
            script_context=script_text,
            lang=str(getattr(config, "LANGUAGE", "tr") or "tr"),
            video_filename=os.path.basename(output_path),
            thumb_path=os.path.basename(output_path.rsplit(".", 1)[0] + "_thumb.jpg"),
            total_renders=total_renders,
        )
        seo_meta = operator.get("seo") or {}
        engagement = operator.get("studio_engagement") or {}
        live_stream_plan = operator.get("live_stream_plan") or {}
        manual_pkg = {
            **operator,
            "video_file": os.path.basename(output_path),
            "title": seo_meta.get("seo_title", clean_title),
            "description": seo_meta.get("seo_description", ""),
            "tags": seo_meta.get("tags", []),
            "pinned_comment": seo_meta.get("pinned_comment", ""),
            "render_spec": {
                "aspect_ratio": "9:16",
                "resolution": "1080x1920",
                "video_codec": "h264",
                "video_bitrate_mbps": "12-16",
                "audio_codec": "aac",
                "audio_sample_rate_hz": 48000,
                "embedded_subtitles": "ass+srt",
                "items": "397-400,403",
            },
            "borderline_content_scan": borderline_scan,
            "channel_health": proof_archiver.build_actionable_channel_health_checklist(
                total_videos=total_renders, lang="tr"
            ),
            "rule_80_altered_synthetic": "MANUEL KARAR (gerçekçi sentetik/ değiştirilmiş içerik varsa YES)",
            "rule_83_source_reference": "Açıklamaya araştırma ve kaynak referansı eklendi.",
            "anti_detect_ready": False,
            "automatic_upload": False,
            "manual_upload_required": True,
            "manual_upload_checklist": [
                "Görsel, ses ve müzik lisanslarını doğrula.",
                "Kaynak manifesti ve kredileri incele.",
                "AI/değiştirilmiş içerik sorusunu gerçek medya içeriğine göre yanıtla.",
                "YouTube Studio'ya yalnızca insan incelemesinden sonra manuel yükle.",
                "Görüntüleme, beğeni, yorum veya abonelik otomasyonu kullanma.",
            ],
            "size_mb": round(os.path.getsize(output_path) / 1048576, 2),
        }
        info_json = output_path.rsplit(".", 1)[0] + "_manual_upload_info.json"
        info_txt = output_path.rsplit(".", 1)[0] + "_manual_upload_guide.txt"
        with open(info_json, "w", encoding="utf-8") as fj:
            json.dump(manual_pkg, fj, ensure_ascii=False, indent=2)
        reupload_guidance = operator.get("reupload_guidance") or {}
        feed_distribution = operator.get("feed_distribution_advisory") or {}
        algorithm_reset = operator.get("algorithm_reset_guidance") or {}
        traffic_advisory = operator.get("traffic_sources_advisory") or {}
        momentum_advisory = operator.get("channel_momentum_advisory") or {}
        end_screen = operator.get("end_screen_guidance") or {}
        competitor_brief = operator.get("competitor_analysis") or {}
        contact_guidance = operator.get("channel_contact") or {}
        upload_sched = operator.get("upload_schedule") or {}
        cta_timing = operator.get("cta_timing") or {}
        studio_meta = operator.get("studio_metadata") or {}
        with open(info_txt, "w", encoding="utf-8") as ft:
            ft.write(
                f"=== YOUTUBE SHORTS MANUEL YÜKLEME REHBERİ ===\n\n"
                f"📌 VİDEO BAŞLIĞI:\n{manual_pkg['title']}\n\n"
                f"📌 VİDEO AÇIKLAMASI (Kural 83 Kaynak ve Fair Use Referanslı):\n{manual_pkg['description']}\n\n"
                f"📌 VİDEO ETİKETLERİ:\n{', '.join(manual_pkg['tags'])}\n\n"
                f"📌 STUDIO METADATA (Items 354-405):\n"
                f"Konum: {studio_meta.get('location_tag')} | Dil: {studio_meta.get('audience_language')}\n"
                f"Kategori: {studio_meta.get('category_label')} | Playlist: {studio_meta.get('playlist_suggestion')}\n"
                f"{studio_meta.get('tags_csv')}\n\n"
                f"📌 İLK YORUM (Sabitleyin — Item 350):\n{manual_pkg['pinned_comment']}\n\n"
                f"❤️ YORUM KALP (Item 351):\n{engagement.get('heart_action', '')}\n\n"
                f"💬 İLK 2 SAAT YORUM YANITI (Item 374):\n{engagement.get('reply_action', '')}\n\n"
                f"🛡️ SPAM YORUM FİLTRESİ (Item 375):\n{engagement.get('spam_filter_action', '')}\n\n"
                f"📺 CANLI YAYIN PLANI (Item 384):\n{live_stream_plan.get('schedule', '')}\n"
                f"{live_stream_plan.get('studio_action', '')}\n\n"
                f"🚫 YENİDEN YÜKLEME UYARISI (Item 380):\n{reupload_guidance.get('rule', '')}\n"
                f"{reupload_guidance.get('action', '')}\n\n"
                f"📈 FEED DAĞITIM İVMESİ (Item 387):\n{feed_distribution.get('message', '')}\n\n"
                f"🔄 ALGORİTMA RESET (Item 394):\n{algorithm_reset.get('rule', '')}\n"
                f"{algorithm_reset.get('action', '')}\n\n"
                f"📊 TRAFİK KAYNAKLARI (Items 406-409):\n{traffic_advisory.get('diagnosis', '')}\n"
                f"Shorts Feed hedef: ≥%{traffic_advisory.get('shorts_feed_target_pct', 80):.0f}\n\n"
                f"⏳ SABIR EŞİĞİ (Item 410):\n{momentum_advisory.get('message', '')}\n\n"
                f"🔗 END SCREEN / LINK (Item 392):\n{end_screen.get('end_screen_action', '')}\n\n"
                f"🎯 RAKİP ANALİZİ (Item 395):\n{competitor_brief.get('action', '')}\n\n"
                f"📧 KANAL İLETİŞİM (Item 396):\n{contact_guidance.get('about_section_text', '')}\n\n"
                f"🎬 RENDER TEKNİK (Items 397-400, 403):\n"
                f"9:16 1080x1920 · H.264 12-16 Mbps · AAC 48kHz · ASS/SRT gömülü altyazı\n\n"
                f"🛡️ TOPLULUK KELİME TARAMASI (Item 390):\n"
                f"{'Temiz' if borderline_scan.get('is_clean', True) else 'Şüpheli kelimeler: ' + ', '.join(borderline_scan.get('flagged_words', []))}\n\n"
                f"⏰ YÜKLEME SAATİ (Items 362-363):\n"
                f"{upload_sched.get('primary_window', '')} ({upload_sched.get('timezone', '')})\n\n"
                f"🔔 CTA ZAMANLAMASI (Item 367):\n"
                f"Abone Ol overlay ~{cta_timing.get('cta_start_second', 27)}s — {cta_timing.get('rule_compliance', '')}\n\n"
                f"📌 STUDIO KANAL ANAHTAR KELİMELERİ (Item 358):\n"
                f"{', '.join(manual_pkg.get('channel_master_keywords', []))}\n\n"
                f"⚠️ YOUTUBE STUDIO ETİKET AYARI (Kural 80):\n"
                f"- Gerçekçi sentetik veya değiştirilmiş gerçek olay/kişi varsa YES; yoksa NO seçimini içeriğe göre yapın.\n"
                f"- Bu çıktı otomatik yüklenmez; insan incelemesi sonrası manuel Studio yüklemesi gerekir.\n\n"
                f"🛡️ DOSYA GÜVENLİK BİLGİSİ:\n"
                f"- Dosya byte'ları ve oluşturulma zamanı değiştirilmedi.\n"
                f"- Anti-detect, sahte etkileşim ve metadata spoofing kullanılmadı.\n"
            )
        print(f"  [Composer] [OK] Manuel yükleme rehberi hazırlandı: {os.path.basename(info_txt)}")
        try:
            from compliance import export_output_package, ai_disclosure_block
            package_dir = output_path.rsplit(".", 1)[0] + "_package"
            export_output_package(
                package_dir,
                video_path=output_path,
                title=manual_pkg.get("title", clean_title),
                description=manual_pkg.get("description", ""),
                tags=manual_pkg.get("tags", []),
                source_manifest={
                    "version": 1,
                    "clips": [],
                    "notes": ["Clip provider/license metadata must be reviewed before upload."],
                },
                compliance={"ai_disclosure": ai_disclosure_block(lang=str(getattr(config, "LANGUAGE", "tr") or "tr"))},
                ai_disclosure=ai_disclosure_block(lang=str(getattr(config, "LANGUAGE", "tr") or "tr")),
                thumbnail_path=thumb_path,
                language=str(getattr(config, "LANGUAGE", "tr") or "tr"),
            )
            print(f"  [Composer] [OK] Canonical output package hazırlandı: {os.path.basename(package_dir)}")
        except Exception as package_err:
            print(f"  [Composer] Canonical output package uyarısı: {package_err}")
    except Exception as mie:
        print(f"  [Composer] Manuel yükleme paketi uyarısı: {mie}")

    try:
        from proof_archiver import proof_archiver
        proof_archiver.archive_video_proof(
            video_filename=os.path.basename(output_path),
            title=os.path.splitext(os.path.basename(output_path))[0],
            niche="auto_detected",
            script_text=" ".join(s.get("narration", "") for s in scene_clips),
            scenes=scene_clips,
            render_params={
                "anti_duplicate": anti_duplicate,
                "fps": config.FPS,
                "split_screen": split_screen,
                "ken_burns": enable_ken_burns,
            },
        )
        print("  [ProofArchiver] [OK] Proof dossier archived.")
    except Exception as pe:
        print(f"  [ProofArchiver] Notice: {pe}")


def _run_cancellable_ffmpeg(command, cwd, cancel_check, on_started=None):
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if on_started:
        on_started()
    try:
        while True:
            if cancel_check and cancel_check():
                raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")
            try:
                stdout, stderr = proc.communicate(timeout=0.25)
                return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                continue
    finally:
        try:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError as exc:
                    print(f"  [Composer] FFmpeg terminate uyarısı: {exc}", flush=True)
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except OSError as exc:
                    print(f"  [Composer] FFmpeg kill uyarısı: {exc}", flush=True)
                proc.wait()
        finally:
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()


def enforce_av_duration_sync(
    video_path: str,
    output_path: str,
    tolerance_sec: float = 0.05,
) -> str:
    """
    Item 129 – Video Dosyasında Ses ve Görüntü Süre Uyuşmazlığı Koruması.
    Ses ile görüntünün bitiş süresi 0.05 saniye hassasiyetle eşitlenir.
    """
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    ffprobe = shutil.which("ffprobe") or ffmpeg.replace("ffmpeg", "ffprobe")

    try:
        probe_cmd = [
            ffprobe, "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            video_path,
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True)
        data = json.loads(probe.stdout)
        streams = data.get("streams", [])

        video_dur = None
        audio_dur = None
        for s in streams:
            codec_type = s.get("codec_type", "")
            dur = float(s.get("duration", 0) or 0)
            if codec_type == "video" and dur > 0:
                video_dur = dur
            elif codec_type == "audio" and dur > 0:
                audio_dur = dur

        if video_dur is None or audio_dur is None:
            print("    [Item 129] Stream süreleri ölçülemedi, atlanıyor.")
            return video_path

        diff = abs(video_dur - audio_dur)
        print(f"    [Item 129] Video: {video_dur:.3f}s | Audio: {audio_dur:.3f}s | Fark: {diff:.4f}s")

        if diff <= tolerance_sec:
            print(f"    [Item 129] Süre farkı tolerans içinde ({diff:.4f}s ≤ {tolerance_sec}s). Hizalama atlandı.")
            return video_path

        print(f"    [Item 129] Süre uyuşmazlığı tespit edildi ({diff:.4f}s). Hizalanıyor...")

        if audio_dur > video_dur:
            filter_v = f"[0:v]tpad=stop_mode=clone:stop_duration={diff:.4f}[v]"
            filter_str = f"{filter_v};[0:a]acopy[a]"
        else:
            filter_str = "[0:v]copy[v];[0:a]apad=pad_dur={diff:.4f}[a]".format(diff=diff)

        cmd = [
            ffmpeg, "-y",
            "-i", video_path,
            "-filter_complex", filter_str.format(diff=diff),
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    [Item 129] Ses-görüntü süreleri hizalandı → {output_path}")
            return output_path
        else:
            print(f"    [Item 129] Hizalama hatası, orijinal korunuyor: {result.stderr[:200]}")
            return video_path
    except Exception as e:
        print(f"    [Item 129] Hata: {e}")
        return video_path
