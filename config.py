"""
YouTube Shorts Ultimate — Configuration
5 Video Sources | Multi-AI | TR+EN | Karaoke Subtitles
"""
import os, sys, re, platform
from typing import Dict, Optional

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from dotenv import load_dotenv
import PIL.Image

# Patch MoviePy PIL 10+ ANTIALIAS removal
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS

# Load environment variables from .env file
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
try:
    load_dotenv(_ENV_PATH)
except UnicodeDecodeError:
    print(
        "ERROR: .env is not valid UTF-8 text (wrong vault passphrase or corrupted file).\n"
        "  Fix: mv .env .env.corrupt.bak && python scripts/env_vault.py unseal --force",
        file=sys.stderr,
    )
    sys.exit(1)

# ══════════════════════════════════════════════════════════════
#  LANGUAGE — "tr" or "en"
# ══════════════════════════════════════════════════════════════
LANGUAGE = os.getenv("LANGUAGE", "tr")

# ══════════════════════════════════════════════════════════════
#  AI PROVIDERS — system auto-detects first available
# ══════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
# Google AI Pro / Gemini Developer — multimodal model slots
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
GEMINI_VIDEO_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "veo-3.1-fast-generate-preview")
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
# Default OFF — Pexels/Pixabay/Coverr/Mixkit/Videvo cover scenes; enable only if you want Nano Banana
USE_GEMINI_IMAGE_GEN = os.getenv("USE_GEMINI_IMAGE_GEN", "false").lower() in ("true", "1", "yes")
USE_GEMINI_VIDEO_GEN = os.getenv("USE_GEMINI_VIDEO_GEN", "false").lower() in ("true", "1", "yes")
# P3-31: explicit paid-quota confirm — prevents silent Veo burn on free tier / 429
GEMINI_VEO_PAID_QUOTA = os.getenv("GEMINI_VEO_PAID_QUOTA", "false").lower() in ("true", "1", "yes")
GEMINI_VEO_PREVIEW_ONLY = os.getenv("GEMINI_VEO_PREVIEW_ONLY", "true").lower() in ("true", "1", "yes")
USE_GEMINI_TTS = os.getenv("USE_GEMINI_TTS", "false").lower() in ("true", "1", "yes")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
USE_GEMINI_GROUNDING = os.getenv("USE_GEMINI_GROUNDING", "false").lower() in ("true", "1", "yes")
USE_GEMINI_EMBEDDINGS = os.getenv("USE_GEMINI_EMBEDDINGS", "false").lower() in ("true", "1", "yes")
PREFER_GEMINI_SCENE_IMAGES = os.getenv("PREFER_GEMINI_SCENE_IMAGES", "false").lower() in ("true", "1", "yes")
AUTO_FETCH_ROYALTY_FREE_BGM = os.getenv("AUTO_FETCH_ROYALTY_FREE_BGM", "true").lower() in ("true", "1", "yes")
YOUTUBE_DATA_API_KEY = os.getenv("YOUTUBE_DATA_API_KEY", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "YouTubeShortsStudio/1.0 (research workflow)")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_MODEL = "grok-4.20-reasoning"

# Item 113: AI Görsel Üretimi — FAL.ai + Stability AI
FAL_API_KEY = os.getenv("FAL_API_KEY", "") or os.getenv("FAL_KEY", "")  # fal.ai Wan/Hunyuan video
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")  # https://stability.ai API (SVD API deprecated)

# Free / freemium AI text-to-video providers (see RESEARCH_FREE_AI_VIDEO_APIS.md)
HF_TOKEN = os.getenv("HF_TOKEN", "") or os.getenv("HUGGINGFACE_TOKEN", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "") or os.getenv("REPLICATE_API_KEY", "")
DEEPINFRA_TOKEN = os.getenv("DEEPINFRA_TOKEN", "") or os.getenv("DEEPINFRA_API_KEY", "")
PIAPI_KEY = os.getenv("PIAPI_KEY", "") or os.getenv("PIAPI_API_KEY", "")
LOCAL_AI_VIDEO_URL = os.getenv("LOCAL_AI_VIDEO_URL", "")  # ComfyUI / self-host Wan proxy
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")  # optional paid Hailuo
MINIMAX_GROUP_ID = os.getenv("MINIMAX_GROUP_ID", "")
RUNWAYML_API_SECRET = (
    os.getenv("RUNWAYML_API_SECRET", "")
    or os.getenv("RUNWAY_API_KEY", "")
    or os.getenv("RUNWAY_API_SECRET", "")
)
LUMA_API_KEY = (
    os.getenv("LUMA_API_KEY", "")
    or os.getenv("LUMAAI_API_KEY", "")
    or os.getenv("LUMA_KEY", "")
)
USE_OPENAI_SORA = os.getenv("USE_OPENAI_SORA", "true").lower() not in ("0", "false", "no", "off")
AI_VIDEO_CLIP_MAX_SEC = float(os.getenv("AI_VIDEO_CLIP_MAX_SEC", "5") or 5)
AI_VIDEO_STYLE_PRESET = os.getenv("AI_VIDEO_STYLE_PRESET", "")  # kids_cartoon auto for niche 36

# Higgsfield Cloud (https://docs.higgsfield.ai) — KEY_ID:SECRET, NOT HF_TOKEN
# Prefer HIGGSFIELD_CREDENTIALS=id:secret OR the pair below
HIGGSFIELD_CREDENTIALS = (
    os.getenv("HIGGSFIELD_CREDENTIALS", "")
    or os.getenv("HIGGSFIELD_API_CREDENTIALS", "")
    or os.getenv("HF_CREDENTIALS", "")
)
HIGGSFIELD_API_KEY_ID = (
    os.getenv("HIGGSFIELD_API_KEY_ID", "")
    or os.getenv("HIGGSFIELD_KEY_ID", "")
    or os.getenv("HF_API_KEY_ID", "")
)
HIGGSFIELD_API_KEY_SECRET = (
    os.getenv("HIGGSFIELD_API_KEY_SECRET", "")
    or os.getenv("HIGGSFIELD_KEY_SECRET", "")
    or os.getenv("HF_API_KEY_SECRET", "")
)
HIGGSFIELD_T2V_MODEL = os.getenv(
    "HIGGSFIELD_T2V_MODEL",
    "bytedance/seedance-2.5/text-to-video",
)
HIGGSFIELD_BASE_URL = os.getenv("HIGGSFIELD_BASE_URL", "https://api.higgsfield.ai")
HIGGSFIELD_RESOLUTION = os.getenv("HIGGSFIELD_RESOLUTION", "720p")
HIGGSFIELD_GENERATE_AUDIO = os.getenv("HIGGSFIELD_GENERATE_AUDIO", "false").lower() in (
    "1", "true", "yes", "on",
)

# Visual mixer: AI + stock + procedural as equal peers (not fallback-only)
# Default USE_AI_VIDEO = true when any video key present (resolved at runtime)
USE_AI_VIDEO = os.getenv("USE_AI_VIDEO", "").lower()  # "", "true", "false"
VISUAL_MIX_AI = float(os.getenv("VISUAL_MIX_AI", "0.4") or 0.4)
VISUAL_MIX_STOCK = float(os.getenv("VISUAL_MIX_STOCK", "0.4") or 0.4)
VISUAL_MIX_PROCEDURAL = float(os.getenv("VISUAL_MIX_PROCEDURAL", "0.2") or 0.2)
VISUAL_MIX_SEED = os.getenv("VISUAL_MIX_SEED", "")

# ══════════════════════════════════════════════════════════════
#  VIDEO SOURCES — 5 free sources, all searched per scene
#  Priority: Pexels → Pixabay → Coverr → Mixkit → Videvo
# ══════════════════════════════════════════════════════════════
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
# Coverr, Mixkit, Videvo — no API key needed

# ══════════════════════════════════════════════════════════════
#  VIDEO SETTINGS
# ══════════════════════════════════════════════════════════════
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
MIN_DURATION = 60
MAX_DURATION = 120
SCENE_CLIP_MIN = 5
SCENE_CLIP_MAX = 10
FPS = 30
# Item 323: 60 FPS export for visual quality differentiation (default 30)
EXPORT_FPS_MODE = os.getenv("EXPORT_FPS_MODE", "30")  # "30" or "60"
MIN_RESOLUTION = 1080
RESULTS_PER_PAGE = 15

# Çözünürlük ve Hızlı Test Modları (1080p Final, 720p Hızlı HD, 540p Ultra Hızlı Test)
RESOLUTIONS = {
    "1080p": (1080, 1920),
    "720p": (720, 1280),
    "540p": (540, 960),
}
RENDER_RESOLUTION_MODE = os.getenv("RENDER_RESOLUTION_MODE", "1080p")

def get_target_resolution():
    mode = getattr(sys.modules[__name__], "RENDER_RESOLUTION_MODE", "1080p")
    return RESOLUTIONS.get(mode, (1080, 1920))

# ══════════════════════════════════════════════════════════════
#  RENDER SAFE MODE — Bilgisayar kapanma sorunlarını önler
#  True: Ağır per-frame Python efektleri devre dışı, FFmpeg tabanlı filtreler kullanılır
#  False: Tüm efektler aktif (güçlü PC gerektirir)
# ══════════════════════════════════════════════════════════════
RENDER_SAFE_MODE = os.getenv("RENDER_SAFE_MODE", "false").lower() in ("true", "1", "yes")

# Item 423: FFmpeg encode thread cap (PC donmasını önler; donanım profili override edebilir)
FFMPEG_THREADS = int(os.getenv("FFMPEG_THREADS", "4"))
# MoviePy / compose path thread budget (FFMPEG_THREADS ile hizalı varsayılan)
RENDER_THREADS = int(os.getenv("RENDER_THREADS", str(FFMPEG_THREADS)))

# NVIDIA RTX / NVENC (Windows) · VideoToolbox (macOS) · libx264 fallback (Item 73, 411)
USE_GPU_ACCELERATION = os.getenv("USE_GPU_ACCELERATION", "true").lower() in ("true", "1", "yes")

def _default_gpu_codec() -> str:
    if platform.system() == "Darwin":
        return "h264_videotoolbox"
    if platform.system() == "Windows":
        return "h264_nvenc"
    return "libx264"

GPU_CODEC = os.getenv("GPU_CODEC", "") or _default_gpu_codec()

# Item 74: FPS Mikro Çeşitlendirmesi (29.97, 30.00, 30.02, 30.05 fps anti-fingerprint)
FPS_DIVERSIFY = os.getenv("FPS_DIVERSIFY", "true").lower() in ("true", "1", "yes")

# Item 324: Talking portrait avatar (D-ID / SadTalker / LivePortrait — paid API, disabled by default)
AVATAR_ANIMATION_PROVIDER = os.getenv("AVATAR_ANIMATION_PROVIDER", "")  # did | sadtalker | liveportrait
AVATAR_ANIMATION_API_KEY = os.getenv("AVATAR_ANIMATION_API_KEY", "")

# ══════════════════════════════════════════════════════════════
#  VOICE — Edge TTS neural catalog (see tts_voices.py)
# ══════════════════════════════════════════════════════════════
from tts_voices import (
    resolve_voice,
    get_voice_catalog,
    EDGE_TTS_VOICE_CATALOG,
    is_elevenlabs_voice,
    is_valid_voice,
)

VOICES = {
    "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
    "en": {"male": "en-US-GuyNeural",   "female": "en-US-JennyNeural"},
}
TTS_GENDER = os.getenv("TTS_GENDER", "male")

def _sanitize_startup_voice(raw_voice: str, lang: str, gender: str) -> str:
    """Prefer locale-native Edge voice at startup (avoids stale fr-FR on Turkish content)."""
    lang = (lang or "tr").lower()
    if raw_voice and is_elevenlabs_voice(raw_voice):
        return raw_voice
    if raw_voice and is_valid_voice(raw_voice, lang):
        native_prefix = {"tr": "tr-TR-", "en": "en-"}.get(lang, "tr-TR-")
        if raw_voice.startswith(native_prefix) or raw_voice.startswith("elevenlabs:"):
            return raw_voice
        print(
            f"  [Config] TTS_VOICE={raw_voice} yerel dil ({lang}) ile uyumsuz; "
            f"yerel varsayilan kullaniliyor.",
            file=sys.stderr,
        )
    return resolve_voice(lang, gender=gender, prefer_native=True)

_env_tts_voice = os.getenv("TTS_VOICE", "")
TTS_VOICE = _sanitize_startup_voice(_env_tts_voice, LANGUAGE, TTS_GENDER) if _env_tts_voice else resolve_voice(LANGUAGE, gender=TTS_GENDER, prefer_native=True)
TTS_RATE = os.getenv("TTS_RATE", "+18%")
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz") or "+0Hz"

# ══════════════════════════════════════════════════════════════
#  DIRECTORIES
# ══════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
BGM_DIR = os.path.join(BASE_DIR, "bgm")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
KEYWORDS_FILE = os.path.join(BASE_DIR, "keywords.txt")
for d in [ASSETS_DIR, AUDIO_DIR, BGM_DIR, OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)


def slugify_channel(channel_id: Optional[str] = None) -> str:
    """P3-30: safe folder slug for per-channel assets/output."""
    raw = (channel_id or "default").strip()
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    safe = re.sub(r"[^\w\s-]", "", raw.translate(tr_map))
    safe = re.sub(r"\s+", "_", safe.strip()).lower()[:48]
    return safe or "default"


def channel_paths(channel_id: Optional[str] = None) -> Dict[str, str]:
    """P3-30: per-channel assets/output directories (Item 435)."""
    slug = slugify_channel(channel_id)
    if slug == "default":
        return {"slug": slug, "assets_dir": ASSETS_DIR, "output_dir": OUTPUT_DIR}
    assets = os.path.join(BASE_DIR, "assets", "channels", slug)
    output = os.path.join(BASE_DIR, "output", "channels", slug)
    for d in (assets, output):
        os.makedirs(d, exist_ok=True)
    return {"slug": slug, "assets_dir": assets, "output_dir": output}


def get_channel_output_dir(channel_id: Optional[str] = None) -> str:
    """Item 435 alias — per-channel isolated output directory."""
    return channel_paths(channel_id)["output_dir"]


# ══════════════════════════════════════════════════════════════
#  SUBTITLE & AUDIO STYLING DEFAULTS
# ══════════════════════════════════════════════════════════════
# Dashboard (settings_service) persists these to .env — read them back on startup
# so a restart does not silently reset the operator's choices.
def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default)) or default))
    except (TypeError, ValueError):
        return default


SUBTITLE_FONT_SIZE = _env_int("SUBTITLE_FONT_SIZE", 54)
SUBTITLE_COLOR = os.getenv("SUBTITLE_COLOR", "white") or "white"
SUBTITLE_HIGHLIGHT_COLOR = os.getenv("SUBTITLE_HIGHLIGHT_COLOR", "#FFD700") or "#FFD700"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 3
SUBTITLE_Y_POSITION = _env_float("SUBTITLE_Y_POSITION", 0.8)
ENABLE_BGM = os.getenv("ENABLE_BGM", "true").lower() in ("true", "1", "yes")
BGM_VOLUME = _env_float("BGM_VOLUME", 0.12)
DEFAULT_BGM_TRACK = os.getenv("DEFAULT_BGM_TRACK", "")

# Ses katmanları (Madde 154-155, 199 — yol haritasına uygun varsayılanlar)
ENABLE_SFX = os.getenv("ENABLE_SFX", "true").lower() in ("true", "1", "yes")
SFX_VOLUME = float(os.getenv("SFX_VOLUME", "0.20"))
# Madde 418: tek geçişli FFmpeg filter_complex (MoviePy fallback korunur)
ENABLE_FFMPEG_GRAPH = os.getenv("ENABLE_FFMPEG_GRAPH", "true").lower() in ("true", "1", "yes")
# DirectorPlan orchestration spine
ENABLE_DIRECTOR_PLAN = os.getenv("ENABLE_DIRECTOR_PLAN", "true").lower() in ("true", "1", "yes")
# P2-23: optional Whisper word-level subtitle alignment (stub — default off)
WHISPER_ALIGN = os.getenv("WHISPER_ALIGN", "false").lower() in ("true", "1", "yes")


# ══════════════════════════════════════════════════════════════
#  YOUTUBE PUBLISH SETTINGS
# ══════════════════════════════════════════════════════════════
YOUTUBE_AUTO_PUBLISH = False
YOUTUBE_PRIVACY = "private" # "public", "private", "unlisted"

# ══════════════════════════════════════════════════════════════
#  AUTO-DETECT AI (do not edit below)
# ══════════════════════════════════════════════════════════════
_P = [
    ("Gemini",   GEMINI_API_KEY,   "https://generativelanguage.googleapis.com/v1beta/openai/", GEMINI_MODEL),
    ("DeepSeek", DEEPSEEK_API_KEY, "https://api.deepseek.com",                                 DEEPSEEK_MODEL),
    ("OpenAI",   OPENAI_API_KEY,   "https://api.openai.com/v1",                                OPENAI_MODEL),
    ("Grok",     GROK_API_KEY,     "https://api.x.ai/v1",                                      GROK_MODEL),
]
AI_PROVIDER = AI_API_KEY = AI_BASE_URL = AI_MODEL = None
for n, k, u, m in _P:
    if k:
        AI_PROVIDER, AI_API_KEY, AI_BASE_URL, AI_MODEL = n, k, u, m
        break
if not AI_PROVIDER:
    AI_PROVIDER = "Yerel Fallback"
    AI_API_KEY = ""
    AI_BASE_URL = ""
    AI_MODEL = "procedural"
