"""
Public APIs Catalog & Zero-Cost Fallback Registry.
Implements Bölüm 34.2 (Public-APIs Fallback Chain) based on https://github.com/public-apis/public-apis.

Zero-auth (Auth: No), HTTPS-enforced, public domain / CC-licensed endpoints:
1. News & Fact-Checking (WikiData / Wikipedia REST API)
2. Open Media & Culture (Openverse API, Met Museum Collection API)
3. Weather & Science (Open-Meteo API, NASA APOD)
4. Quotes & Wisdom (ZenQuotes, DummyJSON Quotes, Quotable)

Provides automatic circuit breaker fallback routing when primary paid/keyed APIs fail.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import requests

logger = logging.getLogger("PublicAPIsCatalog")
USER_AGENT = "ShortsVideoCreators/2.0 (Public APIs Integration; https://github.com/public-apis/public-apis)"
DEFAULT_TIMEOUT = 6.0


class APICategory(str, Enum):
    NEWS_FACTS = "news_facts"
    MEDIA_ART = "media_art"
    WEATHER_SCIENCE = "weather_science"
    QUOTES_WISDOM = "quotes_wisdom"


@dataclass
class PublicEndpoint:
    name: str
    category: APICategory
    base_url: str
    auth_required: bool = False
    https: bool = True
    rate_limit_info: str = "Anonymous / Low threshold"
    description: str = ""
    is_active: bool = True
    last_status_code: int = 0
    failure_count: int = 0


# In-memory ephemeral response cache: {cache_key: (timestamp, data)}
_EPHEMERAL_CACHE: Dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 300.0  # 5 minutes


def _get_cached(key: str) -> Optional[Any]:
    now = time.time()
    if key in _EPHEMERAL_CACHE:
        ts, data = _EPHEMERAL_CACHE[key]
        if now - ts < _CACHE_TTL:
            return data
        del _EPHEMERAL_CACHE[key]
    return None


def _set_cached(key: str, data: Any) -> None:
    _EPHEMERAL_CACHE[key] = (time.time(), data)


# ─── CATALOG DEFINITIONS ──────────────────────────────────────────────────────

PUBLIC_ENDPOINTS: Dict[str, PublicEndpoint] = {
    # 1. News & Fact-Checking
    "wikipedia_summary_tr": PublicEndpoint(
        name="wikipedia_summary_tr",
        category=APICategory.NEWS_FACTS,
        base_url="https://tr.wikipedia.org/api/rest_v1/page/summary",
        description="Turkish Wikipedia page summaries and extracts",
    ),
    "wikipedia_summary_en": PublicEndpoint(
        name="wikipedia_summary_en",
        category=APICategory.NEWS_FACTS,
        base_url="https://en.wikipedia.org/api/rest_v1/page/summary",
        description="English Wikipedia page summaries and extracts",
    ),
    "wikidata_entities": PublicEndpoint(
        name="wikidata_entities",
        category=APICategory.NEWS_FACTS,
        base_url="https://www.wikidata.org/w/api.php",
        description="WikiData entity lookup for anti-hallucination verification",
    ),
    # 2. Open Media & Culture
    "openverse_images": PublicEndpoint(
        name="openverse_images",
        category=APICategory.MEDIA_ART,
        base_url="https://api.openverse.org/v1/images",
        description="Creative Commons & Public Domain image search",
    ),
    "met_museum_art": PublicEndpoint(
        name="met_museum_art",
        category=APICategory.MEDIA_ART,
        base_url="https://collectionapi.metmuseum.org/public/collection/v1",
        description="Metropolitan Museum of Art open access cultural collection",
    ),
    # 3. Weather & Science
    "open_meteo": PublicEndpoint(
        name="open_meteo",
        category=APICategory.WEATHER_SCIENCE,
        base_url="https://api.open-meteo.com/v1/forecast",
        description="Accurate zero-auth global weather & forecast data",
    ),
    # 4. Quotes & Wisdom
    "zenquotes": PublicEndpoint(
        name="zenquotes",
        category=APICategory.QUOTES_WISDOM,
        base_url="https://zenquotes.io/api/random",
        description="Curated philosophical and motivational quotes",
    ),
    "dummyjson_quotes": PublicEndpoint(
        name="dummyjson_quotes",
        category=APICategory.QUOTES_WISDOM,
        base_url="https://dummyjson.com/quotes/random",
        description="High-availability inspirational quotes fallback",
    ),
}


# ─── CATEGORY 1: NEWS & FACT-CHECKING ─────────────────────────────────────────

def fetch_wikipedia_summary(title: str, lang: str = "tr") -> Optional[Dict[str, Any]]:
    """Fetch factual encyclopedic summary for anti-hallucination verification."""
    clean_title = title.strip().replace(" ", "_")
    if not clean_title:
        return None

    cache_key = f"wiki:{lang}:{clean_title}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    endpoint_key = "wikipedia_summary_tr" if lang == "tr" else "wikipedia_summary_en"
    endpoint = PUBLIC_ENDPOINTS.get(endpoint_key)
    if not endpoint:
        return None

    encoded_title = urllib.parse.quote(clean_title)
    url = f"{endpoint.base_url}/{encoded_title}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        endpoint.last_status_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            result = {
                "title": data.get("title", title),
                "extract": data.get("extract", ""),
                "description": data.get("description", ""),
                "thumbnail_url": data.get("thumbnail", {}).get("source") if isinstance(data.get("thumbnail"), dict) else None,
                "page_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "source": "Wikipedia",
            }
            _set_cached(cache_key, result)
            return result
        elif resp.status_code == 404 and lang == "tr":
            # Fallback to English Wikipedia if Turkish article is missing
            return fetch_wikipedia_summary(title, lang="en")
    except Exception as e:
        endpoint.failure_count += 1
        logger.warning(f"[PublicAPIs] Wikipedia fetch failed for '{title}': {e}")
    return None


def fetch_wikidata_claims(query: str, lang: str = "en") -> List[Dict[str, Any]]:
    """Fetch entity IDs and descriptions from WikiData search."""
    cache_key = f"wikidata:{lang}:{query}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    endpoint = PUBLIC_ENDPOINTS["wikidata_entities"]
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": lang,
        "format": "json",
        "limit": 3,
    }
    try:
        resp = requests.get(endpoint.base_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        endpoint.last_status_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            search_items = data.get("search", [])
            results = [
                {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "description": item.get("description", ""),
                    "url": item.get("concepturi"),
                }
                for item in search_items
            ]
            _set_cached(cache_key, results)
            return results
    except Exception as e:
        endpoint.failure_count += 1
        logger.warning(f"[PublicAPIs] WikiData search failed for '{query}': {e}")
    return []


# ─── CATEGORY 2: OPEN MEDIA & ART ─────────────────────────────────────────────

def fetch_openverse_media(query: str, page_size: int = 5, license_type: str = "cc0,pdm,by") -> List[Dict[str, Any]]:
    """Fetch free public domain / CC0 media assets from Openverse."""
    cache_key = f"openverse:{query}:{page_size}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    endpoint = PUBLIC_ENDPOINTS["openverse_images"]
    params = {
        "q": query,
        "page_size": min(page_size, 10),
        "license": license_type,
    }
    try:
        resp = requests.get(endpoint.base_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        endpoint.last_status_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("results", []):
                results.append({
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "url": item.get("url"),
                    "thumbnail": item.get("thumbnail"),
                    "license": item.get("license"),
                    "creator": item.get("creator", "Unknown"),
                    "source": "Openverse",
                })
            _set_cached(cache_key, results)
            return results
    except Exception as e:
        endpoint.failure_count += 1
        logger.warning(f"[PublicAPIs] Openverse fetch failed for '{query}': {e}")
    return []


def fetch_met_museum_artworks(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Fetch high-resolution public domain artwork images from Met Museum."""
    cache_key = f"met:{query}:{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    endpoint = PUBLIC_ENDPOINTS["met_museum_art"]
    search_url = f"{endpoint.base_url}/search"
    params = {"q": query, "hasImages": "true"}
    try:
        resp = requests.get(search_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        endpoint.last_status_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            object_ids = data.get("objectIDs") or []
            results = []
            for obj_id in object_ids[:limit]:
                obj_url = f"{endpoint.base_url}/objects/{obj_id}"
                obj_resp = requests.get(obj_url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
                if obj_resp.status_code == 200:
                    obj_data = obj_resp.json()
                    primary_img = obj_data.get("primaryImage") or obj_data.get("primaryImageSmall")
                    if primary_img:
                        results.append({
                            "id": str(obj_id),
                            "title": obj_data.get("title", ""),
                            "url": primary_img,
                            "artist": obj_data.get("artistDisplayName", "Unknown"),
                            "license": "Public Domain (Met Open Access)",
                            "source": "MetMuseum",
                        })
            _set_cached(cache_key, results)
            return results
    except Exception as e:
        endpoint.failure_count += 1
        logger.warning(f"[PublicAPIs] Met Museum fetch failed for '{query}': {e}")
    return []


# ─── CATEGORY 3: WEATHER & SCIENCE ────────────────────────────────────────────

def fetch_weather_facts(city: str = "Istanbul", lat: float = 41.01, lon: float = 28.97) -> Optional[Dict[str, Any]]:
    """Fetch current real-time meteorological conditions via Open-Meteo."""
    cache_key = f"weather:{city}:{lat}:{lon}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    endpoint = PUBLIC_ENDPOINTS["open_meteo"]
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
    }
    try:
        resp = requests.get(endpoint.base_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        endpoint.last_status_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            current = data.get("current", {})
            result = {
                "city": city,
                "temperature": current.get("temperature_2m"),
                "apparent_temperature": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": current.get("weather_code"),
                "source": "Open-Meteo",
            }
            _set_cached(cache_key, result)
            return result
    except Exception as e:
        endpoint.failure_count += 1
        logger.warning(f"[PublicAPIs] Weather fetch failed for '{city}': {e}")
    return None


# ─── CATEGORY 4: QUOTES & WISDOM ──────────────────────────────────────────────

def fetch_philosophical_quote() -> Optional[Dict[str, str]]:
    """Fetch inspirational or philosophical quote using ZenQuotes with DummyJSON fallback."""
    # 1. Primary: ZenQuotes
    zen = PUBLIC_ENDPOINTS["zenquotes"]
    try:
        resp = requests.get(zen.base_url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        zen.last_status_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                return {
                    "quote": first.get("q", ""),
                    "author": first.get("a", "Unknown"),
                    "source": "ZenQuotes",
                }
    except Exception as e:
        zen.failure_count += 1
        logger.warning(f"[PublicAPIs] ZenQuotes failed: {e}")

    # 2. Fallback: DummyJSON Quotes
    dummy = PUBLIC_ENDPOINTS["dummyjson_quotes"]
    try:
        resp = requests.get(dummy.base_url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        dummy.last_status_code = resp.status_code
        if resp.status_code == 200:
            data = resp.json()
            return {
                "quote": data.get("quote", ""),
                "author": data.get("author", "Unknown"),
                "source": "DummyJSON",
            }
    except Exception as e:
        dummy.failure_count += 1
        logger.warning(f"[PublicAPIs] DummyJSON quotes fallback failed: {e}")

    return {
        "quote": "Bilmeyen ve bilmediğini bilen çocuktur; ona öğretin. Bilen ve bildiğini bilmeyen uykudadır; onu uyandırın.",
        "author": "Kadim Bilgelik",
        "source": "LocalCurated",
    }


# ─── RESILIENT DISPATCHER & CIRCUIT BREAKER HOOK ──────────────────────────────

def snapshot_path() -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "static", "data", "public-apis-snapshot.json")
    )


def load_offline_snapshot() -> List[Dict[str, Any]]:
    """Repo snapshot of public-apis fallbacks. UI and tests work with no network."""
    path = snapshot_path()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        logger.warning("[PublicAPIs] offline snapshot unreadable: %s", exc)
        return []
    rows = data.get("fallbacks") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("id")]


def get_category_endpoints(category: APICategory) -> List[PublicEndpoint]:
    """Retrieve all registered endpoints belonging to a given category."""
    return [ep for ep in PUBLIC_ENDPOINTS.values() if ep.category == category and ep.is_active]


def execute_with_public_fallback(
    service_name: str,
    primary_fn: Callable[[], Any],
    fallback_fn: Callable[[], Any],
    circuit_breaker: Optional[Any] = None,
) -> Any:
    """
    Executes primary function. If it raises an exception or CircuitBreaker is open,
    transparently falls back to public API catalog implementation.
    """
    if circuit_breaker and hasattr(circuit_breaker, "can_execute"):
        if not circuit_breaker.can_execute(service_name):
            logger.info(f"[PublicAPIs] Circuit OPEN for '{service_name}', routing directly to fallback.")
            return fallback_fn()

    try:
        res = primary_fn()
        if circuit_breaker and hasattr(circuit_breaker, "record_success"):
            circuit_breaker.record_success(service_name)
        return res
    except Exception as exc:
        logger.warning(f"[PublicAPIs] Primary service '{service_name}' failed ({exc}), engaging fallback.")
        if circuit_breaker and hasattr(circuit_breaker, "record_failure"):
            circuit_breaker.record_failure(service_name)
        return fallback_fn()
