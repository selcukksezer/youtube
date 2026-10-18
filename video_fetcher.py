"""
5-Source Video Fetcher — Pexels + Pixabay + Coverr + Mixkit + Videvo
- Round-robin: each scene pulls from a DIFFERENT source when possible
- Strict dedup: no video ever reused (ID + file hash)
- Smart scoring: resolution + orientation + duration
- scene_description matching for better relevance

AI image/video fallback, procedural clip generation, and source rotation helpers
are modularized in `visuals/fetcher_ai_fallback.py` and re-exported here.
Selected stock download, pool gathering, and multi-source orchestration are
in `visuals/fetcher_providers.py` and re-exported here.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading as _threading
import time
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import imageio_ffmpeg
import requests

import config
import database
from stock_providers import ALL_SOURCES
from visuals.fetcher_ai_fallback import (
    _SESSION_SOURCE_COUNTS,
    _ai_image_providers_available,
    _file_hash,
    _generate_fallback_clip,
    _pick_next_source,
    _record_visual_manifest,
    _safe_public_url,
    _score,
    _source_label_from_path,
    generate_ai_image_clip,
    generate_veo_scene_clip,
    get_session_source_distribution,
    reset_session_source_counts,
    slice_random_background_loop,
)
from visuals.fetcher_providers import (
    _drop_other_clips,
    _usable_clip,
    fetch_multi_source_clips,
    fetch_scene_clip,
    fetch_selected_stock_video,
    gather_scene_pools,
)

# P1-12: published IDs persist cross-job; job-local IDs block only within one render
_published_ids: set = set()
_job_used_ids: set = set()
_used_hashes: set = set()
_source_counter: int = 0  # Round-robin counter
# K3: thread lock — paralel asyncio.gather fetch'lerinde race condition önlemi
_fetch_lock = _threading.Lock()
_SELECTED_VIDEO_HOSTS = {
    "pexels": frozenset({"videos.pexels.com", "images.pexels.com", "player.vimeo.com"}),
    "pixabay": frozenset({"cdn.pixabay.com", "pixabay.com", "i.vimeocdn.com"}),
    "coverr": frozenset({"cdn.coverr.co", "coverr.co"}),
    "mixkit": frozenset({"assets.mixkit.co"}),
}
_MAX_SELECTED_VIDEO_BYTES = 256 * 1024 * 1024
_USED_PERSIST_PATH = os.path.join(
    getattr(config, "BASE_DIR", os.path.dirname(os.path.abspath(__file__))),
    "data",
    "used_stock_ids.json",
)

# Backward-compatible alias (published-only set for legacy imports/tests)
_used_ids = _published_ids


def _load_persisted_used_ids() -> set:
    try:
        if os.path.exists(_USED_PERSIST_PATH):
            with open(_USED_PERSIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            ids = data.get("ids") if isinstance(data, dict) else data
            return set(str(x) for x in (ids or []))
    except Exception:
        pass
    return set()


def _persist_published_ids() -> None:
    try:
        os.makedirs(os.path.dirname(_USED_PERSIST_PATH), exist_ok=True)
        ids = list(_published_ids)
        if len(ids) > 4000:
            ids = ids[-4000:]
        with open(_USED_PERSIST_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": ids}, f, ensure_ascii=False)
    except Exception as e:
        print(f"  [Fetcher] used_ids persist notice: {e}")


def _blocked_stock_ids() -> set:
    return _published_ids | _job_used_ids


def _stock_candidate_blocked(v: dict) -> bool:
    """P2-24: skip published, job-local, and copyright-blocklisted stock."""
    vid = str(v.get("id", ""))
    source_key = f"{v.get('source', '')}:{vid}"
    if not vid or vid in _blocked_stock_ids():
        return True
    contributor = str(v.get("contributor", "") or "")
    return database.is_stock_blocklisted(source_key, vid, contributor)


# Warm published set from disk — failed/cancelled jobs do not pollute this pool
_published_ids.update(_load_persisted_used_ids())


def commit_published_stock_ids(extra_ids=None) -> int:
    """P1-12: persist stock IDs only after successful publish/render."""
    global _published_ids
    commit = set(extra_ids or []) | set(_job_used_ids)
    if not commit:
        return 0
    _published_ids.update(commit)
    _persist_published_ids()
    return len(commit)


def discard_job_stock_ids() -> None:
    """Drop job-local IDs without persisting (cancel/fail)."""
    _job_used_ids.clear()


def count_pool_candidates(
    queries, target_duration=7, scene_description="", narration="", visual_intent=None, must_exclude=None,
) -> int:
    """P1-12: count unscored stock pool size for a narrow query (no download)."""
    if isinstance(queries, str):
        queries = [queries]
    seen: set = set()
    total = 0
    blocked = _blocked_stock_ids()
    for query in queries[:4]:
        for _src_name, src_fn in ALL_SOURCES:
            try:
                results = src_fn(query) or []
            except Exception:
                results = []
            for v in results:
                vid = str(v.get("id", ""))
                if not vid or vid in seen:
                    continue
                seen.add(vid)
                source_key = f"{v['source']}:{vid}"
                if vid in blocked or _stock_candidate_blocked(v) or database.source_asset_was_used(source_key):
                    continue
                sc = _score(v, target_duration, narration=narration or scene_description, visual_intent=visual_intent)
                if sc > 0:
                    total += 1
    return total


def _download(url, path, cancel_check=None):
    # Item 453: network/process operations bounded by timeout (e.g. timeout=120 for Ken Burns FFmpeg, timeout=60 for stream GET)
    try:
        if cancel_check and cancel_check():
            return False
        r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        with open(path, "wb") as f:
            for c in r.iter_content(8192):
                if cancel_check and cancel_check():
                    f.close()
                    if os.path.exists(path):
                        os.remove(path)
                    return False
                f.write(c)
        return os.path.getsize(path) > 10000  # At least 10KB
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        return False


def _fetch_stock_clip(
    queries, scene_index, project_dir, target_duration=7, scene_description="",
    preferred_source=None, cancel_check=None, narration="", visual_intent=None,
    must_exclude=None, recent_texts=None, niche_id="", intent_dict=None, channel_id=None,
):
    """Stock-only path (license-aware visuals + legacy providers). No procedural."""
    exclude = list(must_exclude or [])
    intent_dict = intent_dict if isinstance(intent_dict, dict) else {}

    if not preferred_source:
        try:
            from visuals.fetch import fetch_open_visual
            from visuals.query_builder import build_shot_queries, validate_query_list
            shot_q = validate_query_list(queries or [], niche_id=niche_id)
            if not shot_q:
                shot_q = build_shot_queries(
                    narration=narration or "", scene_description=scene_description or "",
                    niche_id=niche_id or "", visual_intent=intent_dict,
                )
            path = fetch_open_visual(
                shot_q, scene_index=scene_index, project_dir=project_dir,
                target_duration=target_duration, narration=narration or "",
                scene_description=scene_description or "", niche_id=niche_id or "",
                visual_intent=intent_dict, allow_procedural=False,
                caption_text=narration or scene_description or "",
            )
            if path:
                _promote_stock_to_archive(channel_id, niche_id, path, queries or shot_q)
                return path
        except Exception as exc:
            print(f"    [visuals] layer note: {exc} — falling back to legacy providers")

    clean_queries = []
    for q in queries or []:
        ql = (q or "").lower()
        if exclude and any(ex.lower() in ql for ex in exclude):
            continue
        clean_queries.append(q)
    if not clean_queries:
        if intent_dict.get("search_queries"):
            clean_queries = list(intent_dict["search_queries"])
        else:
            clean_queries = list(queries or [])

    try:
        from visuals.query_builder import build_shot_queries
        from visuals.subject_lock import match_shot, query_matches_clip
        shot = match_shot(
            narration or "", scene_description or "", str((intent_dict or {}).get("subject") or ""),
        )
        extended_queries = list(clean_queries)
        for fq in build_shot_queries(
            narration=narration or "", scene_description=scene_description or "",
            niche_id=niche_id or "", visual_intent=intent_dict, max_queries=4,
        ):
            if fq not in extended_queries:
                if exclude and any(ex.lower() in fq.lower() for ex in exclude):
                    continue
                extended_queries.append(fq)
        if shot is not None:
            anchored = [
                q for q in extended_queries
                if query_matches_clip(shot.primary, q) or query_matches_clip(q, shot.primary)
            ]
            if anchored:
                extended_queries = anchored
    except Exception:
        extended_queries = list(clean_queries)
        from visuals.subject_lock import match_shot
        subject_locked = match_shot(
            narration or "", scene_description or "", str((intent_dict or {}).get("subject") or "")
        )
        generic_fallbacks = [] if subject_locked else [
            "architectural detail soft light", "nature aerial calm", "abstract light particles dark",
        ]
        for fallback_q in generic_fallbacks:
            if fallback_q not in extended_queries:
                if exclude and any(ex.lower() in fallback_q for ex in exclude):
                    continue
                extended_queries.append(fallback_q)

    try:
        from services.stock_simplifier_fallback import build_resilient_query_ladder
        extended_queries = build_resilient_query_ladder(extended_queries)
    except Exception:
        pass

    pref_l = (preferred_source or "").strip().lower()
    if pref_l and pref_l not in ("pexels_pixabay", "stock", "auto"):
        source_order = [
            source for source in ALL_SOURCES if source[0].lower() == pref_l
        ] + [
            source for source in ALL_SOURCES if source[0].lower() != pref_l
        ]
    else:
        paid_top = [s for s in ALL_SOURCES if s[0].lower() in ("pexels", "pixabay")]
        if len(paid_top) == 2 and scene_index % 2 == 1:
            paid_top = [paid_top[1], paid_top[0]]
        others = [s for s in ALL_SOURCES if s[0].lower() not in ("pexels", "pixabay")]
        source_order = paid_top + others

    for qi, query in enumerate(extended_queries):
        if cancel_check and cancel_check():
            return None
        all_results = []
        for src_name, src_fn in source_order:
            if cancel_check and cancel_check():
                return None
            results = src_fn(query)
            if results:
                all_results.extend(results)
        if not all_results:
            continue
        scored = []
        for v in all_results:
            source_key = f"{v['source']}:{v['id']}"
            if _stock_candidate_blocked(v) or database.source_asset_was_used(source_key):
                continue
            sc = _score(
                v, target_duration, narration=narration or scene_description,
                visual_intent=visual_intent, recent_texts=recent_texts,
            )
            if sc > 0:
                scored.append((sc, v))
        scored.sort(key=lambda x: x[0], reverse=True)
        for sc, v in scored[:7]:
            if cancel_check and cancel_check():
                return None
            sid = str(v["id"]).split("_")[-1]
            path = os.path.join(project_dir, f"s{scene_index:03d}_{v['source']}_{sid}.mp4")
            if _download(v["url"], path, cancel_check=cancel_check):
                fh = _file_hash(path)
                with _fetch_lock:
                    if fh in _used_hashes:
                        os.remove(path)
                        continue
                    vid_key = str(v["id"])
                    if vid_key in _job_used_ids:
                        os.remove(path)
                        continue
                    if database.source_asset_was_used(f"{v['source']}:{v['id']}", fh):
                        os.remove(path)
                        continue
                    database.record_source_asset(f"{v['source']}:{v['id']}", v["url"], fh, v["source"])
                    _job_used_ids.add(vid_key)
                    _used_hashes.add(fh)
                print(f"    [OK] [{v['source'].upper()}] {v['fw']}x{v['fh']} {v['duration']}s score:{sc:.0f}")
                try:
                    from director.visual_intent import semantic_relevance_score
                    cand_text = " ".join(
                        str(v.get(k, "")) for k in ("title", "tags", "description", "url", "id")
                    )
                    topic_score = round(
                        semantic_relevance_score(cand_text, narration or "", visual_intent), 4
                    )
                except Exception:
                    topic_score = None
                _record_visual_manifest(
                    path, scene_index, v.get("source", "stock"), str(v.get("id", "")),
                    title=str(v.get("title") or ""), tags=v.get("tags"),
                    description=v.get("description") or "", topic_match_score=topic_score,
                )
                _promote_stock_to_archive(
                    channel_id, niche_id, path, queries or extended_queries,
                    source=v.get("source", "stock"), source_id=str(v.get("id", "")),
                )
                return path
            time.sleep(0.1)
    return None


def _promote_stock_to_archive(channel_id, niche_id, path, queries, source="stock", source_id=""):
    if not channel_id or not path:
        return
    try:
        from channel_broll import promote_clip
        promote_clip(channel_id, niche_id or "", path, queries=queries, source=source, source_id=source_id)
    except Exception as exc:
        print(f"    [ChannelBroll] promote note: {exc}")


def search_and_download(
    queries, scene_index, project_dir, target_duration=7, scene_description="",
    preferred_source=None, cancel_check=None, allow_custom=True, narration="",
    visual_intent=None, must_exclude=None, recent_texts=None, niche_id="",
    channel_id=None, allow_procedural=True,
):
    global _source_counter

    if isinstance(queries, str):
        queries = [queries]

    exclude = list(must_exclude or [])
    if isinstance(visual_intent, dict):
        exclude.extend(visual_intent.get("must_exclude") or [])
        if not narration:
            narration = visual_intent.get("subject", "")
    elif visual_intent is not None:
        exclude.extend(getattr(visual_intent, "must_exclude", []) or [])

    intent_dict = visual_intent if isinstance(visual_intent, dict) else (
        visual_intent.to_dict() if hasattr(visual_intent, "to_dict") else {}
    )

    if channel_id:
        try:
            from channel_broll import try_archive_hit
            hit = try_archive_hit(channel_id, niche_id or "", queries or [], project_dir, scene_index)
            if hit:
                return hit
        except Exception as exc:
            print(f"    [ChannelBroll] lookup note: {exc}")

    # Item 98: custom footage pool first
    custom_bg_dir = os.path.join(config.BASE_DIR, "assets", "custom_backgrounds")
    if allow_custom and os.path.exists(custom_bg_dir):
        valid_exts = (".mp4", ".mov", ".mkv", ".webm")
        custom_files = [
            os.path.join(custom_bg_dir, f) for f in os.listdir(custom_bg_dir)
            if f.lower().endswith(valid_exts) and os.path.isfile(os.path.join(custom_bg_dir, f))
        ]
        if custom_files:
            available_custom = [
                f for f in custom_files
                if f not in _blocked_stock_ids() and not database.source_asset_was_used(f"custom:{_file_hash(f)}")
            ]
            if available_custom:
                raw_custom = available_custom[scene_index % len(available_custom)]
                source_hash = _file_hash(raw_custom)
                database.record_source_asset(f"custom:{source_hash}", raw_custom, source_hash, "custom")
                _job_used_ids.add(raw_custom)
                selected_custom = slice_random_background_loop(
                    raw_custom, project_dir, scene_index, target_duration=target_duration
                )
                print(f"    [OK] [KENDİ ÇEKİM HAVUZU - Madde 98 & 139] Özel kütüphane klibi dinamik kesildi: {os.path.basename(selected_custom)}")
                return selected_custom

    # ── Visual mixer: AI + stock + procedural as equal peers ─────────────
    try:
        from visuals.ai_video import (
            VisualSource, ai_video_enabled, assign_visual_source, generate_ai_clip, peer_failover_order,
        )
        ai_on = ai_video_enabled() if preferred_source not in ("stock", "pexels", "pixabay") else False
        primary = assign_visual_source(
            scene_index, niche_id=niche_id or "",
            seed=getattr(config, "VISUAL_MIX_SEED", None) or None, ai_available=ai_on,
        )
        order = peer_failover_order(primary, niche_id=niche_id or "", ai_available=ai_on)
        print(f"    [MIX] scene={scene_index} primary={primary.value} order={[s.value for s in order]}")
    except Exception as exc:
        print(f"    [MIX] unavailable ({exc}) — stock→procedural")
        order = None
        VisualSource = None  # type: ignore
        generate_ai_clip = None  # type: ignore

    if order and VisualSource is not None:
        for src in order:
            if cancel_check and cancel_check():
                return None
            if src == VisualSource.AI and generate_ai_clip is not None:
                out = os.path.join(project_dir, f"s{scene_index:03d}_ai_video.mp4")
                try:
                    result = generate_ai_clip(
                        narration=narration or "", scene_description=scene_description or "",
                        niche_id=niche_id or "", duration=float(target_duration or 5.0),
                        aspect="9:16", seed=scene_index * 9973, output_path=out,
                    )
                    if result and result.path:
                        try:
                            from visuals.fetch import add_manifest_entry
                            add_manifest_entry(result.to_manifest(scene_index))
                        except Exception:
                            pass
                        return result.path
                except Exception as exc:
                    print(f"    [MIX:ai] {exc}")
                continue
            if src == VisualSource.STOCK:
                path = _fetch_stock_clip(
                    queries, scene_index, project_dir, target_duration,
                    scene_description=scene_description, preferred_source=preferred_source,
                    cancel_check=cancel_check, narration=narration, visual_intent=visual_intent,
                    must_exclude=exclude, recent_texts=recent_texts, niche_id=niche_id,
                    intent_dict=intent_dict, channel_id=channel_id,
                )
                if path:
                    return path
                continue
            if src == VisualSource.PROCEDURAL:
                if not allow_procedural:
                    continue
                fallback_path = _generate_fallback_clip(
                    scene_index, project_dir, target_duration,
                    scene_description=scene_description, visual_intent=visual_intent,
                    narration=narration, niche_id=niche_id,
                )
                if fallback_path:
                    return fallback_path

    # Legacy path if mixer import failed
    path = _fetch_stock_clip(
        queries, scene_index, project_dir, target_duration,
        scene_description=scene_description, preferred_source=preferred_source,
        cancel_check=cancel_check, narration=narration, visual_intent=visual_intent,
        must_exclude=exclude, recent_texts=recent_texts, niche_id=niche_id,
        intent_dict=intent_dict, channel_id=channel_id,
    )
    if path:
        return path
    if cancel_check and cancel_check():
        return None
    if not allow_procedural:
        print(f"    [FAIL] Scene {scene_index}: stock miss, procedural skipped")
        return None
    fallback_path = _generate_fallback_clip(
        scene_index, project_dir, target_duration,
        scene_description=scene_description, visual_intent=visual_intent,
        narration=narration, niche_id=niche_id,
    )
    if fallback_path:
        return fallback_path

    print(f"    [FAIL] Scene {scene_index}: Could not retrieve clip")
    return None


def reset_used_videos():
    """P1-12: clear job-local dedup; published pool stays for cross-job diversity."""
    global _used_hashes, _source_counter
    _job_used_ids.clear()
    _used_hashes.clear()
    _source_counter = 0
