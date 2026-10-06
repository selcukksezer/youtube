"""
ShortsVideoCreators CLI Tool.
Implements Bölüm 15.1 of plan.md: Full terminal control interface for automated workflows.

Options:
  --topic            (required) Video topic or title
  --niche            (default: 4_ai_money_tech) 16 viral niches
  --duration         (default: 45) Target video duration in seconds (15-60)
  --engine           (default: ffmpeg_native) ffmpeg_native | moviepy_legacy
  --hwaccel          (default: auto) auto | cuda | qsv | amf | cpu
  --voice            (default: tr-TR-AhmetNeural) TTS voice id
  --subtitle-style   (default: capcut_yellow) 16 subtitle presets
  --anti-detect      Enable algorithmic originality filter
  --upload-youtube   Automatically upload via headless browser uploader
  --dry-run          Compile DirectorPlan & scenes without rendering MP4
  --output-dir       (default: ./output) Output directory
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict

import config
from director.compiler import compile_director_plan
from director.schema import DirectorPlan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ShortsVideoCreators Industrial Video Engine CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--topic", type=str, required=True, help="Üretilecek videonun konusu veya başlığı")
    parser.add_argument("--niche", type=str, default="4_ai_money_tech", help="Viral niş şablonu (1_news_flash, 6_stoic_philosophy, vb.)")
    parser.add_argument("--duration", type=int, default=45, help="Hedef video süresi (saniye, 15-60)")
    parser.add_argument("--engine", type=str, default="ffmpeg_native", choices=["ffmpeg_native", "moviepy_legacy"], help="Render motoru")
    parser.add_argument("--hwaccel", type=str, default="auto", choices=["auto", "cuda", "qsv", "amf", "cpu"], help="Donanım hızlandırma")
    parser.add_argument("--voice", type=str, default="tr-TR-AhmetNeural", help="TTS ses kimliği (Edge-TTS)")
    parser.add_argument("--subtitle-style", type=str, default="capcut_yellow", help="Altyazı ön ayarı (16 stil)")
    parser.add_argument("--anti-detect", action="store_true", default=True, help="Algoritmik özgünleştirme filtresini aç")
    parser.add_argument("--no-anti-detect", dest="anti_detect", action="store_false", help="Algoritmik özgünleştirmeyi kapat")
    parser.add_argument("--upload-youtube", action="store_true", default=False, help="Render sonrası YouTube Studio yükleme")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Video üretmeden senaryo ve varlık planı çıkar")
    parser.add_argument("--output-dir", type=str, default="./output", help="Nihai MP4 ve manifestoların kaydedileceği dizin")
    return parser


def run_cli(args: argparse.Namespace) -> int:
    topic = args.topic.strip()
    niche = args.niche.strip()
    target_duration = max(15, min(60, args.duration))
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n[CLI] ShortsVideoCreators Başlatılıyor...")
    print(f"  • Konu:             {topic}")
    print(f"  • Niş:              {niche}")
    print(f"  • Hedef Süre:       {target_duration}s")
    print(f"  • Motor:            {args.engine}")
    print(f"  • Donanım Hızland.: {args.hwaccel}")
    print(f"  • TTS Ses:          {args.voice}")
    print(f"  • Altyazı Stili:    {args.subtitle_style}")
    print(f"  • Anti-Detect:      {args.anti_detect}")
    print(f"  • Dry-Run:          {args.dry_run}")
    print(f"  • Çıktı Dizini:     {output_dir}\n")

    # 1. Compile DirectorPlan
    t0 = time.time()
    print("[1/3] DirectorPlan derleniyor...")
    plan = compile_director_plan(
        title=topic,
        niche_id=niche,
        language="tr",
    )

    if not plan or not plan.scenes:
        print("[HATA] DirectorPlan derlenemedi veya sahne üretilemedi!")
        return 1

    total_words = sum(len(s.narration.split()) for s in plan.scenes)
    print(f"  [OK] Plan Derlendi: {len(plan.scenes)} sahne, {total_words} kelime, tahmini süre: {plan.cadence_durations[-1] if plan.cadence_durations else target_duration:.1f}s")
    print(f"  [Kanca]: {plan.hook_text or plan.scenes[0].narration[:60]}")
    print(f"  [Döngü]: {plan.loop_text or plan.scenes[-1].narration[:60]}")

    if args.dry_run:
        plan_json_path = os.path.join(output_dir, f"plan_dry_run_{int(time.time())}.json")
        with open(plan_json_path, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\n[DRY-RUN BİTTİ] Plan JSON kaydedildi: {plan_json_path}")
        print(f"Toplam süre: {time.time() - t0:.2f}s\n")
        return 0

    # 2. Render Pipeline
    print("\n[2/3] Render hattı yürütülüyor...")
    from api_models import VideoRenderRequest
    from server_core.render_worker import process_video_task

    request_payload = VideoRenderRequest(
        keyword=topic,
        niche=niche,
        language="tr",
        tts_voice=args.voice,
        subtitle_preset=args.subtitle_style,
        anti_duplicate=args.anti_detect,
        enable_ken_burns=True,
        auto_publish=args.upload_youtube,
        plan=plan.to_dict(),
    )

    try:
        process_video_task(request_payload)
        elapsed = time.time() - t0
        print(f"\n[3/3] [BAŞARILI] Render tamamlandı! Toplam süre: {elapsed:.1f}s")
        return 0
    except Exception as exc:
        print(f"\n[HATA] Render sırasında hata oluştu: {exc}")
        return 1


def main():
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(run_cli(args))


if __name__ == "__main__":
    main()
