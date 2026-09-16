"""
YouTube Shorts Ultimate — FastAPI Backend Server & SSE Live Streaming
"""
import os, sys, json, time, asyncio, shutil
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from scene_generator import generate_scenes
from video_fetcher import search_and_download, reset_used_videos
import threading
from tts_engine import generate_narration_with_timing
from video_composer import compose_video
from bgm_manager import list_bgm_tracks, get_bgm_path
import database

app = FastAPI(title="YouTube Shorts Ultimate Web Dashboard")

# Concurrency lock to prevent multiple heavy ffmpeg/moviepy renders simultaneously
render_lock = threading.Lock()
is_rendering_active = False

@app.on_event("startup")
def on_startup():
    database.cleanup_stale_tasks()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global queue for SSE event streaming
event_queues: List[asyncio.Queue] = []

# Persistent Render State across page refreshes
current_render_state = {
    "is_rendering": False,
    "percent": 0,
    "step": "Hazır",
    "keyword": "",
    "logs": [],
    "cancel_requested": False,
    "video_url": None,
    "error": None
}

def broadcast_event(event_type: str, data: Any):
    global current_render_state
    if event_type == "progress":
        if isinstance(data, dict):
            current_render_state["percent"] = data.get("percent", current_render_state["percent"])
            current_render_state["step"] = data.get("step", current_render_state["step"])
    elif event_type == "log":
        current_render_state["logs"].append(str(data))
        if len(current_render_state["logs"]) > 150:
            current_render_state["logs"] = current_render_state["logs"][-150:]
    elif event_type == "complete":
        current_render_state["is_rendering"] = False
        current_render_state["percent"] = 100
        current_render_state["step"] = "Tamamlandı!"
        if isinstance(data, dict):
            current_render_state["video_url"] = data.get("url")
    elif event_type == "error":
        current_render_state["is_rendering"] = False
        current_render_state["error"] = str(data)

    payload = json.dumps({"type": event_type, "data": data, "timestamp": time.time()})
    for q in list(event_queues):
        try:
            q.put_nowait(payload)
        except Exception:
            pass

class SSELogStreamer:
    """Redirects print statements to SSE queue."""
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
    def write(self, buf):
        self.original_stdout.write(buf)
        msg = buf.strip()
        if msg:
            broadcast_event("log", msg)
    def flush(self):
        self.original_stdout.flush()

# Models
class ConfigUpdateModel(BaseModel):
    language: Optional[str] = None
    tts_gender: Optional[str] = None
    tts_rate: Optional[str] = None
    tts_pitch: Optional[str] = None
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    grok_key: Optional[str] = None
    pexels_key: Optional[str] = None
    pixabay_key: Optional[str] = None
    subtitle_color: Optional[str] = None
    subtitle_highlight_color: Optional[str] = None
    subtitle_font_size: Optional[int] = None
    subtitle_y_position: Optional[float] = None
    enable_bgm: Optional[bool] = None
    bgm_volume: Optional[float] = None
    default_bgm_track: Optional[str] = None

class ScriptGenerateRequest(BaseModel):
    keyword: str
    language: Optional[str] = "en"

class VideoRenderRequest(BaseModel):
    keyword: str
    plan: Optional[Dict[str, Any]] = None
    language: Optional[str] = "en"
    voice_gender: Optional[str] = "male"
    bgm_track: Optional[str] = ""
    bgm_volume: Optional[float] = 0.12
    subtitle_highlight_color: Optional[str] = "#FFD700"
    subtitle_color: Optional[str] = "white"
    subtitle_font_size: Optional[int] = 54
    subtitle_y_position: Optional[float] = 0.8

# Endpoints
@app.get("/api/config")
def get_config():
    lang = config.LANGUAGE
    voice_dict = config.VOICES.get(lang, config.VOICES["en"])
    
    # Active sources
    srcs = ["Pexels"]
    if config.PIXABAY_API_KEY: srcs.append("Pixabay")
    srcs += ["Coverr", "Mixkit", "Videvo"]

    return {
        "language": config.LANGUAGE,
        "ai_provider": config.AI_PROVIDER,
        "ai_model": config.AI_MODEL,
        "tts_gender": config.TTS_GENDER,
        "tts_rate": config.TTS_RATE,
        "tts_pitch": config.TTS_PITCH,
        "voices": voice_dict,
        "active_sources": srcs,
        "keys": {
            "gemini": bool(config.GEMINI_API_KEY),
            "openai": bool(config.OPENAI_API_KEY),
            "deepseek": bool(config.DEEPSEEK_API_KEY),
            "grok": bool(config.GROK_API_KEY),
            "pexels": bool(config.PEXELS_API_KEY),
            "pixabay": bool(config.PIXABAY_API_KEY),
        },
        "subtitle": {
            "color": getattr(config, "SUBTITLE_COLOR", "white"),
            "highlight_color": getattr(config, "SUBTITLE_HIGHLIGHT_COLOR", "#FFD700"),
            "font_size": getattr(config, "SUBTITLE_FONT_SIZE", 54),
            "y_position": getattr(config, "SUBTITLE_Y_POSITION", 0.8),
        },
        "audio": {
            "enable_bgm": getattr(config, "ENABLE_BGM", True),
            "bgm_volume": getattr(config, "BGM_VOLUME", 0.12),
            "default_bgm_track": getattr(config, "DEFAULT_BGM_TRACK", ""),
        }
    }

@app.post("/api/config")
def update_config(data: ConfigUpdateModel):
    if data.language: config.LANGUAGE = data.language
    if data.tts_gender:
        config.TTS_GENDER = data.tts_gender
        config.TTS_VOICE = config.VOICES.get(config.LANGUAGE, config.VOICES["en"])[data.tts_gender]
    if data.tts_rate: config.TTS_RATE = data.tts_rate
    if data.tts_pitch: config.TTS_PITCH = data.tts_pitch

    if data.gemini_key is not None: config.GEMINI_API_KEY = data.gemini_key
    if data.openai_key is not None: config.OPENAI_API_KEY = data.openai_key
    if data.deepseek_key is not None: config.DEEPSEEK_API_KEY = data.deepseek_key
    if data.grok_key is not None: config.GROK_API_KEY = data.grok_key
    if data.pexels_key is not None: config.PEXELS_API_KEY = data.pexels_key
    if data.pixabay_key is not None: config.PIXABAY_API_KEY = data.pixabay_key

    if data.subtitle_color: config.SUBTITLE_COLOR = data.subtitle_color
    if data.subtitle_highlight_color: config.SUBTITLE_HIGHLIGHT_COLOR = data.subtitle_highlight_color
    if data.subtitle_font_size: config.SUBTITLE_FONT_SIZE = data.subtitle_font_size
    if data.subtitle_y_position: config.SUBTITLE_Y_POSITION = data.subtitle_y_position
    if data.enable_bgm is not None: config.ENABLE_BGM = data.enable_bgm
    if data.bgm_volume is not None: config.BGM_VOLUME = data.bgm_volume
    if data.default_bgm_track is not None: config.DEFAULT_BGM_TRACK = data.default_bgm_track

    # Re-detect AI provider
    for n, k, u, m in config._P:
        if k:
            config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL = n, k, u, m
            break

    return {"status": "ok", "message": "Configuration updated successfully"}

@app.get("/api/bgm/list")
def get_bgm_list():
    tracks = list_bgm_tracks()
    return {"tracks": tracks}

ALLOWED_BGM_EXTS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}

@app.post("/api/bgm/upload")
async def upload_bgm(file: UploadFile = File(...)):
    safe_name = os.path.basename(file.filename or "")
    ext = os.path.splitext(safe_name)[1].lower()
    if not safe_name or ext not in ALLOWED_BGM_EXTS:
        raise HTTPException(
            status_code=400, 
            detail=f"Desteklenmeyen dosya formatı ({ext}). Yalnızca MP3, WAV, M4A, AAC ve OGG kabul edilir."
        )
    os.makedirs(config.BGM_DIR, exist_ok=True)
    file_path = os.path.join(config.BGM_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "ok", "filename": safe_name}

from trending_scanner import scan_youtube_shorts_trends

@app.get("/api/trending/scan")
def api_scan_trending(topic: str = "Uzay", time_filter: str = "week", sort_by: str = "views", category: str = "all"):
    try:
        trends = scan_youtube_shorts_trends(topic, time_filter=time_filter, sort_by=sort_by, category=category)
        return {"status": "ok", "topic": topic, "trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/script/generate")
def api_generate_script(req: ScriptGenerateRequest):
    try:
        old_lang = config.LANGUAGE
        if req.language:
            config.LANGUAGE = req.language
        plan = generate_scenes(req.keyword)
        config.LANGUAGE = old_lang
        return {"status": "ok", "plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import database

def process_video_task(req: VideoRenderRequest):
    global is_rendering_active, current_render_state
    old_stdout = sys.stdout
    sys.stdout = SSELogStreamer(old_stdout)
    db_id = None
    orig_lang = config.LANGUAGE
    orig_voice = config.TTS_VOICE

    def check_cancelled():
        if current_render_state.get("cancel_requested"):
            raise InterruptedError("İşlem kullanıcı tarafından iptal edildi.")

    try:
        current_render_state["cancel_requested"] = False
        target_lang = (req.language or config.LANGUAGE or "tr").lower()
        config.LANGUAGE = target_lang

        gender = req.voice_gender or "male"
        voice_pool = config.VOICES.get(target_lang, config.VOICES.get("tr", {}))
        selected_voice = voice_pool.get(gender, "en-US-GuyNeural" if target_lang == "en" else "tr-TR-AhmetNeural")
        config.TTS_VOICE = selected_voice

        plan = req.plan
        keyword = (plan.get("title") if plan and plan.get("title") else req.keyword) or "Video"
        db_id = database.add_video_record(keyword, target_lang, config.AI_PROVIDER)
        broadcast_event("progress", {"percent": 5, "step": f"İşlem başlatılıyor: '{keyword}'..."})
        
        check_cancelled()

        # Safe directory and filename (ASCII converted for FFmpeg libass compatibility)
        import re
        tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
        safe = re.sub(r'[^\w\s-]', '', keyword.translate(tr_map))
        safe = re.sub(r'\s+', '_', safe.strip())[:80]
        if not safe:
            safe = f"shorts_{int(time.time())}"
        proj = os.path.join(config.ASSETS_DIR, safe)

        os.makedirs(proj, exist_ok=True)
        reset_used_videos()

        # Step 1: Scene plan
        check_cancelled()
        if not plan:
            lang_label = "İngilizce" if target_lang == "en" else "Türkçe"
            msg = f"[1/4] AI senaryosu oluşturuluyor ({lang_label} - {config.AI_PROVIDER}): '{keyword}'"
            print(msg)
            broadcast_event("log", msg)
            broadcast_event("progress", {"percent": 15, "step": msg})
            plan = generate_scenes(keyword)

        with open(os.path.join(proj, "plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

        if db_id and plan.get("scenes"):
            database.save_scenes(db_id, plan["scenes"])

        check_cancelled()

        # Step 2: Download videos
        msg = f"[2/4] Stok videolar aranıyor ve indiriliyor ({len(plan.get('scenes', []))} sahne)..."
        print(msg)
        broadcast_event("log", msg)
        broadcast_event("progress", {"percent": 30, "step": msg})
        clips = []
        scenes = plan.get("scenes", [])
        total_s = len(scenes)
        for i, scene in enumerate(scenes):
            check_cancelled()
            q = scene.get("search_queries", [scene.get("search_query", "nature")])
            d = scene.get("duration", 7)
            desc = scene.get("scene_description", "")
            
            progress_pct = 30 + int((i / max(1, total_s)) * 30)
            step_msg = f"Stok klip indiriliyor [{i+1}/{total_s}]: {desc[:40]}..."
            broadcast_event("progress", {"percent": progress_pct, "step": step_msg})
            broadcast_event("log", f"  -> Sahne {i+1}/{total_s}: {desc[:50]}")
            
            p = search_and_download(q, i, proj, target_duration=d, scene_description=desc)
            clips.append({"path": p, "duration": d, "narration": scene.get("narration","")})
            time.sleep(0.1)

        check_cancelled()

        ok_clips = sum(1 for c in clips if c["path"])
        broadcast_event("log", f"[2/4] Stok klip indirme tamamlandı: {ok_clips}/{total_s} klip hazır.")
        if ok_clips == 0:
            broadcast_event("error", "Stok video indirilemedi.")
            if db_id: database.update_video_status(db_id, "failed")
            return

        # Step 3: Narration TTS
        check_cancelled()
        lang_title = "İngilizce" if target_lang == "en" else "Türkçe"
        msg = f"[3/4] {lang_title} Seslendirme üretiliyor (Edge TTS - {config.TTS_VOICE})..."
        print(msg)
        broadcast_event("log", msg)
        broadcast_event("progress", {"percent": 65, "step": msg})
        audio_path = os.path.join(config.AUDIO_DIR, f"{safe}.wav")

        _, timings = generate_narration_with_timing(plan["full_narration"], audio_path)
        broadcast_event("log", f"[3/4] Seslendirme tamamlandı. {len(timings)} kelime zamanlaması çıkarıldı.")

        # Step 4: Video composition & SFX
        check_cancelled()
        msg = f"[4/4] Video birleştiriliyor, SFX ve Karaoke altyazılar işleniyor..."
        print(msg)
        broadcast_event("log", msg)
        broadcast_event("progress", {"percent": 80, "step": msg})
        output_file = os.path.join(config.OUTPUT_DIR, f"{safe}.mp4")

        sub_opts = {
            "color": req.subtitle_color,
            "highlight_color": req.subtitle_highlight_color,
            "font_size": req.subtitle_font_size,
            "y_position": req.subtitle_y_position,
        }

        def on_compose_progress(pct, step_text):
            broadcast_event("progress", {"percent": pct, "step": step_text})
            broadcast_event("log", f"  {step_text}")

        result = compose_video(
            clips, audio_path, timings, output_file, title=keyword,
            bgm_track=req.bgm_track, bgm_volume=req.bgm_volume,
            subtitle_opts=sub_opts,
            progress_callback=on_compose_progress,
            cancel_check=lambda: current_render_state.get("cancel_requested", False)
        )

        if result and os.path.exists(result) and os.path.getsize(result) > 100000:
            size_mb = round(os.path.getsize(result) / (1024*1024), 2)
            total_dur = sum(c["duration"] for c in clips)
            if db_id:
                database.update_video_status(db_id, "completed", os.path.basename(result), total_dur, size_mb)

            done_msg = f"🎉 Video üretimi tamamlandı! Dosya: {os.path.basename(result)} ({size_mb} MB, {total_dur:.1f}s)"
            print(done_msg)
            broadcast_event("log", done_msg)
            broadcast_event("progress", {"percent": 100, "step": "Video başarıyla tamamlandı!"})
            broadcast_event("complete", {
                "keyword": keyword,
                "filename": os.path.basename(result),
                "url": f"/output/{os.path.basename(result)}"
            })
        else:
            if db_id: 
                database.update_video_status(db_id, "failed", error_message="Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.")
            broadcast_event("error", "Video birleştirme tamamlanamadı.")

    except (InterruptedError, asyncio.CancelledError):
        cancel_msg = "⛔ Video üretimi kullanıcı tarafından iptal edildi."
        print(cancel_msg)
        broadcast_event("log", cancel_msg)
        broadcast_event("progress", {"percent": 0, "step": "İşlem İptal Edildi"})
        broadcast_event("error", cancel_msg)
        if db_id:
            database.update_video_status(db_id, "cancelled", error_message="Kullanıcı tarafından iptal edildi.")
    except Exception as e:
        if db_id: 
            database.update_video_status(db_id, "failed", error_message=str(e))
        broadcast_event("error", f"İşlem hatası: {str(e)}")
    finally:
        current_render_state["cancel_requested"] = False
        current_render_state["is_rendering"] = False
        is_rendering_active = False
        config.LANGUAGE = orig_lang
        config.TTS_VOICE = orig_voice
        sys.stdout = old_stdout


@app.post("/api/video/render")
def api_render_video(req: VideoRenderRequest, background_tasks: BackgroundTasks):
    global is_rendering_active
    with render_lock:
        if is_rendering_active:
            raise HTTPException(
                status_code=429, 
                detail="Şu anda arka planda aktif bir video render işlemi çalışıyor. Lütfen mevcut işlemin bitmesini bekleyin."
            )
        is_rendering_active = True

    background_tasks.add_task(process_video_task, req)
    return {"status": "started", "message": "Video rendering pipeline launched."}

@app.get("/api/events")
async def sse_events(request: Request):
    q = asyncio.Queue()
    event_queues.append(q)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f": keep-alive\n\n"
        finally:
            if q in event_queues:
                event_queues.remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/gallery")
def get_gallery():
    if not os.path.exists(config.OUTPUT_DIR):
        return {"videos": []}
    
    # Filter out temporary working files
    files = [f for f in os.listdir(config.OUTPUT_DIR) if f.lower().endswith(".mp4") and not f.lower().endswith("_tmp.mp4")]
    videos = []
    for f in sorted(files, key=lambda x: os.path.getmtime(os.path.join(config.OUTPUT_DIR, x)), reverse=True):
        fp = os.path.join(config.OUTPUT_DIR, f)
        mtime = os.path.getmtime(fp)
        size_mb = round(os.path.getsize(fp) / (1024*1024), 2)
        videos.append({
            "filename": f,
            "title": f.rsplit(".", 1)[0].replace("_", " "),
            "url": f"/output/{f}",
            "size_mb": size_mb,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        })
    return {"videos": videos}

@app.delete("/api/gallery/{filename}")
def delete_video(filename: str):
    safe_filename = os.path.basename(filename)
    fp = os.path.realpath(os.path.join(config.OUTPUT_DIR, safe_filename))
    out_dir_real = os.path.realpath(config.OUTPUT_DIR)

    # Path traversal check
    if not fp.startswith(out_dir_real) or not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="Video dosyası bulunamadı.")

    try:
        os.remove(fp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya silinemedi: {str(e)}")

    # Delete related ASS and SRT subtitle files if present
    base_no_ext = fp.rsplit(".", 1)[0]
    for sub_ext in [".ass", ".srt"]:
        sub_path = base_no_ext + sub_ext
        if os.path.exists(sub_path):
            try:
                os.remove(sub_path)
            except Exception:
                pass

    # Synchronize and remove from SQLite database
    database.delete_video_by_filename(safe_filename)

    return {"status": "ok", "message": "Video ve ilişkili dosyalar başarıyla silindi."}

@app.get("/api/status")
def get_render_status():
    global current_render_state, is_rendering_active
    current_render_state["is_rendering"] = is_rendering_active
    return current_render_state

@app.post("/api/video/cancel")
def cancel_render():
    global current_render_state, is_rendering_active
    if is_rendering_active:
        current_render_state["cancel_requested"] = True
        broadcast_event("log", "[Sistem] Kullanıcı tarafından render iptal isteği gönderildi.")
        return {"status": "ok", "message": "Render iptal isteği alındı."}
    return {"status": "ok", "message": "Aktif render bulunmuyor."}

@app.delete("/api/bgm/{filename}")
def delete_bgm_track(filename: str):
    safe_name = os.path.basename(filename)
    fp = os.path.realpath(os.path.join(config.BGM_DIR, safe_name))
    bgm_dir_real = os.path.realpath(config.BGM_DIR)
    if not fp.startswith(bgm_dir_real) or not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="Müzik dosyası bulunamadı.")
    try:
        os.remove(fp)
        return {"status": "ok", "message": f"{safe_name} silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/database/videos")
def get_database_videos():
    videos = database.get_recent_videos(100)
    stats = database.get_video_stats()
    return {"status": "ok", "videos": videos, "stats": stats}

class KeyTestRequest(BaseModel):
    provider: str
    api_key: str

@app.post("/api/keys/test")
def test_api_key(req: KeyTestRequest):
    p = req.provider.lower()
    k = req.api_key.strip()
    if not k:
        raise HTTPException(status_code=400, detail="API anahtarı boş olamaz.")
    
    try:
        import requests
        if p == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={k}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "Gemini API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"Gemini API hatası: HTTP {r.status_code}")
        elif p == "openai":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {k}"}, timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "OpenAI API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"OpenAI API hatası: HTTP {r.status_code}")
        elif p == "pexels":
            r = requests.get("https://api.pexels.com/v1/curated?per_page=1", headers={"Authorization": k}, timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "Pexels API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"Pexels API hatası: HTTP {r.status_code}")
        elif p == "pixabay":
            r = requests.get(f"https://pixabay.com/api/?key={k}&q=nature", timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "Pixabay API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"Pixabay API hatası: HTTP {r.status_code}")
        else:
            raise HTTPException(status_code=400, detail="Bilinmeyen sağlayıcı")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bağlantı hatası: {str(e)}")

# Serve BGM audio files for in-browser audio playback
if not os.path.exists(config.BGM_DIR):
    os.makedirs(config.BGM_DIR, exist_ok=True)
app.mount("/bgm_audio", StaticFiles(directory=config.BGM_DIR), name="bgm_audio")

# Serve output static directory
app.mount("/output", StaticFiles(directory=config.OUTPUT_DIR), name="output")

# Serve UI static files
STATIC_DIR = os.path.join(config.BASE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Web Dashboard is loading...</h2>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
