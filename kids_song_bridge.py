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

_LOCK = threading.Lock()
_PROC: Optional[subprocess.Popen] = None
_LAST_ERROR = ""


def studio_port() -> int:
    raw = os.getenv("KIDS_SONG_STUDIO_PORT", "3210").strip() or "3210"
    try:
        port = int(raw)
    except ValueError:
        port = 3210
    return port if 1 <= port <= 65535 else 3210


def studio_url() -> str:
    return f"http://127.0.0.1:{studio_port()}"


def detect_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:
        pass
    found = shutil.which("ffmpeg")
    if found:
        return found
    ms_pw = os.path.expanduser(r"~\AppData\Local\ms-playwright")
    if os.path.isdir(ms_pw):
        for root, _, files in os.walk(ms_pw):
            for f in files:
                if f.lower().startswith("ffmpeg") and f.lower().endswith(".exe"):
                    return os.path.join(root, f)
    return "ffmpeg"


def resolve_studio_dir() -> str:
    env = os.getenv("KIDS_SONG_STUDIO_DIR", "").strip()
    if env:
        return os.path.abspath(env)
    local_dir = os.path.abspath(os.path.join(config.BASE_DIR, "cocuk-sarki-bot-paylasim"))
    if os.path.isdir(local_dir):
        return local_dir
    parent_dir = os.path.abspath(os.path.join(config.BASE_DIR, "..", "cocuk-sarki-bot-paylasim"))
    if os.path.isdir(parent_dir):
        return parent_dir
    return local_dir


def _package_ok(directory: str) -> bool:
    return os.path.isfile(os.path.join(directory, "package.json"))


def _deps_ok(directory: str) -> bool:
    return os.path.isdir(os.path.join(directory, "node_modules"))


def port_open(port: Optional[int] = None, timeout: float = 0.4) -> bool:
    target = studio_port() if port is None else port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex(("127.0.0.1", target)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def _proc_alive() -> bool:
    return _PROC is not None and _PROC.poll() is None


def _log_path(directory: str) -> str:
    folder = os.path.join(directory, "logs")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "shorts-bridge.log")


def _tail(path: str, limit: int = 12) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return ""
    return "".join(lines[-limit:]).strip()


def status() -> dict:
    global _LAST_ERROR
    directory = resolve_studio_dir()
    installed = _package_ok(directory)
    deps = installed and _deps_ok(directory)
    alive = _proc_alive()
    if _PROC is not None and not alive and _PROC.returncode not in (0, None):
        _LAST_ERROR = f"Stüdyo süreci kapandı (kod {_PROC.returncode})."
    running = installed and port_open()
    message = ""
    if not installed:
        message = "Çocuk şarkı klasörü bulunamadı. KIDS_SONG_STUDIO_DIR yolunu kontrol edin."
    elif not deps:
        message = "Bağımlılık yok. Klasörde npm install, ardından npm run db:migrate çalıştırın."
    elif running:
        message = "Stüdyo ayakta."
        start_background_services()
    elif _LAST_ERROR:
        message = _LAST_ERROR
    log_file = os.path.join(directory, "logs", "shorts-bridge.log") if installed else ""
    return {
        "installed": installed,
        "dependencies": deps,
        "dir": directory,
        "running": running,
        "managed": alive,
        "url": studio_url(),
        "port": studio_port(),
        "message": message,
        "log_tail": _tail(log_file) if (installed and not running and _LAST_ERROR) else "",
    }


def start() -> dict:
    global _PROC, _LAST_ERROR
    current = status()
    if not current["installed"]:
        return {**current, "ok": False}
    if not current["dependencies"]:
        return {**current, "ok": False}
    if current["running"]:
        keys = transfer_keys()
        return {**current, "ok": True, "message": "Stüdyo zaten çalışıyor.", "keys": keys}
    # Seed a blank kids .env before spawn so the new process can read it.
    keys = transfer_keys()
    with _LOCK:
        if _proc_alive() or port_open():
            current = status()
            current["ok"] = True
            current["keys"] = keys
            return current
        directory = current["dir"]
        log_file = _log_path(directory)
        port = studio_port()
        command = "npm run dev" if port == 3210 else f"npx next dev -p {port}"
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP
        handle = open(log_file, "a", encoding="utf-8")
        try:
            _PROC = subprocess.Popen(
                command,
                cwd=directory,
                shell=True,
                stdout=handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=flags,
            )
            _LAST_ERROR = ""
        except OSError as exc:
            handle.close()
            _LAST_ERROR = str(exc)
            return {**status(), "ok": False, "message": _LAST_ERROR}
        finally:
            if not handle.closed:
                handle.close()
    started = status()
    started["ok"] = True
    started["message"] = "Stüdyo başlıyor. İlk açılış bir dakika sürebilir."
    started["keys"] = keys
    start_background_services()
    return started


_PREWARMED = False
_SYNC_RUNNING = False


def _prewarm_worker():
    global _PREWARMED
    if _PREWARMED:
        return
    for _ in range(30):
        if port_open():
            break
        import time; time.sleep(1)
    if not port_open():
        return
    routes = ["/cocuk-sarki", "/cocuk-sarki/yeni", "/flow-kalibrasyon", "/settings", "/api/projects"]
    for r in routes:
        try:
            req = urllib.request.Request(studio_url() + r, headers={"User-Agent": "ShortsPrewarmer/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp.read()
        except Exception:
            pass
    _PREWARMED = True


def _auto_sync_worker():
    global _SYNC_RUNNING
    import time
    while _SYNC_RUNNING:
        time.sleep(8)
        try:
            if not port_open():
                continue
            projects_data = list_projects()
            if not projects_data.get("ok"):
                continue
            for p in projects_data.get("projects", []):
                slug = str(p.get("slug") or "")
                final_path = find_final_mp4(slug)
                if final_path and os.path.isfile(final_path):
                    stem = f"cocuk_sarki_{slug}"
                    already = False
                    if os.path.isdir(config.OUTPUT_DIR):
                        for f in os.listdir(config.OUTPUT_DIR):
                            if f.startswith(stem) and f.endswith(".mp4"):
                                already = True
                                break
                    if not already:
                        import_final_file(final_path, slug)
        except Exception:
            pass


def start_background_services():
    global _SYNC_RUNNING
    threading.Thread(target=_prewarm_worker, daemon=True).start()
    if not _SYNC_RUNNING:
        _SYNC_RUNNING = True
        threading.Thread(target=_auto_sync_worker, daemon=True).start()


def generate_kids_song_idea(topic: str, age_group: str = "3-5", mood: str = "Neşeli") -> dict:
    safe_topic = (topic or "Sevimli Hayvanlar").strip()
    prompt = f"""
Sen profesyonel bir çocuk şarkısı yazarı ve müzik prodüktörüsün.
Aşağıdaki tema için 2-6 yaş çocuklara uygun, aşırı akılda kalıcı, ritmik, tekerleme tarzı neşeli bir Türkçe çocuk şarkısı ve prodüksiyon planı hazırla.

Tema / Konu: {safe_topic}
Yaş Grubu: {age_group}
Ruh Hali: {mood}

Yanıtını SADECE geçerli bir JSON objesi olarak ver, format şöyle olsun:
{{
  "title": "Şarkı Adı (Türkçe, kısa ve sevimli)",
  "topic": "{safe_topic}",
  "lyrics": "Tam şarkı sözleri (4-6 kıta, nakaratlı, eğlenceli ses efektleri 'cik cik', 'bip bip' içeren)",
  "suno_prompt": "English prompt for Suno AI music generator (e.g. Upbeat cheerful nursery rhyme, playful xylophone, acoustic guitar, sweet friendly female vocals, catchy pop melody, 120 bpm, high quality)",
  "character_description": "Pixar 3D animated cute friendly character description in English for Google Flow / Veo",
  "visual_style": "pixar3d"
}}
"""
    try:
        from google_ai_hub import generate_text
        ok, text = generate_text(prompt)
        if ok and text:
            clean = text.strip()
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-z]*\s*", "", clean)
                clean = re.sub(r"\s*```$", "", clean)
            parsed = json.loads(clean)
            return {"ok": True, "idea": parsed}
    except Exception:
        pass

    openai_key = _shorts_openai()
    if openai_key:
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }).encode("utf-8"),
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return {"ok": True, "idea": json.loads(content)}
        except Exception:
            pass

    fallback_title = f"{safe_topic} Şarkısı"
    fallback_lyrics = f"""(Giriş - Neşeli alkış ve zil sesleri)

{safe_topic}, bak ne güzel!
Güneş doğdu, bize güler!
Haydi kalk, sen de katıl,
Adım atıp neşeyle zıpla bir-iki-üç!

(Nakarat)
Lalala lalala neşeli dünya,
{safe_topic} bizimle burada!
El çırpalım şap şap şap,
Gülümse sen de tap tap tap!

(Kıta 2)
Renkli çiçekler, mutlu kuşlar,
Gökyüzünde dansa başlar!
Sevgi dolu kalbimizle,
Şarkı söyleriz hep birlikte!

(Bitiş)
Lalala la! En güzel gün bugün!"""

    return {
        "ok": True,
        "idea": {
            "title": fallback_title,
            "topic": safe_topic,
            "lyrics": fallback_lyrics,
            "suno_prompt": f"Upbeat cheerful nursery rhyme about {safe_topic}, playful xylophone, acoustic guitar, sweet female vocals, catchy rhythm, 120 bpm",
            "character_description": "Cute 3D Pixar style character smiling and playing, bright colorful lighting, clean animation render",
            "visual_style": "pixar3d"
        }
    }


def stop_managed() -> dict:
    global _PROC, _LAST_ERROR
    with _LOCK:
        proc = _PROC
        _PROC = None
    if proc is None or proc.poll() is not None:
        current = status()
        if current["running"]:
            current["ok"] = False
            current["message"] = "Port açık ama bu oturum süreci başlatmadı. Stüdyoyu elle kapatın."
            return current
        current["ok"] = True
        current["message"] = "Stüdyo kapalı."
        return current
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            text=True,
        )
    else:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    _LAST_ERROR = ""
    current = status()
    current["ok"] = True
    current["message"] = "Stüdyo durduruldu."
    return current


class StudioUnavailable(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


_PROJECT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_BLANK_SECRET = {
    "",
    "sk-...",
    "sk-…",
    "your-key",
    "your_api_key",
    "changeme",
    "change-me",
    "todo",
    "replace-me",
    "replace_me",
    "xxx",
    "paste-here",
    "api-key-here",
    "null",
    "none",
    "undefined",
}
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
        raise StudioUnavailable(_safe_error(str(payload.get("error") or "Stüdyo isteği başarısız.")))
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


def _studio_request(method: str, path: str, body: Optional[dict] = None, form: Optional[dict] = None, timeout: float = 12.0):
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
    request = urllib.request.Request(studio_url() + path, data=data, headers=headers, method=method)
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
    data = unwrap_studio_payload(payload) if isinstance(payload, dict) and "ok" in payload else payload
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
        render_payload = render_payload["data"] if isinstance(render_payload["data"], dict) else {}
    clips = project.get("clips") if isinstance(project.get("clips"), list) else []
    jobs = project.get("jobs") if isinstance(project.get("jobs"), list) else []
    finals = render_payload.get("finals") if isinstance(render_payload.get("finals"), list) else []
    final = next((item for item in finals if isinstance(item, dict) and item.get("path")), None)
    status_name = str(project.get("status") or "draft")
    running = any(
        isinstance(job, dict) and job.get("state") in ("running", "paused", "needs_manual_action")
        for job in jobs
    )
    clip_count = len(clips) if clips else int(project.get("clipCount") or project.get("clip_count") or 0)
    completed = (
        sum(1 for clip in clips if isinstance(clip, dict) and clip.get("status") == "completed")
        if clips
        else int(project.get("completedClipCount") or project.get("completed_clip_count") or 0)
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
            _studio_request("POST", f"/api/projects/{project_id}/song/upload-lyrics", form={"lyrics": text})
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
        if isinstance(item, dict) and item.get("path") and _final_path_allowed(str(item["path"])):
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
                (slug or "cocuk_sarki", f"Çocuk Şarkısı - {slug}", filename, size_mb)
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


def _shorts_openai() -> str:
    return (getattr(config, "OPENAI_API_KEY", "") or "").strip()


def _shorts_suno() -> str:
    value = getattr(config, "SUNO_API_KEY", "") or os.getenv("SUNO_API_KEY", "")
    return (value or "").strip()


def _is_blank_secret(value: Optional[str]) -> bool:
    if value is None:
        return True
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    if text.lower() in _BLANK_SECRET:
        return True
    if "..." in text and len(text) <= 16:
        return True
    return False


def _quote_env(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_env_key_if_blank(env_path: str, key: str, value: str) -> str:
    """Write key only when the source is set and the target line is empty or a placeholder."""
    if _is_blank_secret(value) or any(char in value for char in ("\n", "\r", "\x00")):
        return "skipped"
    lines = []
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    pattern = re.compile(rf"^(\s*){re.escape(key)}\s*=\s*(.*)$")
    assignments = []
    for index, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            assignments.append((index, match.group(2).strip()))
    if any(not _is_blank_secret(current) for _, current in assignments):
        return "unchanged"
    if assignments:
        lines[assignments[0][0]] = f"{key}={_quote_env(value)}"
    else:
        lines.append(f"{key}={_quote_env(value)}")
    folder = os.path.dirname(env_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(env_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + ("\n" if lines else ""))
    return "written"


def _remote_present(payload: dict, field: str) -> bool:
    info = payload.get(field)
    return isinstance(info, dict) and bool(info.get("present"))


def _env_key_status(key: str, value: str) -> str:
    directory = resolve_studio_dir()
    if not _package_ok(directory) and not os.path.isdir(directory):
        return "failed"
    try:
        return write_env_key_if_blank(os.path.join(directory, ".env"), key, value)
    except OSError:
        return "failed"


def _transfer_message(report: dict) -> str:
    openai_text = {
        "transferred": "OpenAI anahtarı stüdyoya aktarıldı.",
        "present": "Stüdyoda OpenAI anahtarı zaten var.",
        "written": "OpenAI anahtarı stüdyo .env dosyasına yazıldı.",
        "unchanged": "Stüdyo .env içinde OpenAI anahtarı duruyor, değiştirilmedi.",
        "skipped": "Bu uygulamada OpenAI anahtarı yok.",
        "failed": "OpenAI anahtarı aktarılamadı.",
    }
    suno_text = {
        "transferred": "Suno anahtarı stüdyoya aktarıldı.",
        "present": "Stüdyoda Suno anahtarı zaten var.",
        "written": "Suno anahtarı stüdyo .env dosyasına yazıldı.",
        "unchanged": "Stüdyo .env içinde Suno anahtarı duruyor, değiştirilmedi.",
        "absent": "Bu uygulamada Suno alanı yok.",
        "skipped": "Bu uygulamada Suno anahtarı yok.",
        "failed": "Suno anahtarı aktarılamadı.",
    }
    parts = [openai_text.get(report.get("openai"), ""), suno_text.get(report.get("suno"), "")]
    return " ".join(part for part in parts if part)


def transfer_keys() -> dict:
    """Copy non-empty shorts keys into the kids studio. Never return secret values."""
    report = {"ok": True, "openai": "skipped", "suno": "absent"}
    openai = _shorts_openai()
    suno = _shorts_suno()
    remote = None
    if port_open() and (openai or suno):
        try:
            payload = _studio_request("GET", "/api/settings")
            remote = payload if isinstance(payload, dict) else None
        except StudioUnavailable:
            remote = None
    if openai:
        if isinstance(remote, dict) and _remote_present(remote, "openaiKey"):
            report["openai"] = "present"
        elif isinstance(remote, dict):
            try:
                _studio_request(
                    "POST",
                    "/api/settings/openai",
                    body={"apiKey": openai, "storageMode": "encrypted"},
                )
                report["openai"] = "transferred"
            except StudioUnavailable:
                report["openai"] = _env_key_status("OPENAI_API_KEY", openai)
        else:
            report["openai"] = _env_key_status("OPENAI_API_KEY", openai)
    if suno:
        if isinstance(remote, dict) and _remote_present(remote, "sunoKey"):
            report["suno"] = "present"
        elif isinstance(remote, dict):
            suno_info = remote.get("sunoKey") if isinstance(remote.get("sunoKey"), dict) else {}
            model = str(suno_info.get("defaultModel") or "V4_5")[:40]
            try:
                _studio_request(
                    "PUT",
                    "/api/settings",
                    body={"sunoApiKey": suno, "sunoDefaultModel": model},
                )
                report["suno"] = "transferred"
            except StudioUnavailable:
                report["suno"] = _env_key_status("SUNO_API_KEY", suno)
        else:
            report["suno"] = _env_key_status("SUNO_API_KEY", suno)
    ffmpeg_exe = detect_ffmpeg()
    if ffmpeg_exe:
        _env_key_status("FFMPEG_PATH", ffmpeg_exe)
    report["message"] = _transfer_message(report)
    return report


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
            "message": f"'{name}' projesi stüdyoda oluşturuldu."
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": f"Stüdyo isteği başarısız: {e}"
        }

