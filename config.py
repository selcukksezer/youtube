"""
YouTube Shorts Ultimate — Configuration
5 Video Sources | Multi-AI | TR+EN | Karaoke Subtitles
"""
import os, sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ══════════════════════════════════════════════════════════════
#  LANGUAGE — "tr" or "en"
# ══════════════════════════════════════════════════════════════
LANGUAGE = os.getenv("LANGUAGE", "tr")

# ══════════════════════════════════════════════════════════════
#  AI PROVIDERS — system auto-detects first available
# ══════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6KobsFbKVec2KT1-5ISCAiwed5RT5rPtYswk63jUQOO8A")
GEMINI_MODEL = "gemini-flash-lite-latest"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_MODEL = "grok-4.20-reasoning"

# ══════════════════════════════════════════════════════════════
#  VIDEO SOURCES — 5 free sources, all searched per scene
#  Priority: Pexels → Pixabay → Coverr → Mixkit → Videvo
# ══════════════════════════════════════════════════════════════
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "rtGk7Pf9B7UP6iPJFYV1RDHcWftw3eRPTPIWoWXcQKYELCmouL563OU7")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "42780571-e48f71c3638f7c1d222c78ed7")
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
MIN_RESOLUTION = 1080
RESULTS_PER_PAGE = 15

# ══════════════════════════════════════════════════════════════
#  VOICE
# ══════════════════════════════════════════════════════════════
VOICES = {
    "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
    "en": {"male": "en-US-GuyNeural",   "female": "en-US-JennyNeural"},
}
TTS_GENDER = "male"
TTS_RATE = "+5%"
TTS_PITCH = "+0Hz"
TTS_VOICE = VOICES.get(LANGUAGE, VOICES["tr"])[TTS_GENDER]

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

# ══════════════════════════════════════════════════════════════
#  SUBTITLE & AUDIO STYLING DEFAULTS
# ══════════════════════════════════════════════════════════════
SUBTITLE_FONT_SIZE = 54
SUBTITLE_COLOR = "white"
SUBTITLE_HIGHLIGHT_COLOR = "#FFD700"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 3
SUBTITLE_Y_POSITION = 0.8
ENABLE_BGM = True
BGM_VOLUME = 0.12
DEFAULT_BGM_TRACK = ""


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
    print("ERROR: No AI API key set!"); sys.exit(1)
