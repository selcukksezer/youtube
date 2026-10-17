"""Launch the local Çocuk Şarkı MV studio and talk to its HTTP API."""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import uuid
from typing import Optional

import config
from services.kids_song_process import (
    _BLANK_SECRET,
    _auto_sync_worker,
    _deps_ok,
    _env_key_status,
    _is_blank_secret,
    _log_path,
    _package_ok,
    _prewarm_worker,
    _proc_alive,
    _quote_env,
    _remote_present,
    _shorts_openai,
    _shorts_suno,
    _tail,
    _transfer_message,
    detect_ffmpeg,
    generate_kids_song_idea,
    port_open,
    resolve_studio_dir,
    start,
    start_background_services,
    status,
    stop_managed,
    studio_port,
    studio_url,
    transfer_keys,
    write_env_key_if_blank,
)

_LOCK = threading.Lock()
_PROC: Optional[subprocess.Popen] = None
_LAST_ERROR = ""
_PREWARMED = False
_SYNC_RUNNING = False


class StudioUnavailable(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


_PROJECT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SECRET_IN_TEXT = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")


def _fail(message: str, code: int = 503) -> dict:
    return {"ok": False, "error": message, "status_code": code}


def _safe_error(text: str) -> str:
    cleaned = _SECRET_IN_TEXT.sub("sk-…", text or "")
    cleaned = re.sub(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*)\S+", r"\1…", cleaned)
    cleaned = cleaned.strip()
    return cleaned[:300] or "Stüdyo isteği başarısız."


def _valid_project_id(project_id: str) -> bool:
    return bool(_PROJECT_ID.match(project_id or ""))


def unwrap_studio_payload(payload):
    """Accept either a raw body or the Next `{ok, data}` envelope."""
    if isinstance(payload, dict) and payload.get("ok") is False:
        raise StudioUnavailable(
            _safe_error(str(payload.get("error") or "Stüdyo isteği başarısız."))
        )
    if isinstance(payload, dict) and payload.get("ok") is True and "data" in payload:
        return payload["data"]
    return payload


def _encode_form(fields: dict) -> tuple:
    boundary = "----ShortsKids" + uuid.uuid4().hex
    chunks = []
    for key, value in fields.items():
        chunks.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
            ).encode("utf-8")
            + str(value).encode("utf-8")
            + b"\r\n"
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def _error_from_body(raw: str) -> str:
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return ""
    if isinstance(payload, dict):
        return str(payload.get("error") or "")
    return ""


def _studio_request(
    method: str,
    path: str,
    body: Optional[dict] = None,
    form: Optional[dict] = None,
    timeout: float = 12.0,
):
    if not port_open():
        raise StudioUnavailable("Çocuk şarkı stüdyosu kapalı. Önce Başlat.")
    if not path.startswith("/"):
        path = "/" + path
    data = None
    headers = {"Accept": "application/json"}
    if form is not None:
        data, boundary = _encode_form(form)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(
        studio_url() + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = _error_from_body(exc.read().decode("utf-8", errors="replace"))
        raise StudioUnavailable(_safe_error(detail or f"Stüdyo HTTP {exc.code}"))
    except (urllib.error.URLError, TimeoutError, socket.timeout):
        raise StudioUnavailable("Stüdyo yanıt vermedi. Birkaç saniye sonra tekrar deneyin.")
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise StudioUnavailable("Stüdyo yanıtı okunamadı.")
    return unwrap_studio_payload(payload)


def parse_project_list(payload) -> list:
    data = (
        unwrap_studio_payload(payload)
        if isinstance(payload, dict) and "ok" in payload
        else payload
    )
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if not isinstance(data, list):
        return []
    items = []
    for row in data:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        project_id = str(row.get("id"))
        items.append({
            "id": project_id,
            "name": str(row.get("name") or ""),
            "title": str(row.get("title") or ""),
            "slug": str(row.get("slug") or ""),
            "status": str(row.get("status") or "draft"),
            "clip_count": int(row.get("clipCount") or 0),
            "completed_clip_count": int(row.get("completedClipCount") or 0),
            "render_path": f"/cocuk-sarki/{project_id}/render",
        })
    return items


def summarize_project(project: dict, render_payload: Optional[dict] = None) -> dict:
    """Map a kids project payload to the three shorts status labels."""
    project = project if isinstance(project, dict) else {}
    render_payload = render_payload if isinstance(render_payload, dict) else {}
    if render_payload.get("ok") is True and "data" in render_payload:
        render_payload = (
            render_payload["data"] if isinstance(render_payload["data"], dict) else {}
        )
    clips = project.get("clips") if isinstance(project.get("clips"), list) else []
    jobs = project.get("jobs") if isinstance(project.get("jobs"), list) else []
    finals = (
        render_payload.get("finals")
        if isinstance(render_payload.get("finals"), list)
        else []
    )
    final = next(
        (item for item in finals if isinstance(item, dict) and item.get("path")), None
    )
    status_name = str(project.get("status") or "draft")
    running = any(
        isinstance(job, dict)
        and job.get("state") in ("running", "paused", "needs_manual_action")
        for job in jobs
    )
    clip_count = (
        len(clips)
        if clips
        else int(project.get("clipCount") or project.get("clip_count") or 0)
    )
    completed = (
        sum(
            1
            for clip in clips
            if isinstance(clip, dict) and clip.get("status") == "completed"
        )
        if clips
        else int(
            project.get("completedClipCount") or project.get("completed_clip_count") or 0
        )
    )
    project_id = str(project.get("id") or "")
    if final:
        phase, label = "done", "render bitti"
    elif running or status_name in ("automating", "rendering"):
        phase, label = "automation", "otomasyon"
    else:
        phase, label = "preparing", "hazırlanıyor"
    return {
        "id": project_id,
        "name": str(project.get("name") or ""),
        "title": str(project.get("title") or ""),
        "slug": str(project.get("slug") or ""),
        "status": status_name,
        "phase": phase,
        "label": label,
        "clip_count": clip_count,
        "completed_clip_count": completed,
        "automation_running": running or status_name == "automating",
        "final_exists": bool(final),
        "final_name": str((final or {}).get("fileName") or ""),
        "render_path": f"/cocuk-sarki/{project_id}/render" if project_id else "",
    }


def list_projects() -> dict:
    try:
        data = _studio_request("GET", "/api/projects")
    except StudioUnavailable as exc:
        return _fail(exc.message)
    return {"ok": True, "projects": parse_project_list(data), "url": studio_url()}


def build_create_body(title: str, topic: str = "") -> dict:
    name = (title or "").strip()
    if not name:
        raise ValueError("Başlık gerekli.")
    if len(name) > 120:
        name = name[:120].rstrip()
    return {
        "name": name,
        "title": name,
        "topic": (topic or "").strip()[:2000],
        "genre": "Cocuk sarkisi",
        "templateType": "kids_song",
        "targetDurationSeconds": 90,
        "storyLanguage": "Turkish",
        "speechLanguage": "Turkish",
        "speechPace": "normal",
        "ageBand": "3-5",
        "narrationStyle": "kidspop",
        "visualStyle": "pixar3d",
        "audioEnabled": False,
    }


def create_project(title: str, topic: str = "", lyrics: str = "") -> dict:
    try:
        body = build_create_body(title, topic)
    except ValueError as exc:
        return _fail(str(exc), 400)
    text = (lyrics or "").strip()
    if len(text) > 20000:
        return _fail("Söz metni çok uzun.", 400)
    try:
        created = _studio_request("POST", "/api/projects", body=body)
        if not isinstance(created, dict) or not created.get("id"):
            return _fail("Stüdyo proje kimliği döndürmedi.", 502)
        project_id = str(created["id"])
    except StudioUnavailable as exc:
        return _fail(exc.message)
    lyrics_saved = False
    lyrics_error = ""
    if text:
        try:
            _studio_request(
                "POST", f"/api/projects/{project_id}/song/upload-lyrics", form={"lyrics": text}
            )
            lyrics_saved = True
        except StudioUnavailable as exc:
            lyrics_error = exc.message
    render_path = f"/cocuk-sarki/{project_id}/render"
    project = {
        "id": project_id,
        "name": str(created.get("name") or body["name"]),
        "title": str(created.get("title") or body["title"]),
        "slug": str(created.get("slug") or ""),
        "topic": str(created.get("topic") or body["topic"]),
        "lyrics_saved": lyrics_saved,
        "render_path": render_path,
        "url": studio_url() + render_path,
        "label": "hazırlanıyor",
    }
    if lyrics_error:
        project["lyrics_error"] = lyrics_error
    return {"ok": True, "url": studio_url(), "project": project}


def _apply_disk_final(summary: dict) -> dict:
    if summary.get("final_exists"):
        return summary
    found = find_final_mp4(str(summary.get("slug") or ""))
    if not found:
        return summary
    summary["final_exists"] = True
    summary["final_name"] = os.path.basename(found)
    summary["phase"] = "done"
    summary["label"] = "render bitti"
    return summary


def project_status(project_id: str) -> dict:
    if not _valid_project_id(project_id):
        return _fail("Geçersiz proje kimliği.", 400)
    try:
        project = _studio_request("GET", f"/api/projects/{project_id}")
        render = _studio_request("GET", f"/api/projects/{project_id}/render")
    except StudioUnavailable as exc:
        return _fail(exc.message)
    if not isinstance(project, dict):
        return _fail("Stüdyo proje döndürmedi.", 502)
    summary = summarize_project(project, render if isinstance(render, dict) else {})
    summary = _apply_disk_final(summary)
    if summary.get("render_path"):
        summary["url"] = studio_url() + summary["render_path"]
    return {"ok": True, "project": summary, "url": studio_url()}


def _inside(child: str, parent: str) -> bool:
    try:
        child_real = os.path.realpath(child)
        parent_real = os.path.realpath(parent)
    except OSError:
        return False
    return child_real == parent_real or child_real.startswith(parent_real + os.sep)


def _projects_root() -> str:
    return os.path.join(resolve_studio_dir(), "projects")


def _final_path_allowed(source: str) -> bool:
    if not source or not source.lower().endswith(".mp4"):
        return False
    if not os.path.isfile(source):
        return False
    return _inside(source, _projects_root())


def find_final_mp4(slug: str) -> str:
    safe_slug = (slug or "").strip()
    if not safe_slug or safe_slug in (".", "..") or "/" in safe_slug or "\\" in safe_slug:
        return ""
    folder = os.path.join(_projects_root(), safe_slug, "output")
    if not _inside(folder, _projects_root()) or not os.path.isdir(folder):
        return ""
    candidates = []
    try:
        names = os.listdir(folder)
    except OSError:
        return ""
    for name in names:
        if name.lower().endswith(".mp4") and name.lower().startswith("final"):
            path = os.path.join(folder, name)
            if _final_path_allowed(path):
                candidates.append(path)
    if not candidates:
        return ""
    candidates.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    return candidates[0]


def _resolve_final_path(project_id: str, slug: str) -> str:
    render = {}
    try:
        payload = _studio_request("GET", f"/api/projects/{project_id}/render")
        if isinstance(payload, dict):
            render = payload
    except StudioUnavailable:
        render = {}
    for item in render.get("finals") or []:
        if (
            isinstance(item, dict)
            and item.get("path")
            and _final_path_allowed(str(item["path"]))
        ):
            return str(item["path"])
    return find_final_mp4(slug)


def _unique_output_name(slug: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", slug or "sarki").strip("._") or "sarki"
    base = base[:48]
    stem = f"cocuk_sarki_{base}"
    filename = f"{stem}.mp4"
    index = 2
    while os.path.exists(os.path.join(config.OUTPUT_DIR, filename)):
        filename = f"{stem}_{index}.mp4"
        index += 1
    return filename


def import_final_file(source: str, slug: str) -> dict:
    if not _final_path_allowed(source):
        return _fail("Final video stüdyo proje klasöründe değil.", 400)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    filename = _unique_output_name(slug)
    dest = os.path.join(config.OUTPUT_DIR, filename)
    if not _inside(dest, config.OUTPUT_DIR):
        return _fail("Galeri yolu geçersiz.", 400)
    try:
        os.link(source, dest)
        method = "hardlink"
    except OSError:
        shutil.copy2(source, dest)
        method = "copy"
    try:
        import database

        size_mb = round(os.path.getsize(dest) / (1024 * 1024), 2)
        with database.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO videos (keyword, title, status, filename, duration_seconds, size_mb, ai_provider, language, channel_slug)
                VALUES (?, ?, 'completed', ?, 0, ?, 'cocuk_sarki_flow', 'tr', 'cocuk_sarki')
                """,
                (slug or "cocuk_sarki", f"Çocuk Şarkısı - {slug}", filename, size_mb),
            )
            conn.commit()
    except Exception:
        pass
    return {"ok": True, "filename": filename, "url": f"/output/{filename}", "method": method}


def import_project_final(project_id: str) -> dict:
    current = project_status(project_id)
    if not current.get("ok"):
        return current
    project = current.get("project") or {}
    if not project.get("final_exists"):
        return _fail("Final video yok.", 404)
    source = _resolve_final_path(project_id, str(project.get("slug") or ""))
    if not source:
        return _fail("final.mp4 bulunamadı.", 404)
    imported = import_final_file(source, str(project.get("slug") or project_id))
    if imported.get("ok"):
        imported["project_id"] = project_id
    return imported


def create_kids_song_project(
    name: str,
    topic: str = "",
    age_group: str = "3-5",
    mood: str = "neşeli",
    lyrics: str = "",
    suno_prompt: str = "",
) -> dict:
    """
    Creates a new kids song project directly in the Next.js Prisma DB.
    Returns project summary with project slug and iframe navigation URL.
    """
    if not name:
        name = f"{topic or 'Yeni'} Şarkısı"

    payload = {
        "name": name[:120],
        "title": name[:120],
        "topic": topic or name,
        "genre": mood or "neşeli",
        "audience": f"{age_group} Yaş Grubu",
        "storyLanguage": "Turkish",
        "speechLanguage": "Turkish",
        "templateType": "kids_song",
        "targetDurationSeconds": 60,
        "clipSeconds": 5,
        "audioEnabled": True,
        "automationMode": "full",
        "allowSubtitles": True,
        "ageBand": age_group or "3-5",
    }

    try:
        res = _studio_request("POST", "/api/projects", body=payload)
        project_data = unwrap_studio_payload(res)
        slug = str((project_data or {}).get("slug") or "")
        proj_id = str((project_data or {}).get("id") or "")
        return {
            "ok": True,
            "project_id": proj_id,
            "slug": slug,
            "url": f"/cocuk-sarki/{slug or proj_id}",
            "full_url": f"{studio_url()}/cocuk-sarki/{slug or proj_id}",
            "message": f"'{name}' projesi stüdyoda oluşturuldu.",
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": f"Stüdyo isteği başarısız: {e}",
        }
