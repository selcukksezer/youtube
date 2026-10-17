"""Process lifecycle, background sync workers, env key transfer, and AI song idea generator for Çocuk Şarkı studio."""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import urllib.request
from typing import Any, Optional

import config


def _kb_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("kids_song_bridge")
    return getattr(mod, name, default) if mod is not None else default


def _kb_set(name: str, value: Any) -> None:
    mod = sys.modules.get("kids_song_bridge")
    if mod is not None:
        setattr(mod, name, value)


_BLANK_SECRET = {
    "", "sk-...", "sk-…", "your-key", "your_api_key", "changeme", "change-me",
    "todo", "replace-me", "replace_me", "xxx", "paste-here", "api-key-here",
    "null", "none", "undefined",
}


def studio_port() -> int:
    raw = os.getenv("KIDS_SONG_STUDIO_PORT", "3210").strip() or "3210"
    try:
        port = int(raw)
    except ValueError:
        port = 3210
    return port if 1 <= port <= 65535 else 3210


def studio_url() -> str:
    port_fn = _kb_attr("studio_port", studio_port)
    return f"http://127.0.0.1:{port_fn()}"


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
    cfg = _kb_attr("config", config)
    local_dir = os.path.abspath(os.path.join(cfg.BASE_DIR, "cocuk-sarki-bot-paylasim"))
    if os.path.isdir(local_dir):
        return local_dir
    parent_dir = os.path.abspath(os.path.join(cfg.BASE_DIR, "..", "cocuk-sarki-bot-paylasim"))
    if os.path.isdir(parent_dir):
        return parent_dir
    return local_dir


def _package_ok(directory: str) -> bool:
    return os.path.isfile(os.path.join(directory, "package.json"))


def _deps_ok(directory: str) -> bool:
    return os.path.isdir(os.path.join(directory, "node_modules"))


def port_open(port: Optional[int] = None, timeout: float = 0.4) -> bool:
    port_fn = _kb_attr("studio_port", studio_port)
    sock_mod = _kb_attr("socket", socket)
    target = port_fn() if port is None else port
    sock = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex(("127.0.0.1", target)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def _proc_alive() -> bool:
    proc = _kb_attr("_PROC", None)
    return proc is not None and proc.poll() is None


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
    resolve_fn = _kb_attr("resolve_studio_dir", resolve_studio_dir)
    pkg_fn = _kb_attr("_package_ok", _package_ok)
    deps_fn = _kb_attr("_deps_ok", _deps_ok)
    alive_fn = _kb_attr("_proc_alive", _proc_alive)
    port_open_fn = _kb_attr("port_open", port_open)
    bg_fn = _kb_attr("start_background_services", start_background_services)
    url_fn = _kb_attr("studio_url", studio_url)
    port_fn = _kb_attr("studio_port", studio_port)

    directory = resolve_fn()
    installed = pkg_fn(directory)
    deps = installed and deps_fn(directory)
    alive = alive_fn()
    proc = _kb_attr("_PROC", None)
    last_error = _kb_attr("_LAST_ERROR", "")
    if proc is not None and not alive and proc.returncode not in (0, None):
        last_error = f"Stüdyo süreci kapandı (kod {proc.returncode})."
        _kb_set("_LAST_ERROR", last_error)
    running = installed and port_open_fn()
    message = ""
    if not installed:
        message = "Çocuk şarkı klasörü bulunamadı. KIDS_SONG_STUDIO_DIR yolunu kontrol edin."
    elif not deps:
        message = "Bağımlılık yok. Klasörde npm install, ardından npm run db:migrate çalıştırın."
    elif running:
        message = "Stüdyo ayakta."
        bg_fn()
    elif last_error:
        message = last_error
    log_file = os.path.join(directory, "logs", "shorts-bridge.log") if installed else ""
    return {
        "installed": installed, "dependencies": deps, "dir": directory,
        "running": running, "managed": alive, "url": url_fn(), "port": port_fn(),
        "message": message,
        "log_tail": _tail(log_file) if (installed and not running and last_error) else "",
    }


def start() -> dict:
    status_fn = _kb_attr("status", status)
    transfer_fn = _kb_attr("transfer_keys", transfer_keys)
    alive_fn = _kb_attr("_proc_alive", _proc_alive)
    port_open_fn = _kb_attr("port_open", port_open)
    port_fn = _kb_attr("studio_port", studio_port)
    bg_fn = _kb_attr("start_background_services", start_background_services)
    subproc = _kb_attr("subprocess", subprocess)
    lock = _kb_attr("_LOCK", threading.Lock())

    current = status_fn()
    if not current["installed"] or not current["dependencies"]:
        return {**current, "ok": False}
    if current["running"]:
        keys = transfer_fn()
        return {**current, "ok": True, "message": "Stüdyo zaten çalışıyor.", "keys": keys}
    keys = transfer_fn()
    with lock:
        if alive_fn() or port_open_fn():
            current = status_fn()
            return {**current, "ok": True, "keys": keys}
        directory = current["dir"]
        log_file = _log_path(directory)
        port = port_fn()
        command = "npm run dev" if port == 3210 else f"npx next dev -p {port}"
        flags = subproc.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        handle = open(log_file, "a", encoding="utf-8")
        try:
            proc = subproc.Popen(
                command, cwd=directory, shell=True, stdout=handle,
                stderr=subproc.STDOUT, stdin=subproc.DEVNULL, creationflags=flags,
            )
            _kb_set("_PROC", proc)
            _kb_set("_LAST_ERROR", "")
        except OSError as exc:
            handle.close()
            err_str = str(exc)
            _kb_set("_LAST_ERROR", err_str)
            return {**status_fn(), "ok": False, "message": err_str}
        finally:
            if not handle.closed:
                handle.close()
    started = status_fn()
    started["ok"] = True
    started["message"] = "Stüdyo başlıyor. İlk açılış bir dakika sürebilir."
    started["keys"] = keys
    bg_fn()
    return started


def _prewarm_worker():
    if _kb_attr("_PREWARMED", False):
        return
    port_open_fn = _kb_attr("port_open", port_open)
    url_fn = _kb_attr("studio_url", studio_url)
    for _ in range(30):
        if port_open_fn():
            break
        import time

        time.sleep(1)
    if not port_open_fn():
        return
    for r in ["/cocuk-sarki", "/cocuk-sarki/yeni", "/flow-kalibrasyon", "/settings", "/api/projects"]:
        try:
            req = urllib.request.Request(url_fn() + r, headers={"User-Agent": "ShortsPrewarmer/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp.read()
        except Exception:
            pass
    _kb_set("_PREWARMED", True)


def _auto_sync_worker():
    import time

    while _kb_attr("_SYNC_RUNNING", False):
        time.sleep(8)
        try:
            if not _kb_attr("port_open", port_open)():
                continue
            list_fn = _kb_attr("list_projects", None)
            if list_fn is None:
                continue
            projects_data = list_fn()
            if not projects_data.get("ok"):
                continue
            find_fn = _kb_attr("find_final_mp4", None)
            import_fn = _kb_attr("import_final_file", None)
            cfg = _kb_attr("config", config)
            for p in projects_data.get("projects", []):
                slug = str(p.get("slug") or "")
                final_path = find_fn(slug) if find_fn else ""
                if final_path and os.path.isfile(final_path):
                    stem = f"cocuk_sarki_{slug}"
                    already = os.path.isdir(cfg.OUTPUT_DIR) and any(
                        f.startswith(stem) and f.endswith(".mp4") for f in os.listdir(cfg.OUTPUT_DIR)
                    )
                    if not already and import_fn:
                        import_fn(final_path, slug)
        except Exception:
            pass


def start_background_services():
    threading.Thread(target=_kb_attr("_prewarm_worker", _prewarm_worker), daemon=True).start()
    if not _kb_attr("_SYNC_RUNNING", False):
        _kb_set("_SYNC_RUNNING", True)
        threading.Thread(target=_kb_attr("_auto_sync_worker", _auto_sync_worker), daemon=True).start()


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
            return {"ok": True, "idea": json.loads(clean)}
    except Exception:
        pass

    openai_key = _kb_attr("_shorts_openai", _shorts_openai)()
    if openai_key:
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                }).encode("utf-8"),
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"ok": True, "idea": json.loads(data["choices"][0]["message"]["content"])}
        except Exception:
            pass

    fallback_lyrics = (
        f"(Giriş - Neşeli alkış ve zil sesleri)\n\n{safe_topic}, bak ne güzel!\n"
        f"Güneş doğdu, bize güler!\nHaydi kalk, sen de katıl,\nAdım atıp neşeyle zıpla bir-iki-üç!\n\n"
        f"(Nakarat)\nLalala lalala neşeli dünya,\n{safe_topic} bizimle burada!\n"
        f"El çırpalım şap şap şap,\nGülümse sen de tap tap tap!\n\n"
        f"(Kıta 2)\nRenkli çiçekler, mutlu kuşlar,\nGökyüzünde dansa başlar!\n"
        f"Sevgi dolu kalbimizle,\nŞarkı söyleriz hep birlikte!\n\n(Bitiş)\nLalala la! En güzel gün bugün!"
    )
    return {
        "ok": True,
        "idea": {
            "title": f"{safe_topic} Şarkısı",
            "topic": safe_topic,
            "lyrics": fallback_lyrics,
            "suno_prompt": f"Upbeat cheerful nursery rhyme about {safe_topic}, playful xylophone, acoustic guitar, sweet female vocals, catchy rhythm, 120 bpm",
            "character_description": "Cute 3D Pixar style character smiling and playing, bright colorful lighting, clean animation render",
            "visual_style": "pixar3d",
        },
    }


def stop_managed() -> dict:
    status_fn = _kb_attr("status", status)
    subproc = _kb_attr("subprocess", subprocess)
    lock = _kb_attr("_LOCK", threading.Lock())
    with lock:
        proc = _kb_attr("_PROC", None)
        _kb_set("_PROC", None)
    if proc is None or proc.poll() is not None:
        current = status_fn()
        if current["running"]:
            return {**current, "ok": False, "message": "Port açık ama bu oturum süreci başlatmadı. Stüdyoyu elle kapatın."}
        return {**current, "ok": True, "message": "Stüdyo kapalı."}
    if sys.platform == "win32":
        subproc.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, text=True)
    else:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subproc.TimeoutExpired:
            proc.kill()
    _kb_set("_LAST_ERROR", "")
    return {**status_fn(), "ok": True, "message": "Stüdyo durduruldu."}


def _shorts_openai() -> str:
    cfg = _kb_attr("config", config)
    return (getattr(cfg, "OPENAI_API_KEY", "") or "").strip()


def _shorts_suno() -> str:
    cfg = _kb_attr("config", config)
    value = getattr(cfg, "SUNO_API_KEY", "") or os.getenv("SUNO_API_KEY", "")
    return (value or "").strip()


def _is_blank_secret(value: Optional[str]) -> bool:
    if value is None:
        return True
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    return text.lower() in _BLANK_SECRET or ("..." in text and len(text) <= 16)


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
    assignments = [
        (idx, pattern.match(line).group(2).strip())
        for idx, line in enumerate(lines)
        if not line.lstrip().startswith("#") and pattern.match(line)
    ]
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
    resolve_fn = _kb_attr("resolve_studio_dir", resolve_studio_dir)
    pkg_fn = _kb_attr("_package_ok", _package_ok)
    write_fn = _kb_attr("write_env_key_if_blank", write_env_key_if_blank)
    directory = resolve_fn()
    if not pkg_fn(directory) and not os.path.isdir(directory):
        return "failed"
    try:
        return write_fn(os.path.join(directory, ".env"), key, value)
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
    openai = _kb_attr("_shorts_openai", _shorts_openai)()
    suno = _kb_attr("_shorts_suno", _shorts_suno)()
    port_open_fn = _kb_attr("port_open", port_open)
    req_fn = _kb_attr("_studio_request", None)
    exc_cls = _kb_attr("StudioUnavailable", Exception)
    env_status_fn = _kb_attr("_env_key_status", _env_key_status)
    ffmpeg_fn = _kb_attr("detect_ffmpeg", detect_ffmpeg)

    report = {"ok": True, "openai": "skipped", "suno": "absent"}
    remote = None
    if port_open_fn() and (openai or suno) and req_fn is not None:
        try:
            payload = req_fn("GET", "/api/settings")
            remote = payload if isinstance(payload, dict) else None
        except exc_cls:
            remote = None
    if openai:
        if isinstance(remote, dict) and _remote_present(remote, "openaiKey"):
            report["openai"] = "present"
        elif isinstance(remote, dict) and req_fn is not None:
            try:
                req_fn("POST", "/api/settings/openai", body={"apiKey": openai, "storageMode": "encrypted"})
                report["openai"] = "transferred"
            except exc_cls:
                report["openai"] = env_status_fn("OPENAI_API_KEY", openai)
        else:
            report["openai"] = env_status_fn("OPENAI_API_KEY", openai)
    if suno:
        if isinstance(remote, dict) and _remote_present(remote, "sunoKey"):
            report["suno"] = "present"
        elif isinstance(remote, dict) and req_fn is not None:
            suno_info = remote.get("sunoKey") if isinstance(remote.get("sunoKey"), dict) else {}
            model = str(suno_info.get("defaultModel") or "V4_5")[:40]
            try:
                req_fn("PUT", "/api/settings", body={"sunoApiKey": suno, "sunoDefaultModel": model})
                report["suno"] = "transferred"
            except exc_cls:
                report["suno"] = env_status_fn("SUNO_API_KEY", suno)
        else:
            report["suno"] = env_status_fn("SUNO_API_KEY", suno)
    ffmpeg_exe = ffmpeg_fn()
    if ffmpeg_exe:
        env_status_fn("FFMPEG_PATH", ffmpeg_exe)
    report["message"] = _transfer_message(report)
    return report
