"""
Project plan loading, timeline asset preparation, and scene clip replacement routes.
Extracted from routers/video_router.py for modularity.
"""
import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

import config
from scenes.narration_validate import sanitize_plan_scene_descriptions
from server_core import state

router = APIRouter(tags=["Video"])
logger = logging.getLogger(__name__)


def normalize_scene_paths_for_web(
    plan_dict: Optional[Dict[str, Any]], proj_folder_name: str = ""
) -> Dict[str, Any]:
    """Ensures each scene has a web-accessible video_url and thumbnail_url for in-browser playback."""
    if not plan_dict or not isinstance(plan_dict, dict) or "scenes" not in plan_dict:
        return plan_dict or {}
    scenes = plan_dict.get("scenes") or []
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        p = sc.get("path") or (sc.get("selected_video") or {}).get("path")
        if p and isinstance(p, str):
            p_clean = p.replace("\\", "/")
            if "/assets/" in p_clean:
                rel = p_clean.split("/assets/", 1)[-1]
                sc["video_url"] = f"/assets/{rel}"
            elif os.path.isabs(p) and os.path.exists(p):
                try:
                    rel = os.path.relpath(p, config.ASSETS_DIR).replace("\\", "/")
                    if not rel.startswith(".."):
                        sc["video_url"] = f"/assets/{rel}"
                    else:
                        sub = proj_folder_name or ""
                        sc["video_url"] = (
                            f"/assets/{sub}/{os.path.basename(p)}"
                            if sub
                            else f"/assets/{os.path.basename(p)}"
                        )
                except Exception:
                    sub = proj_folder_name or ""
                    sc["video_url"] = (
                        f"/assets/{sub}/{os.path.basename(p)}"
                        if sub
                        else f"/assets/{os.path.basename(p)}"
                    )
            elif not p.startswith("http") and not p.startswith("/"):
                sub = proj_folder_name or ""
                sc["video_url"] = (
                    f"/assets/{sub}/{os.path.basename(p)}"
                    if sub
                    else f"/assets/{os.path.basename(p)}"
                )
            elif p.startswith("http") or p.startswith("/"):
                sc["video_url"] = p
        elif sc.get("selected_video") and sc["selected_video"].get("url"):
            sc["video_url"] = sc["selected_video"]["url"]
            if sc["selected_video"].get("thumbnail"):
                sc["thumbnail_url"] = sc["selected_video"]["thumbnail"]
    return plan_dict


def _sanitize_project_slug(raw_slug: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    cleaned = re.sub(r"[^\w\s-]", "", (raw_slug or "").translate(tr_map))
    cleaned = re.sub(r"\s+", "_", cleaned.strip())[:80]
    return cleaned or f"project_{int(time.time())}"


@router.get("/api/projects/latest/plan")
@router.get("/api/plan/latest")
def get_latest_project_plan():
    """Returns the most recently rendered or saved project plan with real downloaded footage."""
    if not os.path.exists(config.ASSETS_DIR):
        raise HTTPException(status_code=404, detail="Henüz kaydedilmiş bir proje bulunamadı.")

    candidates = []
    try:
        for name in os.listdir(config.ASSETS_DIR):
            folder = os.path.join(config.ASSETS_DIR, name)
            if os.path.isdir(folder) and name not in (".git", "channels", "custom_backgrounds"):
                p_file = os.path.join(folder, "plan.json")
                if os.path.isfile(p_file):
                    mtime = os.path.getmtime(p_file)
                    candidates.append((mtime, name, p_file, folder))
    except Exception as e:
        logger.warning("Error scanning assets for latest plan: %s", e)

    if not candidates:
        raise HTTPException(status_code=404, detail="Henüz kaydedilmiş bir proje senaryosu bulunamadı.")

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, safe_name, p_file, folder = candidates[0]

    try:
        with open(p_file, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan okunamadı: {e}")

    director = None
    dpath = os.path.join(folder, "director_plan.json")
    if os.path.isfile(dpath):
        try:
            with open(dpath, "r", encoding="utf-8") as f:
                director = json.load(f)
        except Exception:
            director = None

    plan = sanitize_plan_scene_descriptions(plan or {})
    plan = normalize_scene_paths_for_web(plan, safe_name)

    return {
        "status": "ok",
        "slug": safe_name,
        "project_slug": safe_name,
        "plan": plan,
        "director": director,
    }


@router.get("/api/projects/{slug}/plan")
def get_project_plan(slug: str):
    """Load saved plan.json / director_plan.json for gallery reopen -> timeline."""
    safe = os.path.basename(slug or "").strip()
    safe = re.sub(r"[^\w\-]", "", safe.replace(" ", "_"))[:120]
    if not safe:
        raise HTTPException(status_code=400, detail="Gecersiz proje adi")

    proj = os.path.join(config.ASSETS_DIR, safe)
    if not os.path.isdir(proj):
        try:
            for name in os.listdir(config.ASSETS_DIR):
                if name.startswith(safe[:40]) or safe.startswith(name[:40]):
                    cand = os.path.join(config.ASSETS_DIR, name)
                    if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "plan.json")):
                        proj = cand
                        safe = name
                        break
        except OSError:
            pass
    plan_path = os.path.join(proj, "plan.json")
    if not os.path.isfile(plan_path):
        raise HTTPException(status_code=404, detail="Bu video icin kayitli senaryo bulunamadi")

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan okunamadi: {e}")

    director = None
    dpath = os.path.join(proj, "director_plan.json")
    if os.path.isfile(dpath):
        try:
            with open(dpath, "r", encoding="utf-8") as f:
                director = json.load(f)
        except Exception:
            director = None

    qg = None
    qpath = os.path.join(proj, "quality_gate.json")
    if os.path.isfile(qpath):
        try:
            with open(qpath, "r", encoding="utf-8") as f:
                qg = json.load(f)
        except Exception:
            qg = None

    from director import compile_director_plan, pre_render_score
    from director.quality_gate import check_narration_integrity

    title = plan.get("title") or safe.replace("_", " ")
    niche_id = (director or {}).get("niche_id") or plan.get("niche_id") or "1_news_flash"
    try:
        compiled = compile_director_plan(plan, title=title, niche_id=niche_id)
        integrity = check_narration_integrity(compiled)
        pre = pre_render_score(compiled)
        if integrity or not pre.get("ok"):
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Kayitli senaryo kopuk cumle iceriyor — yeni senaryo uretin.",
                    "narration_integrity": integrity,
                    "pre_render_score": pre,
                },
            )
        plan = compiled.to_legacy_plan()
        director = compiled.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan dogrulanamadi: {e}")

    plan = sanitize_plan_scene_descriptions(plan or {})
    plan = normalize_scene_paths_for_web(plan, safe)

    return {
        "status": "ok",
        "slug": safe,
        "plan": plan,
        "director": director,
        "quality_gate": qg,
    }


@router.post("/api/timeline/prepare")
def api_prepare_timeline_assets(payload: Dict[str, Any]):
    """
    Prepares high-craft narrative and downloads real video clips for each scene
    into the project assets folder so the Scene & Montage Editor displays real footage and final script.
    """
    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else None
    keyword = str(
        payload.get("keyword")
        or payload.get("title")
        or payload.get("topic")
        or (plan or {}).get("title")
        or (plan or {}).get("keyword")
        or ""
    ).strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Lütfen bir video konusu girin.")

    niche = str(
        payload.get("niche")
        or payload.get("niche_id")
        or (plan or {}).get("niche_id")
        or (plan or {}).get("niche")
        or ""
    ).strip()
    language = str(
        payload.get("language") or (plan or {}).get("language") or config.LANGUAGE or "tr"
    ).strip().lower()

    from director import resolve_niche_from_topic

    locked_niche = resolve_niche_from_topic(keyword, niche or "1_news_flash")

    safe = _sanitize_project_slug(keyword)
    from services.path_security import safe_join

    proj = safe_join(config.ASSETS_DIR, safe)
    os.makedirs(proj, exist_ok=True)

    if not plan or not plan.get("scenes"):
        from scene_generator import generate_scenes

        plan = generate_scenes(
            keyword,
            niche_type=locked_niche,
            language=language,
            variation_attempt=0,
            enable_outro=True,
        )

    try:
        from craft import apply_human_craft

        plan = apply_human_craft(plan, title=keyword, niche_id=locked_niche, language=language)
    except Exception as e:
        logger.warning("apply_human_craft skip in timeline prepare: %s", e)

    try:
        from scenes.retention_hooks import ensure_retention_hooks_on_plan

        plan = ensure_retention_hooks_on_plan(
            plan, keyword, lang=language, niche_type=locked_niche, enable_outro=True
        )
    except Exception as e:
        logger.warning("ensure_retention_hooks skip in timeline prepare: %s", e)

    try:
        from scenes.enrichment import enrich_plan_scenes, enforce_specific_search_queries

        plan = enrich_plan_scenes(plan, lang=language, niche_id=locked_niche)
        if plan.get("scenes"):
            enforce_specific_search_queries(plan["scenes"])
    except Exception as e:
        logger.warning("enrichment skip in timeline prepare: %s", e)

    from director import compile_director_plan

    director = compile_director_plan(plan, title=keyword, niche_id=locked_niche, language=language)
    plan = director.to_legacy_plan()

    from server_core.render_worker import _fetch_single_scene_visual

    scenes = plan.get("scenes") or []
    total_s = len(scenes)

    for i, sc in enumerate(scenes):
        try:
            _, clip_entry, path_str = _fetch_single_scene_visual(
                i=i,
                scene=sc,
                plan=plan,
                proj=proj,
                total_s=total_s,
            )
            if path_str and isinstance(path_str, str) and os.path.exists(path_str):
                sc["path"] = path_str
                if clip_entry and isinstance(clip_entry, dict):
                    sc["selected_video"] = clip_entry
                if i < len(director.scenes):
                    director.scenes[i].path = path_str
            elif (
                clip_entry
                and isinstance(clip_entry, dict)
                and clip_entry.get("path")
                and os.path.exists(clip_entry["path"])
            ):
                sc["path"] = clip_entry["path"]
                sc["selected_video"] = clip_entry
                if i < len(director.scenes):
                    director.scenes[i].path = clip_entry["path"]
        except Exception as err:
            logger.warning("Scene %s footage fetch error: %s", i + 1, err)

    plan["niche_id"] = locked_niche
    plan["title"] = keyword
    plan["project_slug"] = safe

    with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
        json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)

    plan = normalize_scene_paths_for_web(plan, safe)
    plan["project_slug"] = safe

    state.broadcast_event(
        "plan_updated",
        {
            "slug": safe,
            "title": keyword,
            "plan": plan,
        },
    )

    return {
        "status": "ok",
        "slug": safe,
        "project_slug": safe,
        "plan": plan,
        "message": f"{total_s} sahne için gerçek senaryo ve görsel klipler hazırlandı.",
    }


@router.post("/api/timeline/replace-clip")
def api_replace_scene_media(payload: Dict[str, Any]):
    """
    Replaces a single scene's visual clip (stock video download, 0 TL Flux SDXL, or Whiteboard line-art).
    """
    raw_slug = str(payload.get("project_slug") or "").strip()
    scene_idx = int(payload.get("scene_index", 0))
    action = str(payload.get("action") or payload.get("replace_mode") or "stock").strip().lower()

    if not raw_slug:
        raise HTTPException(status_code=400, detail="project_slug gerekli.")
    if ".." in raw_slug.replace("\\", "/").split("/"):
        raise HTTPException(status_code=400, detail="Geçersiz project_slug.")

    from services.path_security import UnsafePathError, safe_join

    try:
        cand_proj = safe_join(config.ASSETS_DIR, raw_slug)
    except UnsafePathError:
        cand_proj = ""

    if cand_proj and os.path.isdir(cand_proj):
        slug = raw_slug
        proj = cand_proj
    else:
        slug = _sanitize_project_slug(raw_slug)
        proj = safe_join(config.ASSETS_DIR, slug)

    plan_path = os.path.join(proj, "plan.json")
    incoming_plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else None
    if not os.path.isfile(plan_path):
        if incoming_plan and incoming_plan.get("scenes"):
            os.makedirs(proj, exist_ok=True)
            incoming_plan["project_slug"] = slug
            with open(plan_path, "w", encoding="utf-8") as f:
                json.dump(incoming_plan, f, ensure_ascii=False, indent=2)
        elif not os.path.isdir(proj):
            raise HTTPException(status_code=404, detail=f"Proje klasörü bulunamadı: {slug}")
        else:
            raise HTTPException(status_code=404, detail="plan.json bulunamadı.")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    scenes = plan.get("scenes") or []
    if scene_idx < 0 or scene_idx >= len(scenes):
        raise HTTPException(status_code=400, detail="Geçersiz sahne indeksi.")

    sc = scenes[scene_idx]
    target_duration = float(sc.get("duration") or 6.0)
    out_clip_path = None

    if action == "stock":
        stock_data = (
            payload.get("stock_video_data")
            if isinstance(payload.get("stock_video_data"), dict)
            else {}
        )
        video_url = payload.get("video_url") or stock_data.get("url") or stock_data.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Stock video_url gerekli.")
        selected_vid = {
            "url": video_url,
            "id": payload.get("video_id") or stock_data.get("id") or f"swap_{int(time.time())}",
            "source": payload.get("source") or stock_data.get("source") or "stock",
        }
        from video_fetcher import fetch_selected_stock_video

        out_clip_path = fetch_selected_stock_video(
            selected_vid,
            scene_idx,
            proj,
            target_duration=target_duration,
        )
        if out_clip_path and os.path.exists(out_clip_path):
            selected_vid["path"] = out_clip_path
        sc["selected_video"] = selected_vid
        sc["visual_mode"] = "stock"

    elif action in ("flux", "flux_ai", "pollinations"):
        desc = (
            payload.get("prompt")
            or sc.get("scene_description")
            or sc.get("narration")
            or "cinematic vertical footage"
        )
        from services.pollinations_ai_visual import create_scene_ai_clip

        ai_path = os.path.join(proj, f"s{scene_idx:03d}_flux.mp4")
        out_clip_path = create_scene_ai_clip(
            scene_description=desc,
            output_video_path=ai_path,
            duration=target_duration,
            scene_index=scene_idx,
        )
        sc["visual_mode"] = "flux"

    elif action in ("whiteboard", "sketch"):
        desc = (
            payload.get("prompt")
            or sc.get("scene_description")
            or sc.get("narration")
            or "whiteboard sketch"
        )
        from services.whiteboard_animator import create_whiteboard_scene_clip

        wb_path = os.path.join(proj, f"s{scene_idx:03d}_whiteboard.mp4")
        out_clip_path = create_whiteboard_scene_clip(
            scene_description=desc,
            output_video_path=wb_path,
            duration=target_duration,
            scene_index=scene_idx,
            narration=sc.get("narration") or "",
        )
        sc["visual_mode"] = "whiteboard"

    if out_clip_path and os.path.exists(out_clip_path):
        sc["path"] = out_clip_path
        sc["video_path"] = out_clip_path
        filename = os.path.basename(out_clip_path)
        sc["video_url"] = f"/assets/{slug}/{filename}"
        if isinstance(sc.get("selected_video"), dict):
            sc["selected_video"]["path"] = out_clip_path
            sc["selected_video"]["url"] = sc["video_url"]
            sc["selected_video"]["preview_url"] = sc["video_url"]

    plan["project_slug"] = slug
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    director_plan_path = os.path.join(proj, "director_plan.json")
    if os.path.isfile(director_plan_path) and out_clip_path and os.path.exists(out_clip_path):
        try:
            with open(director_plan_path, "r", encoding="utf-8") as df:
                d_data = json.load(df)
            if isinstance(d_data.get("scenes"), list) and scene_idx < len(d_data["scenes"]):
                d_data["scenes"][scene_idx]["path"] = out_clip_path
                with open(director_plan_path, "w", encoding="utf-8") as df:
                    json.dump(d_data, df, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return {
        "status": "ok",
        "project_slug": slug,
        "scene_index": scene_idx,
        "video_url": sc.get("video_url"),
        "clip_url": sc.get("video_url"),
        "path": sc.get("path"),
        "scene": sc,
    }
