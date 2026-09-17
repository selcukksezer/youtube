"""Stock-video provider search adapters returning a common candidate shape."""
import re

import requests

import config


def _pick_pexels_file(files):
    candidates = []
    for item in files:
        width, height = item.get("width", 0), item.get("height", 0)
        if max(width, height) >= config.MIN_RESOLUTION:
            candidates.append((height > width, width * height, item))
    if candidates:
        return sorted(candidates, key=lambda item: (item[0], item[1]), reverse=True)[0][2]
    return max(files, key=lambda item: item.get("width", 0) * item.get("height", 0), default=None)


def search_pexels(query):
    if not config.PEXELS_API_KEY:
        return []
    try:
        response = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": config.PEXELS_API_KEY}, params={"query": query, "per_page": config.RESULTS_PER_PAGE, "orientation": "portrait", "size": "large"}, timeout=15)
        response.raise_for_status()
    except Exception as error:
        print(f"        [Pexels] {error}")
        return []
    results = []
    for video in response.json().get("videos", []):
        file = _pick_pexels_file(video.get("video_files", []))
        if file:
            results.append({"source": "pexels", "id": f"px_{video['id']}", "width": video.get("width", 0), "height": video.get("height", 0), "duration": video.get("duration", 0), "url": file["link"], "fw": file.get("width", 0), "fh": file.get("height", 0)})
    return results


def search_pixabay(query):
    if not config.PIXABAY_API_KEY:
        return []
    try:
        response = requests.get("https://pixabay.com/api/videos/", params={"key": config.PIXABAY_API_KEY, "q": query, "video_type": "film", "per_page": config.RESULTS_PER_PAGE, "min_width": 1080, "safesearch": "true"}, timeout=15)
        response.raise_for_status()
    except Exception as error:
        print(f"        [Pixabay] {error}")
        return []
    results = []
    for video in response.json().get("hits", []):
        for quality in ("large", "medium", "small"):
            file = video.get("videos", {}).get(quality, {})
            if file.get("url"):
                results.append({"source": "pixabay", "id": f"pb_{video['id']}", "width": file.get("width", 0), "height": file.get("height", 0), "duration": video.get("duration", 0), "url": file["url"], "fw": file.get("width", 0), "fh": file.get("height", 0)})
                break
    return results


def _search_public_page(url, source, url_pattern, id_prefix=None):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if response.status_code != 200:
            return []
        return [{"source": source, "id": f"{id_prefix}_{index}" if id_prefix else f"vd_{index}_{hash(video_url) % 99999}", "width": 1920, "height": 1080, "duration": 15, "url": video_url, "fw": 1920, "fh": 1080} for index, video_url in enumerate(re.findall(url_pattern, response.text)[:5])]
    except Exception:
        return []


def search_coverr(query):
    try:
        response = requests.get("https://api.coverr.co/videos", params={"query": query, "page_size": 10}, timeout=15)
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
            results.append({"source": "coverr", "id": f"cv_{video.get('id', '')}", "width": video.get("width", 1920), "height": video.get("height", 1080), "duration": video.get("duration", 10), "url": url, "fw": video.get("width", 1920), "fh": video.get("height", 1080)})
    return results


def search_mixkit(query):
    slug = query.lower().replace(" ", "-")
    return _search_public_page(f"https://mixkit.co/free-stock-video/{slug}/", "mixkit", r'https://assets\.mixkit\.co/videos/[^"\']+\.mp4', id_prefix=f"mx_{slug}")


def search_videvo(query):
    slug = query.replace(" ", "-")
    return _search_public_page(f"https://www.videvo.net/search/{slug}/", "videvo", r'https://[^"\']*videvo[^"\']*\.mp4')


ALL_SOURCES = [("Pexels", search_pexels), ("Pixabay", search_pixabay), ("Coverr", search_coverr), ("Mixkit", search_mixkit), ("Videvo", search_videvo)]