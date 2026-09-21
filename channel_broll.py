"""Channel-scoped B-roll archive — prefer local reuse before stock API."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Sequence

import config

_INDEX_NAME = "index.json"
_ROTATION_WINDOW = int(os.getenv("CHANNEL_BROLL_ROTATION", "12"))
_EXTS = (".mp4", ".mov", ".webm", ".mkv")


def _niche_slug(niche_id: str) -> str:
    raw = (niche_id or "general").strip().lower()
    safe = re.sub(r"[^\w\-]+", "_", raw)[:48]
    return safe or "general"


def archive_root(channel_id: Optional[str], niche_id: str = "") -> str:
    paths = config.channel_paths(channel_id)
    root = os.path.join(paths["assets_dir"], "broll", _niche_slug(niche_id))
    os.makedirs(root, exist_ok=True)
    return root


def _index_path(root: str) -> str:
    return os.path.join(root, _INDEX_NAME)


def _load_index(root: str) -> Dict[str, Any]:
    path = _index_path(root)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("clips"), list):
                return data
    except Exception:
        pass
    return {"clips": []}


def _save_index(root: str, data: Dict[str, Any]) -> None:
    path = _index_path(root)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"  [ChannelBroll] index save notice: {exc}")


def _file_sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 256)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _token_set(queries: Sequence[str]) -> set:
    tokens: set = set()
    for q in queries or []:
        for tok in re.split(r"\W+", (q or "").lower()):
            if len(tok) >= 3:
                tokens.add(tok)
    return tokens


def _score_entry(entry: Dict[str, Any], query_tokens: set, blocked: set) -> float:
    uid = str(entry.get("uid") or "")
    if not uid or uid in blocked:
        return -1.0
    path = entry.get("path") or ""
    if not path or not os.path.isfile(path):
        return -1.0
    entry_tokens = _token_set(entry.get("queries") or [])
    overlap = len(query_tokens & entry_tokens) if query_tokens else 0
    score = 10.0 + overlap * 5.0
    # Prefer less-recently-used
    score -= min(20.0, float(entry.get("used_count") or 0) * 0.5)
    return score


def try_archive_hit(
    channel_id: Optional[str],
    niche_id: str,
    queries: Sequence[str],
    project_dir: str,
    scene_index: int,
    rotation_window: int = _ROTATION_WINDOW,
) -> Optional[str]:
    """
    Prefer a channel archive clip matching query tokens.
    Soft-rotates last N uids (channel-scoped) — does NOT use global stock dedup.
    """
    if not channel_id:
        return None
    root = archive_root(channel_id, niche_id)
    data = _load_index(root)
    clips = data.get("clips") or []
    if not clips:
        return None

    # Soft rotate: last N used uids
    recent = [
        str(c.get("uid"))
        for c in sorted(clips, key=lambda x: float(x.get("last_used") or 0), reverse=True)
        if c.get("last_used")
    ][: max(0, rotation_window)]
    blocked = set(recent)
    qtokens = _token_set(queries)

    scored = []
    for entry in clips:
        sc = _score_entry(entry, qtokens, blocked)
        if sc >= 0:
            scored.append((sc, entry))
    if not scored and blocked:
        # Exhausted rotation — allow any readable clip
        for entry in clips:
            sc = _score_entry(entry, qtokens, set())
            if sc >= 0:
                scored.append((sc, entry))
    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    # Stable pick among top few by scene index
    top = scored[: min(5, len(scored))]
    _, pick = top[scene_index % len(top)]
    src = pick["path"]
    uid = pick["uid"]
    dest = os.path.join(project_dir, f"s{scene_index:03d}_broll_{uid[:8]}.mp4")
    try:
        shutil.copy2(src, dest)
    except Exception as exc:
        print(f"  [ChannelBroll] copy failed: {exc}")
        return None

    pick["used_count"] = int(pick.get("used_count") or 0) + 1
    pick["last_used"] = time.time()
    _save_index(root, data)
    print(
        f"    [ChannelBroll] hit niche={_niche_slug(niche_id)} "
        f"uid={uid[:8]} → {os.path.basename(dest)}"
    )
    return dest


def promote_clip(
    channel_id: Optional[str],
    niche_id: str,
    clip_path: str,
    queries: Optional[Sequence[str]] = None,
    source: str = "stock",
    source_id: str = "",
) -> Optional[str]:
    """Copy a freshly downloaded stock clip into the channel archive + index."""
    if not channel_id or not clip_path or not os.path.isfile(clip_path):
        return None
    if not clip_path.lower().endswith(_EXTS):
        return None
    # Skip AI / procedural filenames
    base = os.path.basename(clip_path).lower()
    if any(tag in base for tag in ("_ai_", "ai_video", "veo", "gemini", "procedural", "reddit")):
        return None

    root = archive_root(channel_id, niche_id)
    try:
        sha = _file_sha1(clip_path)
    except Exception:
        return None
    uid = sha[:16]
    dest_name = f"{uid}.mp4"
    dest = os.path.join(root, dest_name)

    data = _load_index(root)
    for entry in data["clips"]:
        if entry.get("uid") == uid or entry.get("sha1") == sha:
            # Refresh queries / bump
            existing_q = list(entry.get("queries") or [])
            for q in queries or []:
                if q and q not in existing_q:
                    existing_q.append(q)
            entry["queries"] = existing_q[:12]
            entry["last_promoted"] = time.time()
            _save_index(root, data)
            return entry.get("path") or dest

    try:
        if not os.path.isfile(dest):
            shutil.copy2(clip_path, dest)
    except Exception as exc:
        print(f"  [ChannelBroll] promote copy failed: {exc}")
        return None

    data["clips"].append(
        {
            "uid": uid,
            "sha1": sha,
            "path": dest,
            "source": source or "stock",
            "source_id": str(source_id or ""),
            "queries": [q for q in (queries or []) if q][:12],
            "license": "provider-commercial",
            "used_count": 0,
            "last_used": 0,
            "last_promoted": time.time(),
        }
    )
    # Cap archive size (keep newest 80)
    if len(data["clips"]) > 80:
        data["clips"] = data["clips"][-80:]
    _save_index(root, data)
    print(f"    [ChannelBroll] promoted {dest_name} niche={_niche_slug(niche_id)}")
    return dest
