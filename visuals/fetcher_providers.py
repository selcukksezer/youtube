"""
Selected stock video download, multi-pool scene orchestration (gather_scene_pools),
fetch_scene_clip, and multi-source clip mixing.
"""
import hashlib
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional
from urllib.parse import urlsplit
import requests
import config
import database


def _vf_mod():
    return sys.modules.get("video_fetcher")


def _usable_clip(path) -> bool:
    return bool(path) and os.path.isfile(path) and os.path.getsize(path) > 1000


def _drop_other_clips(winner, paths):
    for path in paths:
        if path and path != winner and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def fetch_selected_stock_video(
    selected_video: dict[str, Any],
    scene_index: int,
    project_dir: str,
    target_duration: float = 7.0,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Optional[str]:
    """Download a selected licensed stock video from its known provider CDN."""
    vf = _vf_mod()
    req_mod = getattr(vf, "requests", requests) if vf else requests
    db_mod = getattr(vf, "database", database) if vf else database
    selected_hosts = getattr(vf, "_SELECTED_VIDEO_HOSTS", {})
    max_bytes = getattr(vf, "_MAX_SELECTED_VIDEO_BYTES", 256 * 1024 * 1024)
    file_hash_fn = getattr(vf, "_file_hash")
    safe_url_fn = getattr(vf, "_safe_public_url")
    fetch_lock = getattr(vf, "_fetch_lock")
    job_used_ids = getattr(vf, "_job_used_ids")
    used_hashes = getattr(vf, "_used_hashes")
    session_counts = getattr(vf, "_SESSION_SOURCE_COUNTS")

    if not isinstance(selected_video, dict):
        print("    [SelectedStock] selection is not an object; falling back to scene search.")
        return None

    source = str(selected_video.get("source") or "").strip().casefold()
    kind = str(selected_video.get("kind") or "").strip().casefold()
    url = str(selected_video.get("url") or "").strip()
    local_p = selected_video.get("path") or selected_video.get("video_path") or selected_video.get("file_path")
    if local_p and os.path.isfile(local_p) and os.path.getsize(local_p) > 1000:
        return local_p

    allowed_hosts = selected_hosts.get(source)
    if kind != "video":
        print(f"    [SelectedStock] {source or 'unknown'} selection is {kind or 'untyped'}, not video; falling back.")
        return None
    if not allowed_hosts or not url:
        print(f"    [SelectedStock] unsupported provider or empty URL ({source or 'unknown'}); falling back.")
        return None
    try:
        parsed_url = urlsplit(url)
        port = parsed_url.port
    except ValueError as exc:
        print(f"    [SelectedStock] invalid selected URL: {exc}; falling back.")
        return None
    path_lower = parsed_url.path.lower()
    if (
        parsed_url.scheme != "https"
        or parsed_url.username
        or parsed_url.password
        or parsed_url.hostname not in allowed_hosts
        or port not in (None, 443)
        or not (path_lower.endswith(".mp4") or ".mp4" in path_lower or ".mp4" in url.lower())
    ):
        print(f"    [SelectedStock] rejected URL outside the {source} MP4 CDN; falling back.")
        return None
    if cancel_check and cancel_check():
        return None

    source_id = str(selected_video.get("id") or "").strip()
    if not source_id:
        source_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    if source == "mixkit" and (
        "looking-at-camera" in source_id.lower()
        or any(b in url for b in ("/47994/", "/47995/", "/47996/", "/48000/", "/44562/"))
        or source_id in job_used_ids
    ):
        print(f"    [SelectedStock] skipping generic/duplicate Mixkit clip {source_id}; falling back to scene search.")
        return None
    source_key = f"{source}:{source_id}"
    candidate = {
        "source": source,
        "id": source_id,
        "contributor": selected_video.get("contributor") or "",
    }
    if db_mod.is_stock_blocklisted(source_key, source_id, candidate.get("contributor") or ""):
        print(f"    [SelectedStock] {source_key} is copyright-blocklisted; falling back.")
        return None

    os.makedirs(project_dir, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", source_id)[:80] or "selected"
    clip_path = os.path.join(project_dir, f"s{scene_index:03d}_{source}_{safe_id}_selected.mp4")

    if _usable_clip(clip_path):
        print(f"    [SelectedStock] Using existing cached clip: {os.path.basename(clip_path)}")
        return clip_path

    from visuals.license import License, LicenseInfo, is_commercial_safe

    provider_licenses = {
        "pexels": License.PEXELS,
        "pixabay": License.PIXABAY,
        "coverr": License.COVERR,
        "mixkit": License.CC0,
    }
    license_data = selected_video.get("license")
    if license_data is None:
        license_info = LicenseInfo(provider_licenses.get(source, License.CC0), source)
    elif isinstance(license_data, dict) and license_data.get("license"):
        license_info = LicenseInfo.from_dict(license_data)
        if not is_commercial_safe(license_info.license) or (license_info.source and license_info.source.casefold() != source):
            print(f"    [SelectedStock] unsafe or mismatched license metadata for {source_key}; falling back.")
            return None
    else:
        print(f"    [SelectedStock] invalid license metadata for {source_key}; falling back.")
        return None

    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix=f".{os.path.basename(clip_path)}.",
            suffix=".part",
            dir=project_dir,
        )
        os.close(fd)
        with req_mod.get(
            url,
            stream=True,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=False,
        ) as response:
            if response.is_redirect:
                raise req_mod.RequestException("selected video redirect rejected")
            response.raise_for_status()
            declared_size = response.headers.get("Content-Length")
            if declared_size:
                try:
                    if int(declared_size) > max_bytes:
                        raise req_mod.RequestException("selected video exceeds download limit")
                except ValueError as exc:
                    raise req_mod.RequestException("invalid selected video Content-Length") from exc

            downloaded_size = 0
            with open(temp_path, "wb") as output:
                for chunk in response.iter_content(256 * 1024):
                    if cancel_check and cancel_check():
                        print(f"    [SelectedStock] download cancelled for {source_key}.")
                        return None
                    if not chunk:
                        continue
                    downloaded_size += len(chunk)
                    if downloaded_size > max_bytes:
                        raise req_mod.RequestException("selected video exceeds download limit")
                    output.write(chunk)
        if downloaded_size <= 10_000:
            raise req_mod.RequestException("selected video download below size floor")
        os.replace(temp_path, clip_path)
        temp_path = None
    except (req_mod.RequestException, OSError) as exc:
        print(f"    [SelectedStock] {source_key} download failed: {exc}; falling back.")
        return None
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.remove(temp_path)
            except OSError as exc:
                print(f"    [SelectedStock] temporary file cleanup failed: {exc}")

    if cancel_check and cancel_check():
        try:
            os.remove(clip_path)
        except OSError as exc:
            print(f"    [SelectedStock] cancelled clip cleanup failed: {exc}")
        return None

    from system_resilience import verify_stock_video_integrity

    try:
        minimum_duration = min(1.0, max(0.3, float(target_duration) * 0.3))
    except (TypeError, ValueError):
        minimum_duration = 1.0
    integrity = verify_stock_video_integrity(clip_path, min_duration=minimum_duration)
    if not integrity.get("valid"):
        print(f"    [SelectedStock] ffprobe rejected {source_key}: {integrity.get('reason')}; falling back.")
        try:
            os.remove(clip_path)
        except OSError as exc:
            print(f"    [SelectedStock] invalid clip cleanup failed: {exc}")
        return None

    clip_hash = file_hash_fn(clip_path)
    with fetch_lock:
        db_mod.record_source_asset(source_key, url, clip_hash, source)
        job_used_ids.add(source_id)
        used_hashes.add(clip_hash)

    title = str(selected_video.get("title") or f"{source.title()} video {source_id}")
    source_url = safe_url_fn(str(selected_video.get("source_url") or license_info.source_url or "")) or ""
    license_urls = {
        "pexels": "https://www.pexels.com/license/",
        "pixabay": "https://pixabay.com/service/license-summary/",
        "coverr": "https://coverr.co/license",
        "mixkit": "https://mixkit.co/license/#sfxFree",
    }
    license_url = safe_url_fn(str(selected_video.get("license_url") or license_info.license_url or "")) or license_urls.get(source, "https://creativecommons.org/publicdomain/zero/1.0/")
    license_info.source = source
    license_info.title = title
    license_info.source_url = source_url
    license_info.license_url = license_url

    from visuals.fetch import add_manifest_entry

    add_manifest_entry({
        "scene_index": int(scene_index),
        "path": clip_path,
        "uid": f"selected:{source_key}",
        "source": source,
        "id": source_id,
        "title": title,
        "kind": "video",
        "url": url,
        "asset_url": url,
        "source_url": source_url,
        "license_url": license_url,
        "attribution": selected_video.get("attribution") or license_info.attribution,
        "contributor": selected_video.get("contributor") or "",
        "sha1": clip_hash,
        "sha256": clip_hash,
        "topic_match_score": 0.95,
        "visual_verification_score": 1.0,
        "license": license_info.to_dict(),
    })
    if source in session_counts:
        session_counts[source] = session_counts.get(source, 0) + 1
    print(f"    [OK] [SelectedStock:{source}] scene={scene_index} id={source_id}")
    return clip_path


def gather_scene_pools(
    search_queries,
    scene_index,
    project_dir,
    target_duration=7,
    scene_description="",
    cancel_check=None,
    narration="",
    visual_intent=None,
    must_exclude=None,
    recent_texts=None,
    allow_custom=True,
    niche_id="",
    channel_id=None,
    allow_procedural=True,
    runners=None,
):
    """Plan 6.1 pools in one orchestrator."""
    if cancel_check and cancel_check():
        return None

    vf = _vf_mod()
    cfg = getattr(vf, "config", config) if vf else config
    fetch_stock_fn = getattr(vf, "_fetch_stock_clip")
    fallback_clip_fn = getattr(vf, "_generate_fallback_clip")

    def _stock():
        return fetch_stock_fn(
            search_queries, scene_index, project_dir, target_duration,
            scene_description=scene_description, preferred_source=None,
            cancel_check=cancel_check, narration=narration, visual_intent=visual_intent,
            must_exclude=must_exclude, recent_texts=recent_texts, niche_id=niche_id,
            channel_id=channel_id,
        )

    def _flux():
        try:
            from services.pollinations_ai_visual import create_scene_ai_clip, pollinations_circuit_open
            if pollinations_circuit_open():
                return None
            path = os.path.join(project_dir, f"s{scene_index:03d}_flux.mp4")
            made = create_scene_ai_clip(
                scene_description=scene_description or narration or (search_queries[0] if search_queries else "cinematic vertical"),
                output_video_path=path,
                duration=target_duration,
                scene_index=scene_index,
            )
            return made or None
        except Exception as exc:
            print(f"    [POOL:flux] {exc}")
            return None

    def _procedural():
        return fallback_clip_fn(
            scene_index, project_dir, target_duration,
            scene_description=scene_description, visual_intent=visual_intent,
            narration=narration, niche_id=niche_id, include_whiteboard=False,
        )

    def _whiteboard():
        if not getattr(cfg, "ALLOW_PROCEDURAL_VISUALS", False):
            return None
        try:
            from services.whiteboard_animator import create_whiteboard_scene_clip
            path = os.path.join(project_dir, f"s{scene_index:03d}_whiteboard.mp4")
            return create_whiteboard_scene_clip(
                scene_description=scene_description or narration or "whiteboard line art sketch",
                output_video_path=path,
                duration=target_duration,
                scene_index=scene_index,
                narration=narration,
            )
        except Exception as exc:
            print(f"    [POOL:whiteboard] {exc}")
            return None

    jobs = runners or {
        "stock": _stock,
        "flux": _flux,
        "procedural": _procedural,
        "whiteboard": _whiteboard,
    }
    try:
        stock_path = jobs["stock"]()
    except Exception as exc:
        print(f"    [POOL:stock] {exc}")
        stock_path = None
    if _usable_clip(stock_path):
        print(f"    [POOL] scene={scene_index} winner=stock")
        return stock_path
    if not allow_procedural:
        print(f"    [POOL] scene={scene_index} stock miss, generators skipped")
        return None
    if cancel_check and cancel_check():
        return None

    names = ("flux", "procedural", "whiteboard")
    found = {}
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        futures = {name: pool.submit(jobs[name]) for name in names}
        for name, fut in futures.items():
            try:
                found[name] = fut.result()
            except Exception as exc:
                print(f"    [POOL:{name}] {exc}")
                found[name] = None
    for name in names:
        path = found.get(name)
        if _usable_clip(path):
            _drop_other_clips(path, found.values())
            print(f"    [POOL] scene={scene_index} winner={name}")
            return path
    return None


def fetch_scene_clip(
    search_queries,
    scene_index,
    project_dir,
    target_duration=7,
    scene_description="",
    mood="epic",
    cancel_check=None,
    narration="",
    visual_intent=None,
    must_exclude=None,
    recent_texts=None,
    allow_custom=True,
    preferred_source=None,
    niche_id="",
    channel_id=None,
    allow_procedural=True,
):
    """P0-05 / Item 130 – Per-scene multi-provider stock fetch."""
    vf = _vf_mod()
    search_dl_fn = getattr(vf, "search_and_download")
    gather_fn = getattr(vf, "gather_scene_pools", gather_scene_pools)
    source_label_fn = getattr(vf, "_source_label_from_path")
    record_manifest_fn = getattr(vf, "_record_visual_manifest")
    session_counts = getattr(vf, "_SESSION_SOURCE_COUNTS")

    if isinstance(search_queries, str):
        search_queries = [search_queries]

    clip_path = None
    if preferred_source:
        clip_path = search_dl_fn(
            search_queries,
            scene_index,
            project_dir,
            target_duration=target_duration,
            scene_description=scene_description,
            preferred_source=preferred_source,
            cancel_check=cancel_check,
            narration=narration,
            visual_intent=visual_intent,
            must_exclude=must_exclude,
            recent_texts=recent_texts,
            allow_custom=allow_custom,
            niche_id=niche_id or "",
            channel_id=channel_id,
            allow_procedural=False,
        )

    if not clip_path:
        clip_path = gather_fn(
            search_queries,
            scene_index,
            project_dir,
            target_duration=target_duration,
            scene_description=scene_description,
            cancel_check=cancel_check,
            narration=narration,
            visual_intent=visual_intent,
            must_exclude=must_exclude,
            recent_texts=recent_texts,
            allow_custom=allow_custom,
            niche_id=niche_id or "",
            channel_id=channel_id,
            allow_procedural=allow_procedural,
        )

    if not clip_path:
        print(f"    [MultiSource] Scene {scene_index}: stock and generator pools missed")
        return None

    label = source_label_fn(clip_path)
    record_manifest_fn(clip_path, scene_index, label)
    if label in session_counts:
        session_counts[label] = session_counts.get(label, 0) + 1

    try:
        from system_resilience import verify_stock_video_integrity
        integrity = verify_stock_video_integrity(clip_path, min_duration=min(1.0, target_duration * 0.3))
        if not integrity.get("valid"):
            print(f"    [MultiSource] ffprobe reject {os.path.basename(clip_path)}: {integrity.get('reason')}")
            try:
                os.remove(clip_path)
            except OSError:
                pass
            return None
        if integrity.get("soft"):
            print(f"    [MultiSource] keep rounded frame {integrity.get('width')}x{integrity.get('height')}", flush=True)
    except Exception:
        pass

    return clip_path


def fetch_multi_source_clips(
    scenes: list,
    project_dir: str,
    force_source_mix: bool = True,
) -> list:
    """Item 130 – İki Farklı Stok Sağlayıcıyı Karıştırma."""
    vf = _vf_mod()
    reset_counts_fn = getattr(vf, "reset_session_source_counts")
    pick_source_fn = getattr(vf, "_pick_next_source")
    gen_ai_fn = getattr(vf, "generate_ai_image_clip")
    fetch_clip_fn = getattr(vf, "fetch_scene_clip", fetch_scene_clip)
    source_label_fn = getattr(vf, "_source_label_from_path")
    dist_fn = getattr(vf, "get_session_source_distribution")

    reset_counts_fn()
    results = []

    print(f"\n  [Item 130] Çok kaynaklı stok karıştırma: {len(scenes)} sahne...")

    for i, scene in enumerate(scenes):
        query = scene.get("search_queries", ["nature", "abstract", "city"])[0]
        duration = scene.get("duration", 6.0)
        scene_desc = scene.get("scene_description", query)
        preferred_source = pick_source_fn(i)

        clip_path = None
        used_source = None

        if preferred_source == "ai":
            ai_path = os.path.join(project_dir, f"s{i:03d}_ai_gen.mp4")
            clip_path = gen_ai_fn(scene_description=scene_desc, output_path=ai_path, duration=duration)
            used_source = "ai" if clip_path else None

        if not clip_path:
            clip_path = fetch_clip_fn(
                search_queries=scene.get("search_queries", [query]),
                scene_index=i,
                project_dir=project_dir,
                target_duration=duration,
                scene_description=scene_desc,
                mood=scene.get("mood", "epic"),
            )
            if clip_path:
                used_source = source_label_fn(clip_path)

        if clip_path and used_source:
            results.append((i, clip_path, used_source))
            print(f"    [Item 130] Sahne {i}: [{used_source.upper()}] {os.path.basename(clip_path)}")
        else:
            results.append((i, None, "failed"))
            print(f"    [Item 130] Sahne {i}: Klip alınamadı")

    dist = dist_fn()
    unique_sources = [k for k, v in dist.items() if v > 0]
    print(f"\n  [Item 130] Kaynak dağılımı: {dist}")
    print(f"  [Item 130] Kullanılan kaynaklar: {unique_sources} ({len(unique_sources)} farklı)")

    if force_source_mix and len(unique_sources) < 2:
        print(f"  [Item 130] UYARI: Tek kaynak kullanıldı ({unique_sources}). Çeşitlilik hedefi karşılanmadı.")

    return results
