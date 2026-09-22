"""
YouTube Shorts Ultimate — 5 Sources, Multi-AI, TR+EN, Karaoke Subs
"""
import os, sys, re, json, argparse, time
import config
from scene_generator import generate_scenes
from video_fetcher import search_and_download, reset_used_videos
from tts_engine import generate_narration_with_timing
from video_composer import compose_video

def sanitize(n):
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    n = n.translate(tr_map)
    c = re.sub(r'[^\w\s-]', '', n)
    return re.sub(r'\s+', '_', c.strip())[:80]


def load_keywords():
    if not os.path.exists(config.KEYWORDS_FILE):
        print(f"ERROR: {config.KEYWORDS_FILE} not found!"); sys.exit(1)
    with open(config.KEYWORDS_FILE, "r", encoding="utf-8") as f:
        kw = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not kw:
        print("ERROR: keywords.txt empty!"); sys.exit(1)
    return kw

def process(keyword, index):
    print(f"\n{'='*60}")
    print(f"  VIDEO {index}: {keyword}")
    print(f"{'='*60}")

    safe = sanitize(keyword)
    proj = os.path.join(config.ASSETS_DIR, safe)
    os.makedirs(proj, exist_ok=True)
    reset_used_videos()

    # 1) Scene plan
    print(f"\n[1/4] Scene plan ({config.AI_PROVIDER})...")
    try:
        plan = generate_scenes(keyword)
    except Exception as e:
        print(f"  ERROR: {e}"); return None

    with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    # 2) Download videos — 5 sources, scene_description for matching
    active = ["Pexels"]
    if config.PIXABAY_API_KEY: active.append("Pixabay")
    active += ["Coverr", "Openverse", "Wikimedia", "NASA"]
    print(f"\n[2/4] Videos ({' + '.join(active)})...")

    clips = []
    for i, scene in enumerate(plan["scenes"]):
        q = scene.get("search_queries") or ([scene.get("search_query")] if scene.get("search_query") else [])
        d = scene["duration"]
        desc = scene.get("scene_description", "")

        print(f"\n  Scene {i+1}/{len(plan['scenes'])}: {desc[:60]}...")
        p = search_and_download(q, i, proj, target_duration=d, scene_description=desc)
        clips.append({"path": p, "duration": d, "narration": scene.get("narration","")})
        time.sleep(0.3)

    ok = sum(1 for c in clips if c["path"])
    print(f"\n  {ok}/{len(clips)} videos ready")
    if ok == 0:
        print("  ERROR: No videos!"); return None

    # 3) Narration
    lang = "Turkish" if config.LANGUAGE == "tr" else "English"
    print(f"\n[3/4] {lang} narration...")
    audio = os.path.join(config.AUDIO_DIR, f"{safe}.wav")
    try:
        _, timings = generate_narration_with_timing(plan["full_narration"], audio)
    except Exception as e:
        print(f"  ERROR (TTS): {e}"); return None

    # 4) Compose with karaoke subs
    print(f"\n[4/4] Composing + karaoke subtitles...")
    out = os.path.join(config.OUTPUT_DIR, f"{safe}.mp4")
    try:
        result = compose_video(clips, audio, timings, out, keyword)
    except Exception as e:
        print(f"  ERROR: {e}"); return None

    if result and os.path.exists(result):
        print(f"\n  [OK] DONE: {result}")

        # YouTube upload is intentionally manual. The composer writes a
        # reviewable package (sources, credits, policy snapshot, disclosure,
        # and checklist) next to the rendered MP4.
        if getattr(config, "YOUTUBE_AUTO_PUBLISH", False):
            print("  [Policy] Otomatik YouTube yüklemesi devre dışı; manuel Studio paketi üretildi.")

        return result
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", "-k")
    args = parser.parse_args()

    lang = "Türkçe" if config.LANGUAGE == "tr" else "English"
    src = ["Pexels"]
    if config.PIXABAY_API_KEY: src.append("Pixabay")
    src += ["Coverr", "Openverse", "Wikimedia", "NASA"]

    print(f"""
╔══════════════════════════════════════════════════════════╗
║          YouTube Shorts Ultimate System                   ║
╠══════════════════════════════════════════════════════════╣
║  AI        : {config.AI_PROVIDER:44s} ║
║  Language  : {lang:44s} ║
║  Voice     : {config.TTS_VOICE:44s} ║
║  Sources   : {', '.join(src):44s} ║
║  Duration  : {config.MIN_DURATION}-{config.MAX_DURATION}s{' ':38s} ║
║  Subtitles : Karaoke (word-by-word highlight){' ':14s} ║
║  Dedup     : Strict (no repeats ever){' ':22s} ║
╚══════════════════════════════════════════════════════════╝
    """)

    keywords = [args.keyword] if args.keyword else load_keywords()
    print(f"Processing {len(keywords)} title(s)\n")

    results = []
    for i, kw in enumerate(keywords, 1):
        t0 = time.time()
        out = process(kw, i)
        dt = time.time() - t0
        results.append({"keyword": kw, "output": out, "ok": out is not None, "time": f"{dt:.0f}s"})

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(f"  {'[OK]' if r['ok'] else '[FAIL]'} {r['keyword']} ({r['time']})")

        if r["output"]: print(f"    → {r['output']}")
    ok = sum(1 for r in results if r["ok"])
    print(f"\n  {ok}/{len(results)} successful | Output: {config.OUTPUT_DIR}")

if __name__ == "__main__":
    main()
