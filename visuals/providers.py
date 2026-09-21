"""
Search adapters. Every adapter returns List[Candidate] with license metadata attached.

Keyed (skipped gracefully when the .env key is missing):
  pexels     PEXELS_API_KEY     https://www.pexels.com/api/
  pixabay    PIXABAY_API_KEY    https://pixabay.com/api/docs/
  coverr     COVERR_API_KEY     https://coverr.co/  (api.coverr.co)

Keyless (public, CC0 / public domain / CC-BY only):
  wikimedia  Wikimedia Commons  video (webm/ogv/mp4) + bitmap images
  nasa       NASA Image & Video Library (public domain)
  openverse  Openverse (CC0 / BY / PDM images) — low anonymous rate limit, cached hard
  archive_org Internet Archive — ONLY Prelinger + NASA collections (public domain films)

Never: YouTube rips, share-alike, non-commercial, no-derivative material.
"""
from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional

import requests

from .license import License, LicenseInfo, parse_cc_license

USER_AGENT = "youtubeoto-shorts/1.0 (open-license visual sourcing; local dev)"
TIMEOUT = 8

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _env(name: str) -> str:
    try:
        import config
        val = getattr(config, name, "") or ""
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(name, "") or ""


@dataclass
class Candidate:
    source: str
    id: str
    url: str
    kind: str                       # "video" | "image"
    width: int = 0
    height: int = 0
    duration: float = 0.0           # seconds (0 for images)
    title: str = ""
    tags: List[str] = field(default_factory=list)
    thumbnail: str = ""
    contributor: str = ""
    license: LicenseInfo = None     # type: ignore
    extra: Dict = field(default_factory=dict)

    @property
    def uid(self) -> str:
        return f"{self.source}:{self.id}"

    @property
    def text(self) -> str:
        return " ".join([self.title] + list(self.tags)).lower()

    @property
    def is_portrait(self) -> bool:
        return self.height > self.width > 0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["license"] = self.license.to_dict() if self.license else None
        d["uid"] = self.uid
        return d


# ─── Pexels ──────────────────────────────────────────────────────────────────

def _pick_pexels_file(files: List[Dict]) -> Optional[Dict]:
    best, best_score = None, -1e9
    for f in files or []:
        w, h = int(f.get("width") or 0), int(f.get("height") or 0)
        if max(w, h) < 720:
            continue
        score = (100000 if h > w else 0) - (abs(w - 1080) + abs(h - 1920))
        if score > best_score:
            best, best_score = f, score
    return best


def search_pexels(query: str, per_page: int = 12) -> List[Candidate]:
    key = _env("PEXELS_API_KEY")
    if not key:
        return []
    r = _session.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": key},
        params={"query": query, "per_page": per_page, "orientation": "portrait", "size": "medium"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    out: List[Candidate] = []
    for v in r.json().get("videos", []):
        f = _pick_pexels_file(v.get("video_files", []))
        if not f:
            continue
        user = v.get("user") or {}
        out.append(Candidate(
            source="pexels", id=f"px_{v['id']}", url=f["link"], kind="video",
            width=int(f.get("width") or v.get("width") or 0), height=int(f.get("height") or v.get("height") or 0),
            duration=float(v.get("duration") or 0), title=str(v.get("url", "")).rstrip("/").split("/")[-1].replace("-", " "),
            thumbnail=v.get("image", ""), contributor=f"pexels:{user.get('id','')}",
            license=LicenseInfo(License.PEXELS, "pexels", author=str(user.get("name", "")), source_url=v.get("url", ""),
                                license_url="https://www.pexels.com/license/", raw="Pexels License"),
        ))
    return out


# ─── Pixabay ─────────────────────────────────────────────────────────────────

def search_pixabay(query: str, per_page: int = 12) -> List[Candidate]:
    key = _env("PIXABAY_API_KEY")
    if not key:
        return []
    r = _session.get(
        "https://pixabay.com/api/videos/",
        params={"key": key, "q": query, "video_type": "film", "per_page": max(3, per_page), "safesearch": "true"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    out: List[Candidate] = []
    for v in r.json().get("hits", []):
        vids = v.get("videos") or {}
        f = vids.get("large") or vids.get("medium") or vids.get("small") or {}
        if not f.get("url"):
            continue
        out.append(Candidate(
            source="pixabay", id=f"pb_{v['id']}", url=f["url"], kind="video",
            width=int(f.get("width") or 0), height=int(f.get("height") or 0),
            duration=float(v.get("duration") or 0), title="", tags=[t.strip() for t in str(v.get("tags", "")).split(",") if t.strip()],
            thumbnail=f.get("thumbnail", ""), contributor=f"contributor:{str(v.get('user','')).lower()}",
            license=LicenseInfo(License.PIXABAY, "pixabay", author=str(v.get("user", "")), source_url=v.get("pageURL", ""),
                                license_url="https://pixabay.com/service/license-summary/", raw="Pixabay Content License"),
        ))
    return out


# ─── Coverr ──────────────────────────────────────────────────────────────────

def search_coverr(query: str, per_page: int = 10) -> List[Candidate]:
    key = _env("COVERR_API_KEY")
    if not key:
        return []
    r = _session.get(
        "https://api.coverr.co/videos",
        headers={"Authorization": f"Bearer {key}"},
        params={"query": query, "page_size": per_page},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    out: List[Candidate] = []
    for v in data.get("hits", data.get("videos", [])):
        urls = v.get("urls") or {}
        url = urls.get("mp4_download") or urls.get("mp4") or urls.get("mp4_preview")
        if not url:
            continue
        out.append(Candidate(
            source="coverr", id=f"cv_{v.get('id','')}", url=url, kind="video",
            width=int(v.get("max_width") or 1920), height=int(v.get("max_height") or 1080),
            duration=float(v.get("duration") or 8), title=str(v.get("title", "")),
            tags=[t if isinstance(t, str) else str(t.get("name", "")) for t in (v.get("tags") or [])],
            thumbnail=str(v.get("thumbnail", "")),
            license=LicenseInfo(License.COVERR, "coverr", title=str(v.get("title", "")), source_url=str(v.get("url", "")),
                                license_url="https://coverr.co/license", raw="Coverr License"),
        ))
    return out


# ─── Wikimedia Commons ───────────────────────────────────────────────────────

_WM_API = "https://commons.wikimedia.org/w/api.php"
_STRIP_TAGS = re.compile(r"<[^>]+>")


def _wm_license(meta: Dict) -> LicenseInfo:
    short = (meta.get("LicenseShortName") or {}).get("value", "")
    lic_id = (meta.get("License") or {}).get("value", "")
    lic_url = (meta.get("LicenseUrl") or {}).get("value", "")
    artist = html.unescape(_STRIP_TAGS.sub("", (meta.get("Artist") or {}).get("value", ""))).strip()
    title = html.unescape(_STRIP_TAGS.sub("", (meta.get("ObjectName") or {}).get("value", ""))).strip()
    lic = parse_cc_license(lic_url) if lic_url else License.UNKNOWN
    if lic == License.UNKNOWN:
        lic = parse_cc_license(lic_id or short)
    if lic == License.UNKNOWN and short:
        lic = parse_cc_license(short)
    return LicenseInfo(lic, "wikimedia", title=title, author=artist[:80], license_url=lic_url, raw=short or lic_id)


def search_wikimedia(query: str, per_page: int = 10, kind: str = "video") -> List[Candidate]:
    ftype = "video" if kind == "video" else "bitmap"
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:{ftype} {query}", "gsrnamespace": 6, "gsrlimit": per_page,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1600,
        "iiextmetadatafilter": "LicenseShortName|License|LicenseUrl|Artist|ObjectName|Categories",
    }
    r = _session.get(_WM_API, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}
    out: List[Candidate] = []
    for pid, page in pages.items():
        info = (page.get("imageinfo") or [{}])[0]
        if not info:
            continue
        meta = info.get("extmetadata") or {}
        lic = _wm_license(meta)
        if not lic.safe:
            continue
        title = str(page.get("title", "")).replace("File:", "")
        lic.title = lic.title or os.path.splitext(title)[0]
        lic.source_url = info.get("descriptionurl", "")
        cats = html.unescape((meta.get("Categories") or {}).get("value", ""))
        tags = [c.strip().lower() for c in cats.split("|") if c.strip() and "needing" not in c.lower()][:12]
        w, h = int(info.get("width") or 0), int(info.get("height") or 0)
        if kind == "video":
            size = int(info.get("size") or 0)
            if size > 120 * 1024 * 1024 or max(w, h) < 640:
                continue
            url = str(info.get("url", "")).split("?")[0]
            dur = float(info.get("duration") or 0)
        else:
            if max(w, h) < 1000:
                continue
            url = info.get("thumburl") or info.get("url", "")
            url = str(url).split("?")[0]
            dur = 0.0
        out.append(Candidate(
            source="wikimedia", id=f"wm_{pid}", url=url, kind=kind, width=w, height=h, duration=dur,
            title=os.path.splitext(title)[0].replace("_", " "), tags=tags, thumbnail=info.get("thumburl", ""),
            contributor=f"wikimedia:{lic.author.lower()}" if lic.author else "", license=lic,
            extra={"mime": info.get("mime", "")},
        ))
    return out


def search_wikimedia_images(query: str, per_page: int = 10) -> List[Candidate]:
    return search_wikimedia(query, per_page=per_page, kind="image")


# ─── NASA Image & Video Library ──────────────────────────────────────────────

_NASA_API = "https://images-api.nasa.gov/search"


def _nasa_pick_asset(collection_url: str, kind: str) -> Optional[str]:
    try:
        r = _session.get(collection_url, timeout=TIMEOUT)
        r.raise_for_status()
        files = r.json()
    except Exception:
        return None
    if not isinstance(files, list):
        return None
    if kind == "video":
        for pref in ("~medium.mp4", "~mobile.mp4", "~orig.mp4", ".mp4"):
            for f in files:
                if str(f).lower().endswith(pref):
                    return f.replace("http://", "https://")
    else:
        for pref in ("~large.jpg", "~medium.jpg", "~orig.jpg", ".jpg", ".png"):
            for f in files:
                if str(f).lower().endswith(pref):
                    return f.replace("http://", "https://")
    return None


def search_nasa(query: str, per_page: int = 6, kind: str = "video") -> List[Candidate]:
    r = _session.get(_NASA_API, params={"q": query, "media_type": kind, "page_size": per_page}, timeout=TIMEOUT)
    r.raise_for_status()
    items = ((r.json().get("collection") or {}).get("items") or [])
    out: List[Candidate] = []
    for it in items[:per_page]:
        data = (it.get("data") or [{}])[0]
        nasa_id = data.get("nasa_id", "")
        if not nasa_id:
            continue
        url = _nasa_pick_asset(it.get("href", ""), kind)
        if not url:
            continue
        links = it.get("links") or []
        thumb = next((l.get("href", "") for l in links if l.get("rel") == "preview"), "")
        title = str(data.get("title", ""))
        out.append(Candidate(
            source="nasa", id=f"nasa_{nasa_id}", url=url, kind=kind, width=1920, height=1080,
            duration=0.0 if kind == "image" else 12.0, title=title,
            tags=[str(k).lower() for k in (data.get("keywords") or [])][:15], thumbnail=thumb,
            contributor=f"nasa:{str(data.get('center','')).lower()}",
            license=LicenseInfo(License.PUBLIC_DOMAIN, "nasa", title=title, author="NASA",
                                source_url=f"https://images.nasa.gov/details/{nasa_id}",
                                license_url="https://www.nasa.gov/nasa-brand-center/images-and-media/", raw="NASA public domain"),
        ))
    return out


def search_nasa_images(query: str, per_page: int = 6) -> List[Candidate]:
    return search_nasa(query, per_page=per_page, kind="image")


# ─── Openverse (images) ──────────────────────────────────────────────────────

_OV_API = "https://api.openverse.org/v1/images/"
_OV_OK = {"cc0", "by", "pdm"}


def search_openverse(query: str, per_page: int = 10) -> List[Candidate]:
    params = {"q": query, "license": "cc0,by,pdm", "page_size": per_page, "mature": "false"}
    r = _session.get(_OV_API, params=params, timeout=TIMEOUT)
    if r.status_code == 429:
        raise RuntimeError("openverse rate limit (anonymous) — cached results only")
    r.raise_for_status()
    out: List[Candidate] = []
    for it in r.json().get("results", []):
        lic_key = str(it.get("license", "")).lower()
        if lic_key not in _OV_OK:
            continue
        lic = {"cc0": License.CC0, "pdm": License.PUBLIC_DOMAIN, "by": License.CC_BY}[lic_key]
        w, h = int(it.get("width") or 0), int(it.get("height") or 0)
        if w and h and max(w, h) < 900:
            continue
        title = str(it.get("title") or "")
        out.append(Candidate(
            source="openverse", id=f"ov_{it.get('id','')}", url=it.get("url", ""), kind="image", width=w, height=h,
            title=title, tags=[str(t.get("name", "")).lower() for t in (it.get("tags") or [])][:15],
            thumbnail=it.get("thumbnail", ""), contributor=f"openverse:{str(it.get('creator','')).lower()}",
            license=LicenseInfo(lic, "openverse", title=title, author=str(it.get("creator") or ""),
                                source_url=str(it.get("foreign_landing_url") or ""), license_url=str(it.get("license_url") or ""),
                                raw=f"{lic_key} {it.get('license_version','')}".strip()),
            extra={"provider": it.get("provider", "")},
        ))
    return out


# ─── Internet Archive (Prelinger / NASA collections only) ────────────────────

_IA_SEARCH = "https://archive.org/advancedsearch.php"
_IA_COLLECTIONS = "(collection:prelinger OR collection:nasa)"


def search_archive_org(query: str, per_page: int = 6) -> List[Candidate]:
    q = f"mediatype:movies AND {_IA_COLLECTIONS} AND ({query})"
    params = {"q": q, "fl[]": ["identifier", "title", "licenseurl", "creator", "description"], "rows": per_page, "output": "json"}
    r = _session.get(_IA_SEARCH, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    docs = ((r.json().get("response") or {}).get("docs") or [])
    out: List[Candidate] = []
    for d in docs:
        ident = d.get("identifier", "")
        if not ident:
            continue
        lic_url = str(d.get("licenseurl") or "")
        lic = parse_cc_license(lic_url) if lic_url else License.PUBLIC_DOMAIN  # Prelinger/NASA collections are PD
        if lic not in (License.PUBLIC_DOMAIN, License.CC0):
            continue
        try:
            meta = _session.get(f"https://archive.org/metadata/{ident}/files", timeout=TIMEOUT).json()
        except Exception:
            continue
        files = meta.get("result") or []
        mp4 = None
        for pref in ("512kb mpeg4", "h.264", "mpeg4"):
            mp4 = next((f for f in files if str(f.get("format", "")).lower() == pref and str(f.get("name", "")).endswith(".mp4")), None)
            if mp4:
                break
        if not mp4:
            continue
        title = str(d.get("title") or ident)
        creator = d.get("creator")
        creator = creator[0] if isinstance(creator, list) and creator else (creator or "")
        out.append(Candidate(
            source="archive_org", id=f"ia_{ident}", url=f"https://archive.org/download/{ident}/{mp4['name']}", kind="video",
            width=int(mp4.get("width") or 640), height=int(mp4.get("height") or 480), duration=float(mp4.get("length") or 600),
            title=title, tags=[], thumbnail=f"https://archive.org/services/img/{ident}", contributor=f"archive:{str(creator).lower()}",
            license=LicenseInfo(lic, "archive_org", title=title, author=str(creator), source_url=f"https://archive.org/details/{ident}",
                                license_url=lic_url, raw=lic_url or "public domain collection"),
            extra={"remote_slice": True},
        ))
    return out


# ─── Provider registry table ─────────────────────────────────────────────────

@dataclass
class ProviderSpec:
    key: str
    fn: Callable[..., List[Candidate]]
    kind: str                         # video | image
    key_env: Optional[str] = None     # None => keyless
    weight: float = 1.0               # base quality prior
    families: Optional[List[str]] = None  # restrict to palette families (None = all)


PROVIDERS: Dict[str, ProviderSpec] = {
    "pexels": ProviderSpec("pexels", search_pexels, "video", "PEXELS_API_KEY", 1.0),
    "pixabay": ProviderSpec("pixabay", search_pixabay, "video", "PIXABAY_API_KEY", 0.95),
    "coverr": ProviderSpec("coverr", search_coverr, "video", "COVERR_API_KEY", 0.85),
    "wikimedia": ProviderSpec("wikimedia", search_wikimedia, "video", None, 0.7),
    "wikimedia_img": ProviderSpec("wikimedia_img", search_wikimedia_images, "image", None, 0.6),
    "nasa": ProviderSpec("nasa", search_nasa, "video", None, 0.75, ["mystery", "astrology", "science", "general", "news"]),
    "nasa_img": ProviderSpec("nasa_img", search_nasa_images, "image", None, 0.6, ["mystery", "astrology", "science"]),
    "openverse": ProviderSpec("openverse", search_openverse, "image", None, 0.5),
    "archive_org": ProviderSpec("archive_org", search_archive_org, "video", None, 0.45, ["history", "news"]),
}
