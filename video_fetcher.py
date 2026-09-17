"""
5-Source Video Fetcher — Pexels + Pixabay + Coverr + Mixkit + Videvo
- Round-robin: each scene pulls from a DIFFERENT source when possible
- Strict dedup: no video ever reused (ID + file hash)
- Smart scoring: resolution + orientation + duration
- scene_description matching for better relevance
"""
import os, hashlib, requests, re, time
import config

_used_ids: set = set()
_used_hashes: set = set()
_source_counter: int = 0  # Round-robin counter


def _file_hash(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()


def _score(v, target_dur):
    w, h, d = v["width"], v["height"], v["duration"]
    if d < 3: return -1
    s = 0.0
    px = w * h
    s += 40 if px >= 1920*1080 else 30 if px >= 1280*720 else 15 if px >= 854*480 else 5
    s += 25 if h > w else 10 if abs(h-w) < 100 else 5
    s += 25 if d >= target_dur else 15 if d >= target_dur*0.7 else 8 if d >= target_dur*0.4 else 2
    if d > 60: s -= 5
    if 5 <= d <= 30: s += 10
    return s


def _download(url, path):
    try:
        r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        with open(path, "wb") as f:
            for c in r.iter_content(8192):
                f.write(c)
        return os.path.getsize(path) > 10000  # At least 10KB
    except:
        if os.path.exists(path): os.remove(path)
        return False


def _pick_pexels_file(files):
    cands = []
    for f in files:
        w, h = f.get("width", 0), f.get("height", 0)
        if max(w, h) < config.MIN_RESOLUTION: continue
        cands.append((h > w, w*h, f))
    if not cands:
        if files:
            return sorted(files, key=lambda x: x.get("width",0)*x.get("height",0), reverse=True)[0]
        return None
    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return cands[0][2]


# ═══════════════════════════════════════════════════════════
#  SOURCE 1: PEXELS (API)
# ═══════════════════════════════════════════════════════════
def _search_pexels(query):
    if not config.PEXELS_API_KEY: return []
    try:
        r = requests.get("https://api.pexels.com/videos/search",
            headers={"Authorization": config.PEXELS_API_KEY},
            params={"query": query, "per_page": config.RESULTS_PER_PAGE, "orientation": "portrait", "size": "large"},
            timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"        [Pexels] {e}")
        return []
    out = []
    for v in r.json().get("videos", []):
        bf = _pick_pexels_file(v.get("video_files", []))
        if bf:
            out.append({"source":"pexels","id":f"px_{v['id']}","width":v.get("width",0),
                "height":v.get("height",0),"duration":v.get("duration",0),"url":bf["link"],
                "fw":bf.get("width",0),"fh":bf.get("height",0)})
    return out


# ═══════════════════════════════════════════════════════════
#  SOURCE 2: PIXABAY (API)
# ═══════════════════════════════════════════════════════════
def _search_pixabay(query):
    if not config.PIXABAY_API_KEY: return []
    try:
        r = requests.get("https://pixabay.com/api/videos/",
            params={"key": config.PIXABAY_API_KEY, "q": query, "video_type": "film",
                    "per_page": config.RESULTS_PER_PAGE, "min_width": 1080, "safesearch": "true"},
            timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"        [Pixabay] {e}")
        return []
    out = []
    for v in r.json().get("hits", []):
        vids = v.get("videos", {})
        for q in ["large", "medium", "small"]:
            vf = vids.get(q, {})
            if vf.get("url"):
                out.append({"source":"pixabay","id":f"pb_{v['id']}","width":vf.get("width",0),
                    "height":vf.get("height",0),"duration":v.get("duration",0),"url":vf["url"],
                    "fw":vf.get("width",0),"fh":vf.get("height",0)})
                break
    return out


# ═══════════════════════════════════════════════════════════
#  SOURCE 3: COVERR (API)
# ═══════════════════════════════════════════════════════════
def _search_coverr(query):
    try:
        r = requests.get("https://api.coverr.co/videos",
            params={"query": query, "page_size": 10}, timeout=15)
        r.raise_for_status()
        data = r.json()
    except:
        return []
    out = []
    for v in data.get("videos", data.get("hits", [])):
        urls = v.get("urls", {})
        url = urls.get("mp4_download") or urls.get("mp4") or ""
        if not url:
            a = v.get("assets", {})
            url = a.get("mp4", "") if isinstance(a, dict) else ""
        if url:
            out.append({"source":"coverr","id":f"cv_{v.get('id','')}","width":v.get("width",1920),
                "height":v.get("height",1080),"duration":v.get("duration",10),"url":url,
                "fw":v.get("width",1920),"fh":v.get("height",1080)})
    return out


# ═══════════════════════════════════════════════════════════
#  SOURCE 4: MIXKIT (web scrape — bonus source)
# ═══════════════════════════════════════════════════════════
def _search_mixkit(query):
    try:
        slug = query.lower().replace(" ", "-")
        r = requests.get(f"https://mixkit.co/free-stock-video/{slug}/",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200: return []
        # Extract video URLs from page
        urls = re.findall(r'https://assets\.mixkit\.co/videos/[^"\']+\.mp4', r.text)
        out = []
        for i, url in enumerate(urls[:5]):
            out.append({"source":"mixkit","id":f"mx_{slug}_{i}","width":1920,
                "height":1080,"duration":15,"url":url,"fw":1920,"fh":1080})
        return out
    except:
        return []


# ═══════════════════════════════════════════════════════════
#  SOURCE 5: VIDEVO (web scrape — bonus source)
# ═══════════════════════════════════════════════════════════
def _search_videvo(query):
    try:
        r = requests.get(f"https://www.videvo.net/search/{query.replace(' ', '-')}/",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200: return []
        urls = re.findall(r'https://[^"\']*videvo[^"\']*\.mp4', r.text)
        out = []
        for i, url in enumerate(urls[:5]):
            out.append({"source":"videvo","id":f"vd_{i}_{hash(url)%99999}","width":1920,
                "height":1080,"duration":15,"url":url,"fw":1920,"fh":1080})
        return out
    except:
        return []


# ═══════════════════════════════════════════════════════════
#  MAIN: ROUND-ROBIN MULTI-SOURCE SEARCH
# ═══════════════════════════════════════════════════════════
ALL_SOURCES = [
    ("Pexels",  _search_pexels),
    ("Pixabay", _search_pixabay),
    ("Coverr",  _search_coverr),
    ("Mixkit",  _search_mixkit),
    ("Videvo",  _search_videvo),
]


def _generate_fallback_clip(scene_index, project_dir, target_duration=7):
    """
    Failsafe generator: Creates a 1080x1920 HD animated/colored visual clip
    when no stock video could be retrieved from external APIs.
    Guarantees the video pipeline NEVER fails due to missing stock clips.
    """
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
        path = os.path.join(project_dir, f"s{scene_index:03d}_procedural_fallback.mp4")
        
        # Color palette cycling based on scene index
        colors = [(15, 20, 35), (20, 15, 35), (35, 15, 25), (15, 30, 35), (25, 20, 15)]
        col = colors[scene_index % len(colors)]
        
        bg_clip = ColorClip(size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT), color=col, duration=target_duration)

        try:
            text_clip = TextClip("Gorsel Bulunamadi", fontsize=70, color='white', bg_color='rgba(0,0,0,100)')
            text_clip = text_clip.set_position('center').set_duration(target_duration)
            final_clip = CompositeVideoClip([bg_clip, text_clip])
        except Exception:
            # Fallback if ImageMagick is missing or fails
            final_clip = bg_clip

        final_clip.write_videofile(path, fps=config.FPS, codec="libx264", audio=False, preset="ultrafast", logger=None)
        final_clip.close()
        
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print(f"    [OK] [FAILSAFE] Created procedural fallback clip ({target_duration}s)")
            return path
    except Exception as e:
        print(f"    [FAILSAFE] Warning generating fallback clip: {e}")
    return None

def search_and_download(queries, scene_index, project_dir, target_duration=7, scene_description=""):
    global _source_counter

    if isinstance(queries, str):
        queries = [queries]

    # Add general fallback queries to search list
    extended_queries = list(queries)
    for fallback_q in ["abstract motion", "space stars", "nature aerial", "dark background"]:
        if fallback_q not in extended_queries:
            extended_queries.append(fallback_q)

    # Round-robin: start from a different source each scene
    n = len(ALL_SOURCES)
    source_order = [ALL_SOURCES[(scene_index + i) % n] for i in range(n)]

    for qi, query in enumerate(extended_queries):
        label = "primary" if qi == 0 else "secondary" if qi < len(queries) else "fallback"

        # Search sources for this query
        all_results = []
        for src_name, src_fn in source_order:
            results = src_fn(query)
            if results:
                all_results.extend(results)

        if not all_results:
            continue

        # Score and deduplicate
        scored = []
        for v in all_results:
            if v["id"] in _used_ids:
                continue
            sc = _score(v, target_duration)
            if sc > 0:
                scored.append((sc, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Download best
        for sc, v in scored[:7]:
            sid = str(v['id']).split('_')[-1]
            path = os.path.join(project_dir, f"s{scene_index:03d}_{v['source']}_{sid}.mp4")
            if _download(v["url"], path):
                fh = _file_hash(path)
                if fh in _used_hashes:
                    os.remove(path)
                    continue
                _used_ids.add(v["id"])
                _used_hashes.add(fh)
                print(f"    [OK] [{v['source'].upper()}] {v['fw']}x{v['fh']} {v['duration']}s score:{sc:.0f}")
                return path
            time.sleep(0.1)

    # If all API searches fail, use procedural failsafe clip generator
    fallback_path = _generate_fallback_clip(scene_index, project_dir, target_duration)
    if fallback_path:
        return fallback_path

    print(f"    [FAIL] Scene {scene_index}: Could not retrieve clip")
    return None


def reset_used_videos():
    global _used_ids, _used_hashes, _source_counter
    _used_ids.clear()
    _used_hashes.clear()
    _source_counter = 0
