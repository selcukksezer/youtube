"""Stock-video provider search adapters returning a common candidate shape."""
import re

import requests

import config


_QUERY_NOISE_WORDS = {
    "cinematic", "aerial", "view", "of", "the", "a", "an", "in", "on", "at", "by", "with", "from",
    "rotating", "smoothly", "dawn", "closeup", "close", "up", "detail", "perspective", "slow",
    "motion", "moody", "angle", "macro", "texture", "focus", "dynamic", "tracking", "shot",
    "direct", "gaze", "camera", "portrait", "looking", "eye", "contact", "stoic", "subscribe",
    "cut", "vertical", "scene", "wide", "dramatic", "atmospheric", "silhouette", "contrast",
    "light", "lighting", "deep", "shadow", "4k", "8k", "hd", "b-roll", "broll", "footage",
}

_MIXKIT_BANNED_BANNER_IDS = ("/47994/", "/47995/", "/47996/", "/48000/", "/44562/")


def simplify_stock_queries(query: str):
    """Build concise 1-3 word subject queries when a verbose prompt misses on Pexels/Pixabay."""
    raw = (query or "").strip()
    if not raw:
        return []
    out = [raw]
    words = [
        w for w in re.findall(r"[a-zA-Z0-9\u00c0-\u017f]+", raw.lower())
        if w not in _QUERY_NOISE_WORDS and not w.isdigit() and len(w) >= 3
    ]
    if words:
        short3 = " ".join(words[:3])
        short2 = " ".join(words[:2])
        short1 = words[0]
        for cand in (short3, short2, short1):
            if cand and cand.lower() != raw.lower() and cand not in out:
                out.append(cand)
        joined = " ".join(words)
        if "kaaba" in joined or "kabe" in joined or "mecca" in joined:
            for extra in ("kaaba mecca", "islamic mosque", "mosque prayer"):
                if extra not in out:
                    out.append(extra)
    return out


def _pick_pexels_file(files):
    candidates = []
    for item in files:
        w, h = item.get("width", 0), item.get("height", 0)
        if max(w, h) >= config.MIN_RESOLUTION:
            is_portrait = (h > w)
            dist = abs(w - 1080) + abs(h - 1920)
            score = (100000 if is_portrait else 0) - dist
            candidates.append((score, item))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return min(files, key=lambda item: abs(item.get("width", 0) - 1080), default=None)


def _pexels_request(q: str):
    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": config.PEXELS_API_KEY},
            params={"query": q, "per_page": config.RESULTS_PER_PAGE, "orientation": "portrait", "size": "large"},
            timeout=5,
        )
        response.raise_for_status()
    except Exception as error:
        print(f"        [Pexels] {error}")
        return []
    results = []
    for video in response.json().get("videos", []):
        file = _pick_pexels_file(video.get("video_files", []))
        if file:
            user = video.get("user") or {}
            contributor = f"pexels:{user['id']}" if user.get("id") else (f"contributor:{str(user['name']).lower()}" if user.get("name") else "")
            results.append({
                "source": "pexels",
                "id": f"px_{video['id']}",
                "width": video.get("width", 0),
                "height": video.get("height", 0),
                "duration": video.get("duration", 0),
                "url": file["link"],
                "fw": file.get("width", 0),
                "fh": file.get("height", 0),
                "thumbnail": video.get("image", ""),
                "contributor": contributor,
            })
    return results


def search_pexels(query):
    if not config.PEXELS_API_KEY:
        return []
    for cand_q in simplify_stock_queries(query):
        hits = _pexels_request(cand_q)
        if hits:
            return hits
    return []


def _pixabay_request(q: str):
    try:
        response = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": config.PIXABAY_API_KEY, "q": q[:95], "video_type": "film", "per_page": config.RESULTS_PER_PAGE, "safesearch": "true"},
            timeout=5,
        )
        response.raise_for_status()
    except Exception as error:
        print(f"        [Pixabay] {error}")
        return []
    results = []
    for video in response.json().get("hits", []):
        for quality in ("medium", "large", "small"):
            file = video.get("videos", {}).get(quality, {})
            if file.get("url"):
                thumb = f"https://i.vimeocdn.com/video/{video.get('picture_id')}_640x360.jpg" if video.get("picture_id") else ""
                user_name = str(video.get("user") or "").strip()
                contributor = f"contributor:{user_name.lower()}" if user_name else ""
                results.append({
                    "source": "pixabay",
                    "id": f"pb_{video['id']}",
                    "width": file.get("width", 0),
                    "height": file.get("height", 0),
                    "duration": video.get("duration", 0),
                    "url": file["url"],
                    "fw": file.get("width", 0),
                    "fh": file.get("height", 0),
                    "thumbnail": thumb,
                    "contributor": contributor,
                })
                break
    return results


def search_pixabay(query):
    if not config.PIXABAY_API_KEY:
        return []
    for cand_q in simplify_stock_queries(query):
        hits = _pixabay_request(cand_q)
        if hits:
            return hits
    return []


def _search_public_page(url, source, url_pattern, id_prefix=None):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if response.status_code != 200:
            return []
        raw_urls = [
            u for u in re.findall(url_pattern, response.text)
            if not any(b in u for b in _MIXKIT_BANNED_BANNER_IDS)
        ]
        return [
            {
                "source": source,
                "id": f"{id_prefix}_{index}" if id_prefix else f"vd_{index}_{hash(video_url) % 99999}",
                "width": 1920,
                "height": 1080,
                "duration": 15,
                "url": video_url,
                "fw": 1920,
                "fh": 1080,
                "thumbnail": "",
            }
            for index, video_url in enumerate(raw_urls[:5])
        ]
    except Exception:
        return []


def search_coverr(query):
    try:
        response = requests.get("https://api.coverr.co/videos", params={"query": query, "page_size": 10}, timeout=5)
        response.raise_for_status()
    except Exception:
        return []
    results = []
    for video in response.json().get("videos", response.json().get("hits", [])):
        urls = video.get("urls", {})
        assets = video.get("assets", {})
        asset_url = assets.get("mp4", "") if isinstance(assets, dict) else ""
        url = urls.get("mp4_download") or urls.get("mp4") or asset_url
        if url:
            results.append({
                "source": "coverr",
                "id": f"cv_{video.get('id', '')}",
                "width": video.get("width", 1920),
                "height": video.get("height", 1080),
                "duration": video.get("duration", 10),
                "url": url,
                "fw": video.get("width", 1920),
                "fh": video.get("height", 1080),
                "thumbnail": video.get("thumbnail", "")
            })
    return results


def search_mixkit(query):
    slug = query.lower().replace(" ", "-")
    return _search_public_page(f"https://mixkit.co/free-stock-video/{slug}/", "mixkit", r'https://assets\.mixkit\.co/videos/[^"\'\s<>]+\.mp4', id_prefix=f"mx_{slug}")


def search_videvo(query):
    slug = query.replace(" ", "-")
    return _search_public_page(f"https://www.videvo.net/search/{slug}/", "videvo", r'https://[^"\'\s<>]*videvo[^"\'\s<>]*\.mp4')


ALL_SOURCES = [("Pexels", search_pexels), ("Pixabay", search_pixabay), ("Coverr", search_coverr), ("Mixkit", search_mixkit), ("Videvo", search_videvo)]